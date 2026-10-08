# T-205 — CRUD de catálogos: cuentas, categorías, personas y etiquetas

> Fase 2. Agente: **Codex**, modelo `gpt-6-luna` esfuerzo `high` (tarea repetitiva con reglas claras y pruebas fuertes; si rinde mal la devuelvo o la paso a `gpt-6.1-sol`).
> Depende de T-203 y T-204 (integradas). **No hay migración nueva**: las tablas ya existen (`0001`).

## Objetivo

Exponer los cuatro catálogos que ya están en la base de datos con el contrato `docs/api/openapi.json`: **accounts, categories, people, tags**. Todo autenticado, con CSRF en métodos que modifican, aislamiento por usuario y paginación común. Es la primera tarea que usa `UserScopedRepository` en rutas reales.

## Leer primero

`AGENTS.md` (§6, §9), `docs/ARCHITECTURE.md` (§3, §4, §5.3, §7, §10), `docs/api/openapi.json` (rutas `/accounts*`, `/categories*`, `/people*`, `/tags*`) y `docs/api/README.md` (convenciones de paginación, errores, sesión/CSRF). Revisa cómo T-204 monta rutas, esquemas y dependencias (`api/security.py`, `api/routers/auth.py`, `api/schemas/auth.py`) y **repite ese estilo**.

## Reglas de comportamiento (decididas; el contrato no las fija)

1. **Mismos `operationId`, seguridad y códigos de estado que el contrato.** `DELETE` devuelve el cuerpo y el estado que el contrato declare (borrado lógico: `deleted_at`).
2. **Nunca se acepta ni se devuelve `user_id`.** Un id de otro usuario ⇒ `404` (también para referencias como `parent_id`).
3. **Nombres duplicados** (índices únicos parciales de 0001) ⇒ `409` con `code: duplicate_name`; un nombre borrado lógicamente se puede reutilizar. Comparación sin distinguir mayúsculas.
4. **Cuentas:** `currency` **no se puede cambiar** una vez creada ⇒ `409` `code: account_currency_locked` (T-206 lo relajará cuando exista la tabla de transacciones y pueda comprobar "sin movimientos"). `balance` = `initial_balance` por ahora (T-206 sumará transacciones); documéntalo en el README. `archive`/`reactivate` ponen/quitan `archived_at`; los archivados solo aparecen con `include_archived=true`. `DELETE` es borrado lógico (T-206 añadirá el `409` si tiene movimientos).
5. **Categorías:** las de sistema (`is_system`) no se editan ni se borran ⇒ `409` `code: system_category_immutable`; un solo nivel (el trigger de BD es el respaldo: valida antes en el servicio y traduce el error de BD a `422`/`409` claros, sin filtrar mensajes internos); `DELETE` de una categoría con subcategorías vivas ⇒ `409` `code: category_has_children`; cambiar `kind` de una categoría con hijos ⇒ `409`. El `PATCH` no puede convertir una categoría en `is_system` ni tocar `system_key`.
6. **Personas:** `aliases` se normalizan (recorte de espacios), sin duplicados dentro de la persona (comparación sin mayúsculas), máximo 20 alias de 1–60 caracteres, `name` 1–120. `q` (búsqueda): coincide si el **nombre empieza por** `q` (sin distinguir mayúsculas) **o** algún alias es **igual** a `q` (sin distinguir mayúsculas). Sin `q`, lista todas.
7. **Etiquetas:** `archive`/`reactivate` como en cuentas; reactivar una etiqueta cuyo nombre ya usa otra activa ⇒ `409` `duplicate_name`. Archivar no quita vínculos (aún no existen; llegan en T-206).
8. **Paginación común** en un único módulo (`api/pagination.py`): `limit` 1–200 (por defecto 50), `cursor` opaco, respuesta `{items, next_cursor}`. Paginación **por llaves** (keyset) con orden determinista y estable: cuentas y etiquetas por `(sort_order, lower(name), id)`; categorías por `(kind, lower(name), id)`; personas por `(lower(name), id)`. Cursor corrupto o de otro recurso/filtro ⇒ `400` `code: invalid_cursor`. Nunca duplica ni omite filas aunque se inserten otras entre páginas.
9. Esquemas Pydantic **estrictos** (`extra="forbid"`), dinero como cadena decimal (`initial_balance`), monedas `^[A-Z]{3}$`. Endpoints `def` (ADR-007). Sin lógica de negocio en los routers: reglas en `services/`.

## Archivos permitidos

```
services/api/src/monetae/services/catalog.py          # (o un módulo por recurso) reglas de negocio de los 4 catálogos
services/api/src/monetae/api/pagination.py
services/api/src/monetae/api/schemas/common.py         # Page genérica, ActionResult si no existe
services/api/src/monetae/api/schemas/accounts.py
services/api/src/monetae/api/schemas/categories.py
services/api/src/monetae/api/schemas/people.py
services/api/src/monetae/api/schemas/tags.py
services/api/src/monetae/api/routers/accounts.py
services/api/src/monetae/api/routers/categories.py
services/api/src/monetae/api/routers/people.py
services/api/src/monetae/api/routers/tags.py
services/api/src/monetae/api/main.py                   # SOLO registrar routers
services/api/src/monetae/db/repository.py              # SOLO si necesitas orden/filtros keyset; no relajes el aislamiento
services/api/tests/api/conftest.py                     # helpers: crear usuario autenticado, segundo usuario, cliente con CSRF
services/api/tests/api/test_accounts.py
services/api/tests/api/test_categories.py
services/api/tests/api/test_people.py
services/api/tests/api/test_tags.py
services/api/tests/api/test_pagination.py
services/api/tests/api/test_catalog_isolation.py       # matriz de aislamiento entre dos usuarios
services/api/tests/api/test_contract_subset.py         # actualizar para incluir las rutas nuevas
docs/api/README.md                                     # SOLO una sección "Catálogos (T-205)" con las reglas de arriba
```

No tocar `pyproject.toml`/`uv.lock`, migraciones, `domain/`, `openapi.json` ni `api/security.py` (salvo que descubras un defecto: en ese caso pregunta).

## Pruebas obligatorias (PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- Por recurso: crear/listar/leer/editar/borrar felices; validación (422 con lista de campos); `401` sin sesión; `403` sin CSRF/Origin en métodos que modifican; reglas 3–7.
- **Matriz de aislamiento** (`test_catalog_isolation`): con usuarios A y B, **para cada operación de cada recurso** (get, patch, delete, archive, reactivate) sobre un id de B autenticado como A ⇒ `404`; las listas de A nunca contienen filas de B; `parent_id` de B al crear/editar una categoría de A ⇒ `404`; el cuerpo con `user_id` ⇒ `422`.
- Paginación: orden estable, `limit` en los bordes (1 y 200), `cursor` manipulado ⇒ 400, sin duplicados ni huecos al insertar entre páginas, un cursor de cuentas no sirve en etiquetas.
- Contrato: todas las rutas montadas coinciden con `openapi.json` (mismo `operationId`, seguridad y códigos).
- Reutilización de nombres tras borrado lógico; límite de alias; búsqueda `q` (prefijo de nombre y alias exacto, sin mayúsculas).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

Además: una segunda petición concurrente del mismo usuario **no** se bloquea (no tomes bloqueos de fila en lecturas; ver lección de T-204).

## Reglas

Commits pequeños en inglés (`feat(catalog):`, `test(catalog):`). Actualiza tu rama con `master-dev` antes de reportar. Dudas que bloqueen → `orca orchestration ask`. Si el contrato parece inconsistente con estas reglas, **no lo cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
