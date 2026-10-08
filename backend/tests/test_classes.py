"""Регистрация по коду класса (приватность: почта у учеников не нужна)."""


def _teacher(client):
    import uuid
    resp = client.post("/api/auth/register", json={
        "email": f"{uuid.uuid4().hex[:8]}@test.ru", "username": "Учитель", "password": "123456"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_teacher_creates_class_and_pupil_registers(client):
    teacher = _teacher(client)

    resp = teacher.post("/api/classes", json={"name": "7А"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["code"]) == 6 and data["students_count"] == 0

    # ученик входит по коду — без почты
    pupil = client.post("/api/auth/register-class", json={
        "code": data["code"].lower(), "username": "Маша", "password": "123456"})
    assert pupil.status_code == 200, pupil.text
    user = pupil.json()["user"]
    assert user["email"] is None
    assert user["role"] == "pupil"
    assert user["class_name"] == "7А"

    # ученик видит класс в профиле
    token = pupil.json()["access_token"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["class_name"] == "7А"
    assert me.json()["role"] == "pupil"

    # и входит по имени (без email)
    login = client.post("/api/auth/login", json={"login": "Маша", "password": "123456"})
    assert login.status_code == 200

    # учитель видит учеников
    classes = teacher.get("/api/classes").json()
    assert classes[0]["students_count"] == 1
    detail = teacher.get(f"/api/classes/{classes[0]['id']}/students").json()
    assert detail["students"][0]["username"] == "Маша"


def test_wrong_class_code(client):
    resp = client.post("/api/auth/register-class", json={
        "code": "XXXXXX", "username": "Маша", "password": "123456"})
    assert resp.status_code == 400
    assert "код" in resp.json()["detail"].lower()


def test_duplicate_username_in_class(client):
    teacher = _teacher(client)
    code = teacher.post("/api/classes", json={"name": "7Б"}).json()["code"]
    first = client.post("/api/auth/register-class", json={
        "code": code, "username": "Пётр", "password": "123456"})
    assert first.status_code == 200
    second = client.post("/api/auth/register-class", json={
        "code": code, "username": "Пётр", "password": "123456"})
    assert second.status_code == 409


def test_pupil_cannot_create_class(client):
    teacher = _teacher(client)
    code = teacher.post("/api/classes", json={"name": "7В"}).json()["code"]
    pupil_token = client.post("/api/auth/register-class", json={
        "code": code, "username": "Оля", "password": "123456"}).json()["access_token"]
    resp = client.post("/api/classes", json={"name": "8Г"},
                       headers={"Authorization": f"Bearer {pupil_token}"})
    assert resp.status_code == 403


def test_classes_not_for_pupils(client):
    teacher = _teacher(client)
    code = teacher.post("/api/classes", json={"name": "7Г"}).json()["code"]
    pupil_token = client.post("/api/auth/register-class", json={
        "code": code, "username": "Игорь", "password": "123456"}).json()["access_token"]
    resp = client.get("/api/classes", headers={"Authorization": f"Bearer {pupil_token}"})
    assert resp.status_code == 403
