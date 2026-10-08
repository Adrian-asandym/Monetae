# API de Monetae

Esqueleto de FastAPI con Python 3.12+, configuración estricta y endpoints síncronos
(ADR-007). Todavía no contiene modelos, migraciones ni conexiones a la base de datos.
Las dependencias de BD y argon2 se declaran ahora según T-201 para fijar el lock inicial.

Desde `services/api`, usando `uv` (no el Python 3.9 del sistema):

```bash
uv sync --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv lock --check
uv run uvicorn monetae.api.main:app --reload
```

`GET /api/v1/health` responde `200 {"status":"ok"}` sin autenticación ni acceso a BD.
Los errores HTTP, de validación y no controlados usan `application/problem+json`;
los 500 no incluyen detalles internos. `create_app(settings)` permite inyectar configuración.
Las pruebas usan datos sintéticos y no requieren Docker ni PostgreSQL.

## Configuración

`Settings` lee las variables de entorno con prefijo `MONETAE_`:

- `MONETAE_DATABASE_URL`: URL SQLAlchemy síncrona `postgresql+psycopg://...`;
  sin valor predeterminado (`None`). La salud funciona aunque no esté configurada.
- `MONETAE_ENVIRONMENT`: `local` (predeterminado), `test` o `prod`.
- `MONETAE_CORS_ORIGINS`: lista JSON de orígenes exactos, por ejemplo
  `["http://localhost:3000"]`; predeterminado `[]` (sin orígenes autorizados).

La API lee el entorno del proceso. Compose carga el `.env` raíz; para ejecutar fuera
de Docker hay que exportar las variables y sustituir `db:5432` por `127.0.0.1:5433` en la URL.

## Stack local

Desde la raíz del repositorio:

```bash
cp .env.example .env
# Los valores change-me son ejemplos falsos: reemplazarlos para un uso real.
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml ps
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/api/v1/no-existe
# Conserva los datos del volumen:
docker compose -f infra/docker-compose.yml down
```

PostgreSQL 16 espera a estar saludable antes de arrancar la API. Los puertos 5433 (PostgreSQL) y
8000 se publican solo en `127.0.0.1`. El contenedor API usa Python 3.12 slim, instala
el lock congelado con `uv` y ejecuta Uvicorn como usuario no root. No se ejecutan
migraciones hasta T-203. Para eliminar **los datos locales de prueba** al terminar:

```bash
docker compose -f infra/docker-compose.yml down -v
```

`.env` está ignorado por Git y solo `.env.example` se versiona; nunca guardar secretos reales.
