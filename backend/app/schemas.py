from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .config import LEVEL_XP


class UserOut(BaseModel):
    id: int
    email: EmailStr | None = None
    username: str
    xp: int
    level: int
    role: str
    class_name: str | None = None
    created_at: datetime


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterIn(BaseModel):
    """Регистрация учителя (по email)."""
    email: EmailStr
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=6, max_length=128)


class RegisterClassIn(BaseModel):
    """Регистрация ученика по коду класса (без почты)."""
    code: str = Field(min_length=1, max_length=12)
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    """Вход: учителя — по email, ученики — по имени."""
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class CreateClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class ClassOut(BaseModel):
    id: int
    name: str
    code: str
    students_count: int
    created_at: datetime


def level_for(xp: int) -> int:
    return xp // LEVEL_XP + 1


def user_out(user, class_name: str | None = None) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        xp=user.xp,
        level=level_for(user.xp),
        role=user.role,
        class_name=class_name,
        created_at=user.created_at,
    )
