"""El commit debe ocurrir antes de enviar la respuesta (lectura tras escritura).

TestClient espera a que la app termine por completo, así que no distingue
"commit antes de responder" de "commit después de responder". Esta prueba
llama a la app por ASGI y registra el orden real de los eventos.
"""

import asyncio
from types import TracebackType

import pytest
from fastapi import FastAPI
from starlette.types import Message, Scope

from monetae.api import security
from monetae.api.security import Database
from monetae.config import Settings


class RecordingSession:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def __enter__(self) -> "RecordingSession":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.events.append("session_closed")

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


def test_commit_happens_before_the_response_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        security, "create_session_factory", lambda settings: lambda: RecordingSession(events)
    )
    app = FastAPI()
    app.state.settings = Settings(environment="test")

    @app.post("/write")
    def write(db: Database) -> dict[str, bool]:
        events.append("handler")
        return {"ok": True}

    async def call() -> None:
        body_sent = False

        async def receive() -> Message:
            nonlocal body_sent
            if body_sent:
                await asyncio.sleep(3600)
            body_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: Message) -> None:
            if message["type"] == "http.response.start":
                events.append("response_start")

        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/write",
            "raw_path": b"/write",
            "query_string": b"",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "app": app,
        }
        await app(scope, receive, send)

    asyncio.run(call())

    assert "handler" in events and "response_start" in events
    assert "commit" in events, events
    assert events.index("commit") < events.index("response_start"), events
