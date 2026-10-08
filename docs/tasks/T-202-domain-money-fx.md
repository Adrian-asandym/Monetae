# T-202 — Dominio puro: `Money`, monedas y tipos de cambio

> Fase 2. Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (código acotado pero crítico: redondeo de dinero).
> Depende de T-201 (ya integrada). Corre en paralelo con T-203: **archivos disjuntos**.

## Objetivo

Implementar en `monetae.domain` los *value objects* de dinero y tipo de cambio con las reglas de AGENTS.md §6.3 y SPEC §9, sin I/O, con pruebas exhaustivas. Es la base sobre la que se construyen préstamos, suscripciones y reportes.

## Leer primero

`AGENTS.md` (§4 regla de dependencias, §6.1–6.3, §6.7), `docs/SPEC.md` §7 (ejemplos A–E) y §9, `docs/ARCHITECTURE.md` §4 (convenciones) y §5.5 (convención de `fx_rate_applied`).

## Archivos permitidos (todos nuevos salvo `domain/__init__.py`)

```
services/api/src/monetae/domain/__init__.py      # solo re-exportar la API pública
services/api/src/monetae/domain/errors.py
services/api/src/monetae/domain/currency.py
services/api/src/monetae/domain/money.py
services/api/src/monetae/domain/fx.py
services/api/tests/domain/__init__.py
services/api/tests/domain/test_currency.py
services/api/tests/domain/test_money.py
services/api/tests/domain/test_fx.py
```

No tocar `pyproject.toml`, `uv.lock`, `db/`, `api/`, `alembic/` ni `tests/conftest.py`. **Sin dependencias nuevas** (solo `decimal` de la biblioteca estándar). `monetae.domain` **no importa** de `api`, `db`, `importers` ni `reports`, ni siquiera de Pydantic o SQLAlchemy (la prueba `tests/test_architecture.py` ya lo comprueba y debe seguir pasando).

## Requisitos

**Errores (`errors.py`):** `DomainError` (base), `CurrencyMismatchError`, `InvalidMoneyError`, `InvalidExchangeRateError`, todos con mensajes claros y datos útiles (monedas implicadas).

**Moneda (`currency.py`):** `Currency` = código ISO 4217 de 3 letras mayúsculas; valida formato (`^[A-Z]{3}$`), no acepta minúsculas ni espacios. En V1 toda moneda tiene **2 decimales** (PEN, USD); documenta esa limitación en el docstring. Constantes `PEN` y `USD`. Hashable, comparable por igualdad.

**`Money` (`money.py`):** objeto de valor inmutable (`@dataclass(frozen=True, slots=True)`), `amount: Decimal` y `currency: Currency`.
1. Normaliza `amount` a 2 decimales con `ROUND_HALF_UP` (mitades se alejan de cero, también en negativos) y rechaza con `InvalidMoneyError`: `float` (incluido `bool`), `NaN`, `Infinity`, valores fuera de `NUMERIC(18,2)` (más de 16 dígitos enteros). Acepta `Decimal` e `int`; `Money.parse("12.345", currency)` acepta `str` y aplica la misma normalización. Contexto decimal explícito (no depender del contexto global del hilo).
2. Suma y resta solo entre la **misma moneda**; con monedas distintas lanza `CurrencyMismatchError`. `-m`, `abs(m)`, `m.is_zero()`, `m.is_negative()`.
3. Comparación de orden (`<`, `<=`, `>`, `>=`) entre monedas distintas lanza `CurrencyMismatchError`. `==` es estructural: monedas distintas ⇒ `False` **sin excepción** (para no romper conjuntos/diccionarios); `hash` coherente.
4. Multiplicación por escalar `Decimal`/`int` (nunca `float`): redondea una sola vez al final. División por escalar similar. `Money * Money` no existe.
5. `Money.sum(iterable, currency)` suma una colección (vacía ⇒ cero de esa moneda) y rechaza mezcla de monedas.
6. Representación estable: `repr` sin ambigüedad; `format` a cadena decimal con 2 decimales (`"200.00"`) para la capa API.

**Tipo de cambio (`fx.py`):**
1. `ExchangeRate(from_currency, to_currency, rate)`: `rate: Decimal` normalizada a **6 decimales** `ROUND_HALF_UP`, estrictamente `> 0` (si tras redondear queda 0, es inválida), monedas distintas; si no, `InvalidExchangeRateError`. **Convención:** `rate` = unidades de `to_currency` por **1** unidad de `from_currency` (Ej. C: USD→PEN `3.800000`).
2. `convert(money, rate)`: `money.currency` debe ser `from_currency`; resultado en `to_currency` redondeado una sola vez (2 decimales, `ROUND_HALF_UP`). `convert_back(money, rate)`: de `to_currency` a `from_currency` dividiendo (`ARCHITECTURE.md` §5.5: `importe_prestamo = |importe_cuenta| / fx_rate_applied`).
3. `ExchangeRate.inverse()` (redondeo a 6 decimales). `implied_rate(from_money, to_money)` para transferencias entre monedas (RF-03): tasa implícita a 6 decimales; rechaza importes cero o de la misma moneda.
4. `apply_rate_to_base(money, rate_to_base)` documentando el caso `rate = 1` cuando la moneda ya es la base.

## Pruebas (mínimo exigido)

- Redondeo: `0.005→0.01`, `-0.005→-0.01`, `0.004→0.00`, `1.005→1.01` (con `Decimal`, nunca con `float`), 3 decimales de entrada, 6 decimales de tasa.
- Rechazos: `float`, `bool`, `NaN`, `Infinity`, desbordamiento, moneda con formato inválido, tasa cero/negativa/mismas monedas.
- Mezcla de monedas en `+`, `-`, `<`, `sum` ⇒ `CurrencyMismatchError`; `==` ⇒ `False`.
- Inmutabilidad (no se puede asignar), `hash` y uso en `set`/`dict`.
- **Ejemplos de SPEC §7 como pruebas literales de aritmética de dinero:** A (200 + 10 − 100 − 110 = 0), B (500 − 300 − 200 = 0), C (USD 100 ↔ PEN 380 a `3.800000`, ida y vuelta), D (50 − 60 ⇒ exceso `10.00`), E (1000 − 50 − 120 − 30 − 800 = 0).
- Propiedades por muestreo determinista (sin librerías nuevas): para 1 000 valores generados con `random.Random(seed fijo)`, `(a + b) - b == a`, `convert` luego `convert_back` difiere como máximo de 1 centavo cuando `rate >= 1`.
- Cobertura de líneas de `domain/money.py`, `fx.py`, `currency.py` ≥ 95 % (informa el comando; `coverage` no es dependencia del proyecto: puedes medirlo con `uv run --with coverage coverage run -m pytest` sin añadirlo a `pyproject.toml`).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cd services/api
uv sync --frozen
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -q
uv lock --check
grep -rnE "import (fastapi|pydantic|sqlalchemy|alembic)|from (fastapi|pydantic|sqlalchemy|alembic)" src/monetae/domain || echo "dominio limpio"
git diff --stat master-dev...HEAD     # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(domain):`, `test(domain):`). Actualiza tu rama con `master-dev` antes de reportar. Dudas que bloqueen → `orca orchestration ask`. Reporta `worker_done` una sola vez.
