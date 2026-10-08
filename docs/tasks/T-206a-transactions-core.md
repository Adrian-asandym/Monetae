# T-206a — Transacciones: tabla, claves compuestas, CRUD, filtros, etiquetas, saldos e idempotencia

> Fase 2. Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (la tarea más delicada de la fase: esquema con aislamiento a nivel de BD, dinero, filtros y concurrencia).
> Depende de T-205 (integrada). Eres el **único dueño de las migraciones** durante esta tarea: creas la `0003`.
> Esta tarea **no** incluye transferencias, lotes ni «publicar programadas» (T-206b), ni recurrentes, adjuntos, presupuestos, metas, préstamos ni sugerencia de tipo de cambio (fases posteriores).

## Objetivo

Crear la tabla `transactions` (y `transaction_tags`, `idempotency_keys`) con **claves foráneas compuestas con `user_id`** para que la base de datos impida referenciar datos de otro usuario, y exponer: `POST/GET/PATCH/DELETE /transactions`, `GET /transactions/{id}`, `POST /transactions/{id}/restore`, `PUT /transactions/{id}/tags`, con filtros, paginación por llaves y `Idempotency-Key`. Además, **calcular el saldo de las cuentas** y relajar los candados que dejó T-204/T-205.

## Leer primero

`AGENTS.md` (§6 — sobre todo dinero y `user_id`), `docs/ARCHITECTURE.md` (§4, §5.4, §5.8, §7 y **§10 puntos 9 y 8**), `docs/SPEC.md` (§5.3 RF-07 a RF-12, RF-43 a RF-45, §9), `docs/api/openapi.json` (rutas `/transactions*`, esquemas `Transaction*`, `IdempotencyKey`, `Problem`) y `docs/api/README.md`. Reutiliza `UserScopedRepository`, `api/pagination.py`, `services/auth.py::AuthError` y el estilo de T-204/T-205. El dominio `Money`/`ExchangeRate` ya existe: **úsalo**.

## Esquema (migración `0003_transactions.py`, reversible)

1. **Antes de crear tablas**, añade `UNIQUE (id, user_id)` a `accounts`, `categories` y `tags` (necesario para las FK compuestas).
2. **`transactions`** exactamente como `ARCHITECTURE.md` §5.4: columnas y tipos, `CHECK (amount <> 0)`, `CHECK (fx_rate_to_base > 0)`, enumeraciones `text + CHECK` (`kind` ∈ income/expense/transfer/loan; `status` ∈ posted/scheduled; `fx_rate_source`; `source`; `categorization_source`), moneda en mayúsculas, `is_initial_data`, `import_external_id`, `transfer_group_id`, `recurring_rule_id` (**sin FK todavía**: la tabla de reglas llega después; deja comentario).
   - FK compuestas: `(account_id, user_id) → accounts(id, user_id)`, **`(account_id, currency) → accounts(id, currency)`**, `(category_id, user_id) → categories(id, user_id)`.
   - Índices del §5.4, todos parciales `WHERE deleted_at IS NULL`, más único parcial `(user_id, import_external_id) WHERE import_external_id IS NOT NULL AND deleted_at IS NULL`.
3. **`transaction_tags`**: columnas comunes con `deleted_at`; FK compuestas `(transaction_id, user_id) → transactions(id, user_id)` y `(tag_id, user_id) → tags(id, user_id)`; único parcial `(transaction_id, tag_id) WHERE deleted_at IS NULL`; índice `(user_id, tag_id)`.
4. **`idempotency_keys`** (§5.8): `user_id`, `key text`, `request_hash bytea`, `response_status int`, `response_body jsonb`, `created_at`, `expires_at`; único `(user_id, key)`.
5. `upgrade`/`downgrade` completos y probados (`downgrade` a `0002` elimina también las `UNIQUE (id, user_id)`); `alembic check` sin diferencias.

## Reglas de negocio (decididas; el contrato no las fija)

1. **Signo:** `income` ⇒ `amount > 0`; `expense` ⇒ `amount < 0` (el monto viaja con signo, como en la BD). `POST /transactions` solo crea `income` y `expense` (los tipos `transfer` y `loan` los crean sus propios flujos); otro tipo ⇒ `422`. La moneda de la transacción **es la de su cuenta**: si el cuerpo trae otra ⇒ `422` `code: currency_mismatch`.
2. **Tipo de cambio:** el contrato exige siempre `fx_rate_to_base` y `fx_rate_source`. Si la moneda de la cuenta es la moneda base del usuario, `fx_rate_to_base` **debe ser exactamente `1.000000`** (otro valor ⇒ `422` `code: invalid_fx_rate`). Si es otra moneda, debe ser `> 0` (6 decimales, normalizado con `ExchangeRate`/`Money` del dominio) y **no se recalcula nunca**; aún no hay proveedor automático, así que `fx_rate_source` es lo que envía el cliente.
3. **Estado:** `posted` o `scheduled`. Solo las `posted` y no borradas cuentan para saldos. Las `scheduled` pueden tener fecha futura. (Publicar una programada es T-206b.)
4. **Saldo de cuentas (RF-02):** `balance = initial_balance + SUM(amount)` de transacciones `posted` no borradas de esa cuenta, calculado en SQL **sin N+1** en listados (una sola consulta agregada para la página). Reemplaza el `balance = initial_balance` provisional de T-205 y actualiza su prueba.
5. **Candados que se relajan:** (a) `PATCH /accounts/{id}` puede cambiar `currency` **solo si la cuenta no tiene ninguna fila en `transactions`** (borrada o no); si no, `409 account_currency_locked`. (b) `PATCH /users/me` puede cambiar `base_currency` **solo si el usuario no tiene ninguna transacción**; si no, `409 base_currency_locked` (y al cambiarla, `report_currency` sigue su propio valor). (c) `DELETE /accounts/{id}` ⇒ `409` `code: account_in_use` si tiene transacciones no borradas (el mensaje sugiere archivar). (d) `DELETE /categories/{id}` ⇒ `409` `code: category_in_use` si tiene transacciones no borradas.
6. **Etiquetas:** `PUT /transactions/{id}/tags` reemplaza el conjunto (borrado lógico de los vínculos retirados, reutiliza o crea los nuevos); una etiqueta ajena o borrada ⇒ `404`; una etiqueta **archivada** solo puede añadirse si ya estaba vinculada (archivar no quita vínculos). Los vínculos de una etiqueta borrada no aparecen en `tag_ids`. `tag_ids` también se acepta al crear.
7. **Edición:** `PATCH` parcial; cambiar de `account_id` solo a una cuenta **de la misma moneda** (si no ⇒ `422` `code: currency_mismatch`); el signo debe seguir cumpliendo la regla 1 al cambiar `kind` o `amount`. No se pueden editar `source`, `is_initial_data`, `transfer_group_id` ni `import_external_id`.
8. **Borrado lógico y deshacer (RF-12):** `DELETE` marca `deleted_at`; `POST …/restore` lo revierte (`409` si su cuenta o categoría están borradas). Una transacción borrada no aparece salvo `include_deleted=true`.
9. **Listado (RF-10):** orden `occurred_at DESC, id DESC` con paginación por llaves y cursor firmado (reutiliza `api/pagination.py`). Filtros: `date_from` (inclusivo) y `date_to` (**exclusivo**), ambos *timestamps* con zona horaria como define el contrato (uno sin zona ⇒ `422`), `account_id`, `category_id`, `currency`, `kind`, `status`, `tag_ids` (OR, parámetro repetido), `q` (coincidencia por texto completo en español **o** subcadena sin distinguir mayúsculas en título/nota, con escape de comodines), `include_deleted`. `loan_id` y `person_id` se aceptan y, mientras no existan préstamos, devuelven página vacía (se implementarán en la Fase 3; deja un comentario `TODO(phase-3)` con la referencia). `tag_ids` de cada elemento se cargan con **una** consulta por página.
10. **Idempotencia** (`POST /transactions`): cabecera `Idempotency-Key` opcional (1–128 caracteres). Misma clave y mismo cuerpo canónico ⇒ devuelve el estado y cuerpo guardados (sin crear otra); misma clave con cuerpo distinto ⇒ `409` `code: idempotency_conflict`; retención 24 h (las expiradas se ignoran y se purgan de forma oportunista). Dos peticiones simultáneas con la misma clave **no** crean dos transacciones (bloqueo consultivo por `(user_id, key)` dentro de la transacción). Implementa el mecanismo como componente reutilizable (`services/idempotency.py`) porque lo usarán préstamos y movimientos.
11. **Aislamiento y rendimiento:** ninguna lectura toma bloqueos de fila. Con 20 000 transacciones de un usuario, la primera página del listado por defecto debe responder en menos de 300 ms y el plan debe usar el índice `(user_id, occurred_at DESC)` (verifica con `EXPLAIN`).

## Archivos permitidos

```
services/api/alembic/versions/0003_transactions.py
services/api/src/monetae/db/models/ledger.py              # Transaction, TransactionTag, IdempotencyKey
services/api/src/monetae/db/models/__init__.py            # solo exportar
services/api/src/monetae/db/models/catalog.py             # SOLO añadir UniqueConstraint(id, user_id) y relaciones necesarias
services/api/src/monetae/domain/transactions.py           # reglas puras: signo, tipo de cambio, equivalencias (usa Money/ExchangeRate)
services/api/src/monetae/services/transactions.py
services/api/src/monetae/services/idempotency.py
services/api/src/monetae/services/catalog.py              # SOLO: saldo, relajar candados, 409 *_in_use
services/api/src/monetae/services/auth.py                 # SOLO update_user: regla de base_currency
services/api/src/monetae/api/schemas/transactions.py
services/api/src/monetae/api/schemas/accounts.py          # SOLO el campo balance
services/api/src/monetae/api/routers/transactions.py
services/api/src/monetae/api/routers/accounts.py          # SOLO si hace falta para el saldo
services/api/src/monetae/api/main.py                      # registrar router
services/api/src/monetae/db/repository.py                # SOLO si necesitas algo genérico; no relajes el aislamiento
services/api/tests/db/test_migration_0003.py
services/api/tests/db/test_ledger_constraints.py
services/api/tests/db/test_migration_0001.py              # SOLO si la aserción de tablas/cabeza de migración lo exige
services/api/tests/domain/test_transactions_rules.py
services/api/tests/api/conftest.py                        # helpers
services/api/tests/api/test_transactions_crud.py
services/api/tests/api/test_transactions_filters.py
services/api/tests/api/test_transactions_tags.py
services/api/tests/api/test_transactions_isolation.py
services/api/tests/api/test_transactions_idempotency.py
services/api/tests/api/test_account_balance.py
services/api/tests/api/test_transactions_performance.py
services/api/tests/api/test_accounts.py                   # SOLO ajustar el saldo y los candados relajados
services/api/tests/api/test_catalog_isolation.py          # SOLO si se rompe por lo anterior
services/api/tests/api/test_contract_subset.py            # actualizar
docs/api/README.md                                        # SOLO sección «Transacciones (T-206a)»
docs/ARCHITECTURE.md                                      # NO tocar; anota discrepancias en worker_done
```

No tocar `pyproject.toml`/`uv.lock`, `openapi.json`, `api/security.py`, `domain/money.py`, `domain/fx.py`.

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- **Migración:** `0002→0003→0002→0003`, `alembic check` limpio; existen FK compuestas, índices parciales y `UNIQUE (id, user_id)`.
- **Aislamiento a nivel de BD (lo importante de las FK compuestas):** insertar con SQL directo una transacción cuya `account_id` pertenece a otro usuario ⇒ falla; con `category_id` de otro usuario ⇒ falla; con `currency` distinta a la de su cuenta ⇒ falla; vínculo `transaction_tags` con etiqueta o transacción de otro usuario ⇒ falla.
- **API, aislamiento entre dos usuarios** para cada operación (get, patch, delete, restore, tags, listado, filtros): siempre `404`/vacío, nunca datos ajenos; `account_id`/`category_id`/`tag_ids` ajenos al crear ⇒ `404`.
- Saldos: ingresos, gastos, `scheduled` excluidas, borradas excluidas, restauradas incluidas, varias cuentas y monedas, sin N+1 (cuenta las consultas con un contador de sentencias en el listado de 25 cuentas).
- Reglas 1–10 con pruebas de nombre claro (una regla por prueba cuando sea posible), incluido el límite de 300 ms/EXPLAIN con 20 000 filas y la concurrencia de la idempotencia (dos hilos, misma clave).
- Candados relajados: moneda de cuenta y moneda base cambian solo sin transacciones (incluida una transacción borrada que sigue bloqueando).
- Los 229 tests actuales siguen verdes salvo los que deban cambiar por el saldo/candados (explica cuáles en `worker_done`).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0002 && uv run alembic upgrade head
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build   # arranca migrado
docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src | grep -v "^.*#.*:" || true   # sin 'type: ignore' sin razón escrita
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(ledger):`, `test(ledger):`), por etapas (migración → modelos/dominio → servicio → rutas → pruebas). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen → `orca orchestration ask`. Si ARCHITECTURE o el contrato te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
