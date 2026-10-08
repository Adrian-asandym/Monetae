# T-303 — Dominio puro de suscripciones (archivado, equivalentes, fechas)

> **ESTADO: NO LANZADA.** Fase 3. Plan escrito el 2026-10-08; se lanza cuando Adrian apruebe la Fase 3.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (reglas acotadas; el cuidado está en las fechas y el redondeo).
> Depende de: nada nuevo (usa `domain/money.py`). Corre **en paralelo con T-301** (archivos disjuntos).

## Objetivo

Implementar en `monetae.domain` las reglas de SPEC §8 (P4): el estado `active`/`archived` y su transición reversible, los equivalentes mensual/anual, el cálculo de próximas fechas de cobro y la coincidencia de título para sugerir reactivación. Todo puro, sin I/O.

## Leer primero

`AGENTS.md` (§6, §13), `docs/SPEC.md` §5.5 (RF-24 a RF-27) y §8 (reglas y criterios de aceptación), `docs/ARCHITECTURE.md` §5.6 (equivalente mensual/anual, archivar), `docs/api/openapi.json` (esquemas `Subscription*`, `ArchiveRequest`, descripción de `SubscriptionTotal`), y el dominio existente (`money.py`, `errors.py`).

## Diseño (decidido)

Módulo `monetae/domain/subscriptions.py`:

1. **Tipos:** `Period` (`daily`, `weekly`, `monthly`, `yearly`), `Subscription` (inmutable): `title`, `amount: Money` (> 0), `period`, `interval_count` (entero ≥ 1, ≤ 366), `next_due_on: date`, `anchor_on: date` (fecha original del primer cobro), `status` (`active`/`archived`), `archived_at: datetime | None`, `archive_reason: str | None` (≤ 500).
2. **Equivalente mensual/anual** (ARCHITECTURE §5.6, igual al contrato): `monthly_equivalent = amount × f / interval_count` con `f` = `30.4375` (diaria), `4.348125` (semanal), `1` (mensual), `1/12` (anual); `yearly_equivalent = (monthly sin redondear) × 12`; `ROUND_HALF_UP` a 2 decimales **solo al final**, nunca el anual a partir del mensual ya redondeado. Usa precisión suficiente (`Decimal` con contexto explícito; `Money` solo para el resultado final).
3. **Totales:** `totals(subscriptions)` suma **solo `active`**, **por moneda** (nunca mezcla monedas; devuelve un mapa moneda → `(monthly, yearly, active_count)`); las archivadas no aportan nada (RF-26).
4. **Archivar/reactivar:** `archive(sub, at, reason=None)` ⇒ nueva `Subscription` en `archived` con `archived_at` y motivo; archivar una ya archivada ⇒ `SubscriptionStateError`; `reactivate(sub, next_due_on)` ⇒ `active`, limpia `archived_at`/motivo conservando el historial lógico; reactivar una activa ⇒ error. Son transiciones puras: no borran nada (el libro de transacciones pasadas no se toca; eso es de la capa de servicios).
5. **Fechas:** `occurrence(anchor_on, period, interval_count, n)` = n-ésima ocurrencia contada **desde el ancla** (evita la deriva: 31 ene + 1 mes ⇒ 28/29 feb, y el siguiente vuelve a 31 mar). `next_after(sub, after: date)` = primera ocurrencia `>` `after`; `upcoming(sub, after, count)` ⇒ las siguientes `count` (1–60). Bisiestos (29 feb anual), fin de mes, intervalos > 1 y los cuatro periodos con pruebas.
6. **Sugerencia de reactivación (SPEC §8.4):** `normalize_title(t)` (recorta, colapsa espacios, `casefold`, elimina acentos con `unicodedata`) y `matching_archived(title, archived: Iterable[Subscription])` ⇒ las archivadas cuyo título normalizado es **igual** (no «contiene»). Solo sugiere; nunca reactiva.
7. **Total pagado histórico:** `historical_paid(payments: Iterable[Money], currency)` ⇒ suma exacta (vacía ⇒ cero), rechaza otra moneda; `last_paid_on(dates)` ⇒ la mayor o `None`.
8. Errores heredan de `DomainError`.

## Archivos permitidos (todos nuevos salvo `domain/__init__.py`)

```
services/api/src/monetae/domain/subscriptions.py
services/api/src/monetae/domain/__init__.py         # SOLO re-exportar API pública
services/api/tests/domain/test_subscriptions_amounts.py
services/api/tests/domain/test_subscriptions_dates.py
services/api/tests/domain/test_subscriptions_state.py
services/api/tests/domain/test_subscriptions_matching.py
```

No tocar `pyproject.toml`/`uv.lock`, `db/`, `api/`, `services/`, `alembic/`, `domain/money.py`, `fx.py`, ni nada de préstamos (T-301). Sin dependencias nuevas. `monetae.domain` no importa de capas externas ni de Pydantic/SQLAlchemy.

## Pruebas obligatorias

- **Criterios de SPEC §8 a nivel de dominio:** (a) «Netflix activa con 3 pagos previos; la archivo ⇒ desaparece de los totales, el historial pagado se conserva y no queda cobro futuro (lo que el dominio expresa como `status=archived` y totales sin ella)»; (b) «Netflix archivada y llega un pago "Netflix" ⇒ `matching_archived` la sugiere; reactivar la devuelve a los totales».
- Equivalentes: tabla de casos para los 4 periodos × `interval_count` 1, 2, 3 (p. ej. 44,90 mensual; 12,00 semanal; 100,00 anual; 1,00 diaria ×7), el anual calculado desde el mensual **sin redondear** difiere del redondeado en casos construidos a propósito, y los totales por moneda con PEN y USD.
- Fechas: fin de mes, 29 feb (bisiesto y no), intervalos de 2 y 3 meses, cruce de año, `anchor_on` en día 31, `next_after` en el borde (`after` igual a una ocurrencia), `upcoming` con 60.
- Estados: doble archivo/doble reactivación ⇒ error; archivar conserva `anchor_on` y `next_due_on`; las transiciones no mutan el original.
- Coincidencia de títulos: mayúsculas, acentos, espacios, títulos vacíos, `Netflix` ≠ `Netflix Premium`.
- Cobertura de líneas de `domain/subscriptions.py` ≥ 95 %.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cd services/api
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
grep -rnE "^\s*(import|from) (fastapi|pydantic|sqlalchemy|alembic|monetae\.(api|db|importers|reports|services))" src/monetae/domain || echo "dominio limpio"
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(domain):`, `test(domain):`). Sin `Any` ni `# type: ignore` sin razón escrita. Actualiza tu rama con `master-dev` antes de reportar. Si el contrato, ARCHITECTURE o SPEC te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
