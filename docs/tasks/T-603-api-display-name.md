# T-603 — API: `display_name` del usuario (contrato 0.6.0, RF-50)

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-10** (1164 pruebas verificadas por el coordinador; el coordinador añadió la limpieza del usuario de la sonda, que dejaba un intento de login y rompía `test_ip_limit_and_purge` según el orden). (Run `run_c2cebe1745b9`; S3-A de Adrian; SPEC v0.6, contrato 0.6.0). Corre **en paralelo con T-512** (UI de Inicio; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `medium`.

## Contexto

Inicio saludará con el nombre del usuario, como Cashew («Buenos días / Adrian Sandy»). El contrato 0.6.0 añade `display_name` a `CurrentUser` y a `UserUpdate`. Por eso `tests/api/test_contract_subset.py` **falla hoy en `master-dev` a propósito**; esta tarea lo devuelve a verde.

## Leer primero

- `AGENTS.md`, `docs/SPEC.md` v0.6 (RF-50), `docs/api/openapi.json` 0.6.0 (`CurrentUser.display_name`, `UserUpdate.display_name`) y `docs/api/README.md` (sección 0.6.0).
- El código de `users/me`: `api/schemas/auth.py`, `services/auth.py`, `api/security.py` (`profile()`) y el modelo de `User` en `db/models`; los cambios de T-505/T-508 como modelo; `tests/api/test_users_me.py`, `test_contract_subset.py`; el CLI `create-user`.

## Reglas

1. **Columna:** `users.display_name` `VARCHAR(60) NULL` con la migración **`0011`** (reversible).
2. **`GET /users/me`:** siempre incluye `display_name` (`null` si no hay).
3. **`PATCH /users/me`:**
   - `display_name` es opcional; si **no** viene, no cambia nada.
   - Se recortan los espacios de los extremos. Si queda vacío, o tiene más de 60 caracteres después de recortar, responde **422** sin cambiar nada.
   - `null` lo borra.
   - Las demás reglas del `PATCH` (preferencias completas, `base_currency` bloqueada…) siguen igual.
4. **CLI `create-user`:** añade una opción **opcional** `--display-name`, con la misma validación.
5. Sin cambios en el contrato ni en la SPEC (ya están hechos).

## Archivos permitidos

```
services/api/alembic/versions/0011_*.py
services/api/src/monetae/db/**                 # solo la columna en User
services/api/src/monetae/api/schemas/auth.py
services/api/src/monetae/services/auth.py
services/api/src/monetae/api/security.py       # solo si profile() necesita pasar el campo
services/api/src/monetae/cli.py                # --display-name
services/api/tests/**                          # nuevas, más el inventario de esquema de test_migration_0001 si hace falta
docs/api/README.md                             # una línea «implementado en T-603» en la sección 0.6.0
```

No tocar `openapi.json`, `docs/SPEC.md`, `apps/`, `infra/`. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Lectura:** `GET` devuelve `null` por defecto.
- **Escritura con `PATCH`:**
  - guarda el nombre recortado; `null` lo borra; sin el campo, no cambia nada;
  - vacío, solo espacios, o 61 caracteres → 422 sin cambios;
  - las preferencias no se pierden al cambiar solo el nombre.
- **CLI:** `--display-name` funciona y valida igual que el `PATCH`.
- **Aislamiento** entre dos usuarios.
- **`test_contract_subset` en verde.**
- **Sonda con `uvicorn` real + `httpx`:** login, `PATCH` del nombre y `GET /users/me` inmediato con el nombre.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5465 COMPOSE_PROJECT_NAME=monetae-t603
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5465/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                   # todas en verde (1149 previas + nuevas)
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0010 && uv run alembic upgrade head
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

**Importante:**
- No toques la pila de revisión (`monetae-review`, puertos 5433/8000/8080) ni la de T-512 (`monetae-t512`). Usa solo tu proyecto (`monetae-t603`) y tu puerto (5465).
- Disco justo: no dejes contenedores ni volúmenes al terminar.

Commits pequeños en inglés (`feat(api):`, `test(api):`). Actualiza tu rama con `master-dev` antes de reportar. **No inventes reglas de negocio**: ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
