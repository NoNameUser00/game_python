import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import SchoolClass, User
from ..schemas import AuthOut, CreateClassIn, LoginIn, RegisterClassIn, RegisterIn, user_out
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])

# Без омнибусных букв: не путаем 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _class_name(session: Session, user: User) -> str | None:
    if user.class_id is None:
        return None
    klass = session.get(SchoolClass, user.class_id)
    return klass.name if klass else None


@router.post("/auth/register", response_model=AuthOut)
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    """Регистрация учителя (по email)."""
    email = payload.email.lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    user = User(email=email, username=payload.username.strip(),
                password_hash=hash_password(payload.password), role="teacher")
    session.add(user)
    session.commit()
    session.refresh(user)
    return AuthOut(access_token=create_access_token(user.id), user=user_out(user))


@router.post("/auth/register-class", response_model=AuthOut)
def register_class(payload: RegisterClassIn, session: Session = Depends(get_session)):
    """Регистрация ученика по коду класса — почта не нужна (приватность детей)."""
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
    user = User(email=None, username=username,
                password_hash=hash_password(payload.password),
                role="pupil", class_id=klass.id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return AuthOut(access_token=create_access_token(user.id),
                   user=user_out(user, class_name=klass.name))


@router.post("/auth/login", response_model=AuthOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    """Вход: учитель — по email, ученик — по имени."""
    ident = payload.login.strip()
    user = session.exec(
        select(User).where((User.email == ident.lower()) | (User.username == ident))
    ).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email/имя или пароль")
    return AuthOut(access_token=create_access_token(user.id),
                   user=user_out(user, class_name=_class_name(session, user)))
