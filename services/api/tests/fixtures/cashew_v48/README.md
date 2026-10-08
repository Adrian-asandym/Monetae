# Respaldo Cashew sintético v48 / v46

**Todo es ficticio.** Personas, cuentas, UUID, textos, fechas y cantidades se
inventaron para estos tests. No se consultó `reference/backups/` ni se usaron
respaldos reales. Este fixture es un insumo del futuro importador, no un importador.

Desde la raíz del repositorio, con Python 3.9 o posterior y solo su biblioteca estándar:

```bash
python3 -I scripts/generate_cashew_fixture.py
python3 -I scripts/verify_cashew_fixture.py
```

El generador recrea `synthetic_v48.sqlite`, `synthetic_v46_no_tags.sqlite`,
`synthetic_v48.csv` y `expected.json` en esta carpeta. Se debe ejecutar sobre una
copia de trabajo sin modificaciones experimentales que se desee conservar.
`expected.json` usa importes decimales como cadenas y expectativas literales;
los saldos esperados no se calculan a partir de las filas generadas.
El verificador abre ambas bases con `mode=ro`, ejecuta consultas propias sin
importar el generador y compara el esquema contra el DDL del documento de análisis.
Imprime `OK`/`FAIL`, nombres de tablas y columnas, y termina con código 1 si falla.
Sus comprobaciones también son tests ejecutables con pytest.

## Determinismo y representación

Namespace fijo UUID v5: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`.
Los identificadores se obtienen de etiquetas como `A_disbursement`, `loan_A`,
`soles`, `tag_0`; `expected.json.row_map` contiene los UUID de cada transacción.
Las fechas comienzan en **2026-01-01 12:00:00 UTC**, avanzan días completos y se
persisten en **segundos Unix**, no milisegundos (análisis 03 §3.1).
No intervienen reloj, aleatoriedad ni timestamps de ejecución.
Las inserciones tienen orden fijo y las transferencias usan FK diferidas hasta
el commit. Los montos se insertan como cadenas decimales; la afinidad `REAL`
del esquema Cashew los almacena como REAL. Los cálculos y expectativas Python
usan `Decimal`, sin aritmética de dinero con `float`.

Se copian literalmente las 12 sentencias `CREATE TABLE` de
[03-backup-format.md §3.3](../../../../../docs/cashew-analysis/03-backup-format.md).
El DDL manda sobre los conteos descriptivos: wallets tiene 13 columnas y
categories 12. La base v46 conserva todas las filas de las diez tablas comunes,
pero omite `tags`, `transaction_to_tag_links`, `wallets.archived`,
`wallets.emoji_icon_name`, `categories.archived`, `associated_titles.archived` y
`scanner_templates.default_title`, según 03 §2.3.
Los defaults temporales literales del DDL se conservan, pero todas las filas
proporcionan fechas fijas explícitas. `app_settings.settings_pk=1` es entero,
como exige el esquema original; no se convierte esa PK a UUID.

## Mapa caso → filas

Todos los títulos de transacción son `Ejemplo <etiqueta>`.
S = Cuenta Soles (PEN), U = Cuenta Dolares (USD), E = Efectivo (PEN).
`Cuenta Archivada Ejemplo` (PEN) está archivada en v48.
Las personas son `Persona Ejemplo A`…`Persona Ejemplo E`.

| Caso | Etiquetas y montos firmados | Representación / resultado esperado |
|---|---|---|
| A | `A_disbursement` +200 E; `A_interest` −10 E; `A_payment_1` −100 S; `A_payment_2` −110 E | Objetivo `loan_A`, `type=1`, `income=0`; interés en Intereses sin FK de préstamo. Tras confirmar el interés: Monetae 210→110→0, settled. |
| B | `B_disbursement` −500 S; `B_payment_1` +300 E; `B_payment_2` +200 S | Objetivo `loan_B`, `income=1`; saldo 500→200→0, settled; pagos en cuentas diferentes. |
| C | `C_disbursement` −100 U; `C_payment_1` +380 S | Objetivo `loan_C`; Monetae USD 100→0 tras confirmar FX. |
| D | `D_disbursement` −50 U; `D_payment_1` +60 U | Objetivo `loan_D`; sobrepago USD 10, requiere aviso/decisión. |
| E | `E_disbursement` −1000 S; `E_payment_1..4` +50,+120,+30,+800 S | Objetivo `loan_E`; saldos 950,830,800,0; settled solo al final. |
| F | `F_settled` −150 S, type=3 credit, paid=0; `F_open` +80 E, type=4 debt, paid=1 | Préstamos únicos sin objetivo; el primero carece de contraparte y no sale en CSV. |
| G | `G_subscription` −44.90 S; `G_repetitive` +2500 S | type=1 subscription y type=2 repetitive; reoccurrence=3 monthly, period_length=1. |
| H | `H_out` −200 S; `H_in` +200 E | FK `paired_transaction_fk` recíprocas, suma neta 0 PEN. |
| I | `I_food` −25.50 S | Categoría Alimentación/subcategoría Restaurantes; presupuesto mensual 2000 con límite 800 para Alimentación. |
| J | `G_repetitive` → tag_0 y tag_1; `G_subscription` → tag_2 | Tres tags, tag_2 archivada conserva su vínculo; `I_food` sin etiquetas. |
| K | `K_future` −35 S, paid=0; `K_archived_wallet` −12 cuenta archivada | Próxima transacción excluida del CSV; una fila delete_logs para UUID ficticio ausente. |

Todas las transacciones tienen `paid=1` excepto `F_settled` y `K_future`.
Los cinco objetivos loan guardan `amount=0`, como Cashew; el capital se obtiene
de sus desembolsos, no de `objectives.amount`.

## Saldos y diferencias entre Cashew y Monetae

Regla Cashew: **SUM(transactions.amount) WHERE paid=1 por wallet**,
`lib/database/tables.dart:6773`, `watchTotalOfWalletNoConversion`, citada en
[02-loans.md §5.1](../../../../../docs/cashew-analysis/02-loans.md).
El monto ya viene firmado (01-data-model.md §b); `income` no se aplica otra vez.
No se excluyen cuentas archivadas de esta comprobación de saldos.

| Wallet | Moneda | Saldo Cashew esperado |
|---|---|---:|
| Cuenta Soles | PEN | 2209.60 |
| Cuenta Dolares | USD | −90.00 |
| Efectivo | PEN | 660.00 |
| Cuenta Archivada Ejemplo | PEN | −12.00 |

`expected.json.loan_cases` separa resultados Monetae y Cashew.
Los resultados Cashew **nominales** capital/pagos son A=200/210, B=500/500,
C=100/380, D=50/60 y E=1000/1000; el criterio nominal pagos≥capital muestra
settled. Son cantidades de filas, no saldos financieros multimoneda válidos.
En particular, las consultas citadas en 02-loans §4.1 filtran por wallet:
para C, USD tiene capital 100 y pagos 0; PEN tiene capital 0 y pagos 380.
No se presenta la agregación nominal −280 como deuda económica válida.
La visualización real depende de la cuenta seleccionada y de la conversión
global de Cashew; el fixture no finge disponer de una tasa histórica guardada.

Casos ambiguos que deben aparecer en la revisión manual del futuro importador:

- **A:** interés normal huérfano de 10 sin `objective_loan_fk`, y pagos del
  objetivo 210 sobre capital 200 (ambiguos 2/3 de 02-loans). El resultado Monetae
  settled presupone confirmar su asociación como cargo al préstamo. No crear
  otro débito por ese cargo: el SQLite Cashew ya tiene una salida adicional de
  10, además de pagos por 210. Esto difiere del flujo de caja del ejemplo A de
  SPEC; mantener los saldos Cashew y mostrar la posible duplicación para revisión.
- **C:** no hay columna de tasa por transacción. El pacto ficticio se documenta
  solamente en expected.json: `fx_rate_applied=3.800000` **PEN por USD**,
  según [ARCHITECTURE.md §5.5](../../../../../docs/ARCHITECTURE.md).
  `amount_in_loan_currency = 380 / 3.800000 = 100.00 USD`, ROUND_HALF_UP.
  No deducir automáticamente esa tasa ni añadir columnas al SQLite.
- **D:** el saldo bruto diagnóstico es −10 y el único estado permitido por
  SPEC §7 si se evalúa ese bruto es `open`, nunca un estado inventado `overpaid`.
  RF-22 exige confirmación atómica: aplicar 50 al préstamo y 10 como ingreso,
  o ajuste de capital +10 y pago aplicado 60, ambos producen 0/settled.
  En ARCHITECTURE §5.5 esas opciones se llaman `excess_handling=income_expense`
  y `excess_handling=adjustment`, respectivamente; el usuario las elige durante
  la revisión. Todas las transacciones de dinero se importan, incluida la fila
  completa de +60 USD, para conservar los saldos Cashew (RF-40c). Solo queda
  pendiente cómo se representa el exceso en el libro del préstamo (RF-40d).
  Estas son expectativas condicionadas; el fixture no elige una opción ni
  autoriza persistir un saldo negativo silencioso.
- **F_settled:** `paid=0` conserva el desembolso pero no fecha/cuenta de cobro;
  no sintetizar el pago sin confirmación (ambiguo 1 de 02-loans).

## CSV de rescate

Cabecera exacta (03 §2.4), 17 columnas:

```text
account,amount,amount unpaid,currency,title,note,date,income,type,category name,subcategory name,color,icon,emoji,budget,objective,extra
```

El filtro `paid=1` procede de `lib/widgets/exportCSV.dart:88`; salen **23 filas**
y se excluyen exactamente **2**, `F_settled` y `K_future`.
Se exportan nombres textuales y fechas UTC; los UUID, tags, reglas,
presupuestos y vínculos de transferencias no son recuperables desde el CSV.
Los tipos usan `TransactionSpecialType.<nombre>` o `null` como en
`exportCSV.dart:125`. `budget` identifica `I_food` y `objective` los objetivos loan.
`amount unpaid` y `extra` quedan vacías: 03 §2.4 declara que su semántica v48
no está verificada en el código disponible. No se inventó un cálculo ni una
periodicidad localizada para esas columnas. Es una limitación explícita de
este equivalente de rescate, no una reproducción verificada de esos valores.
`expected.json.csv.import_note` exige ignorar ambas columnas y nunca usarlas
para calcular saldos; la representación fue confirmada por el coordinador.
El esquema Cashew tampoco tiene archivo reversible de suscripción; G aporta
las recurrencias de origen y no inventa campos ausentes para SPEC §8.

## Validación de aceptación

```bash
python3 -I scripts/generate_cashew_fixture.py
sha256sum services/api/tests/fixtures/cashew_v48/synthetic_v48.sqlite services/api/tests/fixtures/cashew_v48/synthetic_v48.csv services/api/tests/fixtures/cashew_v48/synthetic_v46_no_tags.sqlite
python3 -I scripts/generate_cashew_fixture.py
sha256sum services/api/tests/fixtures/cashew_v48/synthetic_v48.sqlite services/api/tests/fixtures/cashew_v48/synthetic_v48.csv services/api/tests/fixtures/cashew_v48/synthetic_v46_no_tags.sqlite
python3 -I scripts/verify_cashew_fixture.py
uv run --no-project --python 3.12 python -I scripts/verify_cashew_fixture.py
uv tool run ruff check scripts/generate_cashew_fixture.py scripts/verify_cashew_fixture.py
uv tool run ruff format --check scripts/generate_cashew_fixture.py scripts/verify_cashew_fixture.py
uv tool run mypy --strict --python-version 3.12 scripts/generate_cashew_fixture.py scripts/verify_cashew_fixture.py
PYTHONDONTWRITEBYTECODE=1 uv tool run pytest -q -p no:cacheprovider scripts/verify_cashew_fixture.py
git diff --stat master-dev...HEAD
```

Las herramientas de calidad se ejecutan fuera de las dependencias del proyecto;
no se agregaron dependencias ni configuración. La tarea admite Python 3.9
para ejecución; mypy actual verifica el objetivo 3.12 (ya no admite target 3.9).
Los binarios se generan con SQLite 3.34.1 y Python 3.9.25; dos ejecuciones dieron:

```text
8b8ca665965e8d5c892579f34a22617ccb7f992a9f4b0ea67b9f61b791c2220e  synthetic_v48.sqlite
654a8cc5748eecb68c3c5abc6737a18d19d828a3ba4c4cfbe15f13ec1713c223  synthetic_v48.csv
ec9205865900616b26b37020a75591c21a23dcad06380444916383ec9c512a42  synthetic_v46_no_tags.sqlite
```

SQLite guarda también la versión de su biblioteca en la cabecera binaria:
los hashes deben compararse entre ejecuciones del mismo entorno, no entre
versiones diferentes de SQLite. El contenido y el verificador son compatibles
con Python 3.12.

Salida del verificador (incluye PRAGMA user_version 48/46 y listado validado de tablas/columnas):

```text
OK test_csv_exact_projection
OK test_loan_cases
OK v48 wallets (4 filas): wallet_pk,name,colour,icon_name,date_created,date_time_modified,order,currency,currency_format,decimals,home_page_widget_display,archived,emoji_icon_name
OK v48 categories (7 filas): category_pk,name,colour,icon_name,emoji_icon_name,date_created,date_time_modified,order,income,method_added,main_category_pk,archived
OK v48 objectives (5 filas): objective_pk,type,name,amount,order,colour,date_created,end_date,date_time_modified,icon_name,emoji_icon_name,income,pinned,archived,wallet_fk
OK v48 transactions (25 filas): transaction_pk,paired_transaction_fk,name,amount,note,category_fk,sub_category_fk,wallet_fk,date_created,date_time_modified,original_date_due,income,period_length,reoccurrence,end_date,upcoming_transaction_notification,type,paid,created_another_future_transaction,skip_paid,method_added,transaction_owner_email,transaction_original_owner_email,shared_key,shared_old_key,shared_status,shared_date_updated,shared_reference_budget_pk,objective_fk,objective_loan_fk,budget_fks_exclude
OK v48 budgets (1 filas): budget_pk,name,amount,colour,start_date,end_date,wallet_fks,category_fks,category_fks_exclude,income,archived,added_transactions_only,period_length,reoccurrence,date_created,date_time_modified,pinned,order,wallet_fk,budget_transaction_filters,member_transaction_filters,shared_key,shared_owner_member,shared_date_updated,shared_members,shared_all_members_ever,is_absolute_spending_limit
OK v48 category_budget_limits (1 filas): category_limit_pk,category_fk,budget_fk,amount,date_time_modified,wallet_fk
OK v48 associated_titles (1 filas): associated_title_pk,category_fk,title,date_created,date_time_modified,order,is_exact_match,archived
OK v48 app_settings (1 filas): settings_pk,settings_j_s_o_n,date_updated
OK v48 scanner_templates (1 filas): scanner_template_pk,date_created,date_time_modified,template_name,contains,title_transaction_before,title_transaction_after,amount_transaction_before,amount_transaction_after,default_category_fk,wallet_fk,ignore,default_title
OK v48 delete_logs (1 filas): delete_log_pk,entry_pk,type,date_time_modified
OK v48 tags (3 filas): date_created,date_time_modified,order,archived,name,colour,icon_name,emoji_icon_name,tag_pk
OK v48 transaction_to_tag_links (3 filas): transaction_pk,tag_pk
OK v46 wallets (4 filas): wallet_pk,name,colour,icon_name,date_created,date_time_modified,order,currency,currency_format,decimals,home_page_widget_display
OK v46 categories (7 filas): category_pk,name,colour,icon_name,emoji_icon_name,date_created,date_time_modified,order,income,method_added,main_category_pk
OK v46 objectives (5 filas): objective_pk,type,name,amount,order,colour,date_created,end_date,date_time_modified,icon_name,emoji_icon_name,income,pinned,archived,wallet_fk
OK v46 transactions (25 filas): transaction_pk,paired_transaction_fk,name,amount,note,category_fk,sub_category_fk,wallet_fk,date_created,date_time_modified,original_date_due,income,period_length,reoccurrence,end_date,upcoming_transaction_notification,type,paid,created_another_future_transaction,skip_paid,method_added,transaction_owner_email,transaction_original_owner_email,shared_key,shared_old_key,shared_status,shared_date_updated,shared_reference_budget_pk,objective_fk,objective_loan_fk,budget_fks_exclude
OK v46 budgets (1 filas): budget_pk,name,amount,colour,start_date,end_date,wallet_fks,category_fks,category_fks_exclude,income,archived,added_transactions_only,period_length,reoccurrence,date_created,date_time_modified,pinned,order,wallet_fk,budget_transaction_filters,member_transaction_filters,shared_key,shared_owner_member,shared_date_updated,shared_members,shared_all_members_ever,is_absolute_spending_limit
OK v46 category_budget_limits (1 filas): category_limit_pk,category_fk,budget_fk,amount,date_time_modified,wallet_fk
OK v46 associated_titles (1 filas): associated_title_pk,category_fk,title,date_created,date_time_modified,order,is_exact_match
OK v46 app_settings (1 filas): settings_pk,settings_j_s_o_n,date_updated
OK v46 scanner_templates (1 filas): scanner_template_pk,date_created,date_time_modified,template_name,contains,title_transaction_before,title_transaction_after,amount_transaction_before,amount_transaction_after,default_category_fk,wallet_fk,ignore
OK v46 delete_logs (1 filas): delete_log_pk,entry_pk,type,date_time_modified
OK test_schema_and_counts
OK test_special_transactions_and_relationships
OK test_tags
OK test_version_equivalence_and_dates
OK test_wallet_balances
----------------------------------------------------------------------
Ran 7 tests in 0.055s

OK
```

Calidad: ruff check OK, ruff format --check OK, mypy --strict OK; pytest: 7 passed.
Control negativo sobre copia temporal externa: signo de A_payment_1 alterado detectado
en cuatro comprobaciones: CSV, préstamos, equivalencia entre versiones y saldos.

Privacidad: búsqueda de los nombres personales y bancarios de los ejemplos
de documentación sobre scripts, JSON y CSV: **cero coincidencias**; la consulta de nombres
en las dos bases devolvió solo Cuenta Soles, Cuenta Dolares, Efectivo,
Cuenta Archivada Ejemplo y Persona Ejemplo A–E. La búsqueda es una comprobación
complementaria; la garantía principal es la construcción exclusivamente sintética.
