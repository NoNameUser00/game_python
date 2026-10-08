"""Сквозные тесты API: регистрация → карта → решение задачи → XP."""


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_login_me(client):
    resp = client.post("/api/auth/register", json={
        "email": "a@b.ru", "username": "Аня", "password": "123456"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert resp.json()["user"]["xp"] == 0

    # дубликат email
    resp2 = client.post("/api/auth/register", json={
        "email": "a@b.ru", "username": "Аня2", "password": "123456"})
    assert resp2.status_code == 409

    # вход (email — учитель, имя — ученик)
    login = client.post("/api/auth/login", json={"login": "a@b.ru", "password": "123456"})
    assert login.status_code == 200
    bad = client.post("/api/auth/login", json={"login": "a@b.ru", "password": "wrong"})
    assert bad.status_code == 401

    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "Аня"


def test_topics_require_auth(client):
    assert client.get("/api/topics").status_code == 401


def test_topics_tree(auth_client):
    topics = auth_client.get("/api/topics").json()
    assert len(topics) >= 4
    assert topics[0]["slug"] == "basics"
    assert topics[0]["icon"]
    task_ids = [t["id"] for l in topics[0]["lessons"] for t in l["tasks"]]
    assert len(task_ids) == 2


def test_solve_task_gives_xp_once(auth_client):
    task = auth_client.get("/api/tasks/1").json()
    assert task["title"] == "Приветствие"
    assert task["completed"] is False
    reward = task["xp_reward"]

    code = 'def hello(name):\n    return f"Привет, {name}!"'
    resp = auth_client.post("/api/tasks/1/submit", json={"code": code})
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["xp_gained"] == reward
    assert data["completed"] is True
    assert all(t["passed"] for t in data["tests"])

    # повторное решение XP не даёт
    resp2 = auth_client.post("/api/tasks/1/submit", json={"code": code})
    assert resp2.json()["xp_gained"] == 0

    progress = auth_client.get("/api/me/progress").json()
    assert progress["xp"] == reward
    assert 1 in progress["completed_tasks"]
    assert progress["level"] == 1


def test_wrong_answer_and_error(auth_client):
    wrong = auth_client.post("/api/tasks/1/submit", json={"code": "def hello(name):\n    return ''"})
    assert wrong.json()["status"] == "failed"
    assert wrong.json()["xp_gained"] == 0

    broken = auth_client.post("/api/tasks/1/submit", json={"code": "def hello(name)\n    pass"})
    assert broken.json()["status"] == "error"
    assert broken.json()["tests"] == []


def test_hint_halves_reward(auth_client):
    task = auth_client.get("/api/tasks/4").json()   # max-of-three
    reward = task["xp_reward"]

    hint = auth_client.post("/api/tasks/4/hint")
    assert hint.status_code == 200
    assert hint.json()["index"] == 1
    assert hint.json()["hints_used"] == 1

    code = "def maximum(a, b, c):\n    return max(a, b, c)"
    resp = auth_client.post("/api/tasks/4/submit", json={"code": code})
    assert resp.json()["status"] == "accepted"
    assert resp.json()["xp_gained"] == reward // 2

    # вторая подсказка есть, третей нет
    assert auth_client.post("/api/tasks/4/hint").status_code == 200
    assert auth_client.post("/api/tasks/4/hint").status_code == 400


def test_task_404(auth_client):
    assert auth_client.get("/api/tasks/999").status_code == 404
    assert auth_client.post("/api/tasks/999/submit", json={"code": "x = 1"}).status_code == 404
