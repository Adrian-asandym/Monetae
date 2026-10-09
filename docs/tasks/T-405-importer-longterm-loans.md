# T-405 — Importador de Cashew: préstamos de largo plazo sin desembolso registrado (L1-A)

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-09** (merge `fa06542`; Run `run_f5e95406186a`; decisión **L1-A** de Adrian, ver la adenda del ADR-008). Verificada por el coordinador: 914 pruebas, sonda con servidor real y `--dry-run` real con cuadre exacto. Publicación pendiente del gate G2 (`gate_10f2135dac21`).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (cambio acotado en `loans.py`; el cuidado está en no romper idempotencia ni la segunda pasada de tasas).
> Depende de: Fase 4 integrada y publicada (`origin/main` = `master-dev` en `b0a80ae`). No corre en paralelo con otra tarea.

## Contexto (hallazgo del `--dry-run` real)

En el respaldo real de Adrian, los préstamos de largo plazo (`objectives.type = 1`) **no tienen su desembolso como transacción enlazada**: solo cobros o pagos con `objective_loan_fk`. Hoy `loans.py::_plan` no encuentra el desembolso, `replay` lanza `MissingDisbursementError` y el préstamo cae a `ledger_invalid`: sus cobros se importan como **ingresos ordinarios** (justo el problema P1 de `docs/SPEC.md`: un cobro de préstamo contado como ingreso) y el préstamo no aparece. El saldo de las cuentas sí cuadra. No se incluyen cifras del respaldo real en este repositorio público.

## Objetivo

Que esos préstamos **sí se creen**, con un **desembolso sin dinero** (sin transacción) cuyo principal se **supone** igual a la suma de sus pagos, y con un ítem de revisión `principal_assumed`. Los pagos se importan como pagos reales, cada uno en su cuenta. Ningún saldo de cuenta cambia respecto de hoy.

## Leer primero

`AGENTS.md` (§6, §9), `docs/decisions/008-cashew-loan-import.md` (**incluida la Adenda L1-A al final; manda sobre esta tarea**), `docs/importers/cashew-loans.md`, y el código: `importers/cashew/loans.py` (**`_plan`, `_payment`, `_create`, `_verify_original`, `_plan_conversions`, `run`**), `domain/loans.py` (**`replay`**, `Movement`, `MovementKind`, `split_payment`, `loan_amount_from_account`), `db/models/loans.py`, y la migración `0005` (el `CHECK` ya permite un `disbursement` con `transaction_id` nulo). Pruebas de referencia: `tests/importers/test_cashew_loans_ledger.py` y `test_cashew_loans_anomalies.py`.

## Reglas (decididas)

1. **Cuándo aplica.** Objetivo `type = 1` en el que, **descartadas las filas `paid = 0`**, **no hay ninguna fila con la polaridad de desembolso** y **hay al menos una con la de pago** (la polaridad se define como hoy en `_plan`: `r.income == (direction == "borrowed")` ⇒ desembolso). En cualquier otro caso nada cambia, en particular: un objetivo **sin ninguna fila pagada** sigue siendo `ledger_invalid` (`MissingDisbursementError`) con sus filas ordinarias, y una polaridad o un importe anómalo sigue lanzando `invalid_cash_polarity_or_amount`. Los pagos únicos (`type` 3 y 4) no se ven afectados.
2. **Desembolso sintético.** Primer movimiento del libro: `kind = disbursement`, `transaction_id = NULL`, `fx_rate_applied = NULL`, `note = NULL`, `sequence = 0` (los pagos siguen con 1…n), `occurred_at` = el `occurred_at` del **primer pago** (orden `(occurred_at, pk)`) **menos 1 segundo**. **No crea ninguna transacción** (no mueve dinero ni cambia ningún saldo). `opened_on` sale de ese movimiento, como hoy (America/Lima).
3. **Principal supuesto.** `principal` = suma, **en la moneda del préstamo** (la de la cuenta del objetivo), de los pagos que en este paso serán **movimientos reales**: en la misma moneda, `abs(importe)`; en otra moneda, solo si `--loan-fx-rates` trae tasa para ese `pk` (misma conversión que `_payment`, es decir `loan_amount_from_account`). Un pago en otra moneda **sin tasa** no suma: sigue como hoy (transacción ordinaria + `fx_rate_required`). Reutiliza el cálculo de `_payment` en un helper común para que la suma y los movimientos no puedan divergir. Con eso el préstamo termina en saldo 0 / `settled`. Si la suma fuera 0 (ningún pago convertible), el préstamo **no se crea** y todo queda como hoy (`ledger_invalid` con filas ordinarias).
4. **Pagos.** Exactamente como R4/J2/J3 del ADR-008: cuenta propia, `kind = 'loan'`, reparto con `split_payment`, `import_external_id = 'cashew:sqlite:<pk>'`. Por construcción de la regla 3 no habrá exceso; no cambies la lógica de exceso.
5. **Ítem de revisión `principal_assumed`**, uno por préstamo, con payload `loan_external_id`, `objective_pk`, `payments` (nº de pagos reales), `assumed_principal` (decimal como texto) y `currency`. **Sin títulos, nombres ni notas.** `import_review_items.kind` es texto libre: **no hace falta migración** (si crees que sí, pregunta con `ask`).
6. **Igual que hoy:** persona (R5), `unpaid_loan_transaction`, `orphan_interest`, `extra_disbursement` (no puede darse aquí), etiquetas, y un préstamo inválido nunca aborta el resto.
7. **Idempotencia y solo inserción.** Reimportar ⇒ 0 creados, 0 modificados: el préstamo existe por `cashew:sqlite:objective:<pk>` y **no se duplica el desembolso sintético**. `_verify_original` debe recalcular el **mismo** libro (incluido el desembolso sintético y el mismo principal, usando las tasas ya aplicadas) para que la segunda pasada siga funcionando.
8. **Segunda pasada de tasas en estos préstamos.** Si la tasa nueva convertiría un pago que **no** estaba en el principal supuesto, hoy el resultado sería un sobrepago. Debe terminar en `ambiguous_loan` / `second_pass_conflict` **sin cambiar nada** (ni la transacción, ni los movimientos, ni el ítem `fx_rate_required`). La forma correcta de evitarlo es pasar `--loan-fx-rates` **en la primera importación**; documéntalo.
9. **Corrección posterior (documentar con exactitud).** El préstamo aparece `settled` mientras nadie lo corrija. Si en realidad queda capital pendiente, se añade un movimiento **`adjustment`** (`POST /api/v1/loans/{id}/movements`, sin dinero) por el capital pendiente real. **No** se corrige con el `PUT` del desembolso: la API lo trata como un movimiento **con dinero** y crearía una transacción en una cuenta, cambiando su saldo. Escríbelo así en `docs/importers/cashew-loans.md`.

## Archivos permitidos

```
services/api/src/monetae/importers/cashew/loans.py                # la regla y el helper común
services/api/tests/importers/test_cashew_loans_longterm.py        # nuevo
services/api/tests/importers/test_cashew_loans_ledger.py          # SOLO test_invalid_objective_keeps_cash_and_other_books (ver abajo)
services/api/tests/importers/conftest.py                          # SOLO helpers nuevos
docs/importers/cashew-loans.md                                    # regla, ítem y corrección posterior
```

No tocar `runner.py`, `report.py`, `reader.py`, `mapping.py`, `cli.py`, migraciones, `domain/`, `services/`, `api/`, `docs/decisions/`, `docs/api/openapi.json` ni los fixtures. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real; copias de la fixture, nunca el original)

- **Reescribir** `test_invalid_objective_keeps_cash_and_other_books` (quita el desembolso del caso B): ahora el préstamo B **se crea**, `settled`, con principal = suma de sus dos cobros (300 en Efectivo y 200 en Cuenta Soles), desembolso con `transaction_id` nulo, dos pagos enlazados a **sus** transacciones `kind = 'loan'` (no son ingresos), `created == 7` e `invalid == 0`, ítem `principal_assumed` con los valores del payload, `unexplained = 0.00` en todas las cuentas.
- **Conservar la cobertura de `ledger_invalid`** con un objetivo sin ninguna fila pagada (o solo `paid = 0`): préstamo no creado, filas ordinarias, ítem registrado, el resto sigue.
- **Pago en otra moneda** dentro de un objetivo sin desembolso: (a) sin tasa ⇒ transacción ordinaria + `fx_rate_required`, no suma al principal; (b) con `--loan-fx-rates` en la misma importación ⇒ suma convertida y es un pago real con `fx_rate_applied`; (c) segunda pasada sobre (a) con tasa ⇒ regla 8, sin cambios.
- **Orden y fecha:** el desembolso sintético queda antes del primer pago (`replay` pasa, `sequence` 0, un segundo antes), también con pagos en el mismo instante.
- **Idempotencia** (segunda importación: 0 creados, 0 modificados, un solo desembolso) y **`--dry-run`** (BD financiera intacta).
- **El libro pasa `domain.loans.replay`** y el estado calculado es `settled`, sin columna de saldo.
- **Aislamiento entre dos usuarios.**
- **Privacidad:** ninguna salida estándar de la CLI contiene títulos, notas, nombres ni el importe supuesto (el ítem vive en la BD; la CLI solo imprime conteos).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
# BD PROPIA de esta tarea:
export MONETAE_DB_PORT=5440 COMPOSE_PROJECT_NAME=monetae-t405
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5440/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(importer):`, `test(importer):`, `docs(importer):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso que esta spec o el ADR no cubran, `orca orchestration ask`. Una fila anómala nunca aborta la importación. Si el ADR, el contrato o el dominio te parecen inconsistentes con esto, no los cambies: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
