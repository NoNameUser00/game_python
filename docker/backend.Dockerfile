# Бэкенд-образ: FastAPI + движок проверки кода
FROM python:3.12-slim AS base

WORKDIR /srv
# stdlib-only рантайм для песочницы, без сетевых пакетов вSlim-варианте хватит
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
