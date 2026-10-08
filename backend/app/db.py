"""БД: движок, сессии, инициализация и загрузка контента."""
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine, select

from .config import DATABASE_URL
from . import models  # noqa: F401  (регистрация таблиц)
from .content_loader import load_content

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args)


def get_session():
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope():
    with Session(engine) as session:
        yield session
        session.commit()


def _needs_users_migration() -> bool:
    """Локальная БД старой схемы несовместима (было password_hash/email NULL,
    стало поля fastapi-users) — пересоздаём. Прод-БД создаётся сразу новой."""
    if not DATABASE_URL.startswith("sqlite"):
        return False
    from sqlalchemy import text

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    if not rows:
        return False
    required = {"email", "hashed_password", "is_verified", "username",
                "role", "class_id", "xp"}
    present = {r[1] for r in rows}
    return not required.issubset(present)


def init_db() -> None:
    if _needs_users_migration():
        # Dev-БД пересоздаётся (данные — тестовые; контент загрузится заново из YAML)
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_content(session)


def get_user_or_none(session: Session, user_id: int) -> models.User | None:
    return session.exec(select(models.User).where(models.User.id == user_id)).one_or_none()
