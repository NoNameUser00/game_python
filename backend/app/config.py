"""Конфигурация приложения (переопределяется переменными окружения)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = BASE_DIR.parent                       # backend/
CONTENT_DIR = BASE_DIR / "content"

# В будущем на сервере: postgresql+psycopg://...
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'game.db'}")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

# Режим движка проверки кода: local (subprocess) | docker (позже, на сервере)
RUNNER_MODE = os.getenv("RUNNER_MODE", "local")

# Лимиты песочницы
RUNNER_TIMEOUT_SECONDS = float(os.getenv("RUNNER_TIMEOUT_SECONDS", "3"))
RUNNER_MEMORY_MB = int(os.getenv("RUNNER_MEMORY_MB", "256"))
RUNNER_CPU_SECONDS = int(os.getenv("RUNNER_CPU_SECONDS", "2"))

LEVEL_XP = 100   # XP на уровень
