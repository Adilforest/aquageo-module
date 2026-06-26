# ─── build stage ─────────────────────────────────────────────────────────
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ─── runtime: nginx-unprivileged (слушает :8080, работает не от root) ──────
FROM nginxinc/nginx-unprivileged:1.27-alpine
# default.conf приходит из Helm-ConfigMap (проксирование на web-сервис),
# здесь оставляем только статику. Запуск возможен под любым uid (в т.ч. 65532).
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
