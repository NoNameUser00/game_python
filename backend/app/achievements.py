"""Достижения (значки) — считаются на лету из прогресса и отправок.

Своей таблицы нет: правило монотонно, поэтому «когда открылось» не критично,
а состояние всегда соответствует данным (нет рассинхрона после правок БД).
"""
from dataclasses import dataclass

from sqlmodel import Session, select

from .config import LEVEL_XP
from .models import Lesson, Progress, Submission, Task, Topic, User


@dataclass(frozen=True)
class Achievement:
    key: str
    emoji: str
    title: str
    desc: str

    def as_dict(self, unlocked: bool) -> dict:
        return {"key": self.key, "emoji": self.emoji,
                "title": self.title, "desc": self.desc, "unlocked": unlocked}


# ------------------------------------------------------------------- правила
_STATIC = [
    Achievement("first_task", "🌱", "Первая победа", "Решил свою первую задачу"),
    Achievement("tasks_5", "🚀", "Пятый шаг", "Решено 5 задач"),
    Achievement("tasks_10", "⭐", "Десятка", "Решено 10 задач"),
    Achievement("tasks_20", "🏆", "Двадцатка", "Решено 20 задач"),
    Achievement("level_3", "📈", "Искатель", "Достиг 3 уровня"),
    Achievement("level_5", "🌟", "Звездочёт", "Достиг 5 уровня"),
    Achievement("no_hints", "🧠", "Своя голова", "Решил 3 задачи без подсказок"),
    Achievement("first_try", "🎯", "С первого раза", "Решил задачу первой же отправкой"),
    Achievement("streak_3", "🔥", "На трезвёрь", "Заходил решать 3 дня подряд"),
]


def _facts(user: User, session: Session):
    """Данные для правил: прогресс по задачам + история отправок."""
    progress = session.exec(
        select(Progress).where(Progress.user_id == user.id)).all()
    completed = {r.task_id: r for r in progress if r.completed}
    submissions = session.exec(
        select(Submission).where(Submission.user_id == user.id)
        .order_by(Submission.id)  # type: ignore[arg-type]
    ).all()
    return completed, submissions


def _topic_badges(session: Session) -> list[Achievement]:
    """Значки «Знаток темы» — по одному на каждую тему."""
    badges = []
    for topic in session.exec(select(Topic).order_by(Topic.order)).all():
        badges.append(Achievement(
            key=f"topic:{topic.slug}", emoji=topic.icon or "🎓",
            title=f"Знаток «{topic.title}»",
            desc=f"Решил все задачи темы «{topic.title}»",
        ))
    return badges


def _topic_state(session: Session):
    """→ (список тем, соответствие lesson_id → topic_id, все task_id по темам)."""
    topics = session.exec(select(Topic).order_by(Topic.order)).all()
    lessons = session.exec(select(Lesson)).all()
    lesson_topic = {l.id: l.topic_id for l in lessons}
    tasks_by_topic: dict[int, set[int]] = {t.id: set() for t in topics}
    for task in session.exec(select(Task)).all():
        topic_id = lesson_topic.get(task.lesson_id)
        if topic_id in tasks_by_topic:
            tasks_by_topic[topic_id].add(task.id)
    return topics, tasks_by_topic


def _rules(user: User, session: Session,
           completed: dict, submissions) -> dict[str, bool]:
    """→ {key: открыт ли} для всех известных значков."""
    n = len(completed)
    level = user.xp // LEVEL_XP + 1

    # без подсказок: минимум 3 решённые задачи, где hints_used == 0
    no_hints = sum(1 for r in completed.values() if r.hints_used == 0) >= 3

    # «с первого раза»: первая отправка по решённой задаче была accepted
    first_sub: dict[int, str] = {}
    for s in submissions:
        first_sub.setdefault(s.task_id, s.status)
    first_try = any(completed[t].completed and first_sub.get(t) == "accepted"
                    for t in completed)

    # серия из 3 разных дней подряд (день — по UTC-дате отправки)
    days = sorted({s.created_at.date() for s in submissions})
    streak = any(
        (days[i + 2] - days[i]).days == 2
        for i in range(len(days) - 2)
    )

    unlocked = {
        "first_task": n >= 1,
        "tasks_5": n >= 5,
        "tasks_10": n >= 10,
        "tasks_20": n >= 20,
        "level_3": level >= 3,
        "level_5": level >= 5,
        "no_hints": no_hints,
        "first_try": first_try,
        "streak_3": streak,
    }

    # значки тем: решены ВСЕ задачи темы (и тема не пустая)
    topics, tasks_by_topic = _topic_state(session)
    for topic in topics:
        ids = tasks_by_topic.get(topic.id, set())
        unlocked[f"topic:{topic.slug}"] = bool(ids) and ids <= set(completed)
    return unlocked


def unlocked_keys(user: User, session: Session) -> set[str]:
    completed, submissions = _facts(user, session)
    return {k for k, ok in _rules(user, session, completed, submissions).items() if ok}


def catalogue(user: User, session: Session) -> list[dict]:
    """Все значки с флагом, открыт ли — для страницы профиля."""
    completed, submissions = _facts(user, session)
    state = _rules(user, session, completed, submissions)
    items = [a.as_dict(bool(state.get(a.key))) for a in _STATIC]
    items += [a.as_dict(bool(state.get(a.key))) for a in _topic_badges(session)]
    return items


def new_after(user: User, session: Session, before: set[str]) -> list[dict]:
    """Значки, открытые относительно набора `before` (для ответа на submit)."""
    after = unlocked_keys(user, session)
    fresh = after - before
    if not fresh:
        return []
    return [item for item in catalogue(user, session) if item["key"] in fresh]


def total_xp_for_level(xp: int) -> int:
    return LEVEL_XP - (xp % LEVEL_XP)
