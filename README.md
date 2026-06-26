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

## 🚀 Живое демо

**https://aquageodemo.ruletk.com/**

Аккаунты для входа — в разделе [Демо-аккаунты](#демо-аккаунты) ниже.

## Запуск (dev)

```bash
# 1. Конфигурация
cp .env.example .env        # заполнить SECRET_KEY и GEMINI_API_KEY (для ИИ-парсинга)

# 2. Поднять весь стек (db + redis + web + worker + beat + frontend).
#    Контейнер web сам применяет миграции при старте.
docker compose up --build -d

# 3. Одной командой: справочники + импорт открытых данных + реалистичный
#    демо-сид + пересчёт оценок + демо-аккаунты (идемпотентно).
docker compose exec web python manage.py bootstrap_demo
```

`bootstrap_demo` последовательно выполняет:
`seed_reference` → `import_data` + `import_org_dataset` → `generate_hydropost_history`
→ `seed_demo` (расставляет правдоподобный износ и свежие осмотры, чтобы каталог
не выглядел «сплошь аварийным») → `recompute_assessments` (пересчёт состояний и
риска) → `create_demo_users` (печатает таблицу аккаунтов).

> Сырые датасеты лежат в `backend/data/` (в `.gitignore`). Если их нет, шаги
> импорта пропускаются с предупреждением — добавьте файлы или запустите
> `bootstrap_demo --skip-import` для работы только со справочниками.

Отдельные шаги при необходимости:

```bash
docker compose exec web python manage.py seed_demo            # только демо-сид
docker compose exec web python manage.py recompute_assessments
docker compose exec web python manage.py create_demo_users    # пере-создать аккаунты
```

После старта:
- Backend / API: http://localhost:8000/api/v1/
- OpenAPI / Swagger: http://localhost:8000/api/v1/schema/swagger-ui/
- Frontend: http://localhost:5173/
- Django admin: http://localhost:8000/admin/ (логин `admin`, см. ниже)

## Демо-аккаунты

Создаются командой `create_demo_users` (или `bootstrap_demo`). Пароли
детерминированы — это **демо-учётки**, не для продакшена.

| Логин      | Пароль             | Роль      | Что может на демо                                                      |
|------------|--------------------|-----------|-----------------------------------------------------------------------|
| `viewer`   | `aquageo-viewer`   | viewer    | Карта, каталог, дашборд — только просмотр.                             |
| `engineer` | `aquageo-engineer` | engineer  | Просмотр + ИИ-парсинг (`/parse`), создание черновиков, подача заявки.  |
| `manager`  | `aquageo-manager`  | manager   | Согласование/отклонение заявок, ЭЦП-заглушка и PDF-приказ, видит всё.  |
| `admin`    | `aquageo-admin`    | admin     | Полный доступ + Django admin `/admin/` (суперпользователь).            |

## Сценарий показа (демо)

1. **Карта с фильтрами** — открыть `/`, фильтры по состоянию/бассейну/району,
   цвет маркера = тех. состояние; переключатель области (скейл на регионы).
2. **Карточка объекта** — клик по маркеру: паспорт, состояние, период осмотра.
3. **Дашборд с прогнозом** — `/dashboard`: распределение по состояниям, риск-
   детекторы (паводок/маловодье) и краткосрочный прогноз уровня.
4. **ИИ-парсинг** (под `engineer`) — `/parse`, загрузить
   `backend/data/samples/hydropost_sample.xlsx` → «Распознать»: поля с
   индикатором уверенности, бейдж сверки с базой, мини-карта.
5. **Заявка** (под `engineer`) — на экране парсинга «Отправить на согласование».
6. **Согласование с приказом** (под `manager`) — `/applications`: открыть заявку,
   «Согласовать» → ЭЦП-заглушка (`cert_subject`), PDF-приказ (скачать), объект
   становится «Опубликован».

> Инфраструктура (docker-compose, миграции, seed-команды) подключается по мере
> прохождения бэклога — см. `ISSUES.md` и `WORKFLOW.md`.

## Процесс разработки

См. [`WORKFLOW.md`](./WORKFLOW.md): ветки `main`/`develop`/`feature/*`,
PR `feature → develop → main`, auto-merge после зелёного CI.
Бэклог — в [`ISSUES.md`](./ISSUES.md), контекст проекта — в [`CLAUDE.md`](./CLAUDE.md).

## Лицензия

[MIT](./LICENSE)
