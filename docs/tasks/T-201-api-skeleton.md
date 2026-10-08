# T-201 — Esqueleto del backend (`services/api`) y stack local con Docker Compose

> Fase 2, primera tarea. Agente: **Codex**. Todas las demás tareas de la Fase 2 dependen de esta.

## Objetivo

Crear el proyecto Python tipado de la API con las herramientas de calidad configuradas, un endpoint de salud conforme al contrato OpenAPI, el manejo de errores `application/problem+json`, y un `docker compose` que levante PostgreSQL y la API con un solo comando. **No hay lógica de negocio ni modelos de BD todavía.**

## Leer primero

`AGENTS.md` (§3 stack, §5 comandos, §6 reglas, §9 seguridad, §10 git), `docs/ARCHITECTURE.md` (§3 capas, §7 API, §9 despliegue local), `docs/decisions/007-sqlalchemy-sync-vs-async.md` (endpoints `def`) y `docs/api/openapi.json` (solo `GET /api/v1/health` y el esquema `Problem`).

## Entorno (ya instalado y verificado)

`uv` 0.12.x y Python 3.12 en `~/.local/bin`; Docker 29 con Compose v5 (Docker Desktop); `psql`. Usa `uv` para todo (`uv sync`, `uv run ...`). El `python3` del sistema es 3.9: **no lo uses** para el proyecto.

## Alcance y archivos permitidos (todos nuevos salvo `.gitignore`)

```
services/api/pyproject.toml          # proyecto "monetae-api", requires-python >=3.12, src layout
services/api/uv.lock
services/api/README.md               # cómo instalar, probar y levantar
services/api/Dockerfile
services/api/src/monetae/__init__.py
services/api/src/monetae/config.py                 # Settings (pydantic-settings), prefijo MONETAE_
services/api/src/monetae/api/__init__.py
services/api/src/monetae/api/main.py               # create_app() + app
services/api/src/monetae/api/errors.py            # Problem (Pydantic estricto) y manejadores de excepción
services/api/src/monetae/api/routers/__init__.py
services/api/src/monetae/api/routers/health.py
services/api/src/monetae/domain/__init__.py        # vacío (placeholder de capa)
services/api/src/monetae/db/__init__.py            # vacío
services/api/src/monetae/importers/__init__.py     # vacío
services/api/src/monetae/reports/__init__.py       # vacío
services/api/tests/conftest.py
services/api/tests/test_health.py
services/api/tests/test_problem_json.py
services/api/tests/test_architecture.py            # prueba de dependencias entre capas
infra/docker-compose.yml
.env.example                                      # en la raíz del repo, valores NO secretos
.gitignore                                        # SOLO añadir: .env, .venv/, __pycache__/, .mypy_cache/, .ruff_cache/, .pytest_cache/, *.egg-info/
```

No tocar nada más (ni `docs/`, ni `reference/`, ni `scripts/`, ni `services/api/tests/fixtures/`, que pertenece a T-105).

## Dependencias permitidas (justificadas; no añadas otras sin preguntar)

- Ejecución: `fastapi`, `uvicorn[standard]`, `pydantic` v2, `pydantic-settings` (configuración tipada por entorno), `sqlalchemy>=2`, `alembic`, `psycopg[binary]>=3` (ya fijados en AGENTS.md §3 y ADR-007), `argon2-cffi` (ADR-002: hash de contraseñas; se declara ahora para fijar `uv.lock` una sola vez).
- Desarrollo: `pytest`, `httpx` (cliente de pruebas de FastAPI), `ruff`, `mypy`.
- Sin dependencias asíncronas de BD (`asyncpg`, `pytest-asyncio`): ADR-007.

## Requisitos

1. **Calidad desde el día 1:** `ruff` (lint + format, línea 100), `mypy --strict` con el plugin de Pydantic, `pytest`. Prohibido `Any` y `# type: ignore` sin justificar (AGENTS.md §6.1).
2. **`create_app()`** devuelve la aplicación; `GET /api/v1/health` responde `200 {"status":"ok"}` (esquema `Health` del contrato), sin tocar la BD y sin autenticación. Endpoints con `def` (ADR-007).
3. **Errores `application/problem+json`:** modelo `Problem` estricto con `type`, `title`, `status`, `detail` y opcionales `instance`, `code`, `errors`. Manejadores para: `HTTPException` (404, 405…), errores de validación de FastAPI (422, con la lista `errors` de campos) y cualquier excepción no controlada (500 **sin filtrar detalles internos**). Todas con `Content-Type: application/problem+json`.
4. **Configuración:** `Settings` con `database_url`, `environment` (`local`/`test`/`prod`), `cors_origins` (lista) y nada con valor secreto por defecto; se lee de variables `MONETAE_*`. `.env.example` documenta cada variable con valores de ejemplo claramente falsos (`change-me`).
5. **CORS** restringido a `cors_origins` (vacío por defecto = ninguno).
6. **Docker Compose** (`infra/docker-compose.yml`): servicio `db` (`postgres:16`, volumen nombrado, `healthcheck` con `pg_isready`, puerto publicado solo en `127.0.0.1`) y servicio `api` (build de `services/api/Dockerfile`, `depends_on` con `condition: service_healthy`, lee variables del `.env`, puerto `8000` solo en `127.0.0.1`). El `Dockerfile` usa una imagen oficial de Python 3.12 slim, instala con `uv` desde `uv.lock` (congelado), ejecuta como usuario no root y arranca `uvicorn`.
7. **Prueba de arquitectura** (`test_architecture.py`): comprueba por análisis estático de imports (`ast`) que `monetae.domain` no importa de `api`, `db` ni `importers` (AGENTS.md §4).
8. Cada prueba funciona sin Docker ni BD (la BD llega en T-203).

## Criterios de aceptación (incluye las salidas en `worker_done`)

```bash
cd services/api
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -q
cd ../..
cp .env.example .env            # solo para la prueba; .env está ignorado
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml ps          # db healthy, api running
curl -s -i http://127.0.0.1:8000/api/v1/health         # 200 {"status":"ok"}
curl -s -i http://127.0.0.1:8000/api/v1/no-existe      # 404 application/problem+json
docker compose -f infra/docker-compose.yml down -v
git status --short                                     # .env NO aparece
git diff --stat master-dev...HEAD                      # solo archivos permitidos
```

Además: `uv.lock` versionado y consistente (`uv lock --check`); ningún secreto real en el repo; `GET /api/v1/health` coincide con `docs/api/openapi.json` (comprueba el esquema de respuesta con una prueba).

## Reglas

Commits pequeños en inglés (`feat(api):`, `chore:`). Actualiza tu rama con `master-dev` antes de reportar. Dudas que bloqueen → `orca orchestration ask`. Reporta `worker_done` una sola vez.
