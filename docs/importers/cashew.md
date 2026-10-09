# Importación de SQLite de Cashew

El comando importa **una copia** del SQLite en solo lectura. Nunca se debe
pasar el respaldo original: se rechazan rutas dentro de cualquier directorio
`reference/backups`, incluso mediante enlaces simbólicos. No lee CSV todavía.
Los fixtures y pruebas de esta etapa usan exclusivamente datos sintéticos.

```bash
cd services/api
# MONETAE_DATABASE_URL debe apuntar a PostgreSQL con alembic upgrade head.
# El usuario debe existir previamente (create-user).
cp tests/fixtures/cashew_v48/synthetic_v48.sqlite /tmp/cashew-synthetic.sqlite
uv run python -m monetae.cli import-cashew \
  --file /tmp/cashew-synthetic.sqlite \
  --user-email import@example.test \
  --fx-rate USD=3.800000 \
  --dry-run --report-file /tmp/cashew-report.json
```

Sin `--dry-run`, se aplican las inserciones. El modo de simulación ejecuta los
mismos pasos, calcula los saldos proyectados y revierte las filas financieras;
conserva `import_runs` e `import_review_items`. Cada intento válido registra
una nueva auditoría: la idempotencia se refiere a las entidades financieras.
Si falla un paso, se revierte todo el bloque financiero y se conserva un reporte
con `outcome=failed`, sin parámetros SQL ni mensajes internos privados.

Las opciones son `--file`, `--user-email`, `--dry-run`, `--report-file`,
`--fx-rate MONEDA=TASA` (repetible), `--loan-fx-rates ARCHIVO.json` y
`--allow-balance-diff`.
Las tasas de préstamos se pasan al paso de T-402; no las utiliza el
núcleo. Su formato es `{"<transaction_pk>": "3.800000"}`. Las tasas deben ser
positivas, finitas y no redondear a cero. El reporte no puede sobrescribir ninguna
entrada ni escribirse en `reference/backups`.

Códigos de salida: **0** correcto; **2** argumentos, usuario inexistente o ruta
prohibida; **3** SQLite inválido, inaccesible o sin tablas mínimas; **4** error de
importación o de escritura del reporte; **5** saldos con diferencia sin explicar
sin `--allow-balance-diff` (también en simulación). Los errores se muestran en español y
sin traza. La salida estándar contiene únicamente conteos, códigos y saldos:
no contiene nombres de cuentas, etiquetas, títulos, notas ni payloads de revisión.
El detalle se conserva en PostgreSQL y, si se pide, en `--report-file`.

## Tasas de cambio

En moneda base se guarda `1.000000` con fuente `manual`. En moneda extranjera,
la tasa de `--fx-rate` tiene prioridad y se guarda como `manual`. Si no existe,
se usa el JSON `app_settings.settings_j_s_o_n`:

- `customCurrencyAmounts` tiene prioridad sobre `cachedCurrencyExchange`.
- Las claves se comparan sin distinguir mayúsculas; las monedas de las cuentas
  se normalizan a mayúsculas.
- Cada valor representa **unidades de esa moneda por 1 USD**.
- La tasa de X a la base del usuario es `rate(base) / rate(X)`, redondeada
  `ROUND_HALF_UP` a seis decimales.
- Deben existir ambas claves. Nunca se supone una tasa de 1 para una clave ausente.

Ejemplo: `{"customCurrencyAmounts": {"pen": "3.8", "usd": 1}}` produce
USD→PEN `3.800000`. Las tasas globales se guardan como `auto` y se cuentan en
`provisional_fx` para las transacciones procesadas, también si ya estaban
importadas: **no son tasas históricas**. No cambian
las tasas de transacciones ya importadas. Si falta una tasa necesaria, el
comando falla antes de insertar entidades financieras. El fixture original no
contiene tasas: el ejemplo de uso debe incluir `--fx-rate USD=3.800000`.

## Reporte JSON

`ImportReport` es un modelo Pydantic estricto. Incluye:

- `file_sha256`, `source_schema_version` y `tables` (conteos del SQLite).
- `unknown_tables`, `unknown_columns`, `warnings` (códigos), `unmapped_fields`.
- `counts`: por entidad, `created`, `already_imported`, `deferred`, `skipped`.
- `steps`: secciones JSON extensibles de `loans`, `subscriptions` y `phase_6`.
- `provisional_fx`, `outcome` y `review_items` (`kind`, `payload`).
- `balances`: por cuenta, PK de origen, UUID de cuenta, moneda, `before`,
  `cashew_balance`, `monetae_balance`, `deferred_amount` y `unexplained`.

Importes en JSON son cadenas decimales. El saldo de Cashew suma los importes
brutos de las filas `paid=1`. Monetae suma el saldo inicial y las transacciones
`posted` sin borrado lógico. `unexplained = cashew_balance - monetae_balance -
deferred_amount`. El reporte del modo de simulación contiene saldos **proyectados**,
aunque las cuentas y transacciones nuevas se reviertan. El signo almacenado en Cashew determina ingreso/gasto y se conserva aunque
contradiga `income`; esa anomalía genera `polarity_mismatch` con
`transaction_pk`, `amount` e `income`, sin modificar el dinero ni el saldo. Un saldo previo o una edición manual posterior puede
producir diferencia: la importación no sobrescribe ni ajusta esas filas.

## Filas problemáticas (T-401b)

Estas anomalías individuales no abortan el resto de la importación: la fila se
omite, incrementa `counts.transactions.skipped` y genera un ítem de revisión:

- Transacción ordinaria (tipo nulo o 0) con importe cero:
  `zero_amount_transaction` con `transaction_pk`.
- Cuenta inexistente (incluido `wallet_fk="0"` si no existe esa cuenta):
  `orphan_transaction` con `transaction_pk` y `wallet_pk`.
- Tipo fuera de 0–4: `unsupported_transaction_type` con `transaction_pk` y `type`.

No se cuentan como importadas ni diferidas; sus vínculos de etiquetas también
se cuentan como omitidos. Se detectan cuenta inexistente y tipo desconocido
antes de pasar filas a los pasos de préstamos o recurrentes. Las revisiones no
incluyen títulos, notas ni nombres. Si una fila omitida estaba pagada y su cuenta
existe, su importe sigue en `cashew_balance` y su efecto queda visible en
`unexplained`, sin compensación ni importe diferido artificial. Una cuenta
huérfana no tiene saldo de destino: se señala por sus PK en la revisión.

En las transacciones ordinarias el signo del importe almacenado tiene prioridad
sobre `income`, por ser el que usa `SUM(amount)` de Cashew. `polarity_mismatch`
reemplaza a `polarity_corrected`: se conserva el importe y se avisa, sin invertirlo.

## Alcance de T-401 y extensión

Se importan cuentas, categorías, etiquetas, transacciones ordinarias/programadas
y transferencias válidas. La identidad es `cashew:sqlite:<pk>` por usuario y
entidad. Las identidades existentes, incluidas las borradas lógicamente, se omiten;
no se actualizan nombres, notas, vínculos ni otros campos tras una reimportación.
Los nombres de cuentas/etiquetas que colisionen reciben ` (Cashew)` (y un número
si hace falta). Categorías de Cashew llamadas Intereses siguen siendo distintas
de las categorías de sistema y generan aviso. El archivado y emoji de categorías
se conservan como campos sin destino en el reporte.

Las transferencias exigen dos filas recíprocas, cuentas distintas, misma moneda,
importes opuestos y ambas pagadas. Se insertan atómicamente sin categoría, con
un único grupo. Un par inválido se conserva como transacciones ordinarias y
`unpaired_transfer`; una pareja parcialmente importada nunca modifica la pata
existente y su nueva pata se inserta como ordinaria, con revisión.

Los pasos se ejecutan en orden: cuentas → categorías → etiquetas → transacciones
ordinarias/programadas → transferencias → `loans.run(context)` →
`subscriptions.run(context)`. T-403 importa las suscripciones y recurrentes;
T-402 importa los préstamos y su efectivo, sin importe diferido. Los presupuestos,
límites, reglas de categorización, plantillas de escaneo, configuración y metas
se cuentan como pendientes de Fase 6; `delete_logs` no genera entidades.

`ImportContext` expone `session`, `user_id`, `snapshot`, `options`, `plan`,
`report`, mapas de `accounts`/`categories`/`tags`/`transactions` por PK de origen,
`before`, `deferred_amounts`, `tag_links` y `skipped_pks` (set vacío por defecto).
Los pasos añaden a `skipped_pks` las filas que omiten: el runner clasifica sus
etiquetas como omitidas, además de las de `plan.skipped_transactions`, sin
contarlas como diferidas. `map_transaction` normaliza una fila
ordinaria con su `AccountPlan`. `insert_transaction` conserva la identidad y los
vínculos de etiquetas al crear, incluso etiquetas archivadas; permite indicar
`kind`, `transfer_group_id` e identidad alternativa. `defer` registra filas
pendientes sin efectivo. Los pasos devuelven `dict[str, JsonValue]` para su
sección de `steps` y pueden añadir conteos y revisiones al reporte compartido.

`transaction_tag_map(snapshot)` entrega el mapa completo `transaction_pk →
PK de etiquetas`. Los tres vínculos del fixture apuntan a las filas G recurrentes:
T-403 crea los tres vínculos sobre las transacciones históricas, incluida la
etiqueta archivada. Las nuevas programadas no copian esas etiquetas históricas.

`run_import` no hace commit: el caller confirma la transacción exterior.
Debe confirmar también tras `ImportExecutionError` si quiere conservar su
reporte de fallo; la parte financiera ya se ha revertido al savepoint. No debe
haber escrituras pendientes ajenas al importador en esa sesión. Todos los pasos
usan la misma sesión y usuario. Un bloqueo por usuario serializa importaciones
simultáneas; el cambio de moneda base comparte el bloqueo del historial.

El lector descubre columnas y tablas, avisa de ausentes (incluidas etiquetas en
v46) y omite columnas desconocidas. Convierte inmediatamente SQLite REAL a
`Decimal(str(valor))`, sin cálculos monetarios float. Interpreta timestamps UTC
en segundos, milisegundos (`>10**11`) y microsegundos (`>=10**14`, conforme a
ARCHITECTURE §6), con aviso de escala. La marca de datos iniciales usa fechas
inclusivas agosto–octubre de 2025 en `America/Lima`.


## Suscripciones y recurrentes (T-403 / T-403b)

Cashew crea una fila por ocurrencia: al pagar una fila copia la siguiente con
`paid=false` y una PK `<pk_original>::predict::N` (ver
`upcomingTransactionsFunctions.dart`, `createNewSubscriptionTransaction` y
`updatePredictableKey`, solo lectura). El importador agrupa `type=1` y `type=2`
por `series_id = pk.split("::predict::")[0]`, sin fusionar títulos iguales.
Ordena cada serie por `(date_created, pk)`.

Cada serie válida crea **una regla**; si la plantilla más reciente tiene
`type=1`, crea además **una suscripción de gasto**. `type=2` crea solo una regla,
de ingreso o gasto según el signo. Título, monto, categoría/subcategoría,
cuenta, moneda, periodo, intervalo, nota y fecha de fin proceden de la última
fila; cada transacción histórica conserva sus propios valores. El ancla es
la fecha de la **primera** fila en `America/Lima`. La advertencia agregada
`recurrence_anchor_assumed:N` señala esta interpretación del ancla para N series,
en una única línea por reporte, sin un ítem por fila.

El calendario usa `reoccurrence`: 1 diaria, 2 semanal, 3 mensual, 4 anual;
`period_length` es el intervalo de 1 a 366. Cada fila `paid=1` se importa como
histórica `posted`, con su fecha, cuenta, categoría, monto y etiquetas, vinculada
a la regla; la API calcula `historical_paid` y `last_paid_on` desde ese historial.

Si existe una fila `paid=0`, esa fila es la `scheduled` de la regla a las 00:00
de Lima (05:00 UTC), con su PK original y sus valores, y fija `next_run_on` /
`next_due_on` aunque esté vencida. Una serie con solo esa fila es válida y no
inventa historial. Si hay varias pendientes, la primera por `(date_created, pk)`
es la programada vinculada; las demás se conservan como `scheduled` ordinarias,
sin vincular a la regla, y se registra una revisión `multiple_pending_occurrences`
con `{series_id, count}`.

Si no existe fila pendiente, `next_after` calcula la primera fecha del calendario
mayor o igual que hoy en Lima y materializa una única `scheduled`. El reloj se
inyecta en `subscriptions.run(context, clock=...)`. Se preserva el día del ancla
sin deriva por meses cortos (31 → 28/29 → 31, y 29 de febrero). La tasa se resuelve
antes de insertar por las reglas de T-401, incluida la fuente de la fila mapeada:
las programadas también conservan `auto` cuando corresponde y se cuentan en
`provisional_fx`; no se convierten silenciosamente en tasas manuales.

Si `end_date` ya pasó, la regla queda inactiva y la suscripción archivada con
`archived_at=end_date` y motivo «Terminada en Cashew», conservando el historial
pagado. No se materializa una programada. Las filas pendientes de una serie
terminada se omiten para evitar cobros huérfanos, con
`ended_series_pending_occurrence` y `{series_id, transaction_pk, due_on}`;
cuentan como `skipped`, también sus etiquetas. Un fin futuro sigue siendo
inclusivo: una próxima fecha calculada que lo exceda no se materializa.

**Fallback sin perder dinero:** una periodicidad no soportada o intervalo
fuera de rango importa todas las filas como transacciones ordinarias (posted
si pagadas, scheduled si pendientes), con una revisión por serie
`unsupported_recurrence` y `{series_id, rows}`. Título vacío, plantilla de
suscripción con monto positivo o calendario inválido hace lo mismo con
`invalid_recurring_transaction`. Solo una fila con monto cero se omite, con
`zero_amount_transaction` y su PK. Los enlaces de etiquetas de las filas
ordinarias se conservan; los de filas omitidas cuentan como `skipped`.

Regla y suscripción usan `cashew:sqlite:<series_id>`; cada fila original usa
`cashew:sqlite:<pk_de_la_fila>`. Solo una programada calculada sin fila Cashew
usa `cashew:sqlite:<series_id>:scheduled`. Una serie de una fila pagada conserva
los mismos IDs y resultado de T-403. Reimportar omite identidades existentes,
incluso borradas lógicamente, sin modificar la plantilla, el historial ni sus
vínculos y sin regenerar cobros cancelados. Una transacción previamente importada
como ordinaria no se edita para enlazarla retroactivamente; se conserva con
revisión `recurrence_already_imported`.

`steps.subscriptions` mantiene `subscriptions_created`, `recurring_rules_created`,
`already_imported`, `archived`, `skipped`, `unsupported_recurrence` y
`scheduled_created`, y añade `series`, `rows_total`, `historical_posted`,
`pending_scheduled` (incluye programadas calculadas y pendientes adicionales)
y `ordinary_fallback` (filas conservadas como ordinarias por plantilla inválida).
Los conteos de filas procesadas incluyen las identidades ya importadas; los
contadores `created` indican únicamente inserciones nuevas. `counts.transactions`
cuenta todas las históricas y programadas nuevas, y `counts.subscriptions` /
`counts.recurring_rules` cuentan las entidades por serie.

## Cuadre final y código 5

Después de todos los pasos se exige, **para cada cuenta**:

```text
unexplained = cashew_balance − monetae_balance − deferred_amount = 0.00
```

Solo sigue diferido lo que un paso realmente dejó pendiente: los préstamos de T-402 y las series de T-403b ya no
aportan importe diferido. Una fila omitida pagada no se compensa artificialmente.

Si alguna cuenta no cuadra, el reporte incluye `balance_mismatch=true`, el
aviso `balance_mismatch` y las diferencias por cuenta. Por defecto se **revierte
el bloque financiero completo**, conservando `import_runs`, las revisiones,
los conteos y saldos proyectados para auditoría; `outcome=balance_mismatch` y
el comando devuelve **5**. La salida de error indica: «Los saldos no cuadran;
no se importó nada. Revise el reporte o use --allow-balance-diff.»

`--allow-balance-diff` permite confirmar lo financiero y devolver **0**,
con `outcome=applied_with_balance_diff`, la bandera registrada en el reporte
y la diferencia visible en la salida. `--dry-run` siempre revierte: también
sale con 5 si no cuadra, o 0 y `outcome=dry_run_with_balance_diff` si se permite.
El reporte marca `financial_rolled_back` cuando se revierte por simulación o
cuadre; los conteos `created` en esos casos representan inserciones proyectadas.
Una edición manual previa puede causar descuadre: nunca se sobrescribe.

Para permitir explícitamente una diferencia tras revisar la simulación:

```bash
uv run python -m monetae.cli import-cashew \
  --file /tmp/cashew-synthetic.sqlite \
  --user-email import@example.test \
  --fx-rate USD=3.800000 \
  --allow-balance-diff --report-file /tmp/cashew-report.json
```

`pending_phase_6` y `steps.phase_6` listan los conteos de presupuestos (`budgets`),
límites por categoría (`category_budget_limits`), reglas de título
(`associated_titles`), plantillas del escáner (`scanner_templates`) y metas
(`goals`, solo objetivos de tipo 0). No se importan todavía; tampoco se añaden
rutas `/imports` ni de subida de archivos. La salida estándar conserva únicamente
códigos, conteos, banderas de cuadre e importes, sin textos privados del respaldo.
