import secrets

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session
from ..models import Lesson, Progress, SchoolClass, Task, Topic, User
from ..schemas import ClassOut, CreateClassIn
from .auth import CODE_ALPHABET, _class_name
from .deps import get_current_user

router = APIRouter(tags=["classes"])


def _owned_class(session: Session, user: User, class_id: int) -> SchoolClass:
    """Класс или 404/403 — общая проверка «класс существует и это твой»."""
    klass = session.get(SchoolClass, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Класс не найден")
    if klass.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Это не ваш класс")
    return klass


def _generate_code(session: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if session.exec(select(SchoolClass).where(SchoolClass.code == code)).first() is None:
            return code
    raise HTTPException(status_code=500, detail="Не удалось сгенерировать код класса")


@router.post("/classes", response_model=ClassOut)
def create_class(payload: CreateClassIn,
                 session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Классы может создавать только учитель")
    klass = SchoolClass(code=_generate_code(session), name=payload.name.strip(),
                        teacher_id=user.id)
    session.add(klass)
    session.commit()
    session.refresh(klass)
    return ClassOut(id=klass.id, name=klass.name, code=klass.code,
                    students_count=0, created_at=klass.created_at)


@router.get("/classes", response_model=list[ClassOut])
def list_classes(session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Доступ только для учителей")
    classes = session.exec(
        select(SchoolClass).where(SchoolClass.teacher_id == user.id)
        .order_by(SchoolClass.created_at)  # type: ignore[arg-type]
    ).all()
    out = []
    for klass in classes:
        count = session.exec(select(User).where(User.class_id == klass.id)).all()
        out.append(ClassOut(id=klass.id, name=klass.name, code=klass.code,
                            students_count=len(count), created_at=klass.created_at))
    return out


@router.get("/classes/{class_id}/students")
def class_students(class_id: int,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    """Список учеников класса с их прогрессом (для учителя)."""
    klass = _owned_class(session, user, class_id)

    students = session.exec(select(User).where(User.class_id == class_id)).all()
    result = []
    for s in students:
        rows = session.exec(select(Progress).where(Progress.user_id == s.id)).all()
        result.append({
            "id": s.id,
            "username": s.username,
            "xp": s.xp,
            "level": s.xp // 100 + 1,
            "completed_tasks": sum(1 for r in rows if r.completed),
            "hints_used": sum(r.hints_used for r in rows),
        })
    result.sort(key=lambda r: -r["xp"])
    return {"class": {"id": klass.id, "name": klass.name, "code": klass.code},
            "students": result}


# ------------------------------------------- лидерборд и статистика (№7)
class LeaderRow(BaseModel):
    place: int
    id: int
    username: str
    xp: int
    level: int
    completed_tasks: int


@router.get("/classes/{class_id}/leaderboard", response_model=list[LeaderRow])
def class_leaderboard(class_id: int,
                      session: Session = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """Лидерборд класса: видят учитель-владелец и ученики этого класса."""
    klass = session.get(SchoolClass, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Класс не найден")
    allowed = klass.teacher_id == user.id or (
        user.role == "pupil" and user.class_id == klass.id)
    if not allowed:
        raise HTTPException(status_code=403, detail="Это не ваш класс")

    students = session.exec(select(User).where(User.class_id == class_id)).all()
    rows = []
    for s in students:
        done = session.exec(
            select(Progress).where(Progress.user_id == s.id,
                                   Progress.completed == True)  # noqa: E712
        ).all()
        rows.append(LeaderRow(place=0, id=s.id, username=s.username, xp=s.xp,
                              level=s.xp // 100 + 1, completed_tasks=len(done)))
    rows.sort(key=lambda r: (-r.xp, -r.completed_tasks, r.username))
    for i, row in enumerate(rows, start=1):
        row.place = i
    return rows


@router.get("/classes/{class_id}/stats")
def class_stats(class_id: int,
                session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    """Расширенная статистика класса: по темам, задачам и активности."""
    klass = _owned_class(session, user, class_id)

    students = session.exec(select(User).where(User.class_id == class_id)).all()
    student_ids = [s.id for s in students]

    # решённые задачи учеников
    done_by_task: dict[int, int] = {}
    total_completed = 0
    if student_ids:
        rows = session.exec(
            select(Progress).where(Progress.user_id.in_(student_ids),  # type: ignore[attr-defined]
                                   Progress.completed == True)  # noqa: E712
        ).all()
        for r in rows:
            done_by_task[r.task_id] = done_by_task.get(r.task_id, 0) + 1
            total_completed += 1

    # активность за 7 дней
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_ids: set[int] = set()
    if student_ids:
        from ..models import Submission
        subs = session.exec(
            select(Submission).where(Submission.user_id.in_(student_ids))  # type: ignore[attr-defined]
        ).all()
        for s in subs:
            created = s.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= week_ago:
                active_ids.add(s.user_id)

    # по темам и задачам
    lessons = {l.id: l for l in session.exec(select(Lesson)).all()}
    topics = {t.id: t for t in session.exec(select(Topic)).all()}
    tasks = session.exec(select(Task)).all()
    n_tasks = len(tasks)
    per_topic: dict[int, dict] = {}
    per_task = []
    for t in tasks:
        lesson = lessons.get(t.lesson_id)
        topic = topics.get(lesson.topic_id) if lesson else None
        done = done_by_task.get(t.id, 0)
        per_task.append({"id": t.id, "title": t.title,
                         "topic": topic.title if topic else "?",
                         "done_count": done})
        if topic is not None:
            slot = per_topic.setdefault(topic.id, {"title": topic.title,
                                                   "icon": topic.icon,
                                                   "tasks": 0, "solved": 0})
            slot["tasks"] += 1
            slot["solved"] += done

    avg_xp = round(sum(s.xp for s in students) / len(students)) if students else 0
    return {
        "students": len(students),
        "active_7d": len(active_ids),
        "avg_xp": avg_xp,
        "total_completed": total_completed,
        "total_tasks": n_tasks,
        "per_topic": list(per_topic.values()),
        "per_task": per_task,
    }


class NewPasswordIn(BaseModel):
    password: str = Field(min_length=6, max_length=128)


@router.post("/classes/{class_id}/students/{student_id}/password")
async def reset_student_password(class_id: int, student_id: int,
                                 payload: NewPasswordIn,
                                 session: Session = Depends(get_session),
                                 user: User = Depends(get_current_user)):
    """Учитель задаёт ученику новый пароль (дети часто забывают)."""
    from fastapi_users.password import PasswordHelper

    _owned_class(session, user, class_id)
    student = session.get(User, student_id)
    if student is None or student.class_id != class_id:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    if student.role != "pupil":
        raise HTTPException(status_code=400, detail="Это не ученик")

    student.hashed_password = PasswordHelper().hash(payload.password)
    session.add(student)
    session.commit()
    return {"ok": True, "username": student.username}
