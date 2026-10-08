# T-304 — Suscripciones: migración 0006, reglas recurrentes y API

> **ESTADO: NO LANZADA.** Fase 3, última tarea. Plan escrito el 2026-10-08; se lanza cuando Adrian apruebe la Fase 3 y **T-302 y T-303 estén aceptadas e integradas**.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high`.
> Depende de: **T-303** (dominio) y **T-302** (orden de migraciones y `main.py`). Eres el **único dueño de las migraciones**: creas la `0006`. No corre en paralelo con T-302.

## Objetivo

Persistir y exponer las suscripciones con **archivado reversible** (P4): una suscripción archivada sale de la vista principal y de los totales, conserva todo su historial de pagos y no deja cobros futuros programados; reactivarla la devuelve con su historial. Incluye la tabla `recurring_rules` que las programa y las sugerencias de reactivación.

## Leer primero

`AGENTS.md` (§6, §9), `docs/SPEC.md` §5.5 (RF-24 a RF-27), §8 (reglas y criterios de aceptación), §14; `docs/ARCHITECTURE.md` §5.4, §5.6, §10; `docs/api/openapi.json` (rutas `/subscriptions*`, esquemas `Subscription*`, `ArchiveRequest`, `SubscriptionTotal`, `ReportTotal`, `Transaction.reactivation_suggestions`); `docs/api/README.md`; `domain/subscriptions.py` (T-303); y cómo T-206a/T-206b crean y publican transacciones `scheduled` (`services/transactions.py`).

## Esquema (migración `0006_subscriptions.py`, reversible)

1. **`recurring_rules`** (ARCHITECTURE §5.6): plantilla (`account_id`, `kind`, `amount` con signo, `category_id`, `title`, `note`, `currency`), `period`, `interval_count`, `anchor_on date`, `next_run_on date`, `end_on date NULL`, `active bool`, `subscription_id uuid NULL`, columnas comunes. FK compuestas `(account_id, user_id)`, `(account_id, currency)` y `(category_id, user_id)`.
2. **`subscriptions`**: `title`, `amount NUMERIC(18,2) > 0`, `currency`, `account_id` (FK compuestas con moneda y `user_id`), `category_id`, `period`, `interval_count`, `anchor_on`, `next_due_on`, `status` (`active`/`archived`), `archived_at`, `archive_reason`, `reminder_days_before int NULL`, `recurring_rule_id` (FK compuesta a `recurring_rules`), columnas comunes. `CHECK` de coherencia (`archived` ⇔ `archived_at IS NOT NULL`). Único parcial opcional por `(user_id, lower(title))` entre **activas** no borradas (decide con el contrato; si lo omites, dilo en `worker_done`).
3. **FK** `transactions.recurring_rule_id → recurring_rules (id, user_id)` (la columna existe desde 0003, sin FK; añádela aquí con `NOT VALID` + `VALIDATE` o directamente si la tabla está vacía).
4. `alembic check` limpio; `0005→0006→0005→0006`.

## Reglas (decididas)

1. **Crear** (`POST /subscriptions`): en una sola transacción de BD crea la suscripción y su regla (`anchor_on` = `next_due_on` inicial) y **materializa una sola transacción `scheduled`** (la próxima), vinculada por `recurring_rule_id`, `kind='expense'`, con el monto con signo negativo y las tasas de la moneda base (`1.000000`) o la tasa manual indicada para una moneda foránea (si falta ⇒ `422 fx_rate_required`).
2. **Publicar** una transacción `scheduled` de una regla (`POST /transactions/{id}/post`, T-206b) **avanza la regla** (`next_run_on` y `next_due_on` de la suscripción, usando `domain.subscriptions.next_after`) y **materializa la siguiente** `scheduled`, en la misma transacción de BD (añade un hook mínimo en `services/transactions.py`; sin romper su contrato). Solo reglas `active` de suscripciones `active` generan la siguiente.
3. **Archivar** (`POST /subscriptions/{id}/archive`, con motivo opcional): `status='archived'`, `archived_at`, desactiva la regla, **borra lógicamente las transacciones `scheduled` futuras de esa regla** y **no toca ninguna transacción pasada ni publicada**. Idempotente en el sentido de dominio: archivar una archivada ⇒ `409`. **Reactivar**: vuelve a `active`, reactiva la regla y materializa la próxima `scheduled` (`next_due_on` ≥ hoy; si el cuerpo/estado trae una fecha pasada, la siguiente ocurrencia futura desde el ancla).
4. **Visibilidad:** `GET /subscriptions` devuelve por defecto solo `active` (`status=archived` o `status=all` las incluyen según el contrato); los totales (`GET /subscriptions/totals`) cuentan solo `active` y **separan monedas** con los factores de ARCHITECTURE §5.6; `monthly_total`/`yearly_total` (`ReportTotal`) convierten a `report_currency` con el `unconverted_count` del contrato mientras no exista proveedor de tasas (Fase 6): la moneda que coincide con la de reporte se suma; las demás cuentan como no convertidas. Una archivada nunca aparece en ellos.
5. **Historial:** `historical_paid` y `last_paid_on` de cada suscripción se calculan desde las transacciones **publicadas y no borradas** de su regla (sumas SQL agregadas, sin N+1 en listados); sobreviven al archivado.
6. **Sugerencias de reactivación** (SPEC §8.4): al **crear** o **publicar** una transacción `expense`, el campo de solo lectura `reactivation_suggestions` lista los ids de suscripciones **archivadas** del usuario cuyo título normalizado (`domain.subscriptions.normalize_title`) coincide con el de la transacción. Solo sugiere; **nunca reactiva sola**.
7. **Editar** (`PATCH`): título, importe, periodo, `interval_count`, cuenta, categoría, `next_due_on`, aviso; actualiza la regla y **rematerializa** la próxima `scheduled` (borrado lógico de la anterior no publicada y creación de la nueva). Cambiar de moneda o de cuenta con otra moneda ⇒ `422` (se archiva y se crea otra). `DELETE` es lógico y también borra lógicamente las `scheduled` futuras; no toca las publicadas.
8. **Aislamiento y concurrencia:** toda escritura toma un bloqueo consultivo `(user_id, subscription_id)` (archivar y publicar a la vez se serializan sin interbloqueo; orden fijo suscripción → regla → cuentas); las lecturas no toman bloqueos de fila. Todo atómico.
9. `/recurring-rules` (CRUD genérico del contrato) **no** forma parte de esta tarea (Fase 6): la tabla existe para las suscripciones y queda lista.

## Archivos permitidos

```
services/api/alembic/versions/0006_subscriptions.py
services/api/src/monetae/db/models/recurring.py                 # RecurringRule, Subscription
services/api/src/monetae/db/models/__init__.py                  # solo exportar
services/api/src/monetae/services/subscriptions.py
services/api/src/monetae/services/transactions.py               # SOLO: hook de publicar y reactivation_suggestions
services/api/src/monetae/api/schemas/subscriptions.py
services/api/src/monetae/api/schemas/transactions.py            # SOLO: reactivation_suggestions (ya existe: rellenarlo)
services/api/src/monetae/api/routers/subscriptions.py
services/api/src/monetae/api/main.py                            # registrar router
services/api/tests/db/test_migration_0006.py
services/api/tests/db/test_subscriptions_constraints.py
services/api/tests/api/conftest.py                              # helpers
services/api/tests/api/test_subscriptions_crud.py
services/api/tests/api/test_subscriptions_archive.py            # criterios de aceptación de SPEC §8, de extremo a extremo
services/api/tests/api/test_subscriptions_totals.py
services/api/tests/api/test_subscriptions_scheduling.py
services/api/tests/api/test_subscriptions_suggestions.py
services/api/tests/api/test_subscriptions_isolation.py
services/api/tests/api/test_subscriptions_concurrency.py
services/api/tests/api/test_contract_subset.py                  # actualizar
services/api/tests/db/test_migration_000{1,3,4,5}.py            # SOLO si la cabeza de migración lo exige
docs/api/README.md                                              # SOLO sección «Suscripciones (T-304)»
```

No tocar `pyproject.toml`/`uv.lock`, `openapi.json`, `docs/ARCHITECTURE.md`, `domain/subscriptions.py` (si hace falta un cambio, pídeselo al coordinador).

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- **Criterios de aceptación de SPEC §8 por HTTP:** (a) «Netflix activa con 3 pagos previos; la archivo ⇒ desaparece del listado principal y del total, las 3 transacciones siguen visibles y no queda ningún cobro futuro `scheduled`»; (b) «Netflix archivada; registro un pago "Netflix" ⇒ la respuesta incluye `reactivation_suggestions` con su id; al reactivarla vuelve al listado con su historial y total pagado». Más: `historical_paid`/`last_paid_on` correctos antes y después de archivar.
- Programación: crear materializa una sola `scheduled`; publicar la avanza y crea la siguiente (fin de mes, 29 feb); archivar borra las futuras y no las pasadas; reactivar crea la próxima futura; editar rematerializa; borrar no toca publicadas.
- Totales: solo `active`, monedas separadas, factores de los cuatro periodos con `interval_count` > 1, `unconverted_count` para la moneda distinta a la de reporte, archivadas excluidas.
- BD: FK compuestas (SQL directo) rechazan datos de otro usuario o moneda distinta; `CHECK` archived⇔archived_at; migración reversible y `alembic check` limpio.
- Aislamiento entre dos usuarios para cada operación; el título de una archivada de A no genera sugerencia para B.
- Concurrencia: archivar y publicar simultáneamente sin interbloqueo ni transacciones huérfanas; lecturas sin esperar a una escritura en vuelo.
- Los tests existentes (incluidos los de T-302) siguen verdes.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0005 && uv run alembic upgrade head
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(subscriptions):`, `test(subscriptions):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen → `orca orchestration ask`. Si el contrato o ARCHITECTURE te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
