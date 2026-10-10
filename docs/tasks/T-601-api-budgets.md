# T-601 — API: presupuestos (RF-28, RF-29) con su periodo en curso

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-10** (`b20bc45`; 1106 pruebas; sonda real: gasto del periodo exacto). (Run `run_c2cebe1745b9`; OK de Adrian «P1-A»; SPEC v0.5, contrato 0.5.0). Corre **en paralelo con T-509** (UI; archivos disjuntos). T-602 (metas) va **después** de esta, porque también añade una migración.
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `high` (dominio nuevo con periodos y conversión).

## Contexto

El contrato 0.5.0 ya define los presupuestos (`/budgets`, «Contrato inicial Fase 6»), pero no hay tablas ni rutas. Inicio (T-509) y la pestaña Presupuestos los leen con `GET /budgets`. Esta tarea implementa el CRUD, la asignación de transacciones y el cálculo del **periodo en curso**. El historial por periodos (`/reports/budgets`, RF-30) **no** entra aquí: el contrato es ambiguo para él y se decidirá aparte.

## Leer primero

- `AGENTS.md` (§6 completo y §8–§11), `docs/SPEC.md` v0.5 §5.6 y §7–§8.
- `docs/ARCHITECTURE.md`: tablas `budgets`, `budget_categories`, `budget_transactions` (§ modelo de datos) y §5.8 (conversión de reportes).
- `docs/api/openapi.json` 0.5.0: `Budget`, `BudgetCreate`, `BudgetUpdate`, `BudgetCategoryLimit`, `BudgetPage`, `TransactionAssignment`, `ReportTotal`; las rutas `/budgets`, `/budgets/{id}` y `/budgets/{id}/transactions`, con sus códigos de error.
- El código, como modelo a imitar:
  - `reports/queries.py` y `reports/service.py` (T-506): qué cuenta como gasto y cómo se convierte;
  - `reports/periods.py` (zona del usuario);
  - una entidad completa reciente, por ejemplo suscripciones: `domain/`, `services/subscriptions.py`, `api/routers/subscriptions.py`, esquemas, migración `0006`;
  - `api/routers/transactions.py` (convención de errores para referencias inválidas en el cuerpo);
  - `tests/api/test_contract_subset.py` y `tests/api/conftest.py`.

## Reglas (no inventes otras: ante un caso no cubierto, `ask`)

1. **Migración `0009`:**
   - `budgets` con `color` y las columnas del contrato, `budget_categories (budget_id, category_id, limit_amount)` y `budget_transactions (budget_id, transaction_id, deleted_at)`.
   - FK **compuestas con `user_id`**, como el resto del esquema.
   - `NUMERIC(18,2)`, `CHECK` de `period`/`scope`, `amount > 0`, `limit_amount >= 0`, y `custom ⇒ end_on IS NOT NULL`. Además, `end_on >= start_on` cuando `end_on` no es nulo.
   - Borrado lógico y `created_at`/`updated_at` como en las demás tablas.
2. **Periodos (dominio puro en `domain/budgets.py`, sin I/O):**
   - **Anclaje:** los ciclos parten de `start_on`.
     - `daily`: un día.
     - `weekly`: 7 días.
     - `monthly`: del día *d* de un mes al día anterior a *d* del mes siguiente. Si *d* no existe en un mes, se usa su último día (un 31 cae en 28/29 o 30).
     - `custom`: un único periodo `[start_on, end_on]`.
   - **`end_on`:** si existe en un periodo recurrente, no hay ciclos después de esa fecha y el último ciclo se recorta a `end_on`.
   - **Periodo en curso:** el ciclo que contiene **hoy en la zona del usuario** (como `reports/periods.py`). Si hoy es anterior a `start_on`, se usa el primer ciclo; si es posterior a `end_on`, el último.
   - Pruebas unitarias exhaustivas: finales de mes, febrero bisiesto, cambios de año y recortes por `end_on`.
3. **Qué suma `spent_amount`:** exactamente lo que T-506 clasifica como **gasto**, dentro del periodo en curso (por fecha en la zona del usuario):
   - transacciones `expense` publicadas y no borradas;
   - más el **interés** pagado en préstamos `borrowed`.
   - **No** suman: transferencias, capital de préstamos, ingresos (no restan gasto) ni programadas.
   - Reutiliza la lógica o la consulta de `reports/`; **no la dupliques** con otras reglas.
   - **Filtro por categorías:**
     - con `category_limits` vacío cuenta **todas** las categorías;
     - con `category_limits` cuenta **solo esas categorías** (como un presupuesto con categorías en Cashew).
     - Los `limit_amount` se guardan y devuelven; en esta tarea **no** generan avance por categoría.
   - **`scope = selected`:** solo cuentan las transacciones enlazadas (vínculo no borrado), con las mismas reglas de clasificación, periodo y categorías. Una transacción de préstamo enlazada aporta solo su interés.
4. **Moneda:**
   - `report_total` usa las reglas de conversión de `ReportTotal` con `report_currency = budget.currency`.
   - `spent_amount = report_total.report_amount`; lo que no tiene tasa queda en `unconverted_count`.
   - `remaining_amount = amount − spent_amount`, que **puede ser negativo** (excedido).
   - Todo con `Decimal` y `Money`; nunca sumes monedas distintas.
5. **CRUD:**
   - `POST` crea el presupuesto.
   - `PATCH` es **parcial**: `category_limits`, si viene, reemplaza la lista entera.
   - `DELETE` es un borrado lógico (un presupuesto borrado no aparece y su `GET` da 404).
   - `GET` lista con paginación por cursor, en orden estable.
   - **Sin N+1:** el listado calcula los gastos de toda la página con un número **constante** de consultas.
   - Validaciones con los códigos del contrato:
     - categorías propias, no borradas y sin repetir en `category_limits`;
     - `custom` sin `end_on`, o `end_on < start_on`, da 422.
     - Para referencias inválidas en el cuerpo, sigue la convención existente (`transactions`). Si dudas, `ask`.
6. **`PUT /budgets/{id}/transactions`:**
   - **Sustituye** la selección: los vínculos que salen se borran lógicamente, los que vuelven se restauran y los nuevos se insertan.
   - Máximo 200 ids, sin repetir.
   - Solo transacciones propias y no borradas; las ajenas o inexistentes responden como dice el contrato.
   - Es atómico: si falla, no cambia nada.
   - Con `scope = all` se permite y se guarda (no cambia el cálculo hasta pasar a `selected`).
7. **Seguridad:** sesión, CSRF y `Origin` como en el resto; ningún `user_id` del cliente; aislamiento con **dos usuarios** en cada ruta.
8. Sin cambios en `openapi.json` ni en la SPEC. `/reports/budgets` y las metas (`/goals`) quedan **fuera**.

## Archivos permitidos

```
services/api/alembic/versions/0009_*.py
services/api/src/monetae/db/**              # modelos nuevos de presupuestos
services/api/src/monetae/domain/budgets.py  (+ export en domain/__init__.py)
services/api/src/monetae/services/budgets.py
services/api/src/monetae/api/schemas/budgets.py
services/api/src/monetae/api/routers/budgets.py (+ registro del router)
services/api/src/monetae/reports/**         # solo para exponer/reutilizar la clasificación de gasto, sin cambiar sus resultados
services/api/tests/**
docs/api/README.md                          # sección «Presupuestos (T-601)» con las reglas 2–6
```

No tocar `openapi.json`, `docs/SPEC.md`, `apps/`, `infra/`, el importador ni otras entidades. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Dominio:**
  - ciclos `daily`/`weekly`/`monthly`/`custom`;
  - anclaje en día 31 y en 29 de febrero;
  - recorte por `end_on`;
  - hoy antes del inicio y después del fin.
- **Gasto:**
  - suma gastos y el interés de préstamos `borrowed`;
  - **no** suma capital, transferencias, ingresos, programadas ni borradas;
  - el filtro por categorías funciona;
  - `selected` cuenta solo lo enlazado;
  - un gasto del último día del periodo en hora de Lima entra, y uno del día siguiente no;
  - excedido da `remaining_amount` negativo;
  - con un gasto en USD sin tasa: `unconverted_count = 1` y no entra en `spent_amount`.
- **CRUD y asignación:**
  - validaciones 422;
  - `PATCH` parcial;
  - `DELETE` lógico;
  - sustitución, restauración y borrado de vínculos;
  - atomicidad ante un id inválido;
  - límite de 200;
  - aislamiento entre dos usuarios;
  - número de consultas **constante** en el listado (mídelo).
- `test_contract_subset` en verde con las rutas nuevas. Sonda con `uvicorn` + `httpx`: login, `POST /budgets` y `GET /budgets` inmediatos, con gasto calculado.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5461 COMPOSE_PROJECT_NAME=monetae-t601
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5461/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                   # 1032 previas + las nuevas, todas en verde
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0008 && uv run alembic upgrade head
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

**Importante:**
- Hay una pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080) que **no** debes tocar ni bajar. Usa solo tu proyecto (`monetae-t601`) y tu puerto (5461).
- Disco justo (≈ 3 GB): no dejes contenedores ni volúmenes al terminar.

Commits pequeños en inglés (`feat(api):`, `test(api):`, `docs(api):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
