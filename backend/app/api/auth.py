import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi_users import exceptions as fu_exceptions
from sqlmodel import Session, select

from ..config import REQUIRE_EMAIL_VERIFICATION
from ..db import get_session
from ..models import SchoolClass, User
from ..schemas import AuthOut, CreateClassIn, LoginIn, RegisterClassIn, RegisterIn, user_out
from ..security import create_access_token
from ..users import (PupilCreate, TeacherCreate, UserManager, get_user_manager,
                     synthetic_pupil_email)

router = APIRouter(tags=["auth"])
logger = logging.getLogger("app.auth")

# Без омнибусных букв: не путаем 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _class_name(session: Session, user: User) -> str | None:
    if user.class_id is None:
        return None
    klass = session.get(SchoolClass, user.class_id)
    return klass.name if klass else None


@router.post("/auth/register", response_model=AuthOut)
async def register(payload: RegisterIn,
                   user_manager: UserManager = Depends(get_user_manager)):
    """Регистрация учителя (по реальному email, fastapi-users)."""
    try:
        user = await user_manager.create(TeacherCreate(
            email=payload.email, username=payload.username.strip(),
            password=payload.password, role="teacher"))
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    except fu_exceptions.InvalidPasswordException as e:
        raise HTTPException(status_code=400, detail=f"Неподходящий пароль: {e.reason}")
    # Письмо с ссылкой подтверждения — в dev попадает в outbox-файл.
    # Подтверждение не блокирует вход, поэтому ошибку только логируем.
    try:
        await user_manager.request_verify(user)
    except Exception:
        logger.exception("не удалось отправить письмо подтверждения почты %s", user.email)
    return AuthOut(access_token=create_access_token(user.id), user=user_out(user))


@router.post("/auth/register-class", response_model=AuthOut)
async def register_class(payload: RegisterClassIn,
                         user_manager: UserManager = Depends(get_user_manager),
                         session: Session = Depends(get_session)):
    """Регистрация ученика по коду класса — почта не нужна (приватность детей).

    fastapi-users требует email, поэтому создаётся синтетический адрес
    (никому не показывается); пароль хранит fastapi-users (argon2).
    """
    code = payload.code.strip().upper()
    klass = session.exec(select(SchoolClass).where(SchoolClass.code == code)).first()
    if klass is None:
        raise HTTPException(status_code=400, detail="Неверный код класса")
    username = payload.username.strip()
    dup = session.exec(
        select(User).where(User.class_id == klass.id, User.username == username)
    ).first()
    if dup:
        raise HTTPException(status_code=409,
                            detail=f"В этом классе уже есть ученик «{username}» — придумай другое имя")

    last_error: Exception | None = None
    user = None
    for _ in range(3):  # синтетический email уникален практически всегда, но подстрахуемся
        try:
            user = await user_manager.create(PupilCreate(
                email=synthetic_pupil_email(secrets.token_hex(8)),
                username=username, password=payload.password,
                class_id=klass.id, role="pupil", is_verified=True))
            break
        except fu_exceptions.UserAlreadyExists as e:
            last_error = e
    if user is None:
        raise HTTPException(status_code=409, detail=f"Не удалось создать ученика: {last_error}")
    return AuthOut(access_token=create_access_token(user.id),
                   user=user_out(user, class_name=klass.name))


@router.post("/auth/login", response_model=AuthOut)
async def login(payload: LoginIn,
                user_manager: UserManager = Depends(get_user_manager),
                session: Session = Depends(get_session)):
    """Вход: учитель — по email, ученик — по имени. Пароли проверяет fastapi-users."""
    ident = payload.login.strip()
    user = session.exec(
        select(User).where((User.email == ident.lower()) | (User.username == ident))
    ).first()

    verified = False
    if user is not None:
        try:
            verified, updated_hash = user_manager.password_helper.verify_and_update(
                payload.password, user.hashed_password)
            if updated_hash is not None:  # авто-апгрейд старого хеша
                await user_manager.user_db.update(user, {"hashed_password": updated_hash})
        except Exception:  # неизвестный формат хеша — просто отказ
            verified = False

    if user is None or not verified or not user.is_active:
        raise HTTPException(status_code=401, detail="Неверный email/имя или пароль")
    if REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
        raise HTTPException(status_code=403,
                            detail="Почта не подтверждена — открой ссылку из письма")
    return AuthOut(access_token=create_access_token(user.id),
                   user=user_out(user, class_name=_class_name(session, user)))
