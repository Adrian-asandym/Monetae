# T-203 — Base de datos: SQLAlchemy, Alembic y migración 0001 (identidad y catálogos)

> Fase 2. Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (fidelidad al esquema, restricciones de PostgreSQL y aislamiento multiusuario).
> Depende de T-201 (integrada). Corre en paralelo con T-202: **archivos disjuntos**.
> Eres el **único dueño de las migraciones Alembic** mientras dure esta tarea.

## Objetivo

Crear la capa `db/` (base declarativa tipada, sesión síncrona, repositorio con `user_id` obligatorio), configurar Alembic y escribir la migración `0001` con las tablas de identidad y catálogos de `docs/ARCHITECTURE.md` §5.2–5.3, más una batería de pruebas contra PostgreSQL real que incluye el **test de aislamiento entre dos usuarios**.

## Leer primero

`AGENTS.md` (§3, §6.4–6.5, §6.8–6.10, §9), `docs/decisions/007-sqlalchemy-sync-vs-async.md` (síncrono + psycopg 3), `docs/decisions/002-auth-sessions.md`, `docs/ARCHITECTURE.md` (§3 capas, §4 convenciones, §5.1–5.3 esquema).

## Alcance de la migración 0001

Tablas: `users`, `sessions`, `accounts`, `categories`, `people`, `tags`. (`webauthn_credentials`, `transactions`, `transaction_tags`, préstamos y el resto llegan en migraciones posteriores.) Reproduce **exactamente** las columnas, tipos, `CHECK` e índices de ARCHITECTURE §4–§5.2–5.3:

- PK `uuid` con `server_default gen_random_uuid()`; `created_at`/`updated_at` `timestamptz NOT NULL DEFAULT now()` (y `updated_at` se refresca en cada UPDATE vía ORM); `deleted_at timestamptz NULL`; `user_id uuid NOT NULL` con FK a `users` en todas salvo `users`.
- `CHECK (currency = upper(currency))` y longitud 3 donde haya moneda; enumeraciones como `text` + `CHECK ... IN (...)` (no `ENUM` de PostgreSQL); `NUMERIC(18,2)` para dinero.
- Índices únicos **parciales** `WHERE deleted_at IS NULL`: `lower(users.email)`, `users.google_sub` (cuando no es NULL), `(user_id, lower(accounts.name))`, `(user_id, lower(tags.name))` (solo no archivadas), `categories.system_key` por usuario (`(user_id, system_key)` cuando no es NULL), `sessions.token_hash`.
- `accounts`: `UNIQUE (id, currency)` (para la FK compuesta que usará `transactions`).
- `categories`: `parent_id` autorreferencia; **trigger de respaldo** en PL/pgSQL que impide más de un nivel y exige el mismo `kind` del padre; `system_key` ∈ {`interest_income`,`interest_expense`} o NULL, con `is_system` coherente.
- `people.aliases text[] NOT NULL DEFAULT '{}'` con índice GIN, e índice sobre `lower(name)`.
- Reversible: `downgrade` elimina todo lo creado (incluido el trigger y la función).

## Archivos permitidos

```
services/api/src/monetae/db/__init__.py
services/api/src/monetae/db/base.py            # DeclarativeBase, convención de nombres, TimestampMixin, SoftDeleteMixin
services/api/src/monetae/db/session.py         # engine/sessionmaker síncronos desde Settings; dependencia get_session()
services/api/src/monetae/db/models/__init__.py
services/api/src/monetae/db/models/identity.py # User, Session
services/api/src/monetae/db/models/catalog.py  # Account, Category, Person, Tag
services/api/src/monetae/db/repository.py      # UserScopedRepository[T]
services/api/alembic.ini
services/api/alembic/env.py
services/api/alembic/script.py.mako
services/api/alembic/versions/0001_core_identity_and_catalogs.py
services/api/tests/db/__init__.py
services/api/tests/db/conftest.py
services/api/tests/db/test_migration_0001.py
services/api/tests/db/test_models_constraints.py
services/api/tests/db/test_repository_isolation.py
services/api/Dockerfile                        # SOLO: copiar alembic y ejecutar 'alembic upgrade head' antes de uvicorn
infra/docker-compose.yml                       # SOLO si hace falta para lo anterior
```

No tocar `pyproject.toml`/`uv.lock` (las dependencias ya están), `domain/`, `api/`, `.env.example`, ni `tests/conftest.py`.

## Requisitos de diseño

1. **Modelos 2.0 tipados** (`Mapped[...]`, `mapped_column`), `mypy --strict` limpio; sin `Any`. Los modelos reflejan la migración (misma nomenclatura de constraints/índices).
2. **`UserScopedRepository[T]`:** se construye con `(session, model, user_id)`. **Toda** operación (`get`, `list`, `add`, `update`, `soft_delete`, `restore`, `count`) añade `user_id == self.user_id` y `deleted_at IS NULL` (salvo `include_deleted=True` explícito). `add` fija el `user_id` y rechaza instancias con otro `user_id`. No existe ningún método que consulte sin `user_id`. Documenta la regla en el docstring.
3. **Sesión síncrona** (`def`, ADR-007); `get_session()` hace commit/rollback correctamente. `Settings.database_url` es la fuente; las pruebas usan `MONETAE_TEST_DATABASE_URL`.
4. **Alembic** lee la URL de `Settings` (o `-x url=`), con `compare_type=True`, y la migración se puede ejecutar contra una base vacía.
5. **Dockerfile/compose:** la imagen incluye `alembic/` y `alembic.ini`, y el contenedor `api` ejecuta `alembic upgrade head` antes de `uvicorn`, de forma que `docker compose up` deja la BD migrada.

## Pruebas (contra PostgreSQL real)

Fixture de sesión que crea una base de datos de pruebas aislada (p. ej. `monetae_test_<uuid>`) en el servidor de `MONETAE_TEST_DATABASE_URL` (Compose publica `127.0.0.1:5433`), ejecuta `alembic upgrade head`, y la elimina al final. Si no hay servidor alcanzable: `pytest.skip` con mensaje claro **salvo** que `MONETAE_REQUIRE_DB=1`, en cuyo caso falla.

- `test_migration_0001`: `upgrade` → tablas, columnas, tipos, `CHECK`, índices parciales y trigger existen (consulta a `information_schema`/`pg_indexes`); `downgrade` → todo desaparece; ciclo `upgrade/downgrade/upgrade`; **`alembic check` sin diferencias** entre modelos y migración.
- `test_models_constraints`: unicidad parcial (se puede reutilizar un email tras borrado lógico), `CHECK` de moneda, categorías de más de un nivel rechazadas por el trigger, `kind` distinto al del padre rechazado, `system_key` inválido rechazado, FK compuesta preparada (`UNIQUE (id, currency)`), `updated_at` cambia en UPDATE.
- **`test_repository_isolation` (obligatorio, AGENTS.md §6.9):** con dos usuarios A y B y datos en `accounts`, `categories`, `people` y `tags`: A no puede `get`/`list`/`count`/`update`/`soft_delete`/`restore` filas de B (devuelve `None`/vacío/0 o error explícito, nunca datos); `add` con `user_id` ajeno falla; el borrado lógico de A no afecta a B.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
docker compose -f infra/docker-compose.yml up -d db     # con .env copiado de .env.example (ignorado)
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres
export MONETAE_REQUIRE_DB=1
uv sync --frozen
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
uv run alembic check
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build   # api arranca con la BD migrada
docker compose -f infra/docker-compose.yml down -v
git diff --stat master-dev...HEAD       # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(db):`, `test(db):`, `chore(infra):`). Actualiza tu rama con `master-dev` antes de reportar. Dudas que bloqueen → `orca orchestration ask`. Si ARCHITECTURE.md parece inconsistente o incompleto para algo, **no lo cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
