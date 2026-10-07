import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session
from ..models import Lesson, Progress, Submission, Task, Topic, User
from ..runner import get_runner
from ..schemas import level_for
from .deps import get_current_user

router = APIRouter(tags=["tasks"])


# ---------------------------------------------------------------- схемы ответов
class TaskNode(BaseModel):
    id: int
    title: str
    difficulty: int
    completed: bool


class LessonNode(BaseModel):
    id: int
    slug: str
    title: str
    order: int
    tasks: list[TaskNode]


class TopicNode(BaseModel):
    id: int
    slug: str
    title: str
    icon: str
    order: int
    lessons: list[LessonNode]


class TaskDetail(BaseModel):
    id: int
    topic_id: int
    lesson_id: int
    title: str
    prompt_md: str
    starter_code: str
    difficulty: int
    xp_reward: int
    function: str
    completed: bool
    attempts: int
    hints_used: int
    hints_total: int


class SubmitIn(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)


class TestOut(BaseModel):
    name: str
    passed: bool
    message: str | None = None


class SubmitOut(BaseModel):
    status: str
    xp_gained: int
    completed: bool
    tests: list[TestOut]
    message: str | None = None


class HintOut(BaseModel):
    index: int
    hint: str
    hints_used: int


# ------------------------------------------------------------------- эндпоинты
@router.get("/topics", response_model=list[TopicNode])
def topics(session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    completed_ids = {
        p.task_id for p in session.exec(
            select(Progress).where(Progress.user_id == user.id, Progress.completed == True)  # noqa: E712
        ).all()
    }

    result: list[TopicNode] = []
    for topic in session.exec(select(Topic).order_by(Topic.order)).all():
        lessons = session.exec(
            select(Lesson).where(Lesson.topic_id == topic.id).order_by(Lesson.order)
        ).all()
        lesson_nodes = []
        for lesson in lessons:
            tasks = session.exec(
                select(Task).where(Task.lesson_id == lesson.id).order_by(Task.id)
            ).all()
            lesson_nodes.append(LessonNode(
                id=lesson.id, slug=lesson.slug, title=lesson.title, order=lesson.order,
                tasks=[TaskNode(id=t.id, title=t.title, difficulty=t.difficulty,
                                completed=t.id in completed_ids)
                       for t in tasks],
            ))
        result.append(TopicNode(id=topic.id, slug=topic.slug, title=topic.title,
                                icon=topic.icon, order=topic.order, lessons=lesson_nodes))
    return result


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def task_detail(task_id: int, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    lesson = session.get(Lesson, task.lesson_id)
    progress = _get_progress(session, user.id, task.id)
    return TaskDetail(
        id=task.id, topic_id=lesson.topic_id, lesson_id=task.lesson_id,
        title=task.title, prompt_md=task.prompt_md, starter_code=task.starter_code,
        difficulty=task.difficulty, xp_reward=task.xp_reward, function=task.function,
        completed=progress.completed, attempts=progress.attempts,
        hints_used=progress.hints_used, hints_total=len(json.loads(task.hints_json)),
    )


@router.post("/tasks/{task_id}/hint", response_model=HintOut)
def task_hint(task_id: int, session: Session = Depends(get_session),
              user: User = Depends(get_current_user)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    hints = json.loads(task.hints_json)
    progress = _get_progress(session, user.id, task.id)
    if progress.hints_used >= len(hints):
        raise HTTPException(status_code=400, detail="Подсказки закончились")
    index = progress.hints_used
    progress.hints_used += 1
    session.add(progress)
    session.commit()
    return HintOut(index=index + 1, hint=hints[index], hints_used=progress.hints_used)


@router.post("/tasks/{task_id}/submit", response_model=SubmitOut)
def task_submit(task_id: int, payload: SubmitIn,
                session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    tests = json.loads(task.tests_json)
    outcome = get_runner().run(payload.code, task.function, tests)

    progress = _get_progress(session, user.id, task.id)
    was_completed = progress.completed
    progress.attempts += 1

    xp_gained = 0
    if outcome.status == "accepted" and not was_completed:
        xp_gained = task.xp_reward
        if progress.hints_used > 0:
            xp_gained = max(task.xp_reward // 2, 1)
        progress.completed = True
        user.xp += xp_gained

    session.add(progress)
    session.add(user)
    session.add(Submission(user_id=user.id, task_id=task.id,
                           code=payload.code, status=outcome.status))
    session.commit()

    return SubmitOut(
        status=outcome.status,
        xp_gained=xp_gained,
        completed=progress.completed,
        tests=[TestOut(**vars(t)) for t in outcome.tests],
        message=outcome.message,
    )


def _get_progress(session: Session, user_id: int, task_id: int) -> Progress:
    progress = session.exec(
        select(Progress).where(Progress.user_id == user_id, Progress.task_id == task_id)
    ).first()
    if progress is None:
        progress = Progress(user_id=user_id, task_id=task_id)
        session.add(progress)
        session.flush()
    return progress
