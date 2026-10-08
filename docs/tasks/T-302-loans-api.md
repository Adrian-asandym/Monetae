# T-302 — Préstamos: migración 0005, servicios y API

> **ESTADO: LANZADA el 2026-10-08** (Run `run_63b520544a30`; T-301 aceptada e integrada en `master-dev` `246a6d5`). Plan escrito el 2026-10-08, corregido al lanzar (ver «Correcciones al lanzar»).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (la tarea más delicada del proyecto: P1, P2 y P3 se prueban aquí de extremo a extremo; considerar `gpt-6-astra` si T-301 requirió devoluciones).
> Depende de: **T-301** (dominio). Eres el **único dueño de las migraciones** durante esta tarea: creas la `0005`. No corre en paralelo con T-304.

## Objetivo

Persistir y exponer el libro mayor de préstamos con el contrato `docs/api/openapi.json`: préstamos, movimientos (desembolso, interés, pago, ajuste, condonación), saldo calculado, propuestas, resumen por persona y los efectos reales sobre las cuentas. Es la solución de P1 (nada desaparece), P2 (sin «liquidar»: el interés sube el saldo) y P3 (cada movimiento afecta a su cuenta real).

## Leer primero

`AGENTS.md` (§6, §9), `docs/SPEC.md` §5.4 (RF-13 a RF-23), §7, §14; `docs/decisions/003-interest-recognition.md`; `docs/ARCHITECTURE.md` §4, §5.4, §5.5 (completo), §10; `docs/api/openapi.json` (rutas `/loans*`, esquemas `Loan*`, `MovementCreate` y sus 5 variantes, `PaymentProposal`, `InterestProposal`, `LoanSummary`, `LoanSideEffect`, ejemplos `x-loan-scenarios`) y `docs/api/README.md`. Reutiliza **sin copiar**: `UserScopedRepository`, `api/pagination.py`, `services/idempotency.py`, `services/transactions.py` (referencias, bloqueos, normalización de tasas), `domain/loans.py` (T-301) y el estilo de T-204 a T-206b.

## Esquema (migración `0005_loans.py`, reversible)

1. `UNIQUE (id, user_id)` en `people` (para la FK compuesta).
2. **`loans`** (ARCHITECTURE §5.5): `person_id`, `direction` (`lent`/`borrowed`), `currency`, `principal NUMERIC(18,2) > 0`, `opened_on date`, `due_on date NULL`, `note`, `import_external_id text NULL`, columnas comunes. **Sin columna de saldo ni de estado.** FK compuesta `(person_id, user_id) → people(id, user_id)`; `UNIQUE (id, user_id)`; único parcial `(user_id, import_external_id)`.
3. **`loan_movements`**: `loan_id`, `kind`, `amount_in_loan_currency` (`> 0`, salvo `adjustment` ≠ 0), `transaction_id NULL` **único** cuando no es NULL, `interest_part`/`principal_part NULL` (solo en `payment` y `write_off`; `CHECK` de suma y `≥ 0`), `fx_rate_applied NUMERIC(18,6) NULL`, `occurred_at`, `note`, columnas comunes. FK compuestas a `loans(id, user_id)` y a `transactions(id, user_id)`. `CHECK` de coherencia por tipo. **`sequence bigint NOT NULL`** (interna, **no** se expone en la API): orden de desempate dentro del préstamo, asignada bajo el bloqueo consultivo del préstamo como `COALESCE(MAX(sequence), 0) + 1`; único `(loan_id, sequence)`. Índices `(user_id, loan_id, occurred_at, sequence)`.
4. **Vista `loan_balances`** (o consulta agregada equivalente): `principal + Σinterest + Σadjustment − Σpayment − Σwrite_off` sobre movimientos no borrados, y `status`. Prueba de equivalencia **vista/SQL == `domain.loans.replay`** sobre libros aleatorios (semilla fija).
5. `alembic check` limpio; `0004→0005→0004→0005`.

## Reglas (decididas; el contrato las fija en parte)

1. **Crear préstamo** (`POST /loans`): en **una sola transacción de BD** crea el préstamo y su `disbursement` con su transacción real (`kind='loan'`, en la cuenta indicada, signo `cash_sign`, título generado en español si no se envía, sin categoría), con `Idempotency-Key`. El principal ya incluye el desembolso: **no se suma otra vez al saldo**.
2. **Movimientos** (`POST /loans/{id}/movements`): `payment` (con transacción real en **su propia cuenta**, que puede ser de otra moneda: `fx_rate_applied` y `account_amount`), `interest` y `adjustment` y `write_off` (sin dinero, sin transacción). Reparto de pagos y condonaciones primero a interés (ADR-003), editable y validado con el dominio. **Exceso** (Ejemplo D): sin `excess_handling` ⇒ `422` `code: loan_overpayment` con las opciones y `excess_amount`, sin guardar nada; con `excess_handling` ⇒ ejecución atómica (`adjustment` o `income_expense`) y respuesta con `side_effects`; reintento con `Idempotency-Key` **nueva**.
3. **Libro inmutable salvo edición explícita:** `PUT` de un movimiento re-valida **todo el libro** con `replay`; si lo rompe ⇒ `409` `code: ledger_inconsistent` (con el índice del movimiento afectado) y no cambia nada; actualiza su transacción real de forma atómica. `DELETE`/`restore` de un movimiento (borrado lógico) igual: borra/restaura también su transacción y re-valida el libro. No se puede borrar el desembolso por esta vía (`409`).
4. **Saldo y estado calculados** (`GET /loans/{id}/balance`, `outstanding` y `status` en `Loan`/listados): sin columna; `settled` ⇔ saldo = 0; un saldado sigue visible y filtrable (`status=settled`), y se **reabre** al añadir un movimiento que sube el saldo. `running_balance` por movimiento. **No existe ninguna ruta ni campo «liquidar»**.
5. **Propuestas** (`payment-proposal`, `interest-proposal`): solo cálculo con el dominio; no guardan nada.
6. **Resumen** (`GET /loans/summary`): por persona y moneda (`lent_outstanding`, `borrowed_outstanding`, `open_count`, `settled_count`) en una consulta agregada, sin mezclar monedas. (Los `/reports/*` son de la Fase 6.)
7. **Borrar un préstamo** (`DELETE /loans/{id}`) es lógico y **atómico**: marca el préstamo, sus movimientos y sus transacciones reales; `restore` lo revierte (`409 restore_conflict` si falta persona o cuenta). Borrar una persona con préstamos vivos ⇒ `409 person_in_use`.
8. **Transacciones:** `Transaction.loan_id` (campo de solo lectura del contrato) se rellena vía `loan_movements.transaction_id`; los filtros `loan_id` y `person_id` de `GET /transactions` dejan de devolver vacío (quita el `TODO(phase-3)` de T-206a); `PATCH`/`DELETE`/`batch` sobre transacciones `loan` siguen dando `409 transaction_flow_required`. El capital no cuenta como ingreso/gasto en ningún cálculo; `recognized_interest` queda disponible para los reportes (Fase 6).
9. **Aislamiento y concurrencia:** FK compuestas con `user_id`; toda escritura sobre un préstamo toma un bloqueo consultivo `(user_id, loan_id)` (dos pagos simultáneos se serializan y el segundo ve el saldo del primero); **las lecturas no toman bloqueos de fila** (lección de T-204); orden de bloqueos fijo (préstamo → cuentas por id).
10. Dinero como cadenas decimales, `snake_case`, errores `problem+json`, rutas con los mismos `operationId`/seguridad/códigos que el contrato.

## Correcciones al lanzar y hechos del dominio entregado (T-301, ya en `master-dev`)

1. **Orden de reproducción:** `domain.loans.replay` ordena por `(occurred_at, sequence)`. `created_at` **no** sirve de desempate (`func.now()` es la hora de inicio de la transacción: el ajuste y el pago de un mismo exceso comparten valor). Por eso existe la columna interna `sequence`. En un exceso con `adjustment`, el ajuste recibe una `sequence` menor que la del pago y **el mismo `occurred_at`**. Editar `occurred_at` de un movimiento no cambia su `sequence`. `Movement` exige `occurred_at` con zona horaria y `sequence` entero ≥ 0.
2. **Porcentaje de interés:** el contrato lo transporta como cadena con **6 decimales** (`"5.000000"`); `propose_interest` acepta `Decimal` con precisión numérica ≤ 4 decimales (`5.123400` válido, `5.123456` ⇒ `InvalidInterestError` ⇒ `422`). Convierte en la capa API.
3. **Exceso sobre préstamo ya `settled`:** `plan_excess(income_expense)` devuelve solo `ExcessCash(total)` (sin pago de 0; sigue `settled`); `plan_excess(adjustment)` devuelve `Adjustment(+total)` y `Payment(total)`, y termina `settled`.
4. **Tasas:** el dominio recibe `fx_rate_applied` como `ExchangeRate | None` (`None` = misma moneda); `cash_sign` devuelve `0` para los movimientos sin dinero (interés, ajuste, condonación). `OverpaymentError` trae `excess` y `outstanding` para el cuerpo del `422 loan_overpayment`; `LedgerError.index` (base 0, en orden de reproducción) alimenta el `409 ledger_inconsistent`.
5. `monetae.domain` ya re-exporta la API de préstamos y de suscripciones; impórtala desde `monetae.domain`. **No modifiques `domain/`**: si falta algo, pregúntalo.

## Archivos permitidos

```
services/api/alembic/versions/0005_loans.py
services/api/src/monetae/db/models/loans.py
services/api/src/monetae/db/models/__init__.py              # solo exportar
services/api/src/monetae/db/models/catalog.py               # SOLO UniqueConstraint(id, user_id) en Person
services/api/src/monetae/services/loans.py
services/api/src/monetae/services/transactions.py           # SOLO: loan_id, filtros loan_id/person_id
services/api/src/monetae/services/catalog.py                # SOLO: 409 person_in_use
services/api/src/monetae/api/schemas/loans.py
services/api/src/monetae/api/schemas/transactions.py        # SOLO: campo loan_id
services/api/src/monetae/api/routers/loans.py
services/api/src/monetae/api/main.py                        # registrar router
services/api/tests/db/test_migration_0005.py
services/api/tests/db/test_loans_constraints.py
services/api/tests/api/conftest.py                          # helpers
services/api/tests/api/test_loans_crud.py
services/api/tests/api/test_loans_examples.py               # Ejemplos A–E de extremo a extremo + criterios P1/P2/P3 de SPEC §14
services/api/tests/api/test_loans_movements.py
services/api/tests/api/test_loans_excess.py
services/api/tests/api/test_loans_ledger_edits.py
services/api/tests/api/test_loans_summary.py
services/api/tests/api/test_loans_isolation.py
services/api/tests/api/test_loans_concurrency.py
services/api/tests/api/test_transactions_filters.py         # SOLO los filtros loan_id/person_id
services/api/tests/api/test_contract_subset.py              # actualizar
services/api/tests/db/test_migration_000{1,3,4}.py          # SOLO si la cabeza de migración lo exige
docs/api/README.md                                          # SOLO sección «Préstamos (T-302)»
```

No tocar `pyproject.toml`/`uv.lock`, `openapi.json`, `docs/ARCHITECTURE.md`, `domain/loans.py` (si hace falta un cambio, pídeselo al coordinador), `api/security.py`.

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- **Ejemplos A–E de SPEC §7 por HTTP**, comprobando saldos del préstamo **y de cada cuenta** (A: Efectivo +200 −110, BCP −100; el interés no mueve dinero y es el único «gasto»; B: Yape −500, Efectivo +300, BCP +200; C: cuenta PEN +380 con `fx_rate_applied` 3,800000; D: `422 loan_overpayment` y los dos `excess_handling`; E: saldos tras cada pago). Cada uno verifica que las transacciones reales **siguen visibles** en `GET /transactions` tras quedar `settled` (P1), que no hay «liquidar» (P2) y que cada cobro llegó a su cuenta (P3).
- Migración y BD: FK compuestas rechazan persona/préstamo/transacción de otro usuario (SQL directo), `CHECK` por tipo, `transaction_id` único, vista == dominio con libros aleatorios.
- Edición: `PUT`/`DELETE`/`restore` de movimientos con re-validación (`409 ledger_inconsistent` sin cambios parciales); borrado/restauración atómica del préstamo con sus transacciones.
- Aislamiento entre dos usuarios para **cada** operación de `/loans*`; `person_in_use`.
- Concurrencia: dos pagos simultáneos sobre el mismo préstamo (uno falla o se reparte correctamente, nunca saldo negativo ni interbloqueo); lecturas del mismo usuario **no** esperan a una escritura en vuelo (mide en milisegundos).
- Idempotencia (`Idempotency-Key`) en crear préstamo y crear movimiento, incluida la carrera de dos peticiones.
- Los 404+ tests existentes siguen verdes (explica en `worker_done` cualquier ajuste).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0004 && uv run alembic upgrade head
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(loans):`, `test(loans):`), por etapas (migración → modelos → servicio → rutas → pruebas). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen → `orca orchestration ask`. Si el contrato o ARCHITECTURE te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
