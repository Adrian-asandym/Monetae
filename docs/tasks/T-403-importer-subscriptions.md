# T-403 — Importador de Cashew: suscripciones, recurrentes y cuadre final

> **ESTADO: LANZADA el 2026-10-08 (T-401 aceptada e integrada en `master-dev`)** (Run `run_f5e95406186a`; OK de Adrian al Paso 3, 2026-10-08).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (reglas acotadas; el cuidado está en fechas y en el cuadre de saldos).
> Depende de: **T-401** integrada. Corre **en paralelo con T-402** (archivos disjuntos; esta tarea posee `runner.py`, `report.py` y `cli.py` a partir de T-401).
> Alcance acordado (D4-A, D4b-A del 2026-10-08): **no** se hacen las rutas `/imports` (4 operaciones) ni se importan presupuestos, metas ni reglas; quedan listados como «pendiente de Fase 6» y las rutas de subida de archivos, para las Fases 5-6.

## Objetivo

(1) Reemplazar el stub `importers/cashew/subscriptions.py`: importar las suscripciones (`type = 1`) y las recurrentes (`type = 2`) de Cashew como `subscriptions` + `recurring_rules` con su próxima transacción `scheduled`. (2) Cerrar el cuadre de saldos (RF-40c) y el reporte final con un código de salida que lo haga cumplir. (3) Documentar el comando completo.

## Leer primero

`AGENTS.md` (§6, §9), `docs/SPEC.md` §8 y §11, `docs/ARCHITECTURE.md` §5.6 y §5.9, `docs/cashew-analysis/01-data-model.md` (§b «Suscripciones, Recurrentes y Futuras») y `03-backup-format.md` (§6.3), fixture `cashew_v48` (casos G y K), `docs/importers/cashew.md` (T-401), y el código: `importers/cashew/` (runner, reader, report), `domain/subscriptions.py` (**`next_after`, `occurrence`, `archive`, `Period`**), `services/subscriptions.py` (**`materialize`, `create`, `_rate`**: cómo se arman regla, suscripción y la única `scheduled`; léelo, no lo llames), `db/models/recurring.py`, `services/transactions.py`.

## Reglas (decididas)

1. **Mapeo de periodo:** `reoccurrence` 1 daily, 2 weekly, 3 monthly, 4 yearly (`BudgetReoccurence`, `tables.dart:42`); `period_length` ⇒ `interval_count` (1–366). `reoccurrence` 0 (personalizada), nulo o `period_length` fuera de rango ⇒ no se importa la regla: la transacción queda como **ordinaria** y se registra `review_item` `unsupported_recurrence`.
2. **Suscripción (`type = 1`, gasto):** `subscriptions` + su `recurring_rule` (como `SubscriptionService.create`): `title` = `name`; `amount` = `|amount|`; cuenta y categoría de la fila; `anchor_on` = fecha de la fila (America/Lima); `status = 'active'`. Cashew **no tiene archivado**; si `end_date` ya pasó ⇒ `archived` con `archived_at = end_date` y motivo «Terminada en Cashew» (sin `scheduled`).
3. **Recurrente (`type = 2`):** solo `recurring_rules` (`kind` = `income` o `expense` según el signo) con su `scheduled`; **no** crea suscripción (las suscripciones son gastos). Misma regla de `end_date`.
4. **La fila de Cashew es la última ocurrencia registrada** (la fixture la trae con `paid = 1`): se importa además como **transacción normal `posted`** con su fecha, vinculada a la regla (`recurring_rule_id`), para conservar el historial y el saldo. Esta lectura **no está verificada** en el análisis: regístrala en cada caso como `recurrence_anchor_assumed` en el reporte (una sola línea de advertencia con el total, no un ítem por fila).
5. **Próxima ocurrencia:** `next_due_on` = primera fecha del calendario anclado (`domain.subscriptions.next_after`) **≥ hoy** en America/Lima (reloj inyectable para las pruebas, no `date.today()`); materializa **una sola** `scheduled` con el mismo orden de campos que `SubscriptionService.materialize` (a las 00:00 de Lima, `kind = 'expense'` o `'income'`, tasa provisional de la regla).
6. **Moneda y tasa:** cuenta en moneda base ⇒ `1.000000`; otra moneda ⇒ la misma resolución que T-401 (`--fx-rate`, luego `app_settings`, si no hay, falla antes de escribir), guardada como tasa provisional de la regla.
7. **Etiquetas:** reutiliza el mapa `transaction_pk → tags` de T-401 para la transacción histórica.
8. **Idempotencia:** `import_external_id = 'cashew:sqlite:<pk>'` en la regla y en la suscripción (T-401 ya creó las columnas); la transacción histórica reutiliza el mismo id de transacción. Solo inserción.
9. **Cuadre final (RF-40c):** en `runner.py`, tras todos los pasos, `unexplained = cashew_balance − monetae_balance − deferred_amount` de **cada cuenta** debe ser `0.00`, contando como `deferred_amount` solo lo que **siga** diferido (mientras `loans.py` sea el stub de T-401 el diferido de préstamos explica la diferencia; cuando T-402 esté integrada, el diferido es 0 y el cuadre es total). Si no es 0.00: el reporte lo marca `balance_mismatch`, y el comando termina con **código 5** salvo `--allow-balance-diff` (que lo permite pero lo deja escrito en el reporte y en la salida). Un `--dry-run` aplica el mismo criterio.
10. **Salida y reporte:** `steps['subscriptions']` con suscripciones/recurrentes creadas, omitidas, archivadas y `unsupported_recurrence`; sección `balances` completa (por cuenta: Cashew, Monetae, diferido, sin explicar); lista de lo «pendiente de Fase 6» con sus conteos (presupuestos, límites por categoría, reglas de título, plantillas del escáner, metas). La salida estándar sigue siendo solo conteos y saldos.

## Archivos permitidos

```
services/api/src/monetae/importers/cashew/subscriptions.py   # reemplaza el stub
services/api/src/monetae/importers/cashew/runner.py          # SOLO el cuadre final y el código de salida
services/api/src/monetae/importers/cashew/report.py          # SOLO campos del cuadre y de lo pendiente de Fase 6
services/api/src/monetae/cli.py                              # SOLO --allow-balance-diff y el código de salida 5
services/api/tests/importers/test_cashew_subscriptions_*.py  # nuevos
services/api/tests/importers/test_cashew_reconcile_*.py      # nuevos
services/api/tests/importers/conftest.py                     # SOLO helpers (no cambiar los de T-401)
docs/importers/cashew.md                                     # añadir las secciones de suscripciones, cuadre y salida
```

No tocar `loans.py` ni sus pruebas (T-402), la migración, `reader.py`, `mapping.py`, `domain/`, `services/`, `openapi.json` ni los fixtures. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Fixture G:** la suscripción `G_subscription` (−44,90 mensual) crea suscripción activa + regla + transacción histórica `posted` + **una** `scheduled` futura; la recurrente `G_repetitive` (+2500 mensual) crea regla `income` + su `scheduled`, **sin** suscripción; las etiquetas de G se conservan.
- **`next_due_on`:** fin de mes (ancla día 31), 29 de febrero, intervalos > 1 y los cuatro periodos, con reloj inyectado; la `scheduled` nunca cae antes de «hoy».
- **`end_date` pasado** ⇒ suscripción archivada, sin `scheduled`, historial intacto. **`reoccurrence` 0** ⇒ transacción ordinaria + `unsupported_recurrence`.
- **Moneda foránea** con `--fx-rate`, con tasa de `app_settings` y sin ninguna (falla antes de escribir).
- **Cuadre final:** con el stub de préstamos de T-401, `unexplained = 0.00` en las cuatro cuentas de la fixture (el diferido de préstamos explica la diferencia) y código de salida 0; la comprobación con **diferido 0** (T-402 integrada) la hace el coordinador al integrar ambas ramas; una copia sintética con un saldo alterado ⇒ `balance_mismatch` y código 5; con `--allow-balance-diff` ⇒ código 0 y la diferencia escrita.
- **Idempotencia** (0 creados, 0 modificados) y **`--dry-run`** (financiero intacto, reporte conservado). **Aislamiento entre dos usuarios.** Atomicidad.
- **SPEC §8 sobre lo importado:** una suscripción importada se puede archivar y reactivar con la API de Fase 3 sin errores y sin dejar dos programadas.
- **Privacidad:** salida estándar solo con conteos y saldos.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
# BD PROPIA de esta tarea: otro worker corre en paralelo. NO uses el proyecto ni el puerto por defecto
# (5433) y NO ejecutes `down` sobre un proyecto que no sea el tuyo.
export MONETAE_DB_PORT=5435 COMPOSE_PROJECT_NAME=monetae-t403
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5435/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

**Base de datos propia:** usa el proyecto y el puerto indicados arriba; hay otro worker en paralelo con su propia BD. Una fila anómala nunca aborta la importación: se omite con `review_item` (criterio de T-401b; ver `docs/importers/cashew.md`).

Commits pequeños en inglés (`feat(importer):`, `test(importer):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen (p. ej. la semántica de la fecha de una suscripción en v48) → `orca orchestration ask`; **no inventes reglas de negocio**. Si el contrato, ARCHITECTURE o SPEC te parecen inconsistentes con esto, no los cambies: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
