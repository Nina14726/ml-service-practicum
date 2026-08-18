# ML Service Practicum — Video Analysis

Финальный учебный проект модуля по разработке ML-сервисов на Python.

Сервис предоставляет личный кабинет для анализа коротких видео с помощью Gemini. Пользователь регистрируется, авторизуется, пополняет учебный баланс, загружает видео и получает структурированный режиссёрский разбор. Задачи обрабатываются асинхронно через RabbitMQ и workers, история запросов и транзакций сохраняется в PostgreSQL.

## Возможности

- регистрация и авторизация пользователя;
- личный кабинет и учебный баланс;
- пополнение баланса;
- загрузка MP4, MOV и WebM до 100 МБ и до 60 секунд;
- асинхронная постановка задач через RabbitMQ;
- обработка несколькими workers;
- реальный видео-анализ через Gemini API;
- возврат списанных кредитов при ошибке обработки;
- Master Breakdown и Script Breakdown по таймкодам;
- reproduction prompt для создания похожего видео;
- история анализов и транзакций;
- выгрузка результата в MD/PDF;
- Prometheus-метрики;
- готовый Grafana dashboard;
- application logging;
- pytest и GitHub Actions.

## Архитектура

```text
Browser
  |
Nginx
  |
FastAPI app ---- PostgreSQL
  |
RabbitMQ
  |
worker-1 / worker-2
  |
Gemini API

FastAPI /metrics --> Prometheus --> Grafana
```

Основные Docker Compose сервисы:

- `app` — FastAPI REST API и WebUI;
- `database` — PostgreSQL;
- `rabbitmq` — очередь задач;
- `worker-1`, `worker-2` — обработчики ML-задач;
- `web-proxy` — Nginx;
- `prometheus` — сбор метрик;
- `grafana` — визуализация мониторинга.

## Быстрый запуск

### 1. Подготовить переменные окружения

```bash
cp app/.env.example app/.env
```

Заполните `GEMINI_API_KEY` и укажите поддерживаемую модель в `GEMINI_MODEL`.

Для Grafana рекомендуется задать пароль администратора перед запуском:

```bash
export GRAFANA_ADMIN_PASSWORD='your-strong-password'
```

### 2. Запустить проект

```bash
docker compose up -d --build
```

### 3. Проверить состояние

```bash
docker compose ps
```

Health endpoint:

```text
http://localhost/health
```

WebUI:

```text
http://localhost/web
```

Swagger:

```text
http://localhost/docs
```

Grafana:

```text
http://localhost:3000
```

Логин Grafana по умолчанию: `admin`. Пароль берётся из `GRAFANA_ADMIN_PASSWORD`, если переменная не задана — `admin`.

Prometheus работает внутри Docker-сети и собирает метрики FastAPI с `/metrics`.

## Мониторинг

FastAPI публикует технические и бизнес-метрики:

- `ml_service_http_requests_total` — количество HTTP-запросов;
- `ml_service_http_request_duration_seconds` — длительность запросов;
- `ml_service_http_requests_active` — активные запросы;
- `ml_service_users_total` — количество зарегистрированных пользователей;
- `ml_service_ml_requests_total` — синхронные ML-запросы;
- `ml_service_prediction_tasks_total{status=...}` — асинхронные задачи по статусам;
- `ml_service_transactions_total{type=...}` — credit/debit/refund операции.

Grafana автоматически получает Prometheus datasource и dashboard `ML Service Monitoring` с основными панелями: пользователи, успешные анализы, RPS, p95 latency, HTTP errors и транзакции.

Prometheus хранит метрики 7 дней в отдельном Docker volume.

## Логирование

Приложение пишет логи в stdout контейнера с timestamp, уровнем, logger name и сообщением. Уровень задаётся через `LOG_LEVEL`.

Просмотр логов:

```bash
docker compose logs -f app
```

Worker logs:

```bash
docker compose logs -f worker-1 worker-2
```

## Тестирование

```bash
cd app
pytest
```

Тесты покрывают пользовательские сценарии регистрации, авторизации, баланса, списаний, ML-запросов, истории и worker/refund. Для тестового набора реальный `GEMINI_API_KEY` не требуется.

GitHub Actions автоматически запускает pytest для изменений в репозитории.

## Основной пользовательский сценарий для демонстрации

1. Открыть WebUI.
2. Зарегистрировать пользователя.
3. Авторизоваться.
4. Открыть личный кабинет и показать баланс.
5. Пополнить баланс.
6. Загрузить видео.
7. Запустить анализ.
8. Дождаться результата Gemini.
9. Показать Master Breakdown и Script Breakdown.
10. Показать копирование/выгрузку результата.
11. Открыть историю анализов и транзакций.
12. Открыть Grafana и показать метрики сервиса.

## Остановка

```bash
docker compose down
```

Чтобы удалить также сохранённые Docker volumes:

```bash
docker compose down -v
```

Команду с `-v` не следует использовать, если нужно сохранить базу данных, RabbitMQ, Prometheus и Grafana данные.
