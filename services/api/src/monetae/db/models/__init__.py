"""Importar este módulo registra todos los modelos en Base.metadata."""

from monetae.db.models.catalog import Account, Category, Person, Tag
from monetae.db.models.identity import Session, User
from monetae.db.models.ledger import IdempotencyKey, Transaction, TransactionTag
from monetae.db.models.loans import Loan, LoanMovement
from monetae.db.models.security import LoginAttempt

__all__ = [
    "Loan",
    "LoanMovement",
    "Account",
    "Category",
    "Person",
    "LoginAttempt",
    "Session",
    "Tag",
    "User",
    "Transaction",
    "TransactionTag",
    "IdempotencyKey",
]
