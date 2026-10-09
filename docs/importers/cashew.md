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
Las tasas de préstamos se pasan al paso reservado a T-402; no las utiliza el
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
el stub de préstamos de T-401 cuenta sus filas e importes pagados como diferidos
hasta integrar T-402. Los presupuestos,
límites, reglas de categorización, plantillas de escaneo, configuración y metas
se cuentan como pendientes de Fase 6; `delete_logs` no genera entidades.

`ImportContext` expone `session`, `user_id`, `snapshot`, `options`, `plan`,
`report`, mapas de `accounts`/`categories`/`tags`/`transactions` por PK de origen,
`before`, `deferred_amounts` y `tag_links`. `map_transaction` normaliza una fila
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


## Suscripciones y recurrentes (T-403)

`type=1` y monto negativo crea una suscripción de gasto y su regla; `type=2`
crea solo una regla, de ingreso o gasto según el signo. Se conservan cuenta,
moneda, categoría (subcategoría si existe), título y nota. La suscripción guarda
el monto absoluto y la regla/transacciones su signo original.

El calendario usa `reoccurrence`: 1 diaria, 2 semanal, 3 mensual, 4 anual.
`period_length` es el intervalo de 1 a 366. Personalizada (0), nula, desconocida
u intervalo inválido conserva la fila como transacción ordinaria y genera
`unsupported_recurrence`, sin regla ni suscripción. Monto cero, título vacío,
suscripción con importe positivo o calendario fuera del rango de fechas se
omite con `invalid_recurring_transaction`; otras filas continúan procesándose.
Si esto deja dinero sin explicar, se aplica el criterio de cuadre descrito abajo.

Se interpreta la fecha de cada fila válida como la **última ocurrencia registrada**:
se conserva una transacción histórica `posted`, con su identidad original,
fecha y etiquetas, vinculada a la regla. Esta interpretación de v48 sigue siendo
una hipótesis: el reporte añade una sola advertencia `recurrence_anchor_assumed:N`
con el total de filas interpretadas; no genera un ítem de revisión por fila.

El ancla es la fecha de la fila en `America/Lima`. `next_after` del dominio
calcula la primera fecha del calendario **mayor o igual que hoy** en Lima,
con reloj inyectable en `subscriptions.run(context, clock=...)`. Se preserva
el día del ancla sin deriva por meses cortos (31 → 28/29 → 31, y 29 de febrero).
Se materializa una única `scheduled`, a las 00:00 de Lima (05:00 UTC), con
monto, cuenta, categoría, moneda y tasa provisional de la regla. La tasa se
resuelve antes de insertar, por las reglas de T-401; las programadas llevan
fuente `manual` igual que las creadas por la API y deben confirmarse al publicar.

`end_date` limita el calendario por fecha local inclusiva. Si ya pasó, la regla
queda inactiva y la suscripción queda `archived`, con `archived_at=end_date`
y motivo «Terminada en Cashew», conservando el historial y sin programada.
Si la próxima fecha excede un fin que aún no pasó, tampoco se materializa.
Las suscripciones importadas usan el archivado/reactivación de la API de Fase 3,
que conserva el historial y cancela todas las programadas pendientes al archivar.

Regla, suscripción e histórica usan `cashew:sqlite:<pk>` en sus respectivas
tablas; la nueva programada usa `cashew:sqlite:<pk>:scheduled`. Reimportar omite
identidades existentes incluso borradas lógicamente, sin cambiar las fechas,
montos, vínculos o estados y sin regenerar cobros cancelados. Una transacción
histórica previamente importada sin regla se conserva sin editar y se registra
`recurrence_already_imported` para revisión.

`steps.subscriptions` incluye `subscriptions_created`, `recurring_rules_created`,
`already_imported`, `archived` (reglas terminadas, con o sin suscripción),
`skipped`, `unsupported_recurrence` y `scheduled_created`. `counts` contiene
las entidades `subscriptions` y `recurring_rules`; las históricas y programadas
nuevas también cuentan en `counts.transactions`.

## Cuadre final y código 5

Después de todos los pasos se exige, **para cada cuenta**:

```text
unexplained = cashew_balance − monetae_balance − deferred_amount = 0.00
```

Solo sigue diferido lo que un paso realmente dejó pendiente: el stub de
préstamos lo explica hasta integrar T-402; las suscripciones importadas no
aportan diferido. Una fila omitida pagada no se compensa artificialmente.

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
