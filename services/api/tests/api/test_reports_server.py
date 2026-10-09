"""Immediate reads after login over real TCP/uvicorn, beyond TestClient."""

import os
import socket
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from api.conftest import PASSWORD
from monetae.config import Settings
from monetae.services.auth import AuthService, SystemClock


def test_login_then_immediate_report_requests_with_uvicorn(
    database_url: str,
    db_engine: Engine,
) -> None:
    settings = Settings(environment="test", database_url=database_url, cookie_secure=False)
    email = f"report-probe-{uuid4().hex}@example.test"
    with Session(db_engine) as db:
        AuthService(db, settings, SystemClock()).create_user(email, PASSWORD)
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
            for endpoint in ("cash-flow", "categories"):
                response = client.get(f"/api/v1/reports/{endpoint}")
                assert response.status_code == 200, response.text
                print(f"uvicorn probe: login -> {endpoint} = {response.status_code}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
