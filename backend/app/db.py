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


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_content(session)


def get_user_or_none(session: Session, user_id: int) -> models.User | None:
    return session.exec(select(models.User).where(models.User.id == user_id)).one_or_none()
