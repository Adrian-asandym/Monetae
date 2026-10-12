# T-604 · «Corrección de saldo»: categoría de sistema, par atómico y exclusión de totales

> Lee primero `docs/STATUS.md`, `AGENTS.md` y `docs/SPEC.md` v0.7 (**RF-03**, §9.4). Decisiones de Adrian del 2026-10-12: **T1-B**, **Z1-A**, **Z2-A**, **Z3** (reutilizar `transfer_group_id`).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama/worktree:** `codex/T-604-balance-correction` en `/home/artur/propio2/Monetae-codex-T-604-balance-correction` (sale de `master-dev`).
- **Solo backend, contrato y docs del importador.** La UI («Transferir saldo») será otra tarea (T-519).

## Contexto
La pantalla «Transferir saldo» de Cashew no crea un tipo especial: guarda **dos transacciones independientes** con la categoría «Corrección de saldo» (en Cashew, `categoryPk "0"`): un **gasto** en la cuenta de origen y un **ingreso** en la de destino. Cashew las excluye de los totales de ingresos y de gastos (`onlyShowIfNotBalanceCorrection`, `database/tables.dart` ~5799 y ~6261) y, por defecto, de los presupuestos (`BudgetTransactionFilters.includeBalanceCorrection`). Código de Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`. **Prohibido** leer o tocar `reference/backups/`.

## Qué hacer

### 1. Categorías de sistema (migración `0012`)
- En Monetae cada categoría tiene `kind` `income` o `expense`, así que se crean **dos** categorías de sistema, ambas con nombre **«Corrección de saldo»**: `system_key` `balance_correction_expense` (kind `expense`) y `balance_correction_income` (kind `income`). Mismo patrón que `interest_income`/`interest_expense` (`services/auth.py`, constraint `system_key` en `db/models/catalog.py`).
- La migración amplía el CHECK de `system_key` y **siembra** ambas categorías para cada usuario existente (idempotente). Los usuarios nuevos las reciben al crearse, igual que las de interés. Ícono y color neutros (gris), sin copiar PNG de Cashew.
- Siguen las reglas de las categorías de sistema existentes (no se borran; revisa qué más impiden hoy y aplícalo igual).

### 2. Enlace del par: reutilizar `transfer_group_id` (sin columnas nuevas)
- Hoy el CHECK `transfer_group` exige `(kind = 'transfer') = (transfer_group_id IS NOT NULL)`. Cámbialo para que `transfer` **siga exigiendo** `transfer_group_id` y que `income`/`expense` **puedan** llevarlo (solo lo asigna el servicio de correcciones; el resto de rutas no deben permitir fijarlo).
- Índices únicos parciales equivalentes a los de transferencias para el par de correcciones (un gasto y un ingreso por grupo, con `deleted_at IS NULL`).
- **Revisa todos los usos** de `transfer_group_id` (`services/transfers.py`, `api/routers/transfers.py`, `api/schemas/transactions.py`, importador) y asegúrate de que lo que hoy se interpreta como transferencia siga filtrando por `kind = 'transfer'`: un par de correcciones **no** debe aparecer en `/transfers` ni ser editable por esa ruta.

### 3. API: `POST /api/v1/balance-corrections` y `GET /api/v1/balance-corrections`
- **POST** crea el par de forma **atómica** (si una falla, ninguna). Cuerpo: `from_account_id`, `to_account_id`, `from_amount` (>0, 2 decimales), `to_amount` (>0, 2 decimales), `occurred_at`, `to_occurred_at` (opcional; por defecto = `occurred_at`; debe ser ≥ `occurred_at`: **transferencias diferidas**), `title` (opcional; si falta, «Transferir saldo»), `note` (opcional), `from_fx_rate_to_base` / `to_fx_rate_to_base` / `fx_rate_source` con **las mismas reglas que `TransferCreate`** (reutiliza su validación). `Idempotency-Key` como el resto de POST. Valida: cuentas distintas, del usuario, no archivadas; `status` `posted`/`scheduled` según la fecha de cada pierna, como en transacciones.
  - Respuesta 201: `{ "group_id", "outgoing": Transaction, "incoming": Transaction }`.
  - Crea: gasto (monto negativo según la convención del libro) en origen con `balance_correction_expense`, ingreso en destino con `balance_correction_income`, mismo `transfer_group_id`, mismo `title`/`note`.
- **Después de creadas, cada pierna es una transacción normal**: `PATCH /transactions/{id}` y `DELETE` funcionan **por separado** (fecha/hora, monto, título, nota…). Si se borra una, la otra se queda (Cashew). Prohíbe por `PATCH` cambiar la categoría de una pierna a otra que no sea de corrección o cambiar su `kind` si eso rompe el par: decide la regla mínima coherente y documéntala.
- **GET** lista pares (paginado por cursor, más recientes primero) con filtros opcionales `from_account_id`, `to_account_id`, `from_currency`, `to_currency`. Cada ítem: `group_id`, ambas piernas resumidas (id, cuenta, moneda, monto, `occurred_at`) y `implicit_rate` **calculada** (`to_amount / from_amount`, 6 decimales; no se guarda). Omite pares con alguna pierna borrada. La UI lo usará para la tasa sugerida y para la lista de «Corrección De Saldo».

### 4. Exclusión de totales (Z1-A)
- Las transacciones con categoría `balance_correction_*` **no cuentan** como ingreso ni gasto en: `reports` `cash-flow` (incluido `cumulative_net`) y `categories`, gasto de **presupuestos** (`reports/budgets.py`) y cualquier total que use Inicio. **Sí** cuentan en el saldo y en `transaction_count` de cada cuenta.
- **Objetivos (`reports/goals.py`):** hoy suman `transfer`; aplica a las correcciones el mismo trato que a las transferencias y explica en `worker_done` qué hace Cashew (`objectives`) si difiere.

### 5. Importador de Cashew (Z2-A)
- Las transacciones de Cashew con la categoría «Corrección de saldo» (`category_fk = "0"`) se importan como correcciones: emparejadas (`paired_transaction_fk`) → par con el mismo `transfer_group_id`; sin pareja → una sola corrección (ya no se reporta como `unpaired_transfer`). Ya **no** se crean `transfer` desde Cashew.
- Mantén la idempotencia, `--dry-run` y el cuadre de saldos. Actualiza los fixtures sintéticos y `docs/importers/` si cambian.

### 6. Contrato 0.7.0
- `docs/api/openapi.json` → `info.version` **0.7.0**: rutas nuevas, esquemas (`BalanceCorrectionCreate`, `BalanceCorrection`, página), `system_key` ampliado. `python3 -I scripts/check_openapi.py` en verde. Nota corta en `docs/api/README.md`.

## Archivos permitidos
`services/api/**` (código, migración, pruebas, fixtures sintéticos), `docs/api/openapi.json`, `docs/api/README.md`, `docs/importers/**`. Nada de `apps/web`. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `uv sync --frozen && uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy` limpios.
2. `uv run pytest -q` **todo verde** con PostgreSQL real (usa un compose propio en otro puerto: `cp .env.example .env && MONETAE_DB_PORT=5434 COMPOSE_PROJECT_NAME=monetae-t604 docker compose -f infra/docker-compose.yml up -d db`; el 5433 es de la pila de revisión: **no la toques**). Al terminar: `down -v` y `rm -f .env`.
3. `uv run alembic upgrade head && uv run alembic check` (cabeza `0012`) y prueba de `downgrade` de `0012`.
4. Pruebas nuevas: par atómico (falla una → ninguna), cuentas iguales/ajenas/archivadas → 422/404, `to_occurred_at` diferido, edición y borrado por separado, el par no aparece en `/transfers`, exclusión en cash-flow/categorías/presupuestos con el saldo de cuenta intacto, multimoneda con tasas, siembra para usuarios existentes y nuevos, importador con pares y sin pareja.
5. Sin datos reales, sin secretos, sin dependencias nuevas. `Decimal` en todo el dinero; `user_id` en todas las consultas.
6. Un commit `feat(api): balance corrections as Cashew-style transfers (T-604)` (o varios coherentes) sin push; `worker_done` con archivos, resumen de verificación y respuestas a: regla de `PATCH` elegida y trato en objetivos/Cashew.
