# Importación de préstamos de Cashew

T-402 aplica el [ADR-008 aceptado](../decisions/008-cashew-loan-import.md):
J1-A, J2-C y J3-A. El respaldo se procesa con el lector de T-401, siempre
sobre una copia y en solo lectura. Las pruebas usan exclusivamente datos
sintéticos y PostgreSQL real.

## Libro y efectivo

Los objetivos `type=1` producen préstamos `lent` cuando `income=true`, y
`borrowed` en caso contrario. La moneda pertenece a la cuenta del objetivo;
el principal es el primer desembolso, ordenando por `(date_created, pk)`.
El importe nominal del objetivo, su archivado y la modalidad «solo diferencia»
no cambian estas reglas. `opened_on` usa la fecha del desembolso en America/Lima.

Las transacciones con `objective_loan_fk` pertenecen a ese objetivo, incluso
cuando también tienen un tipo especial. Sin esa FK, `type=3` produce un préstamo
`lent` de pago único y `type=4` uno `borrowed`. Las identidades son
`cashew:sqlite:objective:<pk>` y `cashew:sqlite:tx:<pk>` respectivamente.

Cada desembolso y pago genera su transacción `kind=loan`, con el signo original,
la cuenta y moneda reales, las etiquetas de origen, `source=import` y la identidad
`cashew:sqlite:<pk>`. No recibe categoría ordinaria. Cada pago reparte primero
interés y después capital mediante `split_payment`. No se adivinan cargos de
interés: la fixture importada tiene cero interés devengado.

Un desembolso adicional genera un ajuste positivo sin dinero; su transacción
real conserva `kind=loan`, sin enlace a un movimiento. Se registra
`extra_disbursement`. Dentro de un objetivo, `paid=0` no genera efectivo y produce
`unpaid_loan_transaction`.

Un pago superior al saldo se divide con `plan_excess('income_expense', ...)`:
la parte aplicada usa el saldo exacto; el resto es ingreso/gasto ordinario sin
categoría, con identidad `cashew:sqlite:<pk>:excess`. En otra moneda se convierte
la parte aplicada y se obtiene el exceso por diferencia en la moneda de cuenta,
para conservar exactamente el efectivo original. Se registra
`overpayment_detected`. Si un préstamo ya saldado recibe otro cobro, todo ese
cobro es exceso ordinario; no se introduce un pago de cero.

El préstamo único con `paid=0` recibe un desembolso y un pago sintetizado por el
mismo principal y cuenta. La fecha del pago usa `date_time_modified`, o la del
desembolso cuando falta; la identidad es
`cashew:sqlite:<pk>:synthesized_payment`. Se marca `synthesized_payment`. El efecto
neto en cuenta es cero y el préstamo permanece visible como `settled`.

Antes de insertar un préstamo se valida todo el libro con `replay`; saldo y
estado nunca se guardan en columnas. Un libro inválido no genera préstamo:
su efectivo pagado se importa como transacciones ordinarias y se registra
`ledger_invalid`. Importes cero, que redondeen a cero o fuera de los límites del
dominio se omiten con revisión; cualquier diferencia queda visible en el cuadre.
Las otras cuentas y préstamos siguen procesándose.

## Personas e intereses sueltos

La contraparte se busca por nombre o alias usando `normalize_title`: ignora
mayúsculas, acentos y espacios redundantes. Si falta, se crea una persona con
identidad `cashew:sqlite:person:<nombre normalizado>`, nota «Creada por la
importación de Cashew; revisar» y revisión `provisional_person`. Dos préstamos
con la misma contraparte reutilizan esa persona.

La coordinación aprobó estas salvaguardas durante T-402:

- Varias personas que coincidan: `ambiguous_loan` con `objective_pk` o
  `transaction_pk` y `candidate_person_ids`; préstamo sin crear y efectivo
  ordinario. Tampoco se recrea una persona importada borrada lógicamente.
- Desembolso en una moneda distinta de la cuenta del objetivo: `ledger_invalid`
  con `reason=disbursement_currency_mismatch`; efectivo ordinario. Las tasas
  globales de T-401 no se usan para deducir capital en otra moneda.
- Interés huérfano: categoría o título normalizados contienen `interes` y no hay
  FK de préstamo. Se registra `orphan_interest` sin cambiar ni enlazar la
  transacción. `candidates` contiene los UUID de préstamos cuya contraparte
  normalizada (nombre o alias completo) aparece en el título o nota normalizados.
  Se usa coincidencia textual del nombre completo, sin ventana de fechas.
  Si no coincide ninguna, se conserva `candidates=[]`. Son pistas para revisión.

## Segunda pasada de tasas

Un cobro en otra moneda sin tasa explícita se conserva como ingreso/gasto
ordinario y se registra `fx_rate_required` con PK de transacción, moneda e
identidad del préstamo. El préstamo permanece abierto.

```bash
# Archivo JSON local: {"<transaction_pk>": "3.800000"}
uv run python -m monetae.cli import-cashew \
  --file /tmp/cashew-copy.sqlite --user-email import@example.test \
  --fx-rate USD=3.800000 --loan-fx-rates /tmp/loan-rates.json
```

La tasa representa unidades de la moneda de cuenta por unidad del préstamo:
380 PEN / 3.800000 = 100 USD, con `ROUND_HALF_UP`. También puede proporcionarse
en la primera importación. La tasa global para valorar una transacción en la
moneda base es independiente de esta tasa histórica del préstamo.

La segunda pasada exige una revisión J3 abierta y efectivo original intacto.
Comprueba el libro persistido contra la fuente, conserva los repartos anteriores
y valida `replay` sobre todos los movimientos antes de escribir. Convierte la
transacción ordinaria existente en `loan`, enlaza el nuevo movimiento y guarda
`fx_rate_applied`. Si hay sobrepago, conserva la identidad principal para el pago
y crea la transacción del exceso. Cierra las revisiones J3 abiertas de esa
identidad con `resolved_at`; en `dry-run` estas resoluciones también se revierten.

Por decisión explícita de la coordinación, el nuevo movimiento usa
`MAX(sequence)+1`, incluyendo movimientos borrados. Ningún movimiento anterior
se renumera ni modifica. `replay` ordena por `(occurred_at, sequence)`; un pago
nuevo en la misma fecha y hora queda después de los movimientos existentes.
Las secuencias nuevas no tienen por qué seguir el orden cronológico.

Un libro editado, efectivo cambiado, una identidad preexistente sin revisión J3,
o un pago nuevo que invalide un reparto posterior produce
`ambiguous_loan {reason: second_pass_conflict}` y conserva todo. Si el nuevo pago
queda íntegramente como exceso porque ya no hay deuda aplicable, también requiere
revisión manual y no convierte el efectivo. Volver a proporcionar una tasa ya
resuelta no modifica el historial. Los préstamos existentes se omiten enteros
cuando no hay tasas pendientes; incluye identidades borradas lógicamente.

## Reporte y revisión

`steps.loans` ofrece `created`, `already_imported`, `invalid`, `resolved_fx`,
`modified`, `deferred=0`, `processed_transactions`, movimientos por tipo y conteos
por tipo de revisión. Las revisiones privadas se guardan en PostgreSQL y en el
reporte solicitado; la salida estándar contiene solo conteos/códigos/saldos.
No imprime títulos, notas ni nombres. Las reimportaciones pueden añadir auditoría,
pero no duplican entidades financieras.

Resultados de la fixture con las decisiones aceptadas: A paga 100+100 y deja
un gasto ordinario de 10; B y E quedan saldados con cada pago en su propia cuenta;
C queda abierto hasta confirmar 3.800000; D aplica 50 y deja ingreso de 10;
F saldado tiene pago sintetizado, F abierto conserva deuda de 80. El interés
suelto de A sigue siendo gasto ordinario. Las expectativas antiguas condicionadas
de `expected.json` se interpretan según el ADR-008, que documenta las decisiones
posteriormente aceptadas.

Con T-401 y T-402 no queda dinero de préstamos diferido y `unexplained=0.00`
en las cuatro cuentas del fixture. Hasta integrar T-403, las dos filas recurrentes
siguen diferidas por su propio paso. La UI de resolución manual de los demás
ítems corresponde a las fases posteriores; esta tarea solo resuelve tasas J3.
