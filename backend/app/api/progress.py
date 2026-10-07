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
def me(user: User = Depends(get_current_user)):
    return user_out(user)


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
