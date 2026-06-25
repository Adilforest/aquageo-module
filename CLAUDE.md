# CLAUDE.md — Модуль портала водных ресурсов (AquaGeo)

Это постоянный контекст проекта для Claude Code. Читай его перед работой.

## 1. Что строим

Модуль для портала aquageo.kz: каталог, мониторинг, анализ и редактирование
гидротехнических сооружений (ГТС) и гидропостов. Фокус на Жамбылской области
(Шу-Таласский водохозяйственный бассейн), с возможностью скейла на другие
регионы Казахстана. Контекст: хакатон AITU Hackday (Industry 4.0).

Главный приоритет демо: **живая интерактивная карта с аналитикой**.
Авторские фичи владельца проекта:
- ИИ-парсинг документа (Excel/PDF) при добавлении объекта с автозаполнением полей.
- Гос-флоу подачи и согласования заявки с ЭЦП. В демо ЭЦП это **заглушка**
  (без NCALayer), показывающая возможный функционал.

## 2. Стек

- Backend: Python 3.12, Django 5, Django REST Framework, GeoDjango (PostGIS).
- Async и события: Celery + Redis (брокер и кэш).
- БД: PostgreSQL 16 + PostGIS. Опция: managed Supabase Postgres с включённым
  расширением postgis (Supabase MCP уже подключён у владельца).
- Хранилище файлов (фото, PDF-приказы, исходники импорта): локальный volume
  через django-storages, либо Supabase Storage.
- LLM: провайдер-агностик через **litellm**. Модель и ключ из .env. Основной
  провайдер Gemini (Google AI Studio), Anthropic как альтернатива одной строкой.
- Frontend: React 18 + Vite + TypeScript, react-leaflet (растровые тайлы OSM),
  i18next (RU по умолчанию, KK, EN), TanStack Query, графики на Recharts.
- API: REST под /api/v1, OpenAPI через drf-spectacular, JWT (djangorestframework-simplejwt).

## 3. Git и GitHub

Репозиторий приватный, через gh:
- git init, .gitignore (Python, Node, .env, backend/data/*).
- `gh repo create aquageo-module --private --source=. --remote=origin --push`
- Ветки: main стабильная, feature-ветка на каждый milestone, PR через `gh pr create`.
- Коммиты атомарные, conventional commits (feat:, fix:, chore:, docs:).
- Пушить после каждого осмысленного шага.

## 4. Структура (монорепо)

```
backend/        Django проект (config/) + apps
frontend/       Vite React TS
data/           исходные датасеты (в .gitignore)
docs/           документация
docker-compose.yml
.env.example
```

Django apps:
- common: базовые модели и миксины (timestamps, uuid pk), пагинация, аудит.
- accounts: пользователи, роли, JWT, пермишены.
- catalog: ObjectType, Structure, WaterBody, Basin, AdminUnit, Attachment.
- monitoring: HydropostReading (временной ряд), адаптеры источников.
- assessment: ConditionAssessment, сервис оценки состояния, детекторы риска.
- ingestion: ParseJob, ИИ-парсинг, сравнение с базой, импорт OSM/Excel.
- workflow: Application, Signature (заглушка), ApprovalOrder, генерация PDF.
- notifications: Notification, рассылка по событиям.

## 5. Модель данных (утверждена)

Принцип: одна таблица `Structure` для всех типов объектов. Тип-специфичные
параметры лежат в JSONB-поле `attributes` и валидируются по JSON-схеме из
`ObjectType.schema`. Поля `condition_status` и `repair_status` **вычисляются**
сервисом assessment, руками не вводятся. `HydropostReading` это временной ряд
под прогноз. `AdminUnit` самоссылочный (КАТО: область → район → округ), это
механизм скейла на регионы (новые строки, а не новая система).

Сущности и ключевые поля:

- ObjectType: code (PK), name_ru, name_kk, name_en, schema (json), geometry_kind
  (point|line|polygon). Типы: canal, hydropost, lock, water_intake,
  pumping_station, dam, dike, reservoir, hydro_unit, spillway, pond.
- Basin: id, name_ru/kk/en, geom (polygon). Восемь ВХБ Казахстана.
- WaterBody: id, name_ru/kk/en, kind, basin_id (FK), geom.
- AdminUnit: kato (PK), name_ru, name_kk, level (region|district|okrug),
  parent_id (FK, self).
- Structure: id (uuid PK), type (FK ObjectType), name_ru/kk/en, geom (PostGIS),
  water_body_id (FK), basin_id (FK), admin_unit (FK), commissioning_year,
  wear_percent (износ), ownership, cadastral_number, state_act,
  responsible_org, significance (republican|regional|district|local),
  condition_status (вычисляется), status (lifecycle, см. п.6),
  attributes (jsonb), created_by, timestamps.
- Inspection: id, structure_id (FK), inspected_at, inspector,
  condition_observed, wear_percent, notes.
- ConditionAssessment: id, structure_id (FK), assessed_at, condition_status,
  repair_status, next_inspection_due, risk_scores (jsonb), model_version.
- HydropostReading: id, structure_id (FK), ts, water_level, danger_level,
  discharge, water_temp, status_code.
- Attachment: id, structure_id (FK, nullable), kind (photo|passport|act|order|source_file),
  file, uploaded_by, created_at.
- Application: id, structure_id (FK), kind (create|update|decommission),
  status (см. п.6), submitted_by (FK User), reviewer_id (FK User),
  submitted_at, decided_at, comment.
- Signature (заглушка): id, application_id (FK), signer, signed_at,
  cert_subject, cms_blob, valid (bool).
- ApprovalOrder: id, application_id (FK), number, file, issued_at.
- ParseJob: id, source_kind (excel|pdf|overpass|manual), file (nullable),
  status, raw_extract (jsonb), confidence (jsonb по полям), match_status
  (existing|new|needs_check), matched_structure_id (FK), result_structure_id (FK),
  created_by.
- Notification: id, recipient (FK User), kind, message, related_entity, read,
  created_at.
- AuditLog: id, actor, action, entity_type, entity_id, payload, created_at.

RBAC роли держим на User (см. п.7).

## 6. Машины состояний (v1, можно уточнить)

Structure.status: draft → pending_review → published → archived.
Из published возможен decommission_requested → archived (через заявку).

Application.status: draft → submitted → (approved | rejected).
approved триггерит: signature.created (заглушка) → order.generated →
structure.published → notify(author).

Structure.condition_status (вычисляется): serviceable | monitoring | repair | emergency.
ConditionAssessment.repair_status: norm | inspect | repair | critical.

## 7. Роли и права (v1)

- viewer (публичный/гость): чтение карты, каталога, аналитики.
- engineer/analyst: создание и редактирование черновиков, загрузка файлов,
  запуск ИИ-парсинга, подача заявки.
- manager (руководитель): согласование и отклонение заявок, подпись (заглушка),
  просмотр всего.
- admin: справочники, типы объектов, пользователи, всё.

DRF-пермишены по ролям на каждый ресурс.

## 8. Каталог доменных событий (v1)

```
file.uploaded        -> parse.requested -> parse.completed (черновик, confidence, match_status)
structure.draft_created
application.submitted -> notify(manager)
application.approved  -> signature.created(stub) -> order.generated -> structure.published -> notify(author)
application.rejected  -> notify(author)
inspection.logged    -> assessment.recompute -> [risk.alert при превышении порога] -> notify
reading.ingested     -> assessment.recompute (для гидропоста)
```

Реализация: Django-сигналы для синхронных реакций, Celery-задачи для
асинхронных (парсинг, рассылка, пересчёт состояния, генерация PDF).

## 9. Прогноз (детекторы риска)

Набор детекторов поверх рядов HydropostReading, каждый возвращает уровень
риска и пояснение, результаты в ConditionAssessment.risk_scores, при
превышении порога поднимают событие risk.alert:
- паводок: фактический уровень против опасного, скорость роста.
- маловодье и засуха: падение расхода ниже нормы, сезонный контекст.
- краткосрочный прогноз уровня: простая модель на истории (скользящее среднее
  или линейный тренд; позже можно ARIMA или Prophet).

Архитектурно это интерфейс RiskDetector с реестром, новые детекторы
добавляются без переписывания.

## 10. Конфиг и .env

```
DEBUG=
SECRET_KEY=
DATABASE_URL=postgis://user:pass@db:5432/aquageo
REDIS_URL=redis://redis:6379/0
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.0-flash
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
STORAGE_BACKEND=local
SUPABASE_URL=
SUPABASE_KEY=
```

Используем `GEMINI_API_KEY` как ключ Google AI Studio: litellm читает его сам
из окружения для моделей `gemini/*`, поэтому в коде ключ руками не передаём.
`ANTHROPIC_API_KEY` — опциональная альтернатива (litellm так же читает его для
моделей `anthropic/*`). Смена LLM это правка `LLM_PROVIDER` + `LLM_MODEL` +
соответствующего ключа в `.env`, код не трогаем (litellm читает model-строку).
Для structured-output (извлечение полей) используем JSON-режим и схему типа
объекта.

## 11. Runtime (docker-compose)

Сервисы: db (postgis/postgis:16), redis, web (Django + gunicorn), worker
(celery), beat (celery beat для периодических импортов и пересчётов),
frontend (vite dev или собранный nginx). При Supabase db уходит в managed,
остаётся redis, web, worker, beat, frontend.

## 12. i18n

Frontend: i18next, namespaces, RU дефолт, переключатель RU/KK/EN. Backend:
справочники (ObjectType, Basin, статусы) с полями name_ru/name_kk/name_en;
свободный текст (имена объектов) как есть плюс опциональные name_kk/name_en;
из OSM сразу маппим name:kk в name_kk.

## 13. Источники данных (в backend/data/)

1. HDX Kazakhstan Waterways (GeoJSON, lines и polygons): каналы, реки, водоёмы, name:kk.
2. qazsu гидропосты (Excel): посты с координатами, демо-вход для импорта.
3. Overpass export (GeoJSON): плотины, шлюзы, дамбы, насосные.

Импортер (management command) маппит их в ObjectType/Structure, проставляет
geom, basin, admin_unit. Реальные именованные гидроузлы (Таласский, Ассинский,
Фурмановский, Тасоткель) геокодим по имени через Nominatim/OSM. Дату осмотра,
износ и тех. состояние, которых нет в источнике, генерируем правдоподобно для демо.

## 14. Milestones

- M1 (фундамент): scaffold монорепо, Django + DRF + PostGIS, docker-compose,
  модели catalog и accounts по п.5, админка, JWT, management command сид из
  data/. Создать приватный gh-репо и запушить.
  Acceptance: docker up работает, объекты видны в админке и в /api/v1/structures,
  на карте фронта точки рендерятся.
- M2 (карта и каталог): фронт react-leaflet, слои по типам, цвет маркера по
  состоянию, легенда, карточка объекта, фильтры, список, OpenAPI и Swagger.
- M3 (оценка и прогноз): сервис assessment, детекторы риска, периодический
  пересчёт, индикаторы и графики на дашборде.
- M4 (ИИ-парсинг): загрузка Excel/PDF, litellm-извлечение по JSON-схеме типа,
  ParseJob с confidence, сравнение с базой (match_status), экран проверки черновика.
  Важно: если в файле есть колонки координат, гидропост сразу падает на карту.
- M5 (гос-флоу): заявка, согласование, заглушка подписи, генерация PDF-приказа,
  уведомления, аудит.
- M6 (аналитика и полировка): дашборд по макету организатора, отчёты и экспорт,
  полный i18n, сквозной демо-сценарий.

M1 не зависит от M3-M6, стартовать можно сразу.

## 15. Конвенции

- API /api/v1, snake_case в JSON, пагинация, фильтры через django-filter.
- drf-spectacular для схемы и Swagger UI.
- Тесты (pytest) на сервис оценки и на парсинг.
- Не коммитить .env и data/*. Держать .env.example в актуальном виде.
