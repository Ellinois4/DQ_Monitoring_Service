# DQ Monitoring Service

Вторая версия MVP для дипломного проекта по мониторингу качества данных.

## Что реализовано
- FastAPI backend для управления метаданными и запуска проверок.
- Безопасный шаблонный SQL-движок для DQ-checks.
- React + MUI frontend с формой настройки проверок.
- PostgreSQL как хранилище метаданных, запусков и результатов.
- Отдельный `worker`, который выполняет плановые проверки по `schedule_interval_minutes`.
- Email-уведомления через MailHog.
- Dashboard с трендом результатов, состоянием проверок и историей запусков.
- Просмотр `sample bad rows` для каждого запуска.
- Mermaid ER-диаграмма в `docs/ER_DIAGRAM.md`.

## Структура
- `backend/` — API, runner и worker.
- `frontend/` — интерфейс администратора.
- `sql/init.sql` — инициализация БД и demo-данных.
- `docs/ER_DIAGRAM.md` — ER-диаграмма метаданных.
- `docker-compose.yml` — PostgreSQL, backend, worker, frontend, MailHog.

## Запуск
```bash
docker compose down -v
docker compose up --build
```

После запуска:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- MailHog: http://localhost:8025

## Demo-сценарий
1. Открыть форму и посмотреть преднастроенные проверки.
2. Запустить одну из проверок вручную.
3. Открыть детали результата и посмотреть `sample_payload`.
4. Проверить письмо в MailHog.
5. Оставить worker включённым и дождаться планового запуска по интервалу.

## Что можно развить дальше
- scheduler на cron-выражениях вместо интервала;
- несколько datasource и отдельные секреты для подключений;
- роли и разграничение доступа;
- интеграция с Grafana/Superset;
- звонок дежурному через Twilio;
- webhook/NOTIFY-trigger после обновления таблицы.


## Если менялись SQL-скрипты
Инициализация Postgres выполняется только на пустом volume, поэтому после изменений `sql/init.sql` нужно запускать `docker compose down -v` перед повторной сборкой.


## Расширенный каталог DQ-проверок

В этой версии каталог проверок расширен по измерениям качества данных DAMA-DMBOK. 
Код проверок разнесён по папкам:

```text
backend/app/check_catalog/
├── timeliness/
├── validity/
├── completeness/
├── reasonableness/
├── consistency/
├── conformity/
├── uniqueness/
└── integrity/
```

Общий реестр шаблонов собирается в `backend/app/check_catalog/__init__.py`, а движок исполнения находится в `backend/app/checks.py`.

Подробное описание параметров и кодов проверок находится в `docs/CHECK_CATALOG.md`.

## Переработанный интерфейс и роли

В новой версии интерфейс разделён на два основных раздела:

1. **Настройка проверок** — доступна только роли `admin`.
2. **Мониторинг проверок** — доступен ролям `admin` и `user`.

В верхней панели frontend добавлен переключатель роли. Это демонстрационный вариант авторизации для дипломного проекта: frontend передаёт роль в заголовке `X-User-Role`, а backend ограничивает административные операции.

Администратору доступны:
- создание проверки;
- ручной запуск проверки;
- включение и отключение проверки через `is_enabled`;
- просмотр мониторинга и результатов.

Обычному пользователю доступны:
- выбор таблицы;
- просмотр списка проверок;
- просмотр последнего статуса и результата;
- просмотр sample payload.

Отключение проверки реализовано как soft-disable: запись не удаляется из `dq_check_config`, а поле `is_enabled` переводится в `false`. История запусков и результатов сохраняется.

### Новые/изменённые API

- `GET /api/me` — возвращает текущую роль из заголовка.
- `GET /api/check-configs?dataset_id=...&include_disabled=true` — возвращает проверки с расширенной информацией о таблице, измерении и последнем результате.
- `PATCH /api/check-configs/{id}/enabled` — включает или отключает проверку, доступно только admin.
- `POST /api/check-configs` — создание проверки, доступно только admin.
- `POST /api/check-configs/{id}/run` — ручной запуск проверки, доступно только admin.

## Demo dataset for UI testing

The updated initialization script creates a small demo table:

```text
demo.dq_demo_orders
```

It contains intentionally dirty records for testing DQ checks:

- NULL and blank emails;
- invalid country code `ZZ`;
- negative amount;
- unrealistic age;
- future timestamps;
- duplicate `order_id`;
- mutually exclusive INN fields filled together;
- broken reference to `demo.demo_customers`;
- orders without rows in `demo.demo_order_items`.

Auxiliary demo tables are also created:

```text
demo.ref_country
demo.demo_customers
demo.demo_payments
demo.demo_order_items
```

After changing `sql/init.sql`, recreate the database volume:

```bash
docker compose down -v
docker compose up --build
```

If the UI shows `Failed to fetch`, open `http://localhost:8000/health`. The frontend waits for the backend healthcheck in Docker Compose, but after manual starts the browser page may still need a refresh or the `Повторить` button.
