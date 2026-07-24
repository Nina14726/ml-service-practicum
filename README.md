# ML Service Practicum

## Практическое задание №1

**Тема:** проектирование объектной модели личного кабинета ML-сервиса.

На этом этапе реализована только доменная объектная модель. База данных, REST API, Telegram-бот, RabbitMQ, Web-интерфейс, Docker и мониторинг относятся к следующим заданиям модуля и здесь намеренно не добавлены.

Основной код: [`object_model.py`](object_model.py).

## Покрытие требований

| Требование | Реализация |
|---|---|
| Регистрация и авторизация | `User`, поля `email`, `__password_hash`, метод `authenticate()` |
| Роли пользователя | `UserRole`, классы `User` и `Admin` |
| Просмотр и проверка баланса | приватное поле `User.__balance`, свойства и методы `balance`, `can_afford()` |
| Пополнение баланса | `CreditTransaction`, метод администратора `top_up_user_balance()` |
| Списание только после успешного предсказания | `MLTask.run()` создаёт `DebitTransaction` после успешного `predict()` |
| ML-модель и стоимость предсказания | абстрактный класс `MLModel`, поле `prediction_cost` |
| Валидация входных данных | абстрактный метод `MLModel.validate_data()` возвращает валидные и ошибочные записи |
| Выполнение ML-запроса | класс `MLTask`, метод `run()` |
| Результат и ошибочные данные | `PredictionResult` |
| История запросов | `MLRequestHistory` |
| История транзакций | `Transaction`, `CreditTransaction`, `DebitTransaction`, история внутри `User` |
| Администратор | `Admin`: пополнение баланса пользователей и просмотр всех транзакций |

## Основные сущности

### `User`

Поля:

- `id: int` — public;
- `email: str` — public;
- `_role: UserRole` — protected;
- `_request_history: MLRequestHistory` — protected;
- `__password_hash: str` — private;
- `__balance: float` — private;
- `__transactions: list[Transaction]` — private.

Основные методы:

- `authenticate(password_hash: str) -> bool`;
- `can_afford(amount: float) -> bool`;
- `get_request_history() -> list[MLTask]`;
- `get_transactions() -> list[Transaction]`;
- `_increase_balance(amount: float) -> None`;
- `_decrease_balance(amount: float) -> None`.

### `Admin(User)`

Расширяет пользователя методами:

- `top_up_user_balance(user: User, amount: float) -> CreditTransaction`;
- `view_all_transactions(users: list[User]) -> list[Transaction]`.

### `MLModel`

Абстрактный класс модели.

Поля:

- `id: int`;
- `name: str`;
- `description: str`;
- `prediction_cost: float`.

Методы:

- `validate_data(input_data: list[Any]) -> tuple[list[Any], list[Any]]`;
- `predict(valid_data: list[Any]) -> list[Any]`;
- `calculate_cost(predictions_count: int) -> float`.

### `MLTask`

Хранит пользователя, модель, входные данные, статус и результат. Метод `run()` выполняет последовательность:

1. переводит задачу в обработку;
2. сохраняет запрос в историю;
3. валидирует данные;
4. проверяет достаточность баланса;
5. выполняет предсказание над валидными данными;
6. списывает кредиты только после успешного предсказания;
7. сохраняет результат и ошибочные записи.

### `PredictionResult`

Поля:

- `predictions: list[Any]`;
- `invalid_data: list[Any]`;
- `charged_credits: float`;
- `created_at: datetime`.

### `MLRequestHistory`

Методы:

- `add(task: MLTask) -> None`;
- `get_all() -> list[MLTask]`;
- `get_by_status(status: TaskStatus) -> list[MLTask]`.

### Транзакции

Абстрактный класс `Transaction` содержит общие поля и метод `apply()`.

Производные классы:

- `CreditTransaction` — пополнение баланса;
- `DebitTransaction` — списание кредитов.

## Принципы ООП

### Инкапсуляция

Пароль, баланс и история транзакций пользователя закрыты приватными полями. Баланс нельзя изменить прямым присваиванием — операции выполняются через методы и транзакции.

### Наследование

- `Admin` наследуется от `User`;
- `CreditTransaction` и `DebitTransaction` наследуются от `Transaction`.

### Полиморфизм

Метод `Transaction.apply()` по-разному реализован для пополнения и списания. Методы `MLModel.validate_data()` и `MLModel.predict()` будут переопределяться конкретными ML-моделями.

## Модификаторы доступа в Python

- `field` — public;
- `_field` — protected;
- `__field` — private.

## Структура репозитория

```text
ml-service-practicum/
├── README.md
└── object_model.py
```
