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

# --- Письма (fastapi-users: подтверждение почты, сброс пароля) ---
# Пустой SMTP_HOST = dev-режим: письма складываются в EMAIL_OUTBOX (файл).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@pitonyata.local")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "1") == "1"
EMAIL_OUTBOX = os.getenv("EMAIL_OUTBOX", str(BASE_DIR.parent / "outbox.log"))
# Требовать подтверждение почты при входе (включить на сервере с настроенным SMTP)
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "0") == "1"

# Откуда приходят ссылки из писем (фронтенд)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Лимиты песочницы
RUNNER_TIMEOUT_SECONDS = float(os.getenv("RUNNER_TIMEOUT_SECONDS", "3"))
RUNNER_MEMORY_MB = int(os.getenv("RUNNER_MEMORY_MB", "256"))
RUNNER_CPU_SECONDS = int(os.getenv("RUNNER_CPU_SECONDS", "2"))

LEVEL_XP = 100   # XP на уровень
