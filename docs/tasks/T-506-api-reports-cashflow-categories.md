# T-506 — API: reportes `cash-flow` y `categories` (ingresos y gastos para las gráficas)

> **ESTADO: LANZADA el 2026-10-09** (Run `run_c2cebe1745b9`; OK de Adrian al plan G4 + T-504 ∥ T-506). Corre **en paralelo con T-504** (UI; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (agregación multimoneda, interés de préstamos y aislamiento).

## Objetivo

Implementar `GET /api/v1/reports/cash-flow` y `GET /api/v1/reports/categories` **exactamente** según `docs/api/openapi.json` 0.4.0 (`CashFlowRow`, `CategoryReportRow`, `ReportTotal`, `CurrencyTotal`, sus `*Page` y parámetros). Son la fuente de las gráficas de ingresos y gastos de la UI (T-504).

## Leer primero

`AGENTS.md` (§6 reglas de negocio, §9), `docs/SPEC.md` v0.4 (§7.4 «el capital no es gasto», §9 multimoneda, §10 reportes), `docs/ARCHITECTURE.md` (módulo `reports/`, §5.8 conversión a moneda de reporte, `exchange_rates`, `users.timezone`/`report_currency`), `docs/decisions/003-*.md` (interés en base caja) y `004-*.md`, el contrato de ambos endpoints, y el código: modelos de `transactions`, `loans`/`loan_movements`, `categories` (categorías de sistema `interest_income`/`interest_expense`), `exchange_rates`, y cómo los demás routers aplican sesión, aislamiento, paginación por cursor y `Problem`.

## Reglas (decididas; si algo no encaja con el código o el contrato, `ask`)

1. **Qué cuenta como ingreso o gasto («estadístico»):**
   - Cuentan solo transacciones **publicadas** (`status = posted`) y **no borradas**, de los tipos `income` y `expense`.
   - **No** cuentan las transferencias ni el **capital** de préstamos (`kind = 'loan'`).
   - Las suscripciones archivadas **siguen contando** en su categoría: son gastos que ya ocurrieron.
2. **Interés de préstamos (ADR-003, base caja):**
   - Cuenta la parte `interest_part` de cada movimiento `payment` (y de `write_off` **no**: condonar no mueve dinero), en la **fecha del pago**.
   - Si el préstamo es `lent` es **ingreso**, con categoría de sistema `interest_income`; si es `borrowed` es **gasto**, con `interest_expense`.
   - El interés está en la moneda del préstamo. Cuando el pago se hizo desde una cuenta de otra moneda, se pasa a la moneda de esa cuenta con `fx_rate_applied`, igual que el resto del dominio de préstamos.
   - Lee cómo se registra hoy, para no contar dos veces si ya existe una transacción de interés separada. Si hay ambigüedad, `ask` antes de decidir.
3. **Monedas (§9 y ARCHITECTURE §5.8):**
   - `by_currency` suma por moneda original, sin mezclarlas.
   - `report_amount` usa el `fx_rate_to_base` de cada transacción y, si `report_currency` ≠ base, la tasa base→reporte de `exchange_rates` del día de la transacción o el más cercano **anterior**.
   - Sin tasa, la transacción queda fuera del total convertido y suma 1 a `unconverted_count`.
   - **Nunca** se usa la tasa de hoy para el pasado. Todo con `Decimal`; redondeo `ROUND_HALF_UP` a 2 decimales solo al final.
   - `report_currency` por defecto es la del usuario.
4. **Periodos y zona horaria:**
   - Los cubos se calculan en la zona horaria del usuario (`users.timezone`).
   - `daily` es el día; `weekly` es la semana **ISO, de lunes a domingo** (Cashew usa la del idioma, y en español empieza el lunes); `monthly` es el mes natural; `yearly` es el año natural.
   - `start_on` y `end_on` son inclusivos.
5. **Valores por defecto y forma (el contrato no los fija; quedan decididos así):**
   - **Rango:** sin `date_to` es hoy en la zona del usuario. Sin `date_from`, son los últimos 12 periodos completos hasta `date_to`.
   - **`cash-flow`:** `period` por defecto es `monthly`. Devuelve **una fila por periodo del rango, incluidas las vacías con ceros**, para que la gráfica sea continua. Orden cronológico ascendente.
   - **`categories`:**
     - Sin `period`, es **un solo cubo** para todo el rango. Con `period`, un cubo por periodo.
     - Devuelve **solo** filas con movimiento. El interés va en su categoría de sistema.
     - Una transacción sin categoría va con `category_id = null`.
     - Orden: periodo ascendente y, dentro de él, `report_amount` descendente.
   - `date_from > date_to` devuelve 422. Un rango que daría más de 400 cubos devuelve 422 `range_too_large`.
6. **Filtros:**
   - `account_id` limita a transacciones de esa cuenta. Para el interés, la cuenta es la del pago.
   - `person_id` limita al **interés** de los préstamos de esa persona.
   - Si el filtro apunta a algo ajeno o inexistente, 404.
7. **Aislamiento y seguridad:** todas las consultas filtran por `user_id` de la sesión; sesión obligatoria. Solo lectura: no toman bloqueos de fila (Anexo C de `STATUS.md`). Sin N+1: agregación en SQL.
8. **Paginación:** la del contrato (`Limit`/`Cursor`), estable y sin saltos entre páginas.

## Archivos permitidos

```
services/api/src/monetae/reports/**                 # consultas agregadas (crear si no existe)
services/api/src/monetae/api/routers/reports.py     # nuevo router
services/api/src/monetae/api/schemas/reports.py     # nuevo, espejo del contrato
services/api/src/monetae/api/main.py                # SOLO registrar el router
services/api/tests/reports/**                       # nuevas
services/api/tests/api/test_reports_*.py            # nuevas
services/api/tests/api/test_contract_subset.py      # SOLO añadir los modelos/operaciones nuevos
docs/api/README.md                                  # sección «Reportes (T-506)»
```

No tocar migraciones (si crees que hace falta un índice nuevo, `ask`), `domain/` salvo funciones puras de apoyo justificadas, importador, `openapi.json`, `docs/SPEC.md`, `apps/`. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Base:**
  - un mes con ingresos y gastos en PEN cuadra al céntimo en `cash-flow` y en `categories`;
  - **no** cuentan las transferencias, el capital de préstamos, las programadas ni las borradas.
- **Préstamos (ejemplos de la SPEC §7):** el interés pagado aparece en la fecha del pago y en su categoría de sistema; el capital no aparece. Prueba `lent` y `borrowed`, y un pago desde una cuenta en otra moneda.
- **Multimoneda:**
  - USD y PEN se ven separados en `by_currency` y el total convertido usa `fx_rate_to_base`;
  - con `report_currency` distinto de la base, se usa la tasa del día o la anterior;
  - sin tasa, `unconverted_count` aumenta y la transacción no entra en el total.
- **Periodos:**
  - una semana ISO que cruza un cambio de mes;
  - un borde de día en `America/Lima` (una transacción a las 23:30 hora local cae en su día local, no en el de UTC);
  - los periodos vacíos salen en ceros en `cash-flow`.
- **Validación:** los valores por defecto del rango, `date_from > date_to` y `range_too_large` dan 422; una cuenta o persona ajena da 404.
- **Paginación:** estable, sin filas duplicadas ni perdidas.
- **Aislamiento:** entre dos usuarios, en ambos endpoints.
- **Rendimiento:** con 20 000 transacciones sintéticas, cada endpoint responde en menos de 1 s en local (mide y anótalo; SPEC §12).
- **Sonda con servidor real:** `uvicorn` + `httpx`: login seguido de una petición inmediata a cada endpoint devuelve 200 (Anexo C: `TestClient` no basta).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export MONETAE_DB_PORT=5446 COMPOSE_PROJECT_NAME=monetae-t506
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5446/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check
cd ../.. && python3 -I scripts/check_openapi.py
docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

**Importante:** usa **solo** la base de datos y el proyecto indicados. Hay una pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080) que **no** debes tocar ni bajar.

Commits pequeños en inglés (`feat(reports):`, `test(reports):`, `docs(api):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
