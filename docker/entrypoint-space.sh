#!/bin/sh
# Точка входа контейнера HF Spaces: uvicorn (API, внутренний) + nginx (наружу, 7860).
# Если кто-то из двоих умер — контейнер завершается, и HF перезапускает его.
set -e

# SQLite не любит нескольких писателей — при локальной БД один воркер.
WORKERS="${UVICORN_WORKERS:-2}"
case "${DATABASE_URL:-}" in
  ""|sqlite:*) WORKERS=1 ;;
esac

echo "[space] uvicorn: ${WORKERS} воркер(ов), порт 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers "$WORKERS" &
UVICORN_PID=$!

echo "[space] nginx: порт 7860"
nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true' INT TERM

# Простой надзиратель: выходим с ошибкой, если кто-то из процессов упал.
while kill -0 "$UVICORN_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 5
done
echo "[space] процесс упал — завершаем контейнер" >&2
kill "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true
exit 1
