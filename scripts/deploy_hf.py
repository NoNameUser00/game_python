#!/usr/bin/env python3
"""Публикация репозитория в Hugging Face Space.

Использование:
    HF_TOKEN=hf_xxx HF_SPACE_REPO=логин/подземелья-python python3 scripts/deploy_hf.py

Запускается вручную или из GitHub Actions (.github/workflows/deploy-hf.yml).
Требует пакет huggingface_hub (в CI ставится отдельно).
"""
import os
import sys

from huggingface_hub import HfApi

# Что не тащим в Space (в образе всё нужное соберётся из Dockerfile).
IGNORE = [
    ".git/*",
    ".github/*",
    "**/node_modules/*",
    "frontend/node_modules/*",
    "backend/.venv/*",
    "**/__pycache__/*",
    "backend/game.db",
    "backend/outbox.log",
    "frontend/dist/*",
    ".env",
    ".env.*",
    "docs/design/*",
]


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    repo = os.environ.get("HF_SPACE_REPO")

    if not token or not repo:
        print("Нужны переменные окружения HF_TOKEN и HF_SPACE_REPO "
              "(например, логин/podzemelya-python).")
        return 1

    api = HfApi(token=token)
    api.upload_folder(
        folder_path=".",
        repo_id=repo,
        repo_type="space",
        commit_message="Деплой из GitHub Actions",
        ignore_patterns=IGNORE,
    )
    print(f"Опубликовано: https://huggingface.co/spaces/{repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
