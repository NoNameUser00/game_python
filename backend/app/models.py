from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """Пользователь. Поля id/email/hashed_password/is_* — формат fastapi-users.

    Учитель регистрируется по реальному email; ученик — по коду класса,
    для него создаётся синтетический email (приватность, но fastapi-users
    работает только с email — он обязателен и уникален).
    """
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(True, nullable=False)
    is_superuser: bool = Field(False, nullable=False)
    is_verified: bool = Field(False, nullable=False)  # верификация почты (вкл. на сервере)
    # --- наше ---
    username: str
    role: str = "pupil"                     # teacher | pupil
    class_id: int | None = Field(default=None, index=True, foreign_key="classes.id")
    xp: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class SchoolClass(SQLModel, table=True):
    __tablename__ = "classes"
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)   # 6 символов, раздаётся учителем
    name: str
    teacher_id: int = Field(index=True)          # без FK — чтобы не было цикла FK
    created_at: datetime = Field(default_factory=utcnow)


class Topic(SQLModel, table=True):
    __tablename__ = "topics"
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    icon: str = "🐍"
    order: int = 0


class Lesson(SQLModel, table=True):
    __tablename__ = "lessons"
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    topic_id: int = Field(index=True, foreign_key="topics.id")
    title: str
    order: int = 0


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    lesson_id: int = Field(index=True, foreign_key="lessons.id")
    title: str
    difficulty: int = 1
    xp_reward: int = 20
    function: str = "solution"
    prompt_md: str = ""
    starter_code: str = ""
    hints_json: str = "[]"
    tests_json: str = "[]"


class Progress(SQLModel, table=True):
    __tablename__ = "progress"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    task_id: int = Field(index=True, foreign_key="tasks.id")
    completed: bool = False
    attempts: int = 0
    hints_used: int = 0


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    task_id: int = Field(index=True, foreign_key="tasks.id")
    code: str
    status: str
    created_at: datetime = Field(default_factory=utcnow)
