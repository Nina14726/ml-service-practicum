"""Object model for an ML-service personal account.

The module contains the domain model required by practical assignment 1.
It deliberately does not include persistence, REST, Telegram, RabbitMQ,
web UI, Docker, tests, or monitoring because those belong to later stages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeAlias
from uuid import UUID, uuid4


DataRow: TypeAlias = dict[str, Any]
PredictionValue: TypeAlias = int | float | str


class UserRole(str, Enum):
    """Roles required by the service."""

    USER = "user"
    ADMIN = "admin"


class TaskStatus(str, Enum):
    """Possible states of an ML task."""

    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionType(str, Enum):
    """Types of balance transactions."""

    CREDIT = "credit"
    DEBIT = "debit"


class PredictionResult:
    """Result of processing one ML task."""

    def __init__(
        self,
        predictions: list[PredictionValue],
        invalid_data: list[DataRow],
        charged_credits: float,
    ) -> None:
        self.predictions: list[PredictionValue] = predictions
        self.invalid_data: list[DataRow] = invalid_data
        self.charged_credits: float = charged_credits
        self.created_at: datetime = datetime.now(timezone.utc)


class MLRequestHistory:
    """History of a user's ML requests.

    Access modifiers:
        __tasks: private.
    """

    def __init__(self) -> None:
        self.__tasks: list[MLTask] = []

    def add(self, task: MLTask) -> None:
        """Add a task to history once."""
        if task not in self.__tasks:
            self.__tasks.append(task)

    def get_all(self) -> list[MLTask]:
        """Return a copy of all tasks."""
        return list(self.__tasks)

    def get_by_status(self, status: TaskStatus) -> list[MLTask]:
        """Return tasks filtered by status."""
        return [task for task in self.__tasks if task.status == status]


class Balance:
    """Balance and transaction history of a service account.

    Access modifiers:
        __amount, __transactions: private.
    """

    def __init__(self) -> None:
        self.__amount: float = 0.0
        self.__transactions: list[Transaction] = []

    @property
    def amount(self) -> float:
        """Return the current amount without allowing direct modification."""
        return self.__amount

    def can_afford(self, amount: float) -> bool:
        """Check whether the balance is sufficient."""
        return amount >= 0 and self.__amount >= amount

    def increase(self, amount: float) -> None:
        """Increase the balance by a positive amount."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.__amount += amount

    def decrease(self, amount: float) -> None:
        """Decrease the balance after checking available funds."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.can_afford(amount):
            raise ValueError("Insufficient balance")
        self.__amount -= amount

    def add_transaction(self, transaction: Transaction) -> None:
        """Record a balance transaction."""
        self.__transactions.append(transaction)

    def get_transactions(self) -> list[Transaction]:
        """Return a copy of the transaction history."""
        return list(self.__transactions)


class User:
    """User of the ML service.

    Access modifiers:
        id, email: public;
        _role, _request_history, _balance: protected;
        __password_hash: private.
    """

    def __init__(
        self,
        user_id: int,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ) -> None:
        self.id: int = user_id
        self.email: str = email
        self._role: UserRole = role
        self._request_history: MLRequestHistory = MLRequestHistory()
        self._balance: Balance = Balance()
        self.__password_hash: str = password_hash

    @property
    def role(self) -> UserRole:
        """Return the user's role."""
        return self._role

    @property
    def balance(self) -> float:
        """Return the current balance."""
        return self._balance.amount

    def authenticate(self, password_hash: str) -> bool:
        """Check authorization data."""
        return self.__password_hash == password_hash

    def can_afford(self, amount: float) -> bool:
        """Check whether the account balance is sufficient."""
        return self._balance.can_afford(amount)

    def get_request_history(self) -> list[MLTask]:
        """Return the user's ML request history."""
        return self._request_history.get_all()

    def get_transactions(self) -> list[Transaction]:
        """Return the user's transaction history."""
        return self._balance.get_transactions()


class Admin(User):
    """Administrator with additional balance-management permissions."""

    def __init__(self, user_id: int, email: str, password_hash: str) -> None:
        super().__init__(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )

    def top_up_user_balance(self, user: User, amount: float) -> CreditTransaction:
        """Approve and perform a user's balance top-up."""
        transaction = CreditTransaction(user=user, amount=amount)
        transaction.apply()
        return transaction

    def view_all_transactions(self, users: list[User]) -> list[Transaction]:
        """Return all transactions for administration."""
        transactions: list[Transaction] = []
        for user in users:
            transactions.extend(user.get_transactions())
        return transactions


class MLModel(ABC):
    """Abstract base class for an ML model available in the service."""

    def __init__(
        self,
        model_id: int,
        name: str,
        description: str,
        prediction_cost: float,
    ) -> None:
        if prediction_cost < 0:
            raise ValueError("Prediction cost cannot be negative")

        self.id: int = model_id
        self.name: str = name
        self.description: str = description
        self.prediction_cost: float = prediction_cost

    @abstractmethod
    def validate_data(
        self,
        input_data: list[DataRow],
    ) -> tuple[list[DataRow], list[DataRow]]:
        """Return valid and invalid input rows."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, valid_data: list[DataRow]) -> list[PredictionValue]:
        """Return predictions for valid input rows."""
        raise NotImplementedError

    def calculate_cost(self, predictions_count: int) -> float:
        """Calculate the total cost for successful predictions."""
        if predictions_count < 0:
            raise ValueError("Predictions count cannot be negative")
        return self.prediction_cost * predictions_count


class BinaryClassificationModel(MLModel):
    """Concrete ML-model example demonstrating inheritance and polymorphism.

    A row is valid when it contains a numeric value in ``feature_name``.
    Prediction is 1 when the value is at least ``threshold``, otherwise 0.
    """

    def __init__(
        self,
        model_id: int,
        name: str,
        description: str,
        prediction_cost: float,
        feature_name: str,
        threshold: float,
    ) -> None:
        super().__init__(model_id, name, description, prediction_cost)
        self.feature_name: str = feature_name
        self.threshold: float = threshold

    def validate_data(
        self,
        input_data: list[DataRow],
    ) -> tuple[list[DataRow], list[DataRow]]:
        valid_data: list[DataRow] = []
        invalid_data: list[DataRow] = []

        for row in input_data:
            value = row.get(self.feature_name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                valid_data.append(row)
            else:
                invalid_data.append(row)

        return valid_data, invalid_data

    def predict(self, valid_data: list[DataRow]) -> list[PredictionValue]:
        return [
            int(float(row[self.feature_name]) >= self.threshold)
            for row in valid_data
        ]


class MLTask:
    """A request to run an ML model for a user."""

    def __init__(
        self,
        user: User,
        model: MLModel,
        input_data: list[DataRow],
        task_id: UUID | None = None,
    ) -> None:
        self.id: UUID = task_id or uuid4()
        self.input_data: list[DataRow] = input_data
        self.status: TaskStatus = TaskStatus.CREATED
        self.user: User = user
        self.model: MLModel = model
        self.result: PredictionResult | None = None
        self.created_at: datetime = datetime.now(timezone.utc)

    def run(self) -> PredictionResult:
        """Validate data, predict valid rows, and charge only after success."""
        if self.status is not TaskStatus.CREATED:
            raise RuntimeError("Only a newly created task can be started")

        self.status = TaskStatus.PROCESSING
        self.user._request_history.add(self)

        try:
            valid_data, invalid_data = self.model.validate_data(self.input_data)
            estimated_cost = self.model.calculate_cost(len(valid_data))

            if estimated_cost > 0 and not self.user.can_afford(estimated_cost):
                raise ValueError("Insufficient balance")

            predictions = self.model.predict(valid_data) if valid_data else []
            charged_credits = self.model.calculate_cost(len(predictions))

            if charged_credits > 0:
                transaction = DebitTransaction(
                    user=self.user,
                    amount=charged_credits,
                    related_task=self,
                )
                transaction.apply()

            self.result = PredictionResult(
                predictions=predictions,
                invalid_data=invalid_data,
                charged_credits=charged_credits,
            )
            self.status = TaskStatus.COMPLETED
            return self.result
        except Exception:
            self.status = TaskStatus.FAILED
            raise


class Transaction(ABC):
    """Abstract base class for a balance transaction.

    Access modifiers:
        id, created_at, user, related_task: public;
        _amount: protected.
    """

    def __init__(
        self,
        user: User,
        amount: float,
        related_task: MLTask | None = None,
        transaction_id: UUID | None = None,
    ) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.id: UUID = transaction_id or uuid4()
        self.user: User = user
        self._amount: float = amount
        self.created_at: datetime = datetime.now(timezone.utc)
        self.related_task: MLTask | None = related_task

    @property
    def amount(self) -> float:
        """Return the transaction amount."""
        return self._amount

    @property
    @abstractmethod
    def transaction_type(self) -> TransactionType:
        """Return the concrete transaction type."""
        raise NotImplementedError

    @abstractmethod
    def apply(self) -> None:
        """Apply the concrete balance operation."""
        raise NotImplementedError


class CreditTransaction(Transaction):
    """Transaction that increases a user's balance."""

    @property
    def transaction_type(self) -> TransactionType:
        return TransactionType.CREDIT

    def apply(self) -> None:
        self.user._balance.increase(self.amount)
        self.user._balance.add_transaction(self)


class DebitTransaction(Transaction):
    """Transaction that decreases a user's balance."""

    @property
    def transaction_type(self) -> TransactionType:
        return TransactionType.DEBIT

    def apply(self) -> None:
        self.user._balance.decrease(self.amount)
        self.user._balance.add_transaction(self)
