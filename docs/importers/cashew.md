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
`--fx-rate MONEDA=TASA` (repetible) y `--loan-fx-rates ARCHIVO.json`.
Las tasas de préstamos se pasan al paso reservado a T-402; no las utiliza el
núcleo. Su formato es `{"<transaction_pk>": "3.800000"}`. Las tasas deben ser
positivas, finitas y no redondear a cero. El reporte no puede sobrescribir ninguna
entrada ni escribirse en `reference/backups`.

Códigos de salida: **0** correcto; **2** argumentos, usuario inexistente o ruta
prohibida; **3** SQLite inválido, inaccesible o sin tablas mínimas; **4** error de
importación o de escritura del reporte. Los errores se muestran en español y
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
aunque las cuentas y transacciones nuevas se reviertan. Las correcciones de
polaridad se registran como `polarity_corrected`; su efecto en el saldo queda
visible en `unexplained`. Un saldo previo o una edición manual posterior puede
producir diferencia: la importación no sobrescribe ni ajusta esas filas.

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
`subscriptions.run(context)`. Ambos últimos son stubs de T-401: cuentan filas
diferidas y sus importes pagados por cuenta, sin insertar dinero. Los presupuestos,
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
en T-401 se conservan en ese mapa y se cuentan diferidos; **T-403** creará las
filas `transaction_tags`. No se crean transacciones G anticipadamente.

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
