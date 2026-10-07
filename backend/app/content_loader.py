"""Загрузка YAML-контента (темы → уроки → задачи) в БД с upsert по slug."""
import json
from pathlib import Path

import yaml
from sqlmodel import Session, select

from .config import CONTENT_DIR
from .models import Lesson, Task, Topic


def load_content(session: Session, content_dir: Path | None = None) -> dict:
    content_dir = content_dir or CONTENT_DIR
    stats = {"topics": 0, "lessons": 0, "tasks": 0}

    files = sorted(content_dir.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not data:
            continue

        topic = _upsert(session, Topic,
                        slug=data["slug"],
                        defaults={"title": data["title"],
                                  "icon": data.get("icon", "🐍"),
                                  "order": data.get("order", 0)})
        stats["topics"] += 1

        for lesson_data in data.get("lessons", []):
            lesson = _upsert(session, Lesson,
                             slug=lesson_data["slug"],
                             defaults={"topic_id": topic.id,
                                       "title": lesson_data["title"],
                                       "order": lesson_data.get("order", 0)})
            stats["lessons"] += 1

            for task_data in lesson_data.get("tasks", []):
                _upsert(session, Task,
                        slug=task_data["slug"],
                        defaults={
                            "lesson_id": lesson.id,
                            "title": task_data["title"],
                            "difficulty": task_data.get("difficulty", 1),
                            "xp_reward": task_data.get("xp_reward", 20),
                            "function": task_data.get("function", "solution"),
                            "prompt_md": task_data.get("prompt_md", ""),
                            "starter_code": task_data.get("starter_code", ""),
                            "hints_json": json.dumps(task_data.get("hints", []), ensure_ascii=False),
                            "tests_json": json.dumps(task_data.get("tests", []), ensure_ascii=False),
                        })
                stats["tasks"] += 1

    session.commit()
    return stats


def _upsert(session: Session, model, *, slug: str, defaults: dict):
    obj = session.exec(select(model).where(model.slug == slug)).one_or_none()
    if obj is None:
        obj = model(slug=slug, **defaults)
        session.add(obj)
        session.flush()
    else:
        for key, value in defaults.items():
            setattr(obj, key, value)
        session.add(obj)
        session.flush()
    return obj
