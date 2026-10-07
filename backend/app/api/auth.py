from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import User
from ..schemas import AuthOut, LoginIn, RegisterIn, UserOut, user_out
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=AuthOut)
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    email = payload.email.lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    user = User(email=email, username=payload.username.strip(),
                password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return AuthOut(access_token=create_access_token(user.id), user=user_out(user))


@router.post("/auth/login", response_model=AuthOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return AuthOut(access_token=create_access_token(user.id), user=user_out(user))
