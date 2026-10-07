from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .config import LEVEL_XP


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    xp: int
    level: int
    created_at: datetime


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def level_for(xp: int) -> int:
    return xp // LEVEL_XP + 1


def user_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        xp=user.xp,
        level=level_for(user.xp),
        created_at=user.created_at,
    )
