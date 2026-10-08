"""Сброс пароля и подтверждение почты — роуты fastapi-users.

Письма в dev уходят в файл-«исходящие» (EMAIL_OUTBOX, см. conftest) —
оттуда и достаём токены, как это сделал бы школьник по ссылке из письма.
"""
import json
import os
import re
import uuid
from pathlib import Path

OUTBOX = Path(os.environ["EMAIL_OUTBOX"])


def _entries() -> list[dict]:
    if not OUTBOX.exists():
        return []
    return [json.loads(line) for line in OUTBOX.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _token_from(entry: dict) -> str:
    m = re.search(r"token=([^&\s]+)", entry["text"])
    assert m, f"в письме нет ссылки с токеном: {entry['text']}"
    return m.group(1)


def _last_for(email: str, subject_part: str) -> dict:
    found = [e for e in _entries()
             if e["to"] == email and subject_part in e["subject"].lower()]
    assert found, f"нет письма «{subject_part}» для {email}"
    return found[-1]


def _register_teacher(client) -> str:
    email = f"{uuid.uuid4().hex[:8]}@test.ru"
    r = client.post("/api/auth/register", json={
        "email": email, "username": "Пётр", "password": "123456"})
    assert r.status_code == 200, r.text
    return email


def test_register_sends_verification_email(client):
    email = _register_teacher(client)
    entry = _last_for(email, "подтверди")
    assert "token=" in entry["text"]


def test_verify_email_flow(client):
    email = _register_teacher(client)
    token = _token_from(_last_for(email, "подтверди"))

    r = client.post("/api/auth/verify", json={"token": token})
    assert r.status_code == 200, r.text
    assert r.json()["is_verified"] is True
    assert r.json()["email"] == email

    # повторно токеном — уже нельзя
    r2 = client.post("/api/auth/verify", json={"token": token})
    assert r2.status_code == 400


def test_bad_verify_token(client):
    r = client.post("/api/auth/verify", json={"token": "вот-так-не-работает"})
    assert r.status_code == 400


def test_forgot_reset_password_flow(client):
    email = _register_teacher(client)

    # «забыли пароль» — всегда 202, даже чтобы не раскрывать список почт
    r = client.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code == 202, r.text

    token = _token_from(_last_for(email, "сброс"))

    # сброс по токену
    r = client.post("/api/auth/reset-password",
                    json={"token": token, "password": "654321"})
    assert r.status_code in (200, 204), r.text

    # старый пароль больше не работает, новый — работает
    assert client.post("/api/auth/login",
                       json={"login": email, "password": "123456"}).status_code == 401
    ok = client.post("/api/auth/login",
                     json={"login": email, "password": "654321"})
    assert ok.status_code == 200, ok.text

    # уведомление «пароль изменён» ушло
    _last_for(email, "изменён")


def test_forgot_password_unknown_email_not_revealed(client):
    # ответ одинаковый, есть ли почта — и письмо никто не получает
    before = len(_entries())
    r = client.post("/api/auth/forgot-password",
                    json={"email": f"net-{uuid.uuid4().hex[:8]}@test.ru"})
    assert r.status_code == 202
    assert len(_entries()) == before


def test_reset_with_bad_token(client):
    r = client.post("/api/auth/reset-password",
                    json={"token": "нет-такого", "password": "654321"})
    assert r.status_code == 400


def test_pupil_is_verified_and_has_no_real_email(client):
    """Ученик по коду класса: синтетический email скрыт, is_verified=True
    (код выдал учитель), письма ему не уходят."""
    t = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru",
        "username": "Учитель", "password": "123456"})
    assert t.status_code == 200, t.text
    client.headers.update({"Authorization": f"Bearer {t.json()['access_token']}"})
    code = client.post("/api/classes", json={"name": "7А"}).json()["code"]

    before = len(_entries())
    r = client.post("/api/auth/register-class", json={
        "code": code, "username": "Коля", "password": "123456"})
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["email"] is None          # наружу синтетический адрес не уходит
    assert user["role"] == "pupil"
    assert len(_entries()) == before       # ученику письма не отправляются
