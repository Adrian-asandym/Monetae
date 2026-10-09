# T-402 — Importador de Cashew: préstamos (largo plazo y pago único)

> **ESTADO: PLANIFICADA — NO LANZAR** hasta que Adrian confirme la letra de **J2** del ADR-008 (J1-A y J3-A ya decididos el 2026-10-08) y dé el OK a esta tarea.
> Escrita con las opciones **recomendadas** del ADR-008 (**J1-A, J2-C, J3-A**). Si Adrian elige otras, el coordinador reescribe las secciones «Reglas» y «Pruebas» antes de lanzar.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (regla de negocio sobre datos reales; usa `gpt-6-astra` si T-401 pidió devoluciones o si esta tarea vuelve más de una vez).
> Depende de: **T-401** integrada (migración `0007`, lector, runner y opciones). Corre **en paralelo con T-403** (archivos disjuntos).

## Objetivo

Reemplazar el stub `importers/cashew/loans.py` por la conversión de los préstamos de Cashew a `loans` + `loan_movements` + sus transacciones reales, según `docs/decisions/008-cashew-loan-import.md`. Cada decisión ambigua termina en `import_review_items`, nunca adivinada. Los saldos de las cuentas deben seguir coincidiendo con Cashew (RF-40c).

## Leer primero

`AGENTS.md` (§6, §9), `docs/decisions/008-cashew-loan-import.md` (**todo; manda sobre esta tarea**), `docs/decisions/003-interest-recognition.md`, `docs/cashew-analysis/02-loans.md` (§2, §3, §7), `services/api/tests/fixtures/cashew_v48/README.md` y `expected.json` (`loan_cases`, `one_time_loans`, `ambiguous_cases`), `docs/importers/cashew.md` (T-401), y el código: `importers/cashew/` (runner, reader, report, opciones), `domain/loans.py` (**`replay`, `split_payment`, `plan_excess`, `Movement`, `OverpaymentError`**), `db/models/loans.py`, `services/loans.py` (cómo se arman movimientos y transacciones `kind = 'loan'`; léelo, no lo llames desde el importador), `db/models/ledger.py`.

## Reglas (del ADR-008, con J1-A, J2-C, J3-A)

1. **Detección:** objetivos con `type = 1` ⇒ préstamo de largo plazo; transacciones con `type` 3 (`credit` ⇒ `lent`) o 4 (`debt` ⇒ `borrowed`) sin objetivo ⇒ pago único; cualquier `objective_loan_fk` no nulo pertenece a su objetivo. Estas transacciones **no** se importan como ordinarias (T-401 ya las difiere).
2. **Libro:** aplica R1…R8 del ADR. Ordena por `(date_created, transaction_pk)`; asigna `sequence` consecutiva; `occurred_at` = `date_created`. Cada movimiento con dinero crea su transacción `kind = 'loan'` (importe con signo de Cashew, moneda de **su** cuenta, `source = 'import'`, `import_external_id = 'cashew:sqlite:<pk>'`) y la enlaza (`transaction_id`). Usa `domain.loans.split_payment` para el reparto interés/capital y las etiquetas de T-401 para etiquetar.
3. **Exceso (J2-C):** si un pago supera el saldo, parte la transacción de Cashew en dos: un pago por el **saldo exacto** y una transacción **ordinaria** (`income`/`expense`, sin categoría) por el exceso con `import_external_id = 'cashew:sqlite:<pk>:excess'`. El importe total de ambas es el de la transacción original (la cuenta cuadra). `review_item` `overpayment_detected`. Usa `domain.loans.plan_excess('income_expense', ...)` para calcular las partes.
4. **Pago único `paid = 0` (J1-A):** crea el préstamo con su desembolso y **un pago sintetizado** en la misma cuenta (importe igual al principal; fecha = `date_time_modified`, o la del desembolso si falta; `import_external_id = 'cashew:sqlite:<pk>:synthesized_payment'`). `review_item` `synthesized_payment`. Resultado: `settled` y cuenta con efecto neto 0, como en Cashew.
5. **Otra moneda (J3-A):** si la cuenta de un pago tiene una moneda distinta a la del préstamo, **no adivines tasa**: importa esa transacción como ordinaria (`income`/`expense`) y registra `fx_rate_required` (incluye `transaction_pk` y moneda). Con `--loan-fx-rates` (T-401 ya lo lee) y una tasa para ese `pk`, la **segunda pasada** convierte la transacción ordinaria ya importada en un pago real: cambia su `kind` a `loan`, crea el movimiento con `fx_rate_applied` y `amount_in_loan_currency = |importe| / tasa` (`ROUND_HALF_UP`, como `domain.loans.loan_amount_from_account`), y cierra el `review_item` (`resolved_at`). Si implementar la segunda pasada resulta desproporcionado, **pregunta con `ask`** antes de recortarla.
6. **Personas (R5):** normaliza con `domain.subscriptions.normalize_title`; reutiliza una persona existente por nombre o alias; si no existe, créala con `import_external_id = 'cashew:sqlite:person:<nombre normalizado>'` y la nota indicada en el ADR. Dos préstamos a «Carlos» comparten persona.
7. **Validación final:** antes de persistir cada préstamo, ejecuta `domain.loans.replay`. Si falla (p. ej. un objetivo sin desembolso), **no se crea el préstamo**: todas sus transacciones se importan como ordinarias y se registra `ledger_invalid` con el motivo. Un préstamo inválido nunca aborta el resto.
8. **Interés suelto (R6):** detecta transacciones sin `objective_loan_fk` cuya categoría o título (normalizados) contengan «interes» y regístralas como `orphan_interest` con los préstamos candidatos; **no las enlaces ni las modifiques**.
9. **Idempotencia:** el préstamo usa `import_external_id = 'cashew:sqlite:objective:<pk>'` (largo plazo) o `'cashew:sqlite:tx:<pk>'` (pago único). Si ya existe, se omite entero (solo inserción), salvo la segunda pasada del punto 5.
10. **Reporte:** rellena `steps['loans']` con préstamos creados/omitidos/inválidos, movimientos por tipo, `deferred` que ya no son diferidos, y conteos por tipo de `review_item`. Sin títulos ni nombres en la salida estándar.

## Archivos permitidos

```
services/api/src/monetae/importers/cashew/loans.py           # reemplaza el stub
services/api/tests/importers/test_cashew_loans_*.py          # nuevos
services/api/tests/importers/conftest.py                     # SOLO helpers (no cambiar los de T-401)
docs/importers/cashew-loans.md                               # nuevo: reglas aplicadas y revisión manual
```

No tocar `runner.py`, `report.py`, `reader.py`, `mapping.py`, `cli.py`, la migración, `domain/`, `services/`, `docs/decisions/` ni `docs/importers/cashew.md` (los posee T-401/T-403). Si necesitas un cambio ahí, pídelo con `ask`. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real)

- **Fixture A–F contra `expected.json` y el ADR-008:** A = préstamo `borrowed` 200 con pagos 100 + 100 y gasto ordinario de 10 por el exceso (+ `orphan_interest` del −10 suelto); B = `settled` con cobros 300 (Efectivo) + 200 (Cuenta Soles) en cuentas distintas; C = préstamo USD abierto con `fx_rate_required` y, tras la **segunda pasada** con `3.800000`, `settled` con 100 USD; D = pago 50 + ingreso ordinario 10; E = saldos 950, 830, 800, 0 y `settled` solo al final; F_settled = `lent` 150 `settled` con pago sintetizado; F_open = `borrowed` 80 abierto.
- **Saldos:** con T-401 + T-402, `unexplained = 0.00` en las cuatro cuentas (los préstamos ya no son «diferidos»).
- **P1/P2/P3 sobre lo importado:** ningún préstamo saldado desaparece; el saldo viene de `replay` (sin columna ni «liquidar»); cada pago conserva su cuenta.
- **Invariantes:** el capital no cuenta como gasto/ingreso (`kind = 'loan'`); el libro de cada préstamo pasa `replay`; los pagos suman `interest_part + principal_part`.
- **`ledger_invalid`:** copia sintética con un objetivo sin transacción de desembolso ⇒ préstamo no creado, transacciones ordinarias, ítem registrado, el resto sigue.
- **Persona:** reutiliza existente por alias; crea provisional con la nota; dos préstamos a la misma persona la comparten.
- **Idempotencia** (segunda importación: 0 creados, 0 modificados) y **`--dry-run`** (BD financiera intacta).
- **Aislamiento entre dos usuarios.**
- **Privacidad:** salida estándar solo con conteos.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(importer):`, `test(importer):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso que el ADR no cubre, `orca orchestration ask`. Si el ADR, el contrato o el dominio te parecen inconsistentes con esto, no los cambies: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
