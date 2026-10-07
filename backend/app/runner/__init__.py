"""Движок проверки кода учеников.

ВАЖНО (безопасность): это выполнение НЕЧУЖЕГО кода.
- local: subprocess с лимитами (CPU/память/время) — только для локальной разработки,
  доверенный контекст (один ученик за своим компьютером).
- docker: на публичном сервере ОБЯЗАТЕЛЬНО (--network none --memory 128m --pids-limit 64),
  включается через RUNNER_MODE=docker.
"""
from .local import LocalRunner, RunOutcome, TestResult


def get_runner(mode: str | None = None):
    from ..config import RUNNER_MODE

    mode = mode or RUNNER_MODE
    if mode == "local":
        return LocalRunner()
    if mode == "docker":
        raise NotImplementedError("DockerRunner будет добавлен при деплое на сервер")
    raise ValueError(f"Неизвестный режим раннера: {mode}")


__all__ = ["LocalRunner", "RunOutcome", "TestResult", "get_runner"]
