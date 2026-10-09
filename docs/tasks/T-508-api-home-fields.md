# T-508 — API: cuenta por defecto, nº de transacciones por cuenta y neto acumulado (contrato 0.5.0)

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-09** (verificada por el coordinador: 1032 pruebas, contrato en verde). Autorizados durante la tarea: `api/routers/accounts.py` (pasar `transaction_count`) y **una sola línea** de `api/security.py` (`profile()` delega las preferencias en `AuthService`). (Run `run_c2cebe1745b9`; SPEC v0.5, contrato 0.5.0, disposición de Inicio de Adrian en `docs/ui/home-layout.md`). Corre **en paralelo con T-507** (UI; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium`.

## Contexto

El contrato 0.5.0 añade tres campos que necesita la pantalla de Inicio de Cashew y que el backend aún no tiene. Por eso **`tests/api/test_contract_subset.py` falla hoy en `master-dev` a propósito**; esta tarea lo devuelve a verde. (`Budget.color`, `Goal.color` y `Goal.icon` también son nuevos, pero esos endpoints **no** existen aún: son de la Fase 6; no los implementes.)

## Leer primero

`AGENTS.md`, `docs/SPEC.md` v0.5 (RF-38, RF-48, RF-49), `docs/ui/home-layout.md`, `docs/api/openapi.json` 0.5.0 (`UserPreferences.default_account_id`, `Account.transaction_count`, `CashFlowRow.cumulative_net`) y `docs/api/README.md` (secciones 0.4.0, «Reportes (T-506)» y 0.5.0), y el código: `api/schemas/auth.py` y el servicio de `users/me` (cómo T-505 añadió `transaction_card`), `api/schemas/` y `services/catalog.py` de cuentas, `reports/` (T-506), `tests/api/test_users_me.py`, los tests de cuentas y de reportes, y `test_contract_subset.py`.

## Reglas

1. **`preferences.default_account_id`** (RF-48), `Uuid | null`, por defecto `null`.
   - **Al escribir** (`PATCH /users/me`, que reemplaza `preferences` completo, como en T-505): si apunta a una cuenta inexistente, ajena, borrada o archivada, responde **422 `account_not_found`** y no guarda nada.
   - **Al leer** (`GET /users/me`): si la cuenta guardada se archivó o borró después, devuelve `null`, sin escribir en la base. Los datos antiguos sin el campo se leen como `null`.
2. **`Account.transaction_count`** (RF-49), de solo lectura.
   - Cuenta las transacciones **publicadas** (`status = posted`) y **no borradas** de esa cuenta, de cualquier tipo: incluye las patas de transferencias y las transacciones de préstamos.
   - Aparece en `GET /accounts`, `GET /accounts/{id}` y donde el contrato devuelva `Account`.
   - Se calcula **en SQL y sin N+1**: el listado paginado hace una sola agregación por página, no una consulta por cuenta.
3. **`CashFlowRow.cumulative_net`** (RF-38).
   - Es la suma de `net` desde la **primera fila del rango pedido** hasta la fila actual, incluida, con las mismas reglas de conversión, `by_currency` y `unconverted_count` (acumulados) que `net`.
   - Se calcula en la API (la UI no hace aritmética de dinero).
   - **Con paginación:** la segunda página continúa el acumulado de la primera; no empieza de cero.
4. Sin migración (preferencias en jsonb; los otros dos campos se calculan). Sin cambios en el contrato ni en la SPEC; si algo del contrato te parece incoherente, `ask`.

## Archivos permitidos

```
services/api/src/monetae/api/schemas/auth.py
services/api/src/monetae/api/schemas/<esquemas de cuentas>.py
services/api/src/monetae/api/schemas/reports.py
services/api/src/monetae/services/auth.py            # o el servicio real de users/me
services/api/src/monetae/services/catalog.py         # cuentas: transaction_count
services/api/src/monetae/reports/**                  # cumulative_net
services/api/tests/**                                # nuevas pruebas y SOLO las aserciones existentes que cambien por estos campos
docs/api/README.md                                   # una línea «implementado en T-508» en la sección 0.5.0
```

No tocar migraciones, `domain/`, importador, `openapi.json`, `docs/SPEC.md`, `apps/`, `infra/`. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **`default_account_id`:**
  - guardar una cuenta propia y activa y leerla igual;
  - una cuenta ajena, inexistente, archivada o borrada da 422 y no cambia nada;
  - archivar la cuenta después hace que `GET` devuelva `null`;
  - las preferencias antiguas sin el campo se leen como `null`;
  - el `PATCH` sigue reemplazando el objeto completo, como en T-505.
- **`transaction_count`:**
  - cuenta las publicadas y no las programadas ni las borradas;
  - incluye las patas de transferencias y los movimientos de préstamo con dinero;
  - aislamiento entre dos usuarios;
  - el listado paginado tiene un **número de consultas constante** (mídelo).
- **`cumulative_net`:**
  - con tres meses (ingreso, gasto, vacío) el acumulado sube y baja correctamente;
  - la segunda página continúa el acumulado;
  - con dos monedas, `by_currency` acumula por moneda;
  - `unconverted_count` es acumulado.
- **`test_contract_subset` vuelve a verde.** Además, una sonda con `uvicorn` + `httpx`: login seguido de `GET /accounts` y `GET /reports/cash-flow` inmediatos devuelven 200 con los campos nuevos.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5448 COMPOSE_PROJECT_NAME=monetae-t508
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5448/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

**Importante:** hay una pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080, levantada desde `Monetae-master-dev`) que **no** debes tocar ni bajar. Usa solo tu proyecto y tu puerto.

Commits pequeños en inglés (`feat(api):`, `test(api):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
