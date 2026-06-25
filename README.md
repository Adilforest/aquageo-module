# AquaGeo — модуль портала водных ресурсов

Каталог, мониторинг, анализ и редактирование гидротехнических сооружений (ГТС)
и гидропостов. Фокус на Жамбылской области (Шу-Таласский водохозяйственный
бассейн) с возможностью масштабирования на другие регионы Казахстана.

Проект хакатона **AITU Hackday: Time for Industry 4.0 is now**.

## Возможности

- 🗺️ Живая интерактивная карта объектов с цветовой индикацией состояния.
- 📇 Цифровой каталог ГТС с техническими паспортами и геопривязкой.
- 📊 Аналитика и дашборд по состоянию инфраструктуры.
- 🤖 ИИ-парсинг документов (Excel/PDF) с автозаполнением полей при добавлении объекта.
- 🧮 Модель оценки состояния, периода осмотра и необходимости ремонта.
- 🏛️ Гос-флоу подачи и согласования заявок с заглушкой ЭЦП и генерацией приказа.

## Стек

| Слой       | Технологии                                                                 |
|------------|---------------------------------------------------------------------------|
| Backend    | Python 3.12, Django 5, Django REST Framework, GeoDjango (PostGIS)         |
| Async      | Celery + Redis                                                             |
| БД         | PostgreSQL 16 + PostGIS (опция: Supabase managed Postgres)                |
| LLM        | provider-agnostic через litellm (Gemini по умолчанию, Anthropic опц.)     |
| Frontend   | React 18 + Vite + TypeScript, react-leaflet, TanStack Query, Recharts     |
| i18n       | i18next (RU по умолчанию, KK, EN)                                          |
| API        | REST `/api/v1`, OpenAPI через drf-spectacular, JWT (simplejwt)            |

## Структура (монорепо)

```
backend/    Django проект (config/) + apps
frontend/   Vite React TS
data/        исходные датасеты (в .gitignore)
docs/        документация
```

## Запуск (dev)

```bash
# 1. Конфигурация
cp .env.example .env        # заполнить SECRET_KEY и GEMINI_API_KEY

# 2. Поднять стек (db + redis + web + worker + beat + frontend)
docker compose up --build

# 3. Применить миграции и засидить справочники/данные
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_reference
docker compose exec web python manage.py import_data
```

После старта:
- Backend / API: http://localhost:8000/api/v1/
- OpenAPI / Swagger: http://localhost:8000/api/v1/schema/swagger-ui/
- Frontend: http://localhost:5173/

> Инфраструктура (docker-compose, миграции, seed-команды) подключается по мере
> прохождения бэклога — см. `ISSUES.md` и `WORKFLOW.md`.

## Процесс разработки

См. [`WORKFLOW.md`](./WORKFLOW.md): ветки `main`/`develop`/`feature/*`,
PR `feature → develop → main`, auto-merge после зелёного CI.
Бэклог — в [`ISSUES.md`](./ISSUES.md), контекст проекта — в [`CLAUDE.md`](./CLAUDE.md).

## Лицензия

[MIT](./LICENSE)
