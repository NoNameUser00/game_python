import os
import tempfile
from pathlib import Path

# БД для тестов — временный файл, выставляем ДО импорта приложения
_TEST_DB = Path(tempfile.gettempdir()) / "game_python_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    """Клиент, уже зарегистрированный и авторизованный."""
    import uuid
    resp = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru",
        "username": "Школьник",
        "password": "123456",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
