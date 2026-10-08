"""Тесты расширенного режима учителя (№7) и достижений (№10)."""
import uuid

from .test_api import _task_id


def _register(client, role="pupil", code=None, username=None):
    """Быстрая регистрация: учитель (email) или ученик (код класса)."""
    username = username or f"Уч-{uuid.uuid4().hex[:6]}"
    if role == "teacher":
        resp = client.post("/api/auth/register", json={
            "email": f"{uuid.uuid4().hex[:8]}@test.ru",
            "username": username, "password": "123456"})
    else:
        resp = client.post("/api/auth/register-class", json={
            "code": code, "username": username, "password": "123456"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"], username


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_class(client):
    """Учитель + класс; токен учителя."""
    token, _ = _register(client, role="teacher")
    resp = client.post("/api/classes", json={"name": "7А"},
                       headers=_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    return token, data["id"], data["code"]


def _join(client, code):
    token, username = _register(client, code=code)
    return token, username


# ------------------------------------------------------------ лидерборд
def test_leaderboard_requires_membership(client):
    t1, class_id, code = _make_class(client)
    outsider = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru",
        "username": "Чужак", "password": "123456"}).json()["access_token"]

    assert client.get(f"/api/classes/{class_id}/leaderboard",
                      headers=_headers(t1)).status_code == 200
    assert client.get(f"/api/classes/{class_id}/leaderboard",
                      headers=_headers(outsider)).status_code == 403
    assert client.get(f"/api/classes/{class_id}/leaderboard").status_code == 401
    assert client.get("/api/classes/999/leaderboard",
                      headers=_headers(t1)).status_code == 404


def test_leaderboard_order_and_places(client):
    t_teacher, class_id, code = _make_class(client)
    pupil_a, _ = _join(client, code)          # решает задачу → больше XP
    pupil_b, name_b = _join(client, code)

    task_id = _task_id(client, "greeting", pupil_a)
    code_a = 'def hello(name):\n    return f"Привет, {name}!"'
    assert client.post(f"/api/tasks/{task_id}/submit", json={"code": code_a},
                       headers=_headers(pupil_a)).json()["status"] == "accepted"

    # учителю — видно обоих, места 1 и 2
    rows = client.get(f"/api/classes/{class_id}/leaderboard",
                      headers=_headers(t_teacher)).json()
    assert len(rows) == 2
    assert rows[0]["place"] == 1 and rows[1]["place"] == 2
    assert rows[0]["xp"] > rows[1]["xp"] == 0
    assert rows[0]["completed_tasks"] == 1

    # ученику класса — тоже видно (табличка в классе)
    rows_b = client.get(f"/api/classes/{class_id}/leaderboard",
                        headers=_headers(pupil_b)).json()
    assert len(rows_b) == 2
    assert any(r["username"] == name_b for r in rows_b)


# ------------------------------------------------------------- статистика
def test_class_stats(client):
    t_teacher, class_id, code = _make_class(client)
    pupil, _ = _join(client, code)

    task_id = _task_id(client, "greeting", pupil)
    client.post(f"/api/tasks/{task_id}/submit",
                json={"code": 'def hello(name):\n    return f"Привет, {name}!"'},
                headers=_headers(pupil))

    # чужой учитель не видит статистику
    other = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru",
        "username": "Чужой", "password": "123456"}).json()["access_token"]
    assert client.get(f"/api/classes/{class_id}/stats",
                      headers=_headers(other)).status_code == 403

    stats = client.get(f"/api/classes/{class_id}/stats",
                       headers=_headers(t_teacher)).json()
    assert stats["students"] == 1
    assert stats["total_completed"] == 1
    assert stats["active_7d"] == 1
    assert stats["avg_xp"] > 0
    assert stats["total_tasks"] >= 12
    assert len(stats["per_topic"]) >= 6
    greeting = next(t for t in stats["per_task"] if t["id"] == task_id)
    assert greeting["done_count"] == 1


# ---------------------------------------------------- назначение задач
def test_assignments_flow(client):
    t_teacher, class_id, code = _make_class(client)
    pupil, _ = _join(client, code)
    task_id = _task_id(client, "greeting", pupil)

    # ученик пока не видит заданий
    assert client.get("/api/assignments", headers=_headers(pupil)).json() == []

    # учитель назначает
    resp = client.post(f"/api/classes/{class_id}/assignments",
                       json={"task_id": task_id}, headers=_headers(t_teacher))
    assert resp.status_code == 200
    assignment_id = resp.json()["id"]

    # дубликат нельзя
    assert client.post(f"/api/classes/{class_id}/assignments",
                       json={"task_id": task_id},
                       headers=_headers(t_teacher)).status_code == 409
    # не-задача
    assert client.post(f"/api/classes/{class_id}/assignments",
                       json={"task_id": 99999},
                       headers=_headers(t_teacher)).status_code == 404

    # ученик видит задание без статуса
    mine = client.get("/api/assignments", headers=_headers(pupil)).json()
    assert len(mine) == 1 and mine[0]["task_id"] == task_id
    assert mine[0]["completed"] is False

    # решил → статус true, у учителя done_count
    client.post(f"/api/tasks/{task_id}/submit",
                json={"code": 'def hello(name):\n    return f"Привет, {name}!"'},
                headers=_headers(pupil))
    mine = client.get("/api/assignments", headers=_headers(pupil)).json()
    assert mine[0]["completed"] is True

    teacher_list = client.get(f"/api/classes/{class_id}/assignments",
                              headers=_headers(t_teacher)).json()
    assert teacher_list[0]["done_count"] == 1
    assert teacher_list[0]["students_count"] == 1

    # ученики не управляют заданиями
    assert client.post(f"/api/classes/{class_id}/assignments",
                       json={"task_id": task_id},
                       headers=_headers(pupil)).status_code == 403

    # учитель убирает задание
    assert client.delete(f"/api/assignments/{assignment_id}",
                         headers=_headers(t_teacher)).status_code == 200
    assert client.get("/api/assignments", headers=_headers(pupil)).json() == []


# ------------------------------------------- сброс пароля учителем
def test_teacher_resets_pupil_password(client):
    t_teacher, class_id, code = _make_class(client)
    pupil_token, pupil_name = _join(client, code)
    pupil = client.get("/api/me", headers=_headers(pupil_token)).json()

    # старый пароль работает
    assert client.post("/api/auth/login",
                       json={"login": pupil_name,
                             "password": "123456"}).status_code == 200

    resp = client.post(f"/api/classes/{class_id}/students/{pupil['id']}/password",
                       json={"password": "новый777"},
                       headers=_headers(t_teacher))
    assert resp.status_code == 200 and resp.json()["ok"] is True

    # новый пароль — вход есть, старого — нет
    assert client.post("/api/auth/login",
                       json={"login": pupil_name,
                             "password": "123456"}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"login": pupil_name,
                             "password": "новый777"}).status_code == 200

    # чужой учитель не может менять пароли
    other = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru",
        "username": "Чужой2", "password": "123456"}).json()["access_token"]
    assert client.post(f"/api/classes/{class_id}/students/{pupil['id']}/password",
                       json={"password": "abcdef"},
                       headers=_headers(other)).status_code == 403

    # слишком короткий пароль — 422
    assert client.post(f"/api/classes/{class_id}/students/{pupil['id']}/password",
                       json={"password": "123"},
                       headers=_headers(t_teacher)).status_code == 422


# --------------------------------------------------------- достижения
def test_achievements_catalogue_and_first_unlock(client):
    _, token, _ = _make_class(client)
    pupil, _ = _join(client, _make_class(client)[2])

    data = client.get("/api/me/achievements", headers=_headers(pupil)).json()
    keys = [i["key"] for i in data["items"]]
    assert "first_task" in keys and "streak_3" in keys
    assert any(k.startswith("topic:") for k in keys)
    assert data["unlocked"] == []          # ничего не решено

    # решаем задачу — first_task открывается, сервер сообщает в submit
    task_id = _task_id(client, "greeting", pupil)
    resp = client.post(f"/api/tasks/{task_id}/submit",
                       json={"code": 'def hello(name):\n    return f"Привет, {name}!"'},
                       headers=_headers(pupil))
    fresh = resp.json()["new_achievements"]
    assert any(a["key"] == "first_task" for a in fresh)
    assert all({"key", "emoji", "title", "desc"} <= set(a) for a in fresh)

    data = client.get("/api/me/achievements", headers=_headers(pupil)).json()
    assert "first_task" in data["unlocked"]
    assert "tasks_5" not in data["unlocked"]

    # повторная отправка не открывает значков заново
    resp2 = client.post(f"/api/tasks/{task_id}/submit",
                        json={"code": 'def hello(name):\n    return f"Привет, {name}!"'},
                        headers=_headers(pupil))
    assert resp2.json()["new_achievements"] == []


def test_achievements_no_hints_and_first_try(client):
    _, _, code = _make_class(client)
    pupil, _ = _join(client, code)

    # решение задачи сразу (без подсказок, первой отправкой)
    for slug, fn in [("greeting", 'def hello(name):\n    return f"Привет, {name}!"'),
                     ("sum-two", "def add(a, b):\n    return a + b"),
                     ("is-even", "def is_even(n):\n    return n % 2 == 0")]:
        task_id = _task_id(client, slug, pupil)
        resp = client.post(f"/api/tasks/{task_id}/submit",
                           json={"code": fn}, headers=_headers(pupil))
        assert resp.json()["status"] == "accepted", (slug, resp.json())

    data = client.get("/api/me/achievements", headers=_headers(pupil)).json()
    unlocked = set(data["unlocked"])
    assert "first_try" in unlocked      # решено первой же отправкой
    assert "no_hints" in unlocked       # 3 задачи без подсказок
    assert "tasks_5" not in unlocked
