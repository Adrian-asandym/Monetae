# T-206b — Transferencias de dos patas, lotes y publicar programadas

> Fase 2, última tarea. Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (atomicidad de grupo, concurrencia y lotes).
> Depende de T-206a (integrada). Eres el **único dueño de las migraciones** durante esta tarea: creas la `0004`.

## Objetivo

Completar el núcleo del libro mayor de la Fase 2: transferencias entre cuentas (también entre monedas), operaciones por lote sobre la selección múltiple, y confirmar transacciones programadas. Todo atómico, aislado por usuario y sin bloquear lecturas.

## Leer primero

`AGENTS.md` (§6, §9), `docs/SPEC.md` (RF-03, RF-09, RF-11, RF-12, §9 reglas 2 y 4), `docs/ARCHITECTURE.md` (§5.4, §7, §10), `docs/api/openapi.json` (rutas `/transfers*`, `/transactions/batch`, `/transactions/{id}/post`; esquemas `Transfer*`, `TransactionBatch`, `ActionResult`, `TransactionUpdate`), `docs/api/README.md` (incluida la sección «Transacciones (T-206a)» y «Cambios del contrato durante la Fase 2»). Reutiliza el estilo y los componentes de T-206a (`services/transactions.py`, `domain/transactions.py`, `api/pagination.py`, `services/idempotency.py`) y el dominio `Money`/`ExchangeRate`.

## Decisiones (el contrato no las fija)

### Transferencias
1. **No hay tabla nueva.** Una transferencia son **exactamente dos filas de `transactions`** con `kind='transfer'`, el mismo `transfer_group_id`, `category_id` nulo, mismo `title`, `note`, `occurred_at`, `status='posted'` y `source='web'`: la **pata de salida** (importe negativo, cuenta `from`) y la **de entrada** (importe positivo, cuenta `to`). **El `id` de la transferencia en la API es su `transfer_group_id`.** `outgoing_transaction_id` / `incoming_transaction_id` son los ids de las patas.
2. **Migración `0004_transfer_integrity.py` (reversible)**: (a) `CHECK ((kind = 'transfer') = (transfer_group_id IS NOT NULL))`; (b) dos índices únicos parciales que garantizan **a lo sumo una pata de salida y una de entrada vivas por grupo**: `UNIQUE (transfer_group_id) WHERE kind='transfer' AND amount < 0 AND deleted_at IS NULL` y el análogo con `amount > 0`. `alembic check` limpio; prueba de que SQL directo no puede crear una tercera pata viva.
3. **Reglas de validación:** cuentas `from` y `to` distintas, ambas del usuario y no borradas (otra ⇒ `404`); `from_amount` y `to_amount` positivos (como define el contrato); la pata de salida se guarda como `-from_amount` en la moneda de la cuenta `from`, y la de entrada como `+to_amount` en la moneda de la cuenta `to`. **Misma moneda en ambas cuentas ⇒ `from_amount` debe ser igual a `to_amount`** (si no, `422` `code: transfer_amount_mismatch`; las comisiones se registran como un gasto aparte). **Monedas distintas ⇒** `implicit_rate = to_amount / from_amount` (unidades de la moneda `to` por 1 de la moneda `from`, 6 decimales `ROUND_HALF_UP`, con `ExchangeRate`/`implied_rate` del dominio; si redondea a 0 ⇒ `422`). Cada pata lleva su propio `fx_rate_to_base` con las reglas de T-206a (en la moneda base debe ser exactamente `1.000000`) y el `fx_rate_source` común; **no se recalculan jamás**.
4. **Atomicidad y concurrencia:** crear, editar, borrar y restaurar tocan las dos patas en una sola transacción de BD. Toda operación de escritura sobre un grupo toma un bloqueo consultivo por `(user_id, transfer_group_id)` (como `_write_lock` de T-206a) y, si afecta a cuentas, los `FOR SHARE` de referencias; **las lecturas no toman bloqueos de fila**. Dos escrituras simultáneas sobre la misma transferencia se serializan sin interbloqueo (ordena siempre los bloqueos de la misma manera).
5. **PATCH** parcial: puede cambiar cuentas, importes, tasas, `fx_rate_source`, `occurred_at`, `title`, `note`; tras aplicar el cambio se revalidan **todas** las reglas del punto 3. Si cambia la moneda de una cuenta, el cuerpo debe traer también la tasa de esa pata (si no ⇒ `422`). Se actualizan ambas patas o ninguna.
6. **DELETE** marca `deleted_at` en ambas patas (y devuelve `ActionResult` con `affected_count: 2`); **restore** restaura las dos (`409 restore_conflict` si alguna cuenta está borrada) y devuelve la transferencia. Borrar o restaurar una pata suelta por `/transactions/{id}` ⇒ `409 transaction_flow_required` (ya implementado en T-206a: añade una prueba de que sigue así). Una transferencia borrada no aparece en `GET /transfers` ni en `GET /transfers/{id}` (`404`).
7. **Listado:** `GET /transfers` ordenado `occurred_at DESC, transfer_group_id DESC` con paginación por llaves y cursor firmado (`api/pagination.py`), `limit` 1–200. Una consulta por página para las patas (sin N+1).

### Lotes (`POST /transactions/batch`)
8. **Atómico:** o se aplica a todos o a ninguno. Hasta 200 ids únicos; **cualquier id inexistente, ajeno o borrado (salvo `restore`) ⇒ `404` sin aplicar nada**. Cualquier transacción que no sea `income`/`expense` (patas de transferencia, movimientos de préstamo) ⇒ `409 transaction_flow_required` sin aplicar nada.
9. **Acciones:** `delete` (borrado lógico), `restore` (mismas reglas que T-206a; `409 restore_conflict` si falta cuenta o categoría), `add_tags` / `remove_tags` (requieren `tag_ids` no vacío; mismas reglas de etiquetas que T-206a: etiqueta ajena o borrada ⇒ `404`; archivada solo si ya estaba vinculada), `edit` (requiere `changes`). `changes` solo es válido con `edit` y `tag_ids` solo con las acciones de etiquetas (lo contrario ⇒ `422`). **En `edit` solo se admiten** `category_id`, `occurred_at`, `status`, `title` y `note`; cualquier otro campo del `TransactionUpdate` (`amount`, `kind`, `account_id`, `fx_*`, `tag_ids`) ⇒ `422 batch_field_not_allowed`, porque requeriría validar cada fila por separado. Respuesta `ActionResult{success, affected_count}`.
10. **Orden de bloqueos:** toma los bloqueos consultivos de las transacciones del lote **ordenados por id** para evitar interbloqueos entre dos lotes que se solapan (prueba con dos hilos y lotes cruzados).

### Publicar programadas (`POST /transactions/{id}/post`)
11. Solo `income`/`expense` directas con `status='scheduled'` (otra cosa ⇒ `409 not_scheduled`). El cuerpo es un `TransactionUpdate` **opcional** para confirmar al pagar lo que cambió (típicamente `fx_rate_to_base`, `amount`, `occurred_at`); se validan con las reglas de T-206a y la transacción pasa a `posted`, afectando saldos desde ese momento. Devuelve la `Transaction`. No existe «des-publicar» en V1.

## Archivos permitidos

```
services/api/alembic/versions/0004_transfer_integrity.py
services/api/src/monetae/db/models/ledger.py              # SOLO índices/CHECK de la migración 0004
services/api/src/monetae/domain/transfers.py              # reglas puras (tasa implícita, validación de importes)
services/api/src/monetae/services/transfers.py
services/api/src/monetae/services/transactions.py         # SOLO: batch y publicar programadas (y lo mínimo compartido)
services/api/src/monetae/api/schemas/transfers.py
services/api/src/monetae/api/schemas/transactions.py      # SOLO: batch / ActionResult si no existe
services/api/src/monetae/api/routers/transfers.py
services/api/src/monetae/api/routers/transactions.py      # SOLO: rutas batch y post
services/api/src/monetae/api/main.py                      # registrar router
services/api/tests/db/test_migration_0004.py
services/api/tests/db/test_migration_0003.py              # SOLO si la cabeza de migración lo exige
services/api/tests/db/test_migration_0001.py              # SOLO si la cabeza de migración lo exige
services/api/tests/domain/test_transfers_rules.py
services/api/tests/api/conftest.py                        # helpers
services/api/tests/api/test_transfers.py
services/api/tests/api/test_transfers_isolation.py
services/api/tests/api/test_transfers_concurrency.py
services/api/tests/api/test_transactions_batch.py
services/api/tests/api/test_transactions_post_scheduled.py
services/api/tests/api/test_account_balance.py            # SOLO añadir casos de transferencias
services/api/tests/api/test_contract_subset.py            # actualizar
docs/api/README.md                                        # SOLO sección «Transferencias, lotes y programadas (T-206b)»
```

No tocar `pyproject.toml`/`uv.lock`, `openapi.json`, `docs/ARCHITECTURE.md`, `api/security.py`, ni los módulos de dominio `money.py`/`fx.py`. Si el contrato o ARCHITECTURE te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`.

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- **Migración 0004:** `0003→0004→0003→0004`, `alembic check` limpio; SQL directo no puede crear una tercera pata viva, ni una fila `transfer` sin grupo, ni una no-`transfer` con grupo.
- **Transferencias:** misma moneda (iguales / distintos importes ⇒ 422), monedas distintas con tasa implícita (el Ejemplo C de SPEC §7 en sentido PEN→USD y USD→PEN), tasas por pata en base y no base, cuentas iguales ⇒ 422, cuenta ajena o borrada ⇒ 404, PATCH con revalidación completa y cambio de moneda de cuenta sin tasa ⇒ 422, DELETE/restore de las dos patas, saldos de **ambas** cuentas antes y después (suman cero en una misma moneda), las patas no se pueden tocar por `/transactions/{id}`, listado paginado sin duplicados ni huecos y sin N+1.
- **Aislamiento entre dos usuarios** para cada operación de `/transfers*`, `batch` y `post`: siempre `404`/vacío; `transfer_group_id` ajeno ⇒ `404`.
- **Concurrencia:** (a) dos PATCH simultáneos a la misma transferencia terminan sin interbloqueo y con estado coherente (ambas patas consistentes); (b) dos lotes con ids cruzados no se interbloquean; (c) una lectura (`GET /transfers`, `GET /transactions`) **no** espera mientras una escritura del mismo usuario está en vuelo (mide como en T-204/T-206a: debe responder en milisegundos).
- **Lotes:** cada acción, atomicidad (un id ajeno ⇒ nada cambia), 200 ids, 201 ids ⇒ 422, `changes`/`tag_ids` mal usados ⇒ 422, campos no permitidos en `edit` ⇒ 422, patas de transferencia ⇒ 409 sin cambios.
- **Publicar:** scheduled→posted con y sin cambios, el saldo cambia solo al publicar, ya publicada ⇒ 409, transferencia ⇒ 409, tasa foránea actualizada al publicar.
- Los 333 tests actuales siguen verdes (explica en `worker_done` cualquiera que debas tocar y por qué).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0003 && uv run alembic upgrade head
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build   # arranca migrado
docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

Y mide tú también, con curl contra el stack, que una lectura del mismo usuario **no se retrasa** mientras otra escritura del mismo usuario está en vuelo (simúlalo con `psql 'begin; …; select pg_sleep(6); commit;'` sobre las filas de la transferencia, como en T-204).

## Reglas

Commits pequeños en inglés (`feat(transfers):`, `feat(batch):`, `test(ledger):`), por etapas (migración → dominio → servicio → rutas → pruebas). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen → `orca orchestration ask`. Reporta `worker_done` una sola vez.
