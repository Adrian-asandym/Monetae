"""Códigos de moneda sin dependencias de infraestructura."""

import re
from dataclasses import dataclass

from .errors import DomainError


@dataclass(frozen=True, slots=True)
class Currency:
    """Código ISO 4217; V1 usa dos decimales para toda moneda (PEN y USD).

    Se valida el formato, no la pertenencia al catálogo ISO completo.
    """

    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or re.fullmatch(r"[A-Z]{3}", self.code) is None:
            raise DomainError("Currency must contain exactly three uppercase ASCII letters")


PEN = Currency("PEN")
USD = Currency("USD")
