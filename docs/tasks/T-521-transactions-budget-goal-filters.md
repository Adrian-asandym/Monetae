# T-521 · Filtros `budget_id` y `goal_id` en `GET /transactions` (D12 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` (§5 verificación, §6 reglas de negocio) y `docs/SPEC.md`.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-521-tx-filters`, sale de `master-dev`.
- **Decisión:** Adrian (D12): el historial de un presupuesto o de una meta **no es un historial aparte**: es la lista de transacciones **filtrada**. Aceptado el 2026-10-18.

## Qué hacer
1. **Contrato** `docs/api/openapi.json` → versión **0.8.0**: dos parámetros de consulta opcionales nuevos en `GET /api/v1/transactions`: `budget_id` (uuid) y `goal_id` (uuid). Descripción en español como el resto del contrato. Combinables con los filtros existentes (`date_from`, `date_to`, `account_id`, `category_id`, `kind`, …) y con la paginación por cursor.
2. **Semántica (obligatoria, no la reinventes):**
   - `budget_id`: exactamente las transacciones que **cuentan como gasto de ese presupuesto**, con el **mismo predicado** que `services/api/src/monetae/reports/budgets.py` (`BUDGET_SQL`): clasificación del libro de reportes (`reports/queries.py` `ENTRY_SQL`: capital de préstamos fuera, correcciones de saldo fuera, etc.), `kind = 'expense'`, `scope = 'all'` o vínculo vivo en `budget_transactions`, y filtro de `budget_categories` si existen. **Sin periodo implícito:** el rango lo dan `date_from`/`date_to` si vienen. Extrae el predicado a un solo lugar reutilizado por ambos (reporte y filtro) si se puede sin cambiar resultados; si no, añade una prueba que demuestre que coinciden.
   - `goal_id`: exactamente las transacciones que suman al progreso de la meta según `reports/goals.py` (`GOAL_SQL`).
   - Presupuesto o meta ajenos o inexistentes → **404** (aislamiento por sesión, como el resto). Borrados lógicamente → 404.
   - `user_id` siempre de la sesión; nunca del cliente.
3. **Pruebas** (PostgreSQL real): presupuesto `all` vs `selected`, con y sin categorías, transacción de capital de préstamo excluida, corrección de saldo excluida, combinación con `date_from/date_to` y con paginación, meta con aportes, 404 ajeno. Una prueba de coherencia: para un ciclo, la suma de `amount` de la lista filtrada = el gasto que reporta el presupuesto.
4. **Documentación:** `docs/api/README.md` (0.8.0, los dos filtros). No toques `docs/SPEC.md` (lo hace el coordinador).
5. **DTO de la UI:** regenera con `python3 -I apps/web/tool/generate_dtos.py` (sin `dart format`) y corre `cd apps/web && dart analyze && flutter test` para demostrar que la UI sigue verde. **No** cambies otros archivos de `apps/web`.

## Archivos permitidos
`services/api/**`, `docs/api/openapi.json`, `docs/api/README.md`, `apps/web/lib/data/api_dtos.dart` (solo regenerado) y, si el generador lo exige, `apps/web/tool/generate_dtos.py`. Otro archivo: pregunta (`ask`).

## Criterios de aceptación (pega la salida)
Con BD propia (no compartas puerto ni proyecto con nadie):
```bash
cp .env.example .env && MONETAE_DB_PORT=5461 COMPOSE_PROJECT_NAME=monetae-t521 docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5461/postgres MONETAE_REQUIRE_DB=1 MONETAE_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5461/postgres
uv sync --frozen && uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q          # hoy: 1190 passed; deben pasar todas + las nuevas
uv run alembic upgrade head && uv run alembic check
cd ../.. && python3 -I scripts/check_openapi.py
COMPOSE_PROJECT_NAME=monetae-t521 docker compose -f infra/docker-compose.yml down -v && rm -f .env
```
1. Todo lo anterior en verde; `test_contract_subset` incluido.
2. Sin migraciones nuevas (no hacen falta); si crees que sí, pregunta antes.
3. `cd apps/web && dart analyze && flutter test` en verde tras regenerar los DTO.
4. Un commit `feat(api): budget_id and goal_id filters on transactions list (T-521)`, sin push. `worker_done` con archivos tocados, número de pruebas y salida de verificación.

## Entorno
`export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"`. Docker rootless (`DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`). Si el shell tiene umask 077 y la imagen de la API no lee archivos, `chmod -R a+rX` sobre el worktree (ver `docs/deploy-alfa.md`).
