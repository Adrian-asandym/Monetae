# ADR-008 — Cómo se convierten los préstamos de Cashew al importar

- **Estado:** PROPUESTO — **pendiente de Adrian** (decisiones J1, J2 y J3; las demás reglas son por defecto y puede vetarlas)
- **Fecha:** 2026-10-08 · **Autor:** Claude
- **Relacionado:** SPEC RF-40a…j (§11), RF-22, §7; ADR-003; `docs/cashew-analysis/02-loans.md` §7; fixture `services/api/tests/fixtures/cashew_v48/` (casos A–F); tarea `T-402`

## Contexto

Cashew no tiene un libro de préstamos. Los modela de dos maneras (análisis 02-loans §2):

1. **Largo plazo:** una fila en `objectives` con `type = 1` y transacciones enlazadas con `objective_loan_fk`. El desembolso tiene la polaridad contraria a `objectives.income`, y cada pago, la misma (`income = true` ⇒ prestado por mí/`lent`).
2. **Pago único:** una sola transacción con `type = 3` (`credit`, presté) o `type = 4` (`debt`, me prestaron). «Liquidar» solo cambia `paid` a `false`; no crea ningún cobro (origen de P1 y P3).

La SPEC (RF-40d) exige una heurística documentada en un ADR y que **los casos ambiguos se listen para revisión manual, no se adivinen**. Además RF-40c exige que **los saldos de cada cuenta coincidan con los de Cashew**, y en Cashew el saldo de una cuenta es `SUM(amount) WHERE paid = 1`.

## Principios (no requieren decisión)

- **Todo el dinero que Cashew cuenta se importa.** Así los saldos cuadran. Lo que no encaje en un libro válido se importa como transacción ordinaria y se lista en `import_review_items`; nada se descarta ni se inventa en silencio.
- **El capital no es gasto ni ingreso** (SPEC §7.4): las transacciones de préstamo se importan con `kind = 'loan'`, enlazadas a su movimiento.
- **El libro resultante debe pasar `domain.loans.replay`.** Si no lo pasa, el préstamo **no se crea**: todas sus transacciones se importan como ordinarias y se registra `ledger_invalid`.
- **Inserción solamente:** reimportar el mismo archivo no cambia nada de lo ya importado ni de lo que el usuario editó después.
- **Nada se enlaza por parecido de texto.**

## Reglas por defecto (puedes vetarlas)

| # | Situación en Cashew | Tratamiento |
|---|---|---|
| R1 | Objetivo `type = 1` | Un `loan`. Dirección: `income = true` ⇒ `lent`, `false` ⇒ `borrowed`. Moneda: la de la cuenta (`wallet_fk`) del objetivo. `opened_on`: fecha del primer desembolso. Archivado en Cashew (`archived = 1`) ⇒ se importa igual; Monetae no oculta préstamos. |
| R2 | Transacciones con la polaridad del desembolso | La primera (por fecha, luego `pk`) es el `disbursement`; **el principal es su importe**. `objectives.amount` (0 o −1) se ignora. |
| R3 | Desembolsos posteriores en el mismo objetivo (incluye «solo diferencia», `amount = −1`) | `adjustment` positivo en la fecha de cada uno, sin dinero. El efectivo real se importa como transacción `kind = 'loan'` **sin movimiento enlazado** (así no cuenta como gasto y la cuenta cuadra). Marca `extra_disbursement`. |
| R4 | Transacciones con la polaridad contraria | `payment`, reparto primero a interés y luego a capital (ADR-003), ordenados por fecha. Cada pago conserva **su propia cuenta** (P3). |
| R5 | Nombre de la contraparte (`objectives.name`, o `name` de la transacción en pago único) | Se busca una persona por nombre o alias sin distinguir mayúsculas ni acentos; si no existe se crea con la nota «Creada por la importación de Cashew; revisar» y se marca `provisional_person`. |
| R6 | Transacciones de interés sueltas (categoría o título con «interés», sin `objective_loan_fk`) | **No se enlazan.** Se importan como gasto/ingreso normal y se listan como `orphan_interest` con los préstamos candidatos (misma persona o fechas cercanas) como sugerencia. |
| R7 | Transacción de préstamo con `paid = 0` dentro de un objetivo | Cashew no la cuenta en el saldo. No se importa como dinero; se lista como `unpaid_loan_transaction`. |
| R8 | Pago único con `paid = 1` | Préstamo abierto con su desembolso; sin más movimientos. |

## Decisiones que necesito de Adrian

### J1 — Préstamo de pago único ya «liquidado» en Cashew (`paid = 0`, fixture F_settled)
Cashew conserva el desembolso pero **no guarda cuándo ni por qué cuenta se cobró**. Además su saldo de cuenta ya excluye esa fila (neto 0).

- **A (recomendada): importar el préstamo con su desembolso y un pago sintetizado en la misma cuenta**, con la fecha de `date_time_modified` (si no hay, la del desembolso), y marcarlo `synthesized_payment` para revisión. *Razón:* el préstamo queda `settled` y visible (P1), y el saldo de la cuenta cuadra con Cashew; corriges la fecha y la cuenta reales cuando quieras (P3). *Contra:* la fecha y la cuenta del cobro son una suposición, aunque está marcada.
- B: importar solo el desembolso; el préstamo queda **abierto** hasta que registres el cobro. *Razón:* no se inventa nada. *Contra:* el saldo de esa cuenta queda por debajo del de Cashew en ese importe, y el préstamo aparece como deuda viva cuando ya estaba cobrado.
- C: no importarlo y solo listarlo. *Contra:* se pierde el historial.

### J2 — Pagos que superan el saldo (casos A y D de la fixture)
El dominio no admite un pago mayor que el saldo (RF-22). En Cashew sí se podía.

- **C (recomendada): partir el pago** en «pago por el saldo exacto» + «ingreso o gasto ordinario por el exceso» (la opción `income_expense` de RF-22). *Razón:* conserva el **principal real** (50 siguen siendo 50), el préstamo termina en 0/`settled`, el efectivo cuadra y no se declara como interés algo que quizá no lo era. El exceso se importa como transacción con id `cashew:sqlite:<pk>:excess` y se marca `overpayment_detected`.
- A: `adjustment` positivo por el exceso y pago completo (la opción `adjustment` de RF-22). *Contra:* el principal pasa de 50 a 60: se altera el dato «cuánto presté».
- B: `interest` por el exceso, que el pago cancela. *Contra:* reconoce como gasto un interés que Cashew no etiquetó y puede duplicar el «interés suelto» (R6, caso A).

### J3 — Pagos en una moneda distinta a la del préstamo (caso C: préstamo en USD, cobro en soles)
Cashew **no guarda tasa por transacción**; solo tiene un tipo de cambio global y actual en `app_settings`.

- **A (recomendada): no adivinar la tasa.** El cobro se importa como transacción ordinaria en su cuenta (el saldo cuadra), el préstamo queda abierto con `fx_rate_required` y puedes dar la tasa en una **segunda pasada**: `--loan-fx-rates archivo.json` (`{"<transaction_pk>": "3.800000"}`), que convierte esa transacción en un pago real. *Razón:* respeta ADR-004 (la tasa manual manda) y «no se revalúa el pasado».
- B: usar la tasa actual de `app_settings`. *Contra:* aplica una tasa de hoy a un pago antiguo; contradice RF-40d.
- C: mandar el préstamo entero a revisión sin crearlo. *Contra:* pierde su estructura hasta resolverlo.

## Consecuencias si se aceptan J1-A, J2-C y J3-A

- El importador produce, para la fixture: **A** = préstamo `borrowed` 200, pagos 100 + 100 y un gasto ordinario de 10 por el exceso (más el interés suelto de 10, listado); **B** y **E** = `settled`, con saldos 500→200→0 y 1000→950→830→800→0; **C** = préstamo USD abierto con `fx_rate_required` (y `settled` tras la segunda pasada con 3,800000); **D** = pago de 50 y un ingreso ordinario de 10; **F_settled** = préstamo `lent` 150 `settled` con pago sintetizado; **F_open** = préstamo `borrowed` 80 abierto.
- Los saldos de las 4 cuentas coinciden con `expected.json` (2209,60 · −90,00 · 660,00 · −12,00).
- `import_review_items.kind` incluye: `ambiguous_loan`, `orphan_interest`, `synthesized_payment`, `overpayment_detected`, `fx_rate_required`, `extra_disbursement`, `provisional_person`, `unpaid_loan_transaction`, `ledger_invalid`.
- Resolver los ítems de revisión desde la UI (enlazar un interés suelto, cambiar la cuenta de un pago sintetizado…) queda para las Fases 5 y 6; en la Fase 4 solo se listan, y la única resolución disponible es la segunda pasada de J3.

## Decisión de Adrian

- **2026-10-08 (noche): «todo A»** como respuesta a las recomendaciones.
  - **J1 = A** (pago sintetizado en la misma cuenta, marcado para revisión) — **decidido**.
  - **J3 = A** (no adivinar la tasa; segunda pasada con `--loan-fx-rates`) — **decidido**.
  - **J2 — pendiente de aclarar:** en J2 la opción **recomendada es la C** (partir el pago en «saldo exacto» + ingreso/gasto ordinario por el exceso); la **A** es otra (ajuste de capital, que cambia el principal). «Todo A» podría significar «todo lo recomendado» o la letra A de J2. **No se lanza T-402 hasta que Adrian confirme la letra de J2.**
  - Reglas R1–R8: sin vetos.
- Permiso para un `--dry-run` sobre una copia del respaldo real (solo conteos y saldos): **sin responder**; no bloquea T-401. Hasta entonces solo se usan los fixtures sintéticos.

**Estado: PROPUESTO** (pasa a ACEPTADO cuando Adrian confirme J2).
