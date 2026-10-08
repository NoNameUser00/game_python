from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import LEVEL_XP
from ..db import get_session
from ..models import Progress, Submission, User
from ..schemas import UserOut, user_out
from .deps import get_current_user

router = APIRouter(tags=["me"])


class ProgressOut(BaseModel):
    xp: int
    level: int
    completed_tasks: list[int]
    submissions: int
    hints_used: int


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user),
       session: Session = Depends(get_session)):
    from ..models import SchoolClass

    class_name = None
    if user.class_id is not None:
        klass = session.get(SchoolClass, user.class_id)
        class_name = klass.name if klass else None
    return user_out(user, class_name=class_name)


@router.get("/me/progress", response_model=ProgressOut)
def progress(user: User = Depends(get_current_user),
             session: Session = Depends(get_session)):
    rows = session.exec(select(Progress).where(Progress.user_id == user.id)).all()
    submissions = session.exec(
        select(Submission).where(Submission.user_id == user.id)
    ).all()
    return ProgressOut(
        xp=user.xp,
        level=user.xp // LEVEL_XP + 1,
        completed_tasks=[r.task_id for r in rows if r.completed],
        submissions=len(submissions),
        hints_used=sum(r.hints_used for r in rows),
    )


@router.get("/me/achievements")
def achievements(user: User = Depends(get_current_user),
                 session: Session = Depends(get_session)):
    """Все значки: какие уже открыты (для страницы профиля)."""
    from ..achievements import catalogue
    items = catalogue(user, session)
    return {"unlocked": [i["key"] for i in items if i["unlocked"]],
            "items": items}
