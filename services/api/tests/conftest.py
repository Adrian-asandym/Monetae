from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monetae.api.main import create_app
from monetae.config import Settings


@pytest.fixture
def application() -> FastAPI:
    return create_app(Settings(environment="test", database_url=None, cors_origins=[]))


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client
