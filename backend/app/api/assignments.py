"""Задания учителя: задача, назначенная классу (расширенный режим, №7)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Assignment, Lesson, Progress, SchoolClass, Task, Topic, User
from .deps import get_current_user

router = APIRouter(tags=["assignments"])


def _task_node(session: Session, task: Task) -> dict:
    lesson = session.get(Lesson, task.lesson_id)
    topic = session.get(Topic, lesson.topic_id) if lesson else None
    return {"id": task.id, "title": task.title, "difficulty": task.difficulty,
            "topic": topic.title if topic else "?",
            "icon": topic.icon if topic else "🐍"}


def _owned_class(session: Session, user: User, class_id: int) -> SchoolClass:
    from .classes import _owned_class as check
    return check(session, user, class_id)


class AssignmentIn(BaseModel):
    task_id: int


@router.post("/classes/{class_id}/assignments")
def create_assignment(class_id: int, payload: AssignmentIn,
                      session: Session = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """Назначить задачу классу."""
    _owned_class(session, user, class_id)
    task = session.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    exists = session.exec(
        select(Assignment).where(Assignment.class_id == class_id,
                                 Assignment.task_id == task.id)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="Задача уже назначена")
    row = Assignment(class_id=class_id, task_id=task.id, created_by=user.id)
    session.add(row)
    session.commit()
    session.refresh(row)
    node = _task_node(session, task)
    return {"id": row.id, "task_id": task.id,
            "title": node["title"], "topic": node["topic"],
            "icon": node["icon"], "difficulty": node["difficulty"]}


@router.get("/classes/{class_id}/assignments")
def list_class_assignments(class_id: int,
                           session: Session = Depends(get_session),
                           user: User = Depends(get_current_user)):
    """Назначенные задачи + сколько учеников класса их решило."""
    _owned_class(session, user, class_id)
    rows = session.exec(
        select(Assignment).where(Assignment.class_id == class_id)
        .order_by(Assignment.created_at)  # type: ignore[arg-type]
    ).all()
    students = session.exec(
        select(User).where(User.class_id == class_id)).all()
    n_students = len(students)
    out = []
    for row in rows:
        task = session.get(Task, row.task_id)
        if task is None:
            continue
        done = 0
        for s in students:
            p = session.exec(
                select(Progress).where(Progress.user_id == s.id,
                                       Progress.task_id == task.id)  # noqa: E712
            ).first()
            if p is not None and p.completed:
                done += 1
        node = _task_node(session, task)
        out.append({"id": row.id, "task_id": node["id"],
                    "title": node["title"], "topic": node["topic"],
                    "icon": node["icon"], "difficulty": node["difficulty"],
                    "created_at": row.created_at,
                    "done_count": done, "students_count": n_students})
    return out


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int,
                      session: Session = Depends(get_session),
                      user: User = Depends(get_current_user)):
    row = session.get(Assignment, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    _owned_class(session, user, row.class_id)
    session.delete(row)
    session.commit()
    return {"ok": True}


@router.get("/assignments")
def my_assignments(session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    """Задания для меня (ученика): со статусом «решено / нет»."""
    if user.role != "pupil" or user.class_id is None:
        return []
    rows = session.exec(
        select(Assignment).where(Assignment.class_id == user.class_id)
        .order_by(Assignment.created_at)  # type: ignore[arg-type]
    ).all()
    out: list[dict] = []
    for row in rows:
        task = session.get(Task, row.task_id)
        if task is None:
            continue
        p = session.exec(
            select(Progress).where(Progress.user_id == user.id,
                                   Progress.task_id == task.id)  # noqa: E712
        ).first()
        node = _task_node(session, task)
        out.append({"id": row.id, "task_id": task.id,
                    "title": node["title"], "topic": node["topic"],
                    "icon": node["icon"], "difficulty": node["difficulty"],
                    "created_at": row.created_at,
                    "completed": bool(p and p.completed)})
    return out
