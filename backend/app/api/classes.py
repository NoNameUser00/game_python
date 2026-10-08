import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import SchoolClass, User
from ..schemas import ClassOut, CreateClassIn
from .auth import CODE_ALPHABET, _class_name
from .deps import get_current_user

router = APIRouter(tags=["classes"])


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
    klass = session.get(SchoolClass, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="Класс не найден")
    if klass.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Это не ваш класс")
    from ..models import Progress  # локальный импорт — избегаем цикличных

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
