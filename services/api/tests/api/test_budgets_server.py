"""Immediate reads after login over real TCP/uvicorn, beyond TestClient."""

import os
import socket
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

import httpx
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from api.conftest import PASSWORD
from monetae.config import Settings
from monetae.db.models import (
    Account,
    Budget,
    BudgetCategory,
    BudgetTransaction,
    Category,
    LoginAttempt,
    Transaction,
    User,
)
from monetae.db.models import Session as LoginSession
from monetae.services.auth import AuthService, SystemClock


def test_login_then_immediate_budget_requests_with_uvicorn(
    database_url: str,
    db_engine: Engine,
) -> None:
    settings = Settings(environment="test", database_url=database_url, cookie_secure=False)
    email = f"budget-probe-{uuid4().hex}@example.test"
    with Session(db_engine) as db:
        user = AuthService(db, settings, SystemClock()).create_user(email, PASSWORD)
        user_id = user.id
        db.commit()
    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]
    environment = {
        **os.environ,
        "MONETAE_DATABASE_URL": database_url,
        "MONETAE_ENVIRONMENT": "test",
        "MONETAE_COOKIE_SECURE": "false",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "monetae.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5) as client:
            deadline = monotonic() + 15
            while True:
                assert process.poll() is None, "uvicorn exited before readiness"
                try:
                    health = client.get("/api/v1/health")
                    if health.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert monotonic() < deadline, "uvicorn readiness timed out"
                sleep(0.05)
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "method": "password",
                    "email": email,
                    "password": PASSWORD,
                },
                headers={
                    "Origin": f"http://127.0.0.1:{port}",
                    "X-CSRF-Token": client.cookies["monetae_csrf"],
                },
            )
            assert response.status_code == 200, response.text
            headers = {
                "Origin": f"http://127.0.0.1:{port}",
                "X-CSRF-Token": client.cookies["monetae_csrf"],
            }
            account = client.post(
                "/api/v1/accounts",
                json={
                    "name": "Probe wallet",
                    "type": "cash",
                    "currency": "PEN",
                    "initial_balance": "0.00",
                },
                headers=headers,
            )
            assert account.status_code == 201, account.text
            transaction = client.post(
                "/api/v1/transactions",
                json={
                    "account_id": account.json()["id"],
                    "kind": "expense",
                    "currency": "PEN",
                    "amount": "-12.50",
                    "occurred_at": SystemClock().now().isoformat(),
                    "status": "posted",
                    "title": "Synthetic probe purchase",
                    "fx_rate_to_base": "1.000000",
                    "fx_rate_source": "manual",
                },
                headers=headers,
            )
            assert transaction.status_code == 201, transaction.text
            response = client.post(
                "/api/v1/budgets",
                json={
                    "name": "Probe budget",
                    "period": "monthly",
                    "start_on": "2026-01-01",
                    "amount": "100.00",
                    "currency": "PEN",
                    "scope": "all",
                },
                headers=headers,
            )
            assert response.status_code == 201, response.text
            assert response.json()["spent_amount"] == "12.50"
            listed = client.get("/api/v1/budgets")
            assert listed.status_code == 200, listed.text
            assert listed.json()["items"][0]["spent_amount"] == "12.50"
            print("uvicorn+httpx: login 200 -> expense 201 -> budget 201 -> list 200; spent=12.50")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        # This probe commits real HTTP requests; remove only its synthetic seed so
        # later tests (including the global login-attempt purge) remain isolated.
        with Session(db_engine) as db:
            for model in (
                BudgetTransaction,
                BudgetCategory,
                Budget,
                Transaction,
                Account,
                Category,
                LoginSession,
            ):
                db.execute(delete(model).where(model.user_id == user_id))
            db.execute(delete(LoginAttempt).where(LoginAttempt.email_lower == email))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
