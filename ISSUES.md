# ISSUES.md — полный бэклог AquaGeo

Это исходный список задач от начала до конца. Claude Code создаёт их как GitHub
issues: заголовок, тело (scope, acceptance, depends), лейблы и milestone.

Milestones: M1 Фундамент, M2 Карта и каталог, M3 Оценка и прогноз,
M4 ИИ-парсинг, M5 Гос-флоу, M6 Аналитика и полировка.

Лейблы: area/backend, area/frontend, area/data, area/infra, area/ai,
area/workflow, area/design, type/feature, type/chore, type/test.

Формат заголовка MR для каждой issue: `Resolve "<заголовок issue>"`.

---

## M1 — Фундамент

### 1. Каркас бэкенда: Django, DRF, config, common
Labels: area/backend, type/chore · Milestone: M1
- Django 5 проект `config`, DRF, drf-spectacular, simplejwt, настройки через env (django-environ).
- Приложение `common`: миксины (uuid pk, timestamps), базовая пагинация, заготовка аудита.
- Acceptance: проект поднимается, `/api/v1/schema/` и админка открываются.

### 2. Docker-compose и CI
Labels: area/infra, type/chore · Milestone: M1 · Depends: #1
- docker-compose: db (postgis/postgis:16), redis, web (gunicorn), worker (celery), beat. Makefile, healthchecks.
- Развернуть CI: джоба backend (ruff + pytest с сервисом postgis, установка GDAL/GEOS), джоба frontend (npm ci + build).
- Acceptance: `docker compose up` работает, CI зелёный на пустых тестах.

### 3. Каркас фронтенда: Vite, React, TS, i18n, layout
Labels: area/frontend, type/chore · Milestone: M1 · Depends: #1
- Vite + React 18 + TS, TanStack Query, react-leaflet, Recharts, i18next (RU дефолт, KK, EN).
- Базовый layout: левое меню, шапка с переключателем языка, пустая карта OSM.
- Acceptance: фронт запускается, меню и переключатель языка работают, карта рендерится.

### 4. accounts: пользователи, роли, JWT, пермишены
Labels: area/backend, type/feature · Milestone: M1 · Depends: #1
- Кастомный User с ролью (viewer, engineer, manager, admin), JWT login и refresh.
- DRF-пермишены по ролям, базовые тесты доступа.
- Acceptance: логин выдаёт токен, пермишены ограничивают доступ по роли.

### 5. catalog: справочники ObjectType, Basin, WaterBody, AdminUnit
Labels: area/backend, type/feature · Milestone: M1 · Depends: #1
- Модели по CLAUDE.md п.5, поля name_ru/kk/en, PostGIS-геометрия у Basin и WaterBody, самоссылочный AdminUnit.
- Регистрация в админке.
- Acceptance: справочники создаются и видны в админке, миграции применяются.

### 6. catalog: Structure, Attachment, Inspection
Labels: area/backend, type/feature · Milestone: M1 · Depends: #5
- Structure с PostGIS geom, jsonb attributes, статусами, FK на справочники. Attachment и Inspection.
- Валидация attributes по JSON-схеме из ObjectType.
- Acceptance: объект с attributes проходит валидацию схемы, виден в админке.

### 7. Сиды справочников
Labels: area/data, type/feature · Milestone: M1 · Depends: #6
- Management command: типы объектов с JSON-схемами, 8 бассейнов, КАТО Жамбыла (область, районы, округа), реки Талас, Шу, Аса.
- Acceptance: после сида справочники заполнены, Шу-Таласский бассейн и реки на месте.

### 8. Импортер данных: HDX, Overpass, qazsu
Labels: area/data, type/feature · Milestone: M1 · Depends: #6, #7
- Management command: HDX GeoJSON (каналы, реки, водоёмы) + Overpass GeoJSON (плотины, шлюзы, насосные) + qazsu Excel (гидропосты с координатами) в Structure.
- Геокодинг именованных гидроузлов через Nominatim. Правдоподобные износ, состояние, дата осмотра где их нет.
- Acceptance: после импорта в базе сотни объектов Жамбыла с геометрией и типами.

### 9. API объектов: /api/v1/structures
Labels: area/backend, type/feature · Milestone: M1 · Depends: #6
- CRUD по Structure, фильтры (тип, состояние, бассейн, район), пагинация, поиск, GeoJSON-эндпоинт для карты.
- Acceptance: список с фильтрами и GeoJSON отдаются, покрыты тестами.

---

## M2 — Карта и каталог

### 10. Карта: маркеры, цвет по состоянию, кластеры, легенда
Labels: area/frontend, type/feature · Milestone: M2 · Depends: #9
- Маркеры с иконкой по типу и цветом по состоянию, кластеризация, легенда состояний и типов.
- Acceptance: объекты из API видны на карте с корректными цветом и иконкой.

### 11. Фильтры и поиск на карте
Labels: area/frontend, type/feature · Milestone: M2 · Depends: #10
- Панель фильтров (тип, состояние, бассейн, район) и поиск, связка с API.
- Acceptance: фильтры меняют выборку на карте и в списке.

### 12. Карточка объекта
Labels: area/frontend, type/feature · Milestone: M2 · Depends: #10
- Боковая панель: фото, тип, водный объект, координаты, год, бейдж состояния, ответственная организация, динамические тех. параметры по типу, осмотры, документы.
- Acceptance: клик по маркеру открывает карточку с данными объекта.

### 13. Каталог: таблица
Labels: area/frontend, type/feature · Milestone: M2 · Depends: #9
- Таблица со списком, фильтрами, пагинацией, переходом в карточку.
- Acceptance: каталог листается и фильтруется, открывает объект.

### 14. Дашборд: KPI-карточки и каркас
Labels: area/frontend, type/feature · Milestone: M2 · Depends: #9
- Верхние KPI-карточки (всего, исправно, наблюдение, ремонт, авария) и раскладка дашборда по макету организатора.
- Acceptance: KPI берутся из API и отражают реальные счётчики.

### 15. OpenAPI и Swagger UI
Labels: area/backend, type/chore · Milestone: M2 · Depends: #9
- drf-spectacular: схема и Swagger UI, аннотации эндпоинтов.
- Acceptance: Swagger UI открывается и описывает основные ресурсы.

---

## M3 — Оценка и прогноз

### 16. assessment: ConditionAssessment и расчёт состояния
Labels: area/backend, type/feature · Milestone: M3 · Depends: #6
- Модель ConditionAssessment, сервис вычисления condition_status (serviceable, monitoring, repair, emergency) и repair_status (norm, inspect, repair, critical) по CLAUDE.md п.6.
- Acceptance: сервис считает статус по входным данным, покрыт unit-тестами.

### 17. Модель периода осмотра (задача 5)
Labels: area/backend, type/feature · Milestone: M3 · Depends: #16
- next_inspection_due по состоянию, дате последнего осмотра, возрасту, аварийности, важности, сезону.
- Acceptance: даёт корректный интервал на тестовых кейсах.

### 18. Детекторы риска (задача 6 и прогноз)
Labels: area/backend, type/feature · Milestone: M3 · Depends: #16, #19
- Интерфейс RiskDetector и реестр. Детекторы: паводок (уровень против опасного, скорость роста), маловодье и засуха (падение расхода, сезон), краткосрочный прогноз уровня. Запись в risk_scores, событие risk.alert.
- Acceptance: детекторы поднимают риск на тестовых рядах, новые добавляются без правки ядра.

### 19. monitoring: HydropostReading и ряды
Labels: area/backend, type/feature · Milestone: M3 · Depends: #6
- Модель HydropostReading, генерация демо-рядов, периодический пересчёт (celery beat), API для рядов.
- Acceptance: ряды есть у гидропостов, пересчёт обновляет оценку.

### 20. Графики дашборда
Labels: area/frontend, type/feature · Milestone: M3 · Depends: #14, #16
- Recharts: по типам (donut), оценка состояния (gauge), по бассейнам (bars), динамика по месяцам (line), по значимости (bars).
- Acceptance: графики берут данные из API и согласованы по цвету состояний.

---

## M4 — ИИ-парсинг

### 21. LLM-адаптер на litellm
Labels: area/ai, type/feature · Milestone: M4 · Depends: #1
- Провайдер-агностик через litellm, модель и ключ из env (GEMINI_API_KEY для Gemini, anthropic_api_key опционально), structured-output по JSON-схеме, ретраи и обработка ошибок.
- Acceptance: смена LLM_PROVIDER и LLM_MODEL переключает провайдера без правки кода.

### 22. ingestion: ParseJob и извлечение полей
Labels: area/ai, type/feature · Milestone: M4 · Depends: #6, #21
- Модель ParseJob. Извлечение текста (PDF: текстовый слой и OCR, Excel: pandas), промпт по схеме типа, заполнение полей с confidence.
- Acceptance: из тестового Excel и PDF создаётся черновик с заполненными полями и оценкой уверенности.

### 23. Сравнение с базой (задача 4)
Labels: area/ai, type/feature · Milestone: M4 · Depends: #22, #9
- Сопоставление кандидата с базой по близости координат, similarity имени и типу, match_status (existing, new, needs_check), ссылка на совпавший объект.
- Acceptance: дубликат помечается existing, новый new, спорный needs_check.

### 24. UI загрузки и проверки черновика
Labels: area/frontend, type/feature · Milestone: M4 · Depends: #22, #23
- Дроп-зона загрузки Excel и PDF, экран проверки: поля с индикатором уверенности, правка, пометка совпадения, мини-карта по координатам, отправка на заявку.
- Acceptance: пользователь загружает файл, видит автозаполнение и отправляет на согласование.

---

## M5 — Гос-флоу, ЭЦП-заглушка, уведомления

### 25. workflow: Application и переходы статусов
Labels: area/workflow, type/feature · Milestone: M5 · Depends: #6
- Модель Application, переходы draft, submitted, approved, rejected, доменные события.
- Acceptance: заявка проходит жизненный цикл, события поднимаются.

### 26. Заглушка ЭЦП: Signature
Labels: area/workflow, type/feature · Milestone: M5 · Depends: #25
- Имитация подписи без NCALayer: выбор сертификата-заглушки, подтверждение, valid=true, запись Signature.
- Acceptance: согласование сопровождается записью подписи-заглушки.

### 27. Генерация PDF-приказа и публикация
Labels: area/workflow, type/feature · Milestone: M5 · Depends: #25
- При approve генерируется ApprovalOrder (PDF с номером), объект переходит в published, файл сохраняется.
- Acceptance: после одобрения есть PDF-приказ и объект опубликован.

### 28. notifications: модель и рассылка
Labels: area/backend, type/feature · Milestone: M5 · Depends: #25
- Модель Notification, рассылка по событиям (in-app и email), счётчик непрочитанных, API.
- Acceptance: подача и решение по заявке создают уведомления адресатам.

### 29. AuditLog: журнал действий
Labels: area/backend, type/feature · Milestone: M5 · Depends: #25
- Запись действий и подписей (кто, что, когда), просмотр в админке и в API.
- Acceptance: ключевые действия фиксируются в журнале.

### 30. UI гос-флоу
Labels: area/frontend, type/feature · Milestone: M5 · Depends: #25, #26, #27
- Список заявок, карточка заявки, кнопки согласовать и отклонить, экран подписания, просмотр PDF-приказа, статусные бейджи.
- Acceptance: руководитель проходит согласование с подписью и видит приказ.

---

## M6 — Аналитика и полировка

### 31. Аналитика и отчёты с экспортом
Labels: area/backend, area/frontend, type/feature · Milestone: M6 · Depends: #16, #20
- Сводки по состоянию, типам, бассейнам, экспорт PDF и Excel.
- Acceptance: отчёт формируется и выгружается.

### 32. Полный i18n
Labels: area/frontend, type/feature · Milestone: M6 · Depends: #3
- Переводы всех экранов и справочников на RU, KK, EN.
- Acceptance: переключение языка меняет интерфейс целиком без пропусков.

### 33. Скейл на регионы
Labels: area/backend, area/frontend, type/feature · Milestone: M6 · Depends: #9
- Переключатель региона и бассейна, проверка фильтров и карты на другом регионе.
- Acceptance: смена региона корректно меняет выборку и центрирование карты.

### 34. Демо-сценарий end-to-end
Labels: area/infra, type/chore · Milestone: M6 · Depends: many
- Сид демо-данных, сквозной сценарий (импорт, карта, оценка, ИИ-парсинг, заявка, подпись, приказ), README с запуском, полировка UI по макету.
- Acceptance: демо проходится от старта до приказа без ручных правок.
