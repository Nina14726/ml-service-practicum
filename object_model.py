"""Object model for an ML-service personal account.

This module contains only the domain model required by assignment 1.
It intentionally does not include a database, REST API, Telegram bot,
RabbitMQ, web interface, Docker configuration, or monitoring.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


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
    """Result of processing one ML task.

    Public fields:
        predictions: model predictions for valid input rows.
        invalid_data: rows rejected during validation.
        charged_credits: credits charged only after successful prediction.
        created_at: result creation time.
    """

    def __init__(
        self,
        predictions: list[Any],
        invalid_data: list[Any],
        charged_credits: float,
    ) -> None:
        self.predictions: list[Any] = predictions
        self.invalid_data: list[Any] = invalid_data
        self.charged_credits: float = charged_credits
        self.created_at: datetime = datetime.now(timezone.utc)


class MLRequestHistory:
    """History of a user's ML requests."""

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


class User:
    """User of the ML service.

    Access modifiers:
        id, email: public.
        _role, _request_history: protected.
        __password_hash, __balance, __transactions: private.
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
        self.__password_hash: str = password_hash
        self.__balance: float = 0.0
        self.__transactions: list[Transaction] = []

    @property
    def role(self) -> UserRole:
        """Return the user's role."""
        return self._role

    @property
    def balance(self) -> float:
        """Return the current balance without exposing direct modification."""
        return self.__balance

    def authenticate(self, password_hash: str) -> bool:
        """Check authorization data."""
        return self.__password_hash == password_hash

    def can_afford(self, amount: float) -> bool:
        """Check whether the balance is sufficient."""
        return amount >= 0 and self.__balance >= amount

    def get_request_history(self) -> list[MLTask]:
        """Return the user's ML request history."""
        return self._request_history.get_all()

    def get_transactions(self) -> list[Transaction]:
        """Return a copy of the user's transaction history."""
        return list(self.__transactions)

    def _increase_balance(self, amount: float) -> None:
        """Protected balance operation used by credit transactions."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.__balance += amount

    def _decrease_balance(self, amount: float) -> None:
        """Protected balance operation used by debit transactions."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.can_afford(amount):
            raise ValueError("Insufficient balance")
        self.__balance -= amount

    def _add_transaction(self, transaction: Transaction) -> None:
        """Protected method for recording a balance transaction."""
        self.__transactions.append(transaction)


class Admin(User):
    """Administrator with additional balance-management permissions."""

    def __init__(self, user_id: int, email: str, password_hash: str) -> None:
        super().__init__(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )

    def top_up_user_balance(
        self,
        user: User,
        amount: float,
    ) -> CreditTransaction:
        """Approve a user's balance top-up."""
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
    """Base class for an ML model available in the service.

    Public fields:
        id: model identifier.
        name: model name.
        description: model purpose.
        prediction_cost: cost of one prediction in credits.
    """

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
        input_data: list[Any],
    ) -> tuple[list[Any], list[Any]]:
        """Return valid and invalid input rows."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, valid_data: list[Any]) -> list[Any]:
        """Return predictions for valid input rows."""
        raise NotImplementedError

    def calculate_cost(self, predictions_count: int) -> float:
        """Calculate the total cost for successful predictions."""
        if predictions_count < 0:
            raise ValueError("Predictions count cannot be negative")
        return self.prediction_cost * predictions_count


class MLTask:
    """A request to run an ML model for a user.

    Public fields:
        id, input_data, status, user, model, result, created_at.
    """

    def __init__(
        self,
        user: User,
        model: MLModel,
        input_data: list[Any],
        task_id: UUID | None = None,
    ) -> None:
        self.id: UUID = task_id or uuid4()
        self.input_data: list[Any] = input_data
        self.status: TaskStatus = TaskStatus.CREATED
        self.user: User = user
        self.model: MLModel = model
        self.result: PredictionResult | None = None
        self.created_at: datetime = datetime.now(timezone.utc)

    def run(self) -> PredictionResult:
        """Validate data, run prediction, and charge credits after success."""
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
    """Base class for a balance transaction.

    Access modifiers:
        id, created_at, user, related_task: public.
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
    """Polymorphic transaction that increases a user's balance."""

    @property
    def transaction_type(self) -> TransactionType:
        return TransactionType.CREDIT

    def apply(self) -> None:
        self.user._increase_balance(self.amount)
        self.user._add_transaction(self)


class DebitTransaction(Transaction):
    """Polymorphic transaction that decreases a user's balance."""

    @property
    def transaction_type(self) -> TransactionType:
        return TransactionType.DEBIT

    def apply(self) -> None:
        self.user._decrease_balance(self.amount)
        self.user._add_transaction(self)
