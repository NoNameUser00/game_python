# Hugging Face Spaces (SDK: docker) — единый контейнер:
#   nginx слушает :7860 (порт Spaces), uvicorn внутри на 127.0.0.1:8000.
# Локальная проверка образа:
#   docker build -t podzemelya-space .
#   docker run --rm -p 7860:7860 podzemelya-space   # http://127.0.0.1:7860
FROM node:20-slim AS webbuild
WORKDIR /srv
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=webbuild /srv/dist ./dist

# nginx: статика фронта + reverse-proxy /api, SPA-fallback
COPY docker/nginx-space.conf /etc/nginx/conf.d/default.conf
COPY docker/entrypoint-space.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7860
ENTRYPOINT ["/entrypoint.sh"]
