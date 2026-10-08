# T-301 — Dominio puro de préstamos (libro mayor, reparto interés/capital, exceso)

> **ESTADO: NO LANZADA.** Fase 3, primera tarea. Plan escrito el 2026-10-08; se lanza cuando Adrian apruebe la Fase 3.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (reglas de negocio centrales; cero margen de error en dinero).
> Depende de: nada nuevo (usa `domain/money.py` y `domain/fx.py`). Corre **en paralelo con T-303** (archivos disjuntos).

## Objetivo

Implementar en `monetae.domain` las reglas de los préstamos de SPEC §7 y ADR-003 como funciones y objetos de valor **puros** (sin I/O, sin SQLAlchemy ni Pydantic), con pruebas exhaustivas que reproduzcan **literalmente** los Ejemplos A–E. Esto resuelve en el dominio P1, P2 y P3: el saldo y el estado se calculan; no existe «liquidar»; cada movimiento tiene su propia cuenta/moneda.

## Leer primero

`AGENTS.md` (§6, §13), `docs/SPEC.md` §7 (reglas 1–6 y ejemplos A–E) y §14, `docs/decisions/003-interest-recognition.md`, `docs/ARCHITECTURE.md` §5.5 (todo: signos, `interest_part`/`principal_part`, exceso RF-22, `fx_rate_applied`), `docs/api/openapi.json` (esquemas `Loan*`, `Payment*`, `Interest*`, `MovementCreate` y los ejemplos `x-loan-scenarios`), y el dominio existente (`money.py`, `fx.py`, `errors.py`, `transactions.py`, `transfers.py`).

## Diseño (decidido)

Módulo `monetae/domain/loans.py` (puede dividirse en `loans/` solo si supera ~500 líneas):

1. **Tipos:** `Direction` (`lent`, `borrowed`), `MovementKind` (`disbursement`, `interest`, `payment`, `adjustment`, `write_off`), `Movement` (inmutable): `kind`, `amount: Money` (moneda del préstamo; `> 0` salvo `adjustment`, que es con signo y `≠ 0`), `interest_part` y `principal_part` (`Money | None`; obligatorios y `≥ 0` en `payment` y `write_off`, con suma igual a `amount`; `None` en el resto) y `occurred_at`. El orden de reproducción es `(occurred_at, sequence)`; el llamador pasa `sequence`.
2. **`replay(principal, movements) -> LoanBalance`:** reproduce el libro en orden y **falla en el primer incumplimiento** con una subclase de `LedgerError` (con el índice del movimiento): exactamente un `disbursement` con importe igual a `principal`; `interés_pendiente = Σ interest − Σ interest_part(payment, write_off) ≥ 0` y `capital_pendiente = principal + Σ adjustment − Σ principal_part(payment, write_off) ≥ 0` **tras cada movimiento**; monedas coherentes. Devuelve `LoanBalance` con `principal`, `interest_total`, `adjustment_total`, `payment_total`, `write_off_total`, `interest_pending`, `principal_outstanding`, `outstanding` (= `principal + interest + adjustment − payment − write_off`, comprobado como identidad), `status` (`settled` si `outstanding` es exactamente 0, si no `open`) y `running` (saldo tras cada movimiento). **El desembolso no suma al saldo** (el principal ya está en `principal`).
3. **Reabrir:** un préstamo `settled` vuelve a `open` al añadir un movimiento que sube el saldo (interés o ajuste positivo); no hay estado almacenado.
4. **Reparto de pagos (ADR-003):** `split_payment(amount, state)` → `PaymentSplit(interest_part, principal_part)` con `interest_part = min(amount, interés_pendiente)`; si `amount > outstanding` lanza `OverpaymentError(excess, outstanding)` (nunca un saldo negativo silencioso). `validate_split(amount, interest_part, principal_part, state)` para reparto editado por el usuario (suma exacta, cada parte `≥ 0` y `≤` lo pendiente de su concepto).
5. **Exceso (RF-22, Ejemplo D):** `plan_excess(handling, amount, state)` devuelve el plan de operaciones ordenadas: `adjustment` ⇒ [`Adjustment(+exceso)`, `Payment(amount)` repartido tras el ajuste]; `income_expense` ⇒ [`Payment(outstanding)`, `ExcessCash(exceso)`]. Valores de `handling` inválidos ⇒ error de dominio.
6. **Interés:** `propose_interest(percentage, outstanding)` = `outstanding × percentage / 100` redondeado `ROUND_HALF_UP` a 2 decimales (porcentaje `> 0` y `≤ 1000`, hasta 4 decimales). Es una propuesta; el movimiento `interest` solo sube el saldo.
7. **Condonación y ajuste:** `split_write_off(amount, state)` reparte primero a interés (no mueve dinero, no genera gasto/ingreso); `validate_adjustment(amount, state)`: afecta solo a capital; uno negativo no puede dejar el capital pendiente por debajo de 0.
8. **Moneda:** `loan_amount_from_account(account_money, fx_rate_applied)` y `account_amount_from_loan(loan_money, fx_rate_applied)` con la convención de ARCHITECTURE §5.5 (`fx_rate_applied` = unidades de la moneda de la cuenta por 1 de la del préstamo; `importe_préstamo = |importe_cuenta| / fx_rate_applied`, `ROUND_HALF_UP` una sola vez). Mezclar monedas ⇒ `CurrencyMismatchError`.
9. **Signo de la transacción real** (para T-302): `cash_sign(direction, kind)` ⇒ +1/−1 (desembolso: `lent` −, `borrowed` +; pago: `lent` +, `borrowed` −; el resto no mueve dinero).
10. **Estadística:** `recognized_interest(direction, movements)` devuelve, por cada pago/condonación-no, las `interest_part` de **pagos** con su fecha y lado (`borrowed` ⇒ gasto, `lent` ⇒ ingreso). El capital nunca aparece (SPEC §7.4).
11. Errores nuevos heredan de `DomainError`; mensajes claros y datos útiles (índice, importes).

## Archivos permitidos (todos nuevos salvo `domain/__init__.py`)

```
services/api/src/monetae/domain/loans.py            # (o domain/loans/ si crece)
services/api/src/monetae/domain/__init__.py         # SOLO re-exportar API pública
services/api/tests/domain/test_loans_balance.py
services/api/tests/domain/test_loans_payments.py
services/api/tests/domain/test_loans_replay.py
services/api/tests/domain/test_loans_examples.py    # Ejemplos A–E literales + P1/P2/P3
services/api/tests/domain/test_loans_fx.py
```

No tocar `pyproject.toml`/`uv.lock` (sin dependencias nuevas), `db/`, `api/`, `services/`, `alembic/`, `domain/money.py`, `fx.py`, `transactions.py`, `transfers.py`, ni nada de suscripciones (T-303). `monetae.domain` no importa de `api`, `db`, `importers`, `reports`, ni de Pydantic/SQLAlchemy (la prueba de arquitectura debe seguir pasando).

## Pruebas obligatorias

- **Ejemplos A–E de SPEC §7 como pruebas literales**, con los números del documento: A (me prestaron 200, interés 5 % = 10, saldo 210, pago 100 ⇒ reparto 10/90, saldo 110, pago 110 ⇒ reparto 0/110, saldo 0 `settled`; interés reconocido total 10, en la fecha del primer pago); B (presté 500, cobros 300 + 200 en cuentas distintas ⇒ `settled`); C (USD 100 cobrado como S/ 380 a `3.800000` ⇒ préstamo −100, ida y vuelta de conversión); D (saldo 50, pago 60 ⇒ `OverpaymentError(excess=10)`; los dos caminos de `plan_excess` terminan en saldo 0 `settled`); E (1000 con 50, 120, 30, 800 ⇒ saldos 950, 830, 800, 0 y `settled` solo al final).
- **P1/P2/P3 como propiedades de dominio:** un préstamo saldado conserva todo su libro; el interés sube el saldo sin botón alguno y el estado cambia solo por cálculo; movimientos con monedas/cuentas distintas se componen correctamente.
- Invariantes con muestreo determinista (sin librerías nuevas, `random.Random(semilla)` con ≥ 2 000 libros válidos generados): la identidad `outstanding` siempre se cumple; nunca hay pendiente negativo; `replay` incremental == recálculo desde cero.
- `replay` rechaza: sin/duplicado desembolso, desembolso ≠ principal, pago que excede un concepto, ajuste que deja capital negativo, orden retroactivo que vuelve inválido un reparto posterior (movimiento editado/borrado), mezcla de monedas.
- Redondeo (`0.005`, interés propuesto con porcentajes de 4 decimales), reabrir un saldado, condonación (no genera interés reconocido), ajuste positivo/negativo.
- Cobertura de líneas de `domain/loans.py` ≥ 95 % (`uv run --with coverage coverage run -m pytest`; no se añade a `pyproject.toml`).

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cd services/api
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                    # sin Docker ni BD; las pruebas existentes siguen verdes
grep -rnE "^\s*(import|from) (fastapi|pydantic|sqlalchemy|alembic|monetae\.(api|db|importers|reports|services))" src/monetae/domain || echo "dominio limpio"
git diff --stat master-dev...HEAD   # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(domain):`, `test(domain):`). Sin `Any` ni `# type: ignore` sin razón escrita. Actualiza tu rama con `master-dev` antes de reportar. Si el contrato, ARCHITECTURE o SPEC te parecen inconsistentes con esto, **no los cambies**: pregunta con `orca orchestration ask` o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
