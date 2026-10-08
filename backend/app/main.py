import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, classes, progress, tasks
from .config import RUNNER_MODE
from .db import init_db
from .users import UserRead, fastapi_users

logger = logging.getLogger("game_python")

app = FastAPI(title="Питонята — обучающая игра", version="0.1.0")

# В разработке фронтенд хостится на другом порту (Vite) — разрешаем CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(classes.router, prefix="/api")

# Роуты fastapi-users: сброс пароля и подтверждение почты
app.include_router(fastapi_users.get_reset_password_router(), prefix="/api/auth")
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/api/auth")


@app.on_event("startup")
def on_startup():
    stats = init_db()
    logger.info("Контент загружен: %s | режим раннера: %s", stats, RUNNER_MODE)


@app.get("/api/health")
def health():
    return {"status": "ok", "runner": RUNNER_MODE}
