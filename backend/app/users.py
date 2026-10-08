"""Слой аутентификации на fastapi-users v15.

Что берём у fastapi-users:
- хеши паролей (pwdlib/argon2) и их авто-апгрейд;
- токены и роуты «забыли пароль» (/api/auth/forgot-password, /reset-password);
- подтверждение почты (/api/auth/request-verify-token, /verify);
- UserManager как единая точка создания/обновления пользователей.

Что оставляем своим (контракт из docs/API.md не меняется):
- /api/auth/register (учитель), /api/auth/register-class (ученик по коду класса),
  /api/auth/login (email ИЛИ имя), наш JWT для доступа к API.
"""
import logging

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, schemas
from fastapi_users_db_sqlmodel import SQLModelUserDatabase
from sqlmodel import Session

from .config import FRONTEND_URL, JWT_SECRET
from .db import get_session
from .email import send_email_async
from .models import User

logger = logging.getLogger("app.users")

APP_TITLE = "Питонята"


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Менеджер пользователей: секреты для токенов + отправка писем."""

    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        logger.info("зарегистрирован %s (id=%s, role=%s)", user.email, user.id, user.role)

    async def on_after_forgot_password(self, user: User, token: str,
                                       request: Request | None = None) -> None:
        link = f"{FRONTEND_URL}/reset-password?token={token}"
        await send_email_async(
            user.email,
            f"{APP_TITLE}: сброс пароля",
            f"Привет! Не получается вспомнить пароль? Нажми на ссылку, "
            f"чтобы задать новый (действует 1 час):\n\n{link}\n\n"
            f"Если это не ты — просто игнорируй письмо.",
        )

    async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
        logger.info("пароль сброшен для %s", user.email)
        await send_email_async(
            user.email,
            f"{APP_TITLE}: пароль изменён",
            "Только что был изменён пароль от твоего аккаунта.\n"
            "Если это не ты — срочно напиши учителю!",
        )

    async def on_after_request_verify(self, user: User, token: str,
                                      request: Request | None = None) -> None:
        link = f"{FRONTEND_URL}/verify?token={token}"
        await send_email_async(
            user.email,
            f"{APP_TITLE}: подтверди почту",
            f"Осталось подтвердить, что почта твоя: перейди по ссылке\n\n{link}\n\n"
            f"(ссылка действует 1 час)",
        )

    async def on_after_verify(self, user: User, request: Request | None = None) -> None:
        logger.info("почта %s подтверждена", user.email)


def get_user_db(session: Session = Depends(get_session)) -> SQLModelUserDatabase[User, int]:
    return SQLModelUserDatabase(session, User)


async def get_user_manager(user_db: SQLModelUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


# Экземпляр fastapi-users: его роуты подключаются в main.py.
# auth_backends пусты — токены для API выдаём сами (см. security.py).
fastapi_users = FastAPIUsers[User, int](get_user_manager, [])


# ---------- Pydantic-схемы fastapi-users ----------

class UserRead(schemas.BaseUser[int]):
    """Публичный вид пользователя для /api/auth/verify."""
    username: str
    role: str
    xp: int = 0


class TeacherCreate(schemas.BaseUserCreate):
    """Регистрация учителя по реальному email."""
    username: str
    role: str = "teacher"


class PupilCreate(schemas.BaseUserCreate):
    """Регистрация ученика: email синтетический (приватность),
    is_verified=True — код класса выдал учитель, почту подтверждать нечем."""
    username: str
    role: str = "pupil"
    class_id: int
    is_verified: bool = True


def synthetic_pupil_email(token_hex: str) -> str:
    """Синтетический адрес ученика: нужен только для схемы fastapi-users,
    настоящим пользователям не показывается (см. user_out).
    Домен — запасной, почта на него никогда не отправляется."""
    return f"pupil-{token_hex}@pupils.pitonyata.ru"
