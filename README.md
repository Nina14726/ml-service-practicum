# ML Service Practicum

Проект развивается по этапам общего задания модуля: от объектной модели личного кабинета ML-сервиса до базы данных, REST API, Telegram-бота, RabbitMQ, Web-интерфейса, тестов, контейнеризации и мониторинга.

## Практическое задание №1

В файле [`object_model.py`](object_model.py) спроектирована объектная модель ML-сервиса.

Основные сущности:

- `User` и `Admin`;
- `Balance`;
- `MLModel` и `BinaryClassificationModel`;
- `MLTask` и `PredictionResult`;
- `Transaction`, `CreditTransaction`, `DebitTransaction`;
- `MLRequestHistory`.

Модель демонстрирует инкапсуляцию, композицию, наследование и полиморфизм. Дополнительная роль администратора позволяет пополнять баланс пользователей и просматривать все транзакции.

## Практическое задание №2

Добавлена воспроизводимая Docker Compose-инфраструктура для того же ML-сервиса.

### Структура

```text
.
├── app/
│   ├── src/
│   │   └── main.py
│   ├── .env
│   ├── Dockerfile
│   └── requirements.txt
├── web-proxy/
│   ├── Dockerfile
│   └── nginx.conf
├── data/
│   ├── postgres/
│   └── rabbitmq/
├── docker-compose.yml
├── object_model.py
└── README.md
```

### Сервисы

- `app` — минимальное FastAPI-приложение, конфигурируемое через `env_file`; исходники подключены через `volumes`;
- `web-proxy` — Nginx reverse proxy, зависит от `app`, публикует порты `80` и `443`;
- `rabbitmq` — RabbitMQ с management UI, портами `5672` и `15672`, постоянным хранилищем и автоматическим перезапуском при сбоях;
- `database` — PostgreSQL с постоянным локальным хранилищем данных.

Сервис `app` не публикует порт наружу напрямую. Внешние запросы проходят через `web-proxy`.

## Запуск

Требуется установленный Docker с поддержкой Docker Compose.

```bash
docker compose up --build
```

После запуска:

- приложение через Nginx: `http://localhost`;
- проверка состояния: `http://localhost/health`;
- RabbitMQ Management UI: `http://localhost:15672`;
- PostgreSQL доступен контейнерам внутри сети Docker по адресу `database:5432`.

Остановка сервисов:

```bash
docker compose down
```
