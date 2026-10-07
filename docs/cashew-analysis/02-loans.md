# Análisis de Préstamos en Cashew (02-loans)

> **Documento:** `docs/cashew-analysis/02-loans.md`  
> **Fecha:** 2026-10-06  
> **Autor:** Antigravity (Gemini)  
> **Alcance:** Fase 0 — Análisis del código fuente de Cashew (`reference/Cashew/budget/`) para confirmar o refutar la hipótesis de `docs/SPEC.md` §2 sobre el origen de los problemas P1, P2 y P3.

---

## 1. Resumen Ejecutivo y Veredicto

El objetivo de esta investigación es verificar la hipótesis planteada en `docs/SPEC.md` §2:
> *"Según su README, un préstamo de largo plazo se modela como una meta (objective) cuyo total se calcula con transacciones de polaridad contraria. Hipótesis: de ahí nacen P1 a P3."*

Tras una inspección exhaustiva del código fuente de Cashew en `reference/Cashew/budget/` (en Drift/Dart), **la hipótesis queda plenamente CONFIRMADA**.

| Problema | Descripción resumida | Veredicto | Causa raíz en el código de Cashew |
|---|---|---|---|
| **P1** | Al marcar un préstamo como pagado, deja de aparecer en transacciones. | **CONFIRMADO** | En préstamos únicos, `settleTransactions` muta la transacción original a `paid: false` (`lib/struct/upcomingTransactionsFunctions.dart:393`), excluyéndola del saldo de cuenta (`lib/database/tables.dart:6773`) y del resumen de préstamos (`lib/database/tables.dart:6938`). En préstamos a largo plazo, el archivado del objetivo oculta el préstamo y sus transacciones (`lib/database/tables.dart:6916`). |
| **P2** | Si se cobra interés como transacción normal, la deuda sigue pendiente salvo que se use "liquidar". | **CONFIRMADO** | No existe vínculo relacional entre transacciones normales y préstamos únicos (`lib/database/tables.dart:309`). En préstamos de objetivo, el total solo acumula transacciones con `objectiveLoanFk` (`lib/database/tables.dart:5637, 5661`), por lo que un gasto normal de interés queda huérfano. Además, Cashew carece de un modelo de movimientos de capital vs. interés. |
| **P3** | Préstamo pagado por otra cuenta acredita la cuenta original y parece inexistente. | **CONFIRMADO** | Al liquidar un préstamo único, Cashew no registra una transacción de cobro en la cuenta receptora; simplemente desactiva `paid: false` en la transacción original (`lib/struct/upcomingTransactionsFunctions.dart:393`). Esto revierte el egreso en la cuenta original (`lib/database/tables.dart:6773`), devolviéndole el dinero a ella y dejando a la cuenta receptora en cero. |

---

## 2. Representación de Préstamos en Cashew

Cashew implementa **dos modelos paralelos y heterogéneos** para gestionar deudas y créditos:

1. **Préstamos de pago único (One-time loans / Credit & Debt):** Modelados como una única fila en la tabla `transactions`.
2. **Préstamos a largo plazo (Long-term loans):** Modelados como una meta en la tabla `objectives` vinculada a múltiples transacciones con polaridad contable invertida mediante la clave foránea `objectiveLoanFk`.

### 2.1 Tablas y Enumeraciones Involucradas

#### A. Enumeraciones (`lib/database/tables.dart`)
* `TransactionSpecialType` (Líneas 44–50):
  ```dart
  enum TransactionSpecialType {
    upcoming,
    subscription,
    repetitive,
    credit, // lent, withdraw, owed (Presté)
    debt,   // borrowed, deposit, owe (Me prestaron)
  }
  ```
* `ObjectiveType` (Líneas 52–55):
  ```dart
  enum ObjectiveType {
    goal,
    loan, // income==true ? lent (loan) : borrowed
  }
  ```

#### B. Tabla `Objectives` (`lib/database/tables.dart:515–539`)
Representa tanto metas de ahorro (`goal`) como préstamos a largo plazo (`loan`):
* `objectivePk`: Identificador UUID (PK).
* `type`: Entero basado en `ObjectiveType` (0 = `goal`, 1 = `loan`).
* `name`: Nombre o título descriptivo (suele ser el nombre de la persona o motivo).
* `amount`: Monto meta. En préstamos a largo plazo se guarda en `0` (Línea 299 de `lib/pages/addObjectivePage.dart`), o `-1` para "difference-only loans" (Línea 296).
* `income`: Booleano que define la dirección del préstamo:
  * `income == true`: **Lent** (Presté / me deben).
  * `income == false`: **Borrowed** (Me prestaron / debo).
* `walletFk`: Cuenta principal vinculada (`Wallets.walletPk`).
* `archived`: Booleano para ocultar el objetivo.

#### C. Columnas clave en la tabla `Transactions` (`lib/database/tables.dart:285–340`)
* `transactionPk`: Identificador UUID.
* `amount`: Importe numérico (positivo para ingreso, negativo para gasto o viceversa según UI).
* `income`: Booleano de polaridad financiera (true = entrada, false = salida).
* `type`: Tipo especial (`TransactionSpecialType`). Los préstamos únicos llevan `credit` o `debt`.
* `paid`: Booleano contable con una semántica distorsionada documentada en el propio código (Líneas 310–313):
  > *"For credit and debts, paid will be true initially, then false when it is received/paid. this is the opposite of what is expected - but that's because we only want it to count for the totals until it is recieved/paid off resulting in a net of 0"*
* `objectiveLoanFk`: Clave foránea que referencia `Objectives.objectivePk` para vincular desembolsos y pagos a un préstamo a largo plazo (Línea 333).

---

## 3. Creación y Ciclo de Vida de los Préstamos

### 3.1 Creación desde la Interfaz
En `lib/pages/creditDebtTransactionsPage.dart:569–656`, el diálogo emergente `AddLoanPopup` bifurca la creación:
* **"Long-term loan"**: Abre `AddObjectivePage(objectiveType: ObjectiveType.loan, ...)` (`lib/pages/creditDebtTransactionsPage.dart:595`).
* **"One-time loan"**: Abre `AddTransactionPage(selectedType: selectedTransactionType)` (`lib/pages/creditDebtTransactionsPage.dart:633`).

### 3.2 Polaridad Contable en Préstamos a Largo Plazo
En `lib/pages/addObjectivePage.dart:507–536`, el selector de tipo invierte la lógica:
* Si el usuario selecciona **"Lent"** (Presté):
  * `objective.income` se establece en `true` (Línea 518).
  * Se inserta la transacción inicial de desembolso (`lib/pages/addObjectivePage.dart:248–266`) con:
    * `income: !selectedIncome` -> **`false`** (un gasto / salida de dinero).
    * `amount: selectedAmount.abs() * (!selectedIncome ? 1 : -1)` -> **negativo**.
    * `name: "initial-record"` (o texto localizado).
    * `objectiveLoanFk: objectiveJustAdded.objectivePk`.
* Si el usuario selecciona **"Borrowed"** (Me prestaron):
  * `objective.income` se establece en `false`.
  * Se inserta la transacción inicial de desembolso con `income: true` (un ingreso / entrada de dinero) y monto positivo.

Cuando el usuario registra una amortización o devolución desde la pantalla del préstamo (`lib/pages/objectivePage.dart:203–211`), el botón flotante (FAB) abre `AddTransactionPage` con:
```dart
AddTransactionPage(
  selectedObjective: widget.objective,
  routesToPopAfterDelete: RoutesToPopAfterDelete.One,
  selectedIncome: widget.objective.income, // Polaridad opuesta al desembolso
)
```
Por tanto, si presté (`objective.income == true`), el desembolso fue gasto (`income: false`) y cada pago registrado es ingreso (`income: true`).

---

## 4. Cálculo de Totales y Progreso

El README de Cashew resume su cálculo (`reference/Cashew/README.md:270–274`):
> *"Long term loans create a goal. However, the goals total is not used. Instead the total of the goal is calculated by totalling the proper polarity of transactions of the opposite type... When a payment is made, it is made in the opposite (positive) polarity (income) and added to the total 'paid back'."*

### 4.1 Consultas en Drift / SQL (`lib/database/tables.dart`)
1. **Capital inicial / Desembolso (`watchTotalAmountObjectiveLoan`, L. 5627–5648):**
   Filtra las transacciones asociadas cuya polaridad coincida con el desembolso (`!objective.income`):
   ```dart
   where(transactions.objectiveLoanFk.equals(objective.objectivePk) &
         transactions.walletFk.equals(wallet.walletPk) &
         transactions.income.equals(!objective.income))
   ```
2. **Total general asociado (`watchTotalTowardsObjective`, L. 5650–5672):**
   Suma todas las transacciones vinculadas a `objectiveLoanFk` sin filtrar por polaridad:
   ```dart
   where(transactions.objectiveLoanFk.equals(objective.objectivePk) &
         transactions.walletFk.equals(wallet.walletPk))
   ```

### 4.2 Lógica de progreso en UI (`lib/pages/objectivesListPage.dart:1003–1058`)
El widget `WatchTotalAndAmountOfObjective` combina ambos flujos:
```dart
double objectiveAmount = (snapshotAmount.data ?? 0); // Suma de desembolsos
double totalAmount = ((snapshot.data ?? 0) - (snapshotAmount.data ?? 0)) * -1; // Suma de amortizaciones
double percentageTowardsGoal = objectiveAmount == 0 ? 0 : totalAmount / objectiveAmount;
```
* **Estado "Saldado":** Se evalúa visualmente en `lib/pages/objectivePage.dart:478–495` cuando `totalAmount >= objectiveAmount`. En ese momento muestra `"all-settled"` o `"paid"`.
* **Diferencia o saldo pendiente:** En "difference-only loans" se utiliza la función auxiliar `getDifferenceOfLoan` (`lib/pages/objectivesListPage.dart:36–41`):
  ```dart
  double getDifferenceOfLoan(Objective objective, double totalAmount, double objectiveAmount) {
    return objective.income ? totalAmount - objectiveAmount : objectiveAmount - totalAmount;
  }
  ```

---

## 5. Análisis Detallado de los Problemas (P1, P2 y P3)

### 5.1 Problema P1: Al marcar un préstamo como pagado, deja de aparecer en transacciones

* **Veredicto:** **CONFIRMADO**.
* **Evidencia en código:**
  1. `lib/struct/upcomingTransactionsFunctions.dart:389–407` (`onSubmit` en `openPayDebtCreditPopup`):
     ```dart
     Transaction transactionNew = transaction.copyWith(
       paid: false, // Desactiva el indicador contable
     );
     popRoute(context, true);
     await database.createOrUpdateTransaction(transactionNew);
     ```
  2. `lib/widgets/selectedTransactionsAppBar.dart:909–918` (`settleTransactions`):
     ```dart
     Future settleTransactions(String transactionPk) async {
       Transaction transaction = await database.getTransactionFromPk(transactionPk);
       if (transaction.type == TransactionSpecialType.credit ||
           transaction.type == TransactionSpecialType.debt) {
         Transaction transactionNew = transaction.copyWith(
           paid: false,
         );
         await database.createOrUpdateTransaction(transactionNew);
       }
     }
     ```
  3. `lib/database/tables.dart:6773` (`watchTotalOfWalletNoConversion`):
     ```dart
     final totalAmt = transactions.amount.sum(filter: transactions.paid.equals(true));
     ```
  4. `lib/database/tables.dart:6938` (`watchTotalWithCountOfCreditDebt`):
     ```dart
     transactions.paid.equals(true) & ...
     ```
* **Mecanismo:**  
  En un préstamo único, al pulsar "Settle" (liquidar), Cashew **no crea ninguna transacción de amortización ni de ingreso**. En su lugar, muta la transacción original cambiando su campo `paid` de `true` a `false`.
  Debido a que las consultas de saldo de billetera (`watchTotalOfWalletNoConversion`) y el cálculo de préstamos pendientes (`watchTotalWithCountOfCreditDebt`) exigen estrictamente `transactions.paid.equals(true)`, la transacción saldada deja de computar en la cuenta y desaparece de las métricas activas.
  En la consulta general de transacciones (`lib/database/tables.dart:5803–5815`), la presencia del filtro `isNotLoan` excluye los préstamos cuando el usuario filtra por ingresos o gastos. Además, en préstamos a largo plazo, para que desaparezcan de la vista activa deben archivarse manualmente (`archived: true`), lo que excluye sus movimientos mediante `objectives.archived.equals(false)` (`lib/database/tables.dart:6916`).

---

### 5.2 Problema P2: El interés registrado como transacción normal no salda la deuda

* **Veredicto:** **CONFIRMADO**.
* **Evidencia en código:**
  1. `lib/database/tables.dart:309, 333` (Esquema de `Transactions`):
     Un préstamo único solo posee las columnas de una transacción común. No tiene hijos, ni lista de movimientos, ni relación con otras transacciones.
  2. `lib/database/tables.dart:5637, 5661` (`watchTotalAmountObjectiveLoan` y `watchTotalTowardsObjective`):
     El cálculo del préstamo a largo plazo filtra exclusivamente por `transactions.objectiveLoanFk.equals(objective.objectivePk)`.
  3. `lib/widgets/selectedTransactionsAppBar.dart:909–918` (`settleTransactions`):
     La deuda persiste abierta salvo que se active manualmente la acción de liquidar.
* **Mecanismo:**  
  Si un prestamista cobra un 5 % de interés (ej. S/ 10 sobre S/ 200 de deuda) y el usuario registra una transacción normal en la categoría "Intereses" (gasto de S/ 10 en su billetera):
  * Dicha transacción **carece de `objectiveLoanFk`**, por lo que las funciones agregadoras del objetivo (`tables.dart:5661`) la ignoran por completo. El objetivo sigue marcando únicamente el principal.
  * Si el usuario intentara asociar la transacción del interés a `objectiveLoanFk`, en Cashew toda transacción vinculada debe ser un movimiento financiero real en una cuenta (`walletFk`). No existe la figura de interés devengado sin desembolso de caja. Y si se vincula como pago, Cashew la sumaría como amortización de capital, reduciendo la deuda en lugar de aumentarla.
  * En un préstamo único, al no haber libro mayor, la transacción de deuda original permanece fija en su importe inicial y `paid = true` hasta que el usuario hace clic forzado en "Settle".

---

### 5.3 Problema P3: Cobro por otra cuenta acredita la cuenta original y oculta el préstamo

* **Veredicto:** **CONFIRMADO**.
* **Evidencia en código:**
  1. `lib/struct/upcomingTransactionsFunctions.dart:389–407` (`onSubmit` en `openPayDebtCreditPopup`):
     El flujo de liquidación total no cuenta con ningún selector de cuenta/billetera receptora (`selectedWalletPk` no existe en `onSubmit`).
  2. `lib/database/tables.dart:6773` (`watchTotalOfWalletNoConversion`):
     ```dart
     final totalAmt = transactions.amount.sum(filter: transactions.paid.equals(true));
     ```
  3. Comentario explícito del autor en `lib/struct/upcomingTransactionsFunctions.dart:398–406`:
     ```dart
     // Make a separate transaction for one time loan collections... something like below?
     // Transaction transactionNew = transaction.copyWith(
     //   //we don't want it to count towards the total - net is zero now
     //   dateCreated: DateTime.now(),
     //   income: !transaction.income,
     //   pairedTransactionFk: Value(transaction.transactionPk),
     // );
     // popRoute(context, true);
     // await database.createOrUpdateTransaction(transactionNew, insert: true);
     ```
* **Mecanismo:**  
  El autor de Cashew reconoció la deficiencia en su propio código y dejó la solución como comentario sin implementar.
  Cuando el usuario prestó S/ 500 desde la Cuenta A ("Yape"):
  * Se registró una transacción con `walletFk = Yape`, `amount = -500`, `paid = true`. El saldo de Yape disminuyó en 500.
  * Cuando el deudor paga en efectivo (Cuenta B) y el usuario marca el préstamo como "Cobrado/Liquidado", la función `onSubmit` solo hace `transaction.copyWith(paid: false)`.
  * Como el saldo de Yape solo suma filas con `paid == true`, al pasar la transacción a `paid: false`, el descuento de 500 deja de aplicarse. **El saldo de Yape sube instantáneamente en 500 (el dinero "regresa" a Yape).**
  * La Cuenta B (Efectivo) **nunca recibe ninguna transacción**.
  * No queda rastro histórico del pago y el préstamo queda invisible.

---

## 6. Implicaciones para Monetae

Para corregir estos fallos respetando la familiaridad visual de Cashew requerida por `docs/SPEC.md`, se define la siguiente división entre UI y Dominio:

### 6.1 Lo que DEBE REPLICARSE en la UI (Apariencia y UX de Cashew)
1. **Panel de Préstamos:**
   * Resumen superior con total neto pendiente: "Te deben" (color verde / `unPaidUpcoming`) vs. "Debes" (color naranja/rojo / `unPaidOverdue`).
   * Selector deslizable tipo pastilla (`SlidingSelectorIncomeExpense`) con opciones: "Todos", "Presté", "Me prestaron".
   * Selector de pestañas para diferenciar préstamos activos de préstamos históricos/saldados.
2. **Tarjeta de Detalle de Préstamo:**
   * Barra de progreso circular o lineal (`AnimatedCircularProgress`) que muestre visualmente el porcentaje amortizado.
   * Fechas clave (inicio y vencimiento opcional).
   * Línea de tiempo o historial ordenado cronológicamente con los movimientos.
3. **Flujo de Registro Rápido:**
   * Diálogo para seleccionar contraparte (Persona) y dirección con íconos claros.

### 6.2 Lo que DEBE SUSTITUIRSE por `loans` + `loan_movements` (Dominio Monetae)
1. **Eliminar el uso de `Objectives` para préstamos:** Las metas (`goals`) solo deben modelar metas de ahorro y gasto.
2. **Eliminar la mutación de la bandera `paid`:**
   * Toda transacción de desembolso y de cobro es inmutable en su estado contable (`paid = true` persistente).
   * "Saldado" (`settled`) es un **estado calculado** (`saldo pendiente == 0`), nunca una bandera mutable ni un botón de liquidación.
3. **Libro Mayor Estricto (`SPEC.md §7`):**
   * Tabla `loans`: vincula `person_id`, `direction` (`lent` | `borrowed`), `currency`, `principal`, `opened_on`, `due_on`.
   * Tabla `loan_movements`: secuencia de eventos tipados:
     * `disbursement`: desembolso inicial.
     * `interest`: devengo o cobro de intereses (asociado a la categoría de sistema "Intereses").
     * `payment`: pago/cobro parcial o total.
     * `adjustment`: ajuste de balance.
     * `write_off`: condonación de saldo incobrable.
4. **Independencia de Cuentas por Movimiento:**
   * Cada movimiento con impacto monetario genera su propia transacción enlazada en la tabla `transactions`, afectando a la cuenta (`account_id`) y moneda en la que realmente se produjo la operación (resolviendo P3).

---

## 7. Heurística Candidata para el Importador (RF-40d)

El importador (`monetae.importers.cashew`) deberá transformar los respaldos de Cashew (exportación SQLite/Drift) a la estructura tipada de Monetae.

### 7.1 Reglas de Mapeo
1. **Detección de Préstamos a Largo Plazo:**
   * Identificar filas en `objectives` con `type == 1` (`ObjectiveType.loan`).
   * Dirección: `income == true` -> `lent`; `income == false` -> `borrowed`.
   * Persona: Buscar o crear en `people` usando `objectives.name`.
   * Moneda: Obtener de la cuenta asociada en `objectives.wallet_fk`.
   * Movimientos:
     * Consultar `transactions` donde `objective_loan_fk == objective.objective_pk`.
     * Desembolsos: Transacciones con `income == !objective.income` -> movimiento `disbursement`.
     * Amortizaciones: Transacciones con `income == objective.income` -> movimiento `payment`.
2. **Detección de Préstamos Únicos:**
   * Identificar transacciones con `type == 3` (`credit` -> `lent`) o `type == 4` (`debt` -> `borrowed`).
   * Crear entidad `loans` correspondiente.
   * Generar movimiento `disbursement` correspondiente a la transacción original.
   * Si la transacción tiene `paid == true`: el préstamo se importa como `open`.
   * Si la transacción tiene `paid == false`: el préstamo fue liquidado en Cashew. Generar movimiento `payment` sintetizado (ver caso ambiguo 1).

### 7.2 Casos Ambiguos para Revisión Manual (Sin datos reales)

De acuerdo con el requisito de aceptación, se definen los siguientes casos ambiguos abstractos:

#### Caso Ambiguo 1: Préstamo único liquidado sin transacción de contrapartida (`paid == false`)
* **Situación:** En Cashew, una transacción con `type = credit` o `debt` tiene `paid = false`. Representa un préstamo que fue saldado, pero en la base de datos solo existe la fila de desembolso original; no existe registro alguno del pago ni de en qué cuenta o fecha se recibió.
* **Problema:** Para que en Monetae el saldo pendiente sea 0 (`settled`), se requiere un movimiento `payment`. Sin embargo, se desconocen la fecha exacta del pago y la cuenta real de cobro.
* **Tratamiento propuesto:** Crear el movimiento `payment` con la fecha de la última modificación (`date_time_modified`) o la misma fecha de creación, asignado a la misma cuenta del desembolso, pero marcar el préstamo con una etiqueta de advertencia (`needs_review: true`, "Pago sintetizado por importación de préstamo liquidado").

#### Caso Ambiguo 2: Sobrepago o intereses implícitos en préstamo a largo plazo (`sum(pagos) > principal`)
* **Situación:** En un objetivo con `type = loan`, la suma de las transacciones de amortización (`income == objective.income`) excede el monto total de desembolsos (`income == !objective.income`). Por ejemplo, desembolso de 100 y pagos acumulados por 105.
* **Problema:** Cashew permitía que `totalAmount` superara el 100 % sin categorizar el excedente. El importador no puede determinar automáticamente si los 5 adicionales corresponden a intereses cobrados/pagados, a un ajuste por diferencia de cambio, o a un error de digitación del usuario.
* **Tratamiento propuesto:** Mapear los primeros 100 como `payment` y el excedente de 5 como un movimiento preliminar de tipo `adjustment` o `interest`, enviando el préstamo a la lista de revisión manual (`flag: overpayment_detected`).

#### Caso Ambiguo 3: Transacciones de intereses huérfanas en categorías globales
* **Situación:** Transacciones con títulos como "Interés préstamo" o con la categoría "Intereses", registradas en fechas coincidentes con el préstamo pero con `objective_loan_fk IS NULL` (registradas como transacciones comunes para resolver P2).
* **Problema:** No hay clave foránea que vincule la transacción con el préstamo. Vincularlas automáticamente por coincidencia de texto puede provocar falsos positivos y alterar saldos de préstamos no relacionados.
* **Tratamiento propuesto:** No vincularlas de forma automática. El reporte de `--dry-run` debe emitir una lista de "Transacciones de intereses sin préstamo asociado" sugiriendo al usuario vincularlas manualmente al préstamo respectivo.

#### Caso Ambiguo 4: Préstamo de tipo "Difference-Only" (`amount == -1`)
* **Situación:** Un objetivo de préstamo con `amount == -1` activado mediante la funcionalidad experimental de Cashew (`longTermLoansDifferenceFeature`). No tiene un monto objetivo definido y su saldo simplemente refleja la diferencia acumulada entre ingresos y egresos.
* **Problema:** En Monetae, un préstamo requiere un monto inicial de capital (`principal`). Un objetivo con monto `-1` no explicita el principal contratado si los desembolsos fueron parciales o múltiples.
* **Tratamiento propuesto:** Deducir el `principal` como la suma de las transacciones de desembolso iniciales y marcar el préstamo como originado desde "Diferencia acumulada" para validación del usuario.

#### Caso Ambiguo 5: Ambigüedad en la entidad de contraparte (`objectives.name` no es una persona)
* **Situación:** El campo `objectives.name` contiene descripciones conceptuales (p. ej. "Adelanto Sueldo", "Tarjeta de Crédito", "Préstamo Vehicular") en lugar del nombre de una persona.
* **Problema:** En Monetae, todo préstamo conecta obligatoriamente con una entidad `people`.
* **Tratamiento propuesto:** Si el nombre no coincide con ninguna persona conocida o alias, crear una entrada en `people` con dicho nombre y agregar una marca `is_provisional: true` para que el usuario pueda fusionarla o renombrarla en la configuración.

---

## 8. Conclusiones y Recomendaciones para la Fase 1

1. **Confirmación de Hipótesis:** La causa estructural de P1, P2 y P3 radica en el intento de Cashew de modelar una relación financiera bilateral mediante una meta unidireccional (`Objectives`) combinada con el truco contable de invertir la polaridad de las transacciones y mutar la bandera `paid: false`.
2. **Arquitectura Monetae:** La especificación de `SPEC.md §7` (`loans` + `loan_movements`) es completamente necesaria y suficiente para solucionar los tres problemas sin comprometer la integridad contable de las cuentas.
3. **Diseño de UI:** En la Fase 5 (Flutter web), la UI debe reutilizar los componentes visuales de Cashew (`AnimatedCircularProgress`, `SlidingSelectorIncomeExpense`), pero conectándolos directamente a los endpoints `/api/v1/loans` del backend de Monetae.
