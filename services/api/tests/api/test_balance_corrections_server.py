"""Correction commit, idempotency and rollback over real TCP/uvicorn."""

import os
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from uuid import uuid4

import httpx
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from api.conftest import PASSWORD
from monetae.config import Settings
from monetae.db.models import Account, Category, IdempotencyKey, LoginAttempt, Transaction, User
from monetae.db.models import Session as LoginSession
from monetae.services.auth import AuthService, SystemClock


def test_correction_committed_pair_and_rollback_with_uvicorn(
    database_url: str,
    db_engine: Engine,
) -> None:
    settings = Settings(environment="test", database_url=database_url, cookie_secure=False)
    email = f"correction-probe-{uuid4().hex}@example.test"
    with Session(db_engine) as db:
        user = AuthService(db, settings, SystemClock()).create_user(email, PASSWORD)
        outgoing = Account(user_id=user.id, name="USD probe", type="cash", currency="USD")
        incoming = Account(user_id=user.id, name="PEN probe", type="cash", currency="PEN")
        db.add_all([outgoing, incoming])
        db.flush()
        from_id, to_id = str(outgoing.id), str(incoming.id)
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
                "Idempotency-Key": "real-server-pair",
            }
            now = datetime.now(UTC)
            payload = {
                "from_account_id": from_id,
                "to_account_id": to_id,
                "from_amount": "10.00",
                "to_amount": "38.00",
                "from_fx_rate_to_base": "3.800000",
                "to_fx_rate_to_base": "1.000000",
                "fx_rate_source": "manual",
                "occurred_at": now.isoformat(),
                "to_occurred_at": (now + timedelta(days=1)).isoformat(),
            }
            response = client.post("/api/v1/balance-corrections", json=payload, headers=headers)
            assert response.status_code == 201, response.text
            pair = response.json()
            assert pair["outgoing"]["status"] == "posted"
            assert pair["incoming"]["status"] == "scheduled"
            assert (
                client.post("/api/v1/balance-corrections", json=payload, headers=headers).json()
                == pair
            )
            with Session(db_engine) as db:
                rows = list(db.scalars(select(Transaction).where(Transaction.user_id == user_id)))
                assert len(rows) == 2 and {r.kind for r in rows} == {"expense", "income"}
            response = client.get("/api/v1/balance-corrections")
            assert response.status_code == 200, response.text
            assert response.json()["items"][0]["group_id"] == pair["group_id"]
            assert response.json()["items"][0]["implicit_rate"] == "3.800000"
            failed = client.post(
                "/api/v1/balance-corrections",
                json={**payload, "to_fx_rate_to_base": "2.000000"},
                headers={**headers, "Idempotency-Key": "real-server-invalid"},
            )
            assert failed.status_code == 422, failed.text
            with Session(db_engine) as db:
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Transaction)
                        .where(Transaction.user_id == user_id)
                    )
                    == 2
                )
            assert (
                client.delete(
                    f"/api/v1/transactions/{pair['outgoing']['id']}", headers=headers
                ).status_code
                == 200
            )
            assert client.get("/api/v1/balance-corrections").json()["items"] == []
            assert client.get(f"/api/v1/transactions/{pair['incoming']['id']}").status_code == 200
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
            db.execute(delete(IdempotencyKey).where(IdempotencyKey.user_id == user_id))
            db.execute(delete(Transaction).where(Transaction.user_id == user_id))
            db.execute(delete(Account).where(Account.user_id == user_id))
            db.execute(delete(Category).where(Category.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
