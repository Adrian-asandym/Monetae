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
from monetae.db.models import Account, Category, LoginAttempt, User
from monetae.db.models import Session as LoginSession
from monetae.services.auth import AuthService, SystemClock


def test_login_then_immediate_home_requests_with_uvicorn(
    database_url: str,
    db_engine: Engine,
) -> None:
    settings = Settings(environment="test", database_url=database_url, cookie_secure=False)
    email = f"report-probe-{uuid4().hex}@example.test"
    with Session(db_engine) as db:
        user = AuthService(db, settings, SystemClock()).create_user(email, PASSWORD)
        db.add(Account(user_id=user.id, name="Probe account", type="cash", currency="PEN"))
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
            assert response.json()["user"]["preferences"]["default_account_id"] is None
            response = client.get("/api/v1/accounts")
            assert response.status_code == 200, response.text
            assert response.json()["items"][0]["transaction_count"] == 0
            print("uvicorn probe: login -> accounts = 200 with transaction_count")
            response = client.get("/api/v1/reports/cash-flow")
            assert response.status_code == 200, response.text
            assert all(
                row["cumulative_net"]["report_amount"] == "0.00" for row in response.json()["items"]
            )
            print("uvicorn probe: login -> cash-flow = 200 with cumulative_net")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        # TCP requests commit outside db_session's savepoint. Remove this probe's
        # fixtures, especially attempts using SystemClock, before FakeClock tests.
        with Session(db_engine) as db:
            db.execute(delete(LoginAttempt).where(LoginAttempt.email_lower == email))
            db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
            db.execute(delete(Account).where(Account.user_id == user_id))
            db.execute(delete(Category).where(Category.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
