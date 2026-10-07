from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..models import User
from ..security import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется вход в аккаунт")
    user_id = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if user_id is None:
        raise HTTPException(status_code=401, detail="Сессия истекла — войди заново")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
