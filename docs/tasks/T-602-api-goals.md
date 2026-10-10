# T-602 — API: metas (RF-31, RF-32) con progreso calculado

> **ESTADO: LANZADA el 2026-10-10** (Run `run_c2cebe1745b9`; OK de Adrian «P1-A»; SPEC v0.5, contrato 0.5.0). Va **después de T-601** (integrada en `master-dev`, `b20bc45`), porque también añade una migración. Corre en paralelo con T-510 (UI; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `medium` (mismo patrón que T-601).

## Contexto

El contrato 0.5.0 define las metas (`/goals`, «Contrato inicial Fase 6»), pero aún no existen ni tablas ni rutas. Inicio (T-509) las lee con `GET /goals`. Esta tarea implementa el CRUD, la asignación de transacciones y el **progreso**, siguiendo el patrón que T-601 acaba de dejar para presupuestos (cópialo: modelos, servicio, router, asignación reversible y número de consultas constante). `/reports/goals` **no** entra aquí; se decidirá junto a `/reports/budgets`.

## Leer primero

- `AGENTS.md` (§6 completo y §8–§11), `docs/SPEC.md` v0.5 §5.7 (RF-31, RF-32) y §7–§8.
- `docs/ARCHITECTURE.md`: tablas `goals` y `goal_transactions`, y §5.8 (conversión).
- `docs/api/openapi.json` 0.5.0: `Goal`, `GoalCreate`, `GoalUpdate`, `GoalPage`, `TransactionAssignment`, `ReportTotal`; las rutas `/goals`, `/goals/{id}` y `/goals/{id}/transactions`, con sus errores.
- El código de **T-601**: migración `0009`, `db/models/budgets.py`, `services/budgets.py`, `reports/budgets.py`, `api/routers/budgets.py`, `api/schemas/budgets.py` y sus pruebas.
- Para la regla de progreso, Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/pages/objectivesListPage.dart` (cerca de las líneas 1020–1070).

**PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Reglas (no inventes otras: ante un caso no cubierto, `ask`)

1. **Migración `0010`:**
   - `goals` con `kind` ∈ {`spend`,`save`}, `name`, `target_amount NUMERIC(18,2) > 0`, `currency`, `due_on NULL`, `color` (`CHECK` `^#[0-9A-Fa-f]{6}$` o null) e `icon` (de 1 a 64 caracteres, o null).
   - `goal_transactions (goal_id, transaction_id, deleted_at)`.
   - FK **compuestas con `user_id`**, borrado lógico y marcas de tiempo, como en `0009`.
2. **Progreso (como Cashew):**
   - Suma **con signo** de las transacciones **enlazadas** (vínculo no borrado), **publicadas** y **no borradas**, sin importar la fecha: ingreso `+`, gasto `−`, y cada pata de transferencia con su propio signo.
   - Meta `save`: `progress_amount` = esa suma. Meta `spend`: la suma **cambiada de signo** (los gastos suman; un reembolso resta).
   - El progreso **puede ser negativo**. Las programadas no cuentan.
   - Conversión con las reglas de `ReportTotal` y `report_currency = goal.currency` (como T-601). `progress_amount = report_total.report_amount`; lo que no tiene tasa queda en `unconverted_count`. `by_currency` lleva los importes con el mismo signo que el progreso.
   - Con `Decimal` y `Money`; nunca sumes monedas distintas.
3. **Préstamos (RF-32, «las metas no modelan préstamos»):**
   - Enlazar una transacción de `kind = loan` responde **422 `loan_transaction_not_allowed`** y no cambia nada.
   - Las transferencias, los ingresos y los gastos sí se permiten.
4. **CRUD:**
   - `POST` crea la meta.
   - `PATCH` es parcial.
   - `DELETE` es un borrado lógico; el `GET` de una meta borrada da 404.
   - El listado se pagina por cursor, en orden estable y con un número **constante** de consultas.
   - Las validaciones siguen el contrato. `icon` se guarda tal cual (texto del catálogo o `custom:<uuid>`). **No** compruebes que el SVG exista: su API es de la Fase 6.
5. **`PUT /goals/{id}/transactions`:** igual que en T-601.
   - Sustituye la selección: los vínculos que salen se borran lógicamente, los que vuelven se restauran y los nuevos se insertan.
   - Máximo 200 ids, sin repetir; solo transacciones propias y no borradas; es atómico.
   - Además, aplica la regla 3.
6. **Seguridad:** sesión, CSRF y `Origin`; ningún `user_id` del cliente; aislamiento entre **dos usuarios** en cada ruta.
7. Sin cambios en `openapi.json` ni en la SPEC. **Refactor permitido:** extraer lo común de la asignación reversible de T-601 a un módulo compartido, **sin cambiar** el comportamiento de presupuestos (sus pruebas siguen en verde sin tocarlas).

## Archivos permitidos

```
services/api/alembic/versions/0010_*.py
services/api/src/monetae/db/**                      # modelos de metas
services/api/src/monetae/services/goals.py          (+ módulo compartido de asignación si lo extraes; services/budgets.py solo para usarlo)
services/api/src/monetae/api/schemas/goals.py
services/api/src/monetae/api/routers/goals.py       (+ registro en api/main.py)
services/api/src/monetae/reports/**                 # solo para reutilizar la conversión, sin cambiar resultados
services/api/tests/**                               # nuevas; las de presupuestos NO se modifican
docs/api/README.md                                  # sección «Metas (T-602)» con las reglas 2–5
```

No tocar `openapi.json`, `docs/SPEC.md`, `apps/`, `infra/`, el importador ni otras entidades. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Progreso:**
  - `save` con un ingreso, un gasto y una transferencia de entrada da la suma con signo;
  - `spend` con dos gastos y un reembolso da la suma cambiada de signo;
  - las programadas, las borradas y los vínculos borrados no cuentan;
  - el progreso puede ser negativo;
  - conversión: una meta en **USD** sin tasa histórica base→USD deja la transacción en `by_currency`, fuera de `progress_amount`, con `unconverted_count = 1`; una meta en PEN con un gasto en USD convierte con el `fx_rate_to_base` de la transacción; una meta en USD con tasa base→USD convierte (corregido el 2026-10-10 tras la pregunta del worker).
- **Asignación:**
  - un préstamo da 422 y la selección queda intacta;
  - sustitución, restauración y borrado de vínculos;
  - un id ajeno da 404 y no cambia nada;
  - límite de 200.
- **CRUD:** validaciones; `PATCH` parcial; `DELETE` lógico; aislamiento entre dos usuarios; número de consultas **constante** en el listado (mídelo).
- `test_contract_subset` en verde. Sonda con `uvicorn` real + `httpx` (como `test_budgets_server.py`): login, `POST /goals`, `PUT` de transacciones y `GET /goals` inmediatos, con el progreso calculado.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5463 COMPOSE_PROJECT_NAME=monetae-t602
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5463/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                   # 1106 previas + las nuevas, todas en verde
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0009 && uv run alembic upgrade head
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

**Importante:**
- No toques la pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080). Usa solo tu proyecto (`monetae-t602`) y tu puerto (5463).
- Disco justo: no dejes contenedores ni volúmenes al terminar.

Commits pequeños en inglés (`feat(api):`, `test(api):`, `docs(api):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
