# T-505 — API: preferencia `transaction_card` en `users/me` (RF-47)

> **ESTADO: LANZADA el 2026-10-09** (Run `run_c2cebe1745b9`; decisión D11-A de Adrian; SPEC v0.4, contrato 0.4.0).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (cambio pequeño, pero toca un esquema estricto de usuario y datos ya guardados). Corre **en paralelo con T-502** (UI; archivos disjuntos).

## Contexto

El contrato 0.4.0 añade `UserPreferences.transaction_card` (`TransactionCardPreferences`: `show_date`, `show_time`, `show_note`, `show_tags`, `show_account`, `show_actions`, con valores por defecto `true`, `false`, `true`, `true`, `false`, `false`, que reproducen Cashew). El backend aún no lo tiene. **Por eso `tests/api/test_contract_subset.py::test_schema_properties_mirror_contract` falla hoy en `master-dev` a propósito**; esta tarea lo devuelve a verde.

## Leer primero

`AGENTS.md`, `docs/SPEC.md` v0.4 (**RF-47**), `docs/api/openapi.json` 0.4.0 (`UserPreferences`, `TransactionCardPreferences`, `UserUpdate`, `/api/v1/users/me`), `docs/api/README.md` (sección 0.4.0), y el código: `src/monetae/api/schemas/auth.py` (`UserPreferences`, `CurrentUser`, `UserUpdate`), el servicio y la ruta de `users/me`, `tests/api/test_users_me.py` y `tests/api/test_contract_subset.py`.

## Reglas

1. Modelo `TransactionCardPreferences` (estricto, sin campos extra) con los seis booleanos y sus valores por defecto **exactamente** como el contrato; `UserPreferences.transaction_card` con valor por defecto.
2. **Datos ya guardados:** `users.preferences` (jsonb) de usuarios existentes no tiene `transaction_card`. `GET /api/v1/users/me` debe devolverlo **completo con los valores por defecto**, sin migración y sin fallar.
3. **Actualización:** sigue la **semántica actual** de `preferences` en `PATCH /api/v1/users/me` (léela en el servicio y descríbela en el `worker_done`). Si hoy es reemplazo completo del objeto, los campos omitidos de `transaction_card` toman su valor por defecto; no inventes una fusión parcial nueva. Si la semántica actual te parece incoherente con el contrato, pregunta con `ask`.
4. Añade `TransactionCardPreferences` a la lista de modelos comparados en `test_contract_subset.py`.
5. Sin migración (es jsonb). Sin cambios en el contrato ni en la SPEC.

## Archivos permitidos

```
services/api/src/monetae/api/schemas/auth.py
services/api/src/monetae/services/<servicio de usuarios>.py   # SOLO si hace falta para los valores por defecto
services/api/tests/api/test_users_me.py
services/api/tests/api/test_contract_subset.py                 # SOLO añadir el modelo
docs/api/README.md                                             # SOLO una línea en la sección 0.4.0: "implementado en T-505"
```

No tocar migraciones, `domain/`, importador, `openapi.json`, `docs/SPEC.md`, `apps/`. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- Usuario con `preferences` guardadas **sin** `transaction_card` (insértalo así por SQL o ORM): `GET users/me` devuelve los seis valores por defecto.
- `PATCH` que cambia `show_time` y `show_actions` a `true`: persiste y se lee igual; el resto queda según la regla 3.
- Campo desconocido dentro de `transaction_card` o tipo no booleano ⇒ 422.
- Aislamiento: la preferencia de un usuario no afecta a otro.
- `test_contract_subset` vuelve a verde.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5442 COMPOSE_PROJECT_NAME=monetae-t505
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5442/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

Commits pequeños en inglés (`feat(api):`, `test(api):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. Reporta `worker_done` una sola vez.
