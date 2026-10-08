"""БД: движок, сессии, инициализация и загрузка контента."""
from contextlib import contextmanager

from sqlalchemy import text
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

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    if not rows:
        return False
    required = {"email", "hashed_password", "is_verified", "username",
                "role", "class_id", "xp"}
    present = {r[1] for r in rows}
    return not required.issubset(present)


# Ключ session-level advisory lock: схему на свежей БД создаёт только один
# воркер/процесс, остальные ждут и увидят готовую схему.
_INIT_LOCK_KEY = 764_321


def init_db():
    if _needs_users_migration():
        # Dev-БД пересоздаётся (данные — тестовые; контент загрузится заново из YAML)
        SQLModel.metadata.drop_all(engine)

    if not DATABASE_URL.startswith("sqlite"):
        # PostgreSQL: несколько воркеров стартуют одновременно, а create_all
        # на гонке падает с UniqueViolation (duplicate key ..._id_seq).
        # Advisory lock снимаем на одном соединении и держим через весь init.
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _INIT_LOCK_KEY})
            try:
                SQLModel.metadata.create_all(bind=conn)
                with Session(conn) as session:
                    stats = load_content(session)
                conn.commit()
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _INIT_LOCK_KEY})
                conn.commit()
        return stats

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        return load_content(session)


def get_user_or_none(session: Session, user_id: int) -> models.User | None:
    return session.exec(select(models.User).where(models.User.id == user_id)).one_or_none()
