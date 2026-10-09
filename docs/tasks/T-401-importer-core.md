# T-401 — Importador de Cashew: migración 0007 y núcleo (cuentas, categorías, etiquetas, transacciones, transferencias)

> **ESTADO: PLANIFICADA — NO LANZAR** hasta que Adrian dé el OK al Paso 3 (2026-10-08).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (esquema real v48 desconocido, idempotencia y migración).
> Depende de: nada (Fase 3 integrada en `master-dev`). **Eres el único dueño de las migraciones**: creas la `0007`. T-402 y T-403 salen de tu rama ya integrada.

## Objetivo

Implementar `monetae.importers.cashew` y el comando `python -m monetae.cli import-cashew` para cargar desde un **SQLite de Cashew (copia, solo lectura)** las cuentas, categorías, etiquetas, transacciones normales, programadas y transferencias, con idempotencia, `--dry-run` y un reporte que explique los saldos. Dejas el andamiaje (pasos enchufables, opciones y reporte) para que **T-402 (préstamos)** y **T-403 (suscripciones y cuadre final)** trabajen en archivos distintos sin pisarse.

## Leer primero

`AGENTS.md` (§6, §8, §9), `docs/SPEC.md` §11 (RF-40a…j), `docs/ARCHITECTURE.md` §5.9 y §6, `docs/cashew-analysis/01-data-model.md` y `03-backup-format.md`, `services/api/tests/fixtures/cashew_v48/README.md` + `expected.json` (los casos A–K), `docs/decisions/008-cashew-loan-import.md` (contexto; los préstamos NO son tuyos), y el código existente: `domain/` (`money`, `fx`, `transactions`, `transfers`), `db/models/` (`catalog`, `ledger`, `loans`, `recurring`), `services/transfers.py` y `services/transactions.py` (invariantes que debes respetar), `cli.py`, `docs/api/README.md` (secciones de transacciones y transferencias).

## Reglas de privacidad (obligatorias)

**Nunca** abras `reference/backups/`. Solo trabajas con los fixtures sintéticos. El comando **rechaza** (código 2, mensaje en español) cualquier ruta que resuelva dentro de un directorio `reference/backups`. La **salida estándar** del CLI muestra solo conteos, saldos y códigos (jamás títulos, notas ni nombres); el detalle va al archivo de `--report-file`.

## Diseño (decidido)

Paquete `services/api/src/monetae/importers/cashew/`:

1. **`reader.py`** — abre `file:<ruta>?mode=ro` (URI) y `PRAGMA query_only=ON`; lee `PRAGMA user_version`; descubre tablas y columnas con `PRAGMA table_info`; **ignora lo desconocido y lo reporta** (`unknown_tables`, `unknown_columns`); tolera tablas ausentes (el v46 no trae `tags`) con una advertencia. Devuelve dataclasses inmutables tipadas. Dinero: `Decimal(str(valor))` redondeado a 2 decimales `ROUND_HALF_UP`, **nunca aritmética con `float`**. Fechas: segundos Unix UTC; si un valor supera `10**11` se interpreta como milisegundos y se avisa. Calcula `sha256` del archivo. Archivo que no es SQLite o sin las tablas mínimas (`wallets`, `categories`, `transactions`) ⇒ error claro, sin traza.
2. **`mapping.py`** — funciones puras (sin BD) que convierten el snapshot en un *plan* tipado.
3. **`runner.py`** — `run_import(session, user_id, snapshot, options) -> ImportReport` en **una sola transacción de BD**. Pasos en este orden: cuentas → categorías → etiquetas → transacciones normales/programadas → transferencias → **`loans.run`** → **`subscriptions.run`**. Crea `loans.py` y `subscriptions.py` como **módulos stub** que solo cuentan lo que difieren (`deferred_loans`, `deferred_recurring`) y devuelven su sección vacía del reporte. `ImportOptions` (dataclass inmutable) ya incluye: `dry_run`, `fx_rate_overrides: dict[str, Decimal]` (moneda → tasa), `loan_fx_rates: dict[str, Decimal]` (pk de transacción → tasa) y `source_path`.
4. **`report.py`** — modelos Pydantic estrictos: `file_sha256`, `source_schema_version`, `tables`, `unknown_tables`, `unknown_columns`, `warnings`, conteos por entidad (`created`, `already_imported`, `deferred`, `skipped`), `steps: dict[str, ...]` genérico (T-402 y T-403 rellenan su sección **sin cambiar el modelo**), `balances` por cuenta y `review_items`.
5. **`cli.py`** (ya existe): subcomando `import-cashew --file RUTA --user-email EMAIL [--dry-run] [--report-file RUTA] [--fx-rate MONEDA=TASA]... [--loan-fx-rates ARCHIVO.json]`. `--user-email` debe existir (los usuarios se crean con `create-user`). Códigos de salida: 0 ok, 2 uso/ruta prohibida, 3 archivo inválido, 4 error de importación. Tú implementas todo el plumbing de opciones; `--loan-fx-rates` solo se lee y se pasa (lo usa T-402).

### Migración `0007_importer.py` (reversible)

- Tablas `import_runs` (`source_kind` ∈ {`sqlite`,`csv`}, `source_schema_version int NULL`, `file_sha256`, `mode` ∈ {`dry_run`,`apply`}, `started_at`, `finished_at`, `report jsonb`) e `import_review_items` (`import_run_id`, `kind`, `payload jsonb`, `resolved_at NULL`), con columnas comunes y **FK compuestas con `user_id`** (ARCHITECTURE §5.9).
- `import_external_id text NULL` en `accounts`, `categories`, `people`, `tags`, `recurring_rules` y `subscriptions` (hoy solo existe en `transactions` y `loans`), con índice único parcial `(user_id, import_external_id) WHERE import_external_id IS NOT NULL AND deleted_at IS NULL`. Es la única migración de la fase: **añade aquí las seis columnas**, aunque tú solo uses cuatro.
- `alembic check` limpio; `0006→0007→0006→0007` con datos.

### Reglas de mapeo

- **Identidad:** `import_external_id = 'cashew:sqlite:<pk>'`. **Solo inserción:** si ya existe, se omite (`already_imported`); nunca se sobrescribe lo importado ni lo editado después. Reimportar el mismo archivo ⇒ **cero filas creadas o modificadas**.
- **wallets → accounts:** `type = 'other'`, `initial_balance = 0.00` (en Cashew el saldo es la suma de transacciones), `currency` de la cuenta (si es `NULL`: moneda base del usuario + advertencia), `archived` (v48) ⇒ `archived_at`, `order` ⇒ `sort_order`, color e ícono. Si el nombre choca con una cuenta viva de otro origen, añade « (Cashew)» y avisa (los nombres de cuentas son únicos).
- **categories → categories:** `income` ⇒ `kind`; `main_category_pk` ⇒ `parent_id` (dos pasadas); duplicados permitidos; `archived` y `emoji_icon_name` no tienen destino ⇒ se listan en `unmapped_fields`. **No** se fusionan con las categorías de sistema «Intereses»; si una categoría de Cashew se llama así, se avisa.
- **tags / transaction_to_tag_links → tags / transaction_tags:** conserva nombre, color, ícono, emoji, orden y `archived` ⇒ `archived_at`; una etiqueta archivada **conserva sus vínculos**; nombres únicos (misma regla de colisión que cuentas). Entrega una función que mapee `transaction_pk → tags` para que T-402/T-403 etiqueten sus transacciones.
- **transactions (`type` nulo o 0, `paid = 1`):** `kind` por el **signo** de `amount` (si no coincide con `income`, manda `abs(amount) * (1 si income, -1 si no)` como `fixTransactionPolarity` de Cashew, y se registra la anomalía); categoría = `sub_category_fk` si existe, si no `category_fk`; `occurred_at` = `date_created`; `source = 'import'`; `categorization_source = 'manual'`; `is_initial_data = true` si la fecha (America/Lima) cae entre **2025-08-01 y 2025-10-31** (RF-40e). Usa `domain.transactions.normalize_transaction` y `ExchangeRate` para signo, moneda y tasa.
- **Tasa a moneda base:** cuenta en moneda base ⇒ `1.000000`, `fx_rate_source = 'manual'`. Cuenta en otra moneda ⇒ primero `--fx-rate MONEDA=TASA` (`'manual'`); si falta, la tasa de `app_settings.settings_j_s_o_n` (campo de conversión global de Cashew) con `fx_rate_source = 'auto'`; si tampoco hay, el comando **falla antes de escribir** con un mensaje claro. Todas las filas con tasa no manual se cuentan como `provisional_fx` en el reporte (las tasas históricas reales no existen en Cashew).
- **`paid = 0` con `type` nulo o 0 (próxima transacción):** `status = 'scheduled'` (K_future), sin afectar saldos.
- **Transferencias:** dos filas con `paired_transaction_fk` **recíproco**, importes opuestos y misma moneda ⇒ dos patas `kind = 'transfer'` con un `transfer_group_id` nuevo, respetando las invariantes de `services/transfers.py` y del `CHECK`/índices de la migración `0004`. Cualquier otro caso ⇒ dos transacciones ordinarias y `review_item` `unpaired_transfer`.
- **Se difieren** (se cuentan, con su importe y cuenta, para explicar saldos): `type` 3/4 u `objective_loan_fk` no nulo ⇒ `deferred_loans` (T-402); `type` 1/2 ⇒ `deferred_recurring` (T-403).
- **No se importan todavía** (solo conteo en el reporte como «pendiente de Fase 6»): `budgets`, `category_budget_limits`, `associated_titles`, `scanner_templates`, `app_settings`, objetivos `type = 0` (metas). `delete_logs` se ignora.
- **`--dry-run`:** ejecuta todo, revierte los datos financieros y **conserva** la fila de `import_runs` (`mode = 'dry_run'`) con el reporte y sus `import_review_items`.

### Saldos (RF-40c)

Por cuenta: `cashew_balance` = `SUM(amount) WHERE paid = 1` en el SQLite; `monetae_balance` = `initial_balance` + suma de transacciones `posted`; `deferred_amount` = suma de lo diferido con `paid = 1`; `unexplained = cashew_balance − monetae_balance − deferred_amount`. Con los pasos de préstamos y suscripciones aún en stub, la fixture debe dar `unexplained = 0.00` en las cuatro cuentas.

## Archivos permitidos

```
services/api/alembic/versions/0007_importer.py
services/api/src/monetae/db/models/imports.py            # ImportRun, ImportReviewItem
services/api/src/monetae/db/models/__init__.py           # solo exportar
services/api/src/monetae/db/models/catalog.py            # SOLO import_external_id (+ índice)
services/api/src/monetae/db/models/recurring.py          # SOLO import_external_id (+ índice)
services/api/src/monetae/importers/__init__.py
services/api/src/monetae/importers/cashew/{reader,mapping,runner,report,loans,subscriptions}.py   # loans/subscriptions: stubs
services/api/src/monetae/cli.py                          # SOLO el subcomando import-cashew
services/api/tests/importers/                            # conftest + tests nuevos
services/api/tests/db/test_migration_0007.py
services/api/tests/db/test_migration_000{1,5,6}.py       # SOLO si la cabeza de migración lo exige
docs/importers/cashew.md                                 # uso, opciones, formato del reporte (nuevo)
```

No tocar `pyproject.toml`/`uv.lock` (solo biblioteca estándar `sqlite3`), `openapi.json`, `domain/`, `services/` (puedes **leer** su código y reutilizar funciones de dominio, no editar), ni los fixtures. Dependencias: `importers` puede importar de `domain` y `db`; `domain` no importa de `importers`.

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- **Fixture v48 contra `expected.json`:** conteos por tabla, cuentas (moneda, archivada), jerarquía de categorías, las 3 etiquetas y sus 3 vínculos (la archivada conserva el suyo), transferencia H (dos patas, neto 0), `K_future` como `scheduled`, `is_initial_data`, saldos `unexplained = 0.00` en las cuatro cuentas.
- **v46 sin etiquetas:** importa con advertencia de tablas ausentes.
- **Tolerancia:** copia temporal con una columna y una tabla desconocidas ⇒ se reportan y no rompen; archivo no SQLite ⇒ código 3; ruta en `reference/backups` ⇒ código 2.
- **Solo lectura:** el `sha256` del archivo no cambia tras importar y la apertura de escritura falla.
- **Idempotencia:** dos importaciones ⇒ la segunda crea 0 y modifica 0; sin duplicados en ninguna tabla.
- **`--dry-run`:** tablas financieras intactas, fila de `import_runs` presente.
- **Aislamiento entre dos usuarios** (mismo archivo importado por ambos ⇒ datos separados) y atomicidad (un fallo a mitad ⇒ nada persistido salvo el reporte).
- **Moneda foránea:** con `--fx-rate`, con tasa de `app_settings`, y sin ninguna ⇒ falla antes de escribir.
- Migración: `0006→0007→0006→0007` con datos; `alembic check` limpio.
- Privacidad: ningún test imprime ni vuelca títulos o notas; la salida estándar del CLI solo trae conteos y saldos.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0006 && uv run alembic upgrade head
# humo del CLI sobre COPIA del fixture (nunca el original):
cp tests/fixtures/cashew_v48/synthetic_v48.sqlite /tmp/cashew-copy.sqlite
echo 'una-contraseña-larga-123' | uv run python -m monetae.cli create-user --email import@example.test --password-stdin
uv run python -m monetae.cli import-cashew --file /tmp/cashew-copy.sqlite --user-email import@example.test --dry-run
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env /tmp/cashew-copy.sqlite
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(importer):`, `test(importer):`), por etapas (migración → modelos → lector → mapeo → runner → CLI → pruebas). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Dudas que bloqueen (p. ej. cómo guarda v48 el tipo de cambio en `app_settings`) → `orca orchestration ask` con el dato concreto del fixture; **no inventes reglas de negocio**. Si el contrato, ARCHITECTURE o SPEC te parecen inconsistentes con esto, **no los cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
