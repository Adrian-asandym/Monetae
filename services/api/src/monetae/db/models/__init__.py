"""Importar este módulo registra todos los modelos en Base.metadata."""

from monetae.db.models.catalog import Account, Category, Person, Tag
from monetae.db.models.identity import Session, User

__all__ = ["Account", "Category", "Person", "Session", "Tag", "User"]
