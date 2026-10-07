# Фронтенд-образ: сборка Vite → раздача nginx с прокси /api
FROM node:20-slim AS build
WORKDIR /srv
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /srv/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
