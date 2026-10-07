# Formato de Respaldo de Cashew (Análisis e Importación)

Este documento describe detalladamente los formatos de respaldo generados y consumidos por la aplicación Cashew, con el objetivo de sustentar el diseño del importador de datos para Monetae (`RF-40a..f`).

---

## 1. Verificación de fuentes y metodología de análisis

Para la elaboración de este análisis técnico se utilizaron exclusivamente dos fuentes:
1. **Código fuente de Cashew (SOLO LECTURA):** Ubicado en `reference/Cashew/budget/` (`lib/`, `drift_schemas/`, `pubspec.yaml`).
2. **Inspección estricta de esquema en respaldos:** Siguiendo la política de privacidad estricta (sin consultar datos privados de transacciones, importes ni descripciones reales), se ejecutaron exclusivamente los siguientes comandos técnicos:
   - `file reference/backups/cashew-2026-10-05-21-02-50-406966.sql`: confirmó tipo de archivo `SQLite 3.x database, user version 48`.
   - `python3 -c "import sqlite3; conn = sqlite3.connect('...'); cursor.execute(\"SELECT sql FROM sqlite_master WHERE type='table';\"); ..."`: extrajo únicamente las sentencias DDL (`CREATE TABLE`) y PRAGMAs de esquema (`PRAGMA user_version`).
   - `head -n 1 reference/backups/cashew-2026-10-06-18-17-57-084794.csv`: leyó únicamente la cabecera (lista de nombres de columnas) del archivo CSV.

> **Confirmación de privacidad:** No se extrajo, visualizó ni copió ningún valor financiero real, registro personal, nombre de cuenta o monto de Adrian.

---

## 2. Formatos de Respaldo y Mecanismos de Exportación/Importación en Cashew

Cashew implementa tres mecanismos de persistencia e intercambio de datos:

### 2.1 Archivo de Base de Datos SQLite / `.sql` / `.sqlite`

#### Mecanismos de Exportación
- **Exportación manual a almacenamiento local (`lib/widgets/exportDB.dart`):**
  - La función `exportDB(boxContext:)` invoca `saveDBFileToDevice()` (`exportDB.dart:11-45`).
  - Llama primero a `backupSettings()` (`lib/struct/settings.dart:324`), el cual extrae el JSON de preferencias (`userSettings`) de `sharedPreferences` y lo persiste en la tabla SQLite `app_settings` con `settings_pk = 0`.
  - Obtiene el stream binario de la base de datos subyacente mediante `getCurrentDBFileInfo()` (`lib/database/tables.dart` y dependencias de plataforma).
  - Guarda el archivo con el patrón de nombre:
    ```
    cashew-YYYY-MM-DD-HH-mm-ss-ffffff.sql
    ```
    (generado con `cleanFileNameString(DateTime.now().toString()) + ".sql"`, `exportDB.dart:42`).
- **Respaldo en la nube / Google Drive (`lib/widgets/accountAndBackup.dart`):**
  - La función `createBackup()` (`accountAndBackup.dart:390-450`) persiste la configuración vía `backupSettings()` y envía el archivo binario a la carpeta de Google Drive `appDataFolder`.
  - El nombre de archivo en Drive sigue el patrón:
    ```
    db-v<schemaVersionGlobal>-<deviceName>.sqlite
    ```
    (donde `schemaVersionGlobal = 46` en el código fuente `tables.dart:29`).

#### Mecanismos de Importación y Restauración
- **Restauración manual local (`lib/widgets/importDB.dart`):**
  - La función `importDBFromDevice()` (`importDB.dart:15-55`) permite seleccionar archivos `.sql` o `.sqlite` mediante `FilePicker`.
  - Llama a `cancelAndPreventSyncOperation()` (`lib/struct/syncClient.dart:185`) para abortar sincronizaciones concurrentes.
  - Sobrescribe físicamente el archivo de base de datos local usando `overwriteDefaultDB(fileBytes)` (`importDB.dart:45-50`).
  - Reinicia el idioma del sistema y establece el flag `databaseJustImported = true` (`importDB.dart:52-53`).
  - Requiere un reinicio o recarga obligatoria de la app (`importDB.dart:95-102`). Al abrirse, Drift ejecuta las migraciones automáticas (`tables.dart:927-1168`) si la versión de la base importada es anterior a `schemaVersionGlobal`.

---

### 2.2 Archivo CSV (`.csv`)

#### Mecanismo de Exportación (`lib/widgets/exportCSV.dart`)
- La clase `ExportCSV` y el método `exportCSV()` (`exportCSV.dart:77-176`) permiten filtrar por un rango de fechas (`DateTimeRange`) y por una lista de billeteras (`selectedWalletPks`).
- **Filtro restrictivo crítico:**
  ```dart
  // exportCSV.dart:88
  tbl.paid.equals(true)
  ```
  **Solo exporta transacciones con `paid == true`**. Las transacciones pendientes (`paid == false`), como cuotas impagas o deudas activas no liquidadas en la lógica de Cashew, son completamente omitidas.
- **Columnas exportadas por defecto en Cashew (`exportCSV.dart:110-140`):**
  1. `account`: Nombre de la billetera (`transactionWithCategory.wallet?.name`).
  2. `amount`: Monto como cadena (`transactionWithCategory.transaction.amount.toString()`).
  3. `currency`: Código de moneda en mayúsculas (`wallet.currency.allCaps`).
  4. `title`: Nombre o concepto de la transacción (`transaction.name`).
  5. `note`: Nota textual (`transaction.note`).
  6. `date`: Fecha de creación en formato ISO (`transaction.dateCreated.toString()`).
  7. `income`: Booleano `"true"` o `"false"` (`transaction.income.toString()`).
  8. `type`: Entero como cadena que mapea a `TransactionSpecialType` (`transaction.type.toString()`).
  9. `category name`: Nombre de la categoría principal (`category.name`).
  10. `subcategory name`: Nombre de la subcategoría si existe (`subCategory?.name`).
  11. `color`: Color hexadecimal de la categoría (`category.colour`).
  12. `icon`: Nombre del asset de icono (`category.iconName`).
  13. `emoji`: Emoji asociado a la categoría (`category.emojiIconName`).
  14. `budget`: Nombre del presupuesto asignado (`budget?.name`).
  15. `objective`: Nombre del objetivo o meta asignada (`objective?.name`).
- **Variantes en respaldos de usuario:**
  En archivos reales generados por exportaciones anteriores o personalizadas, pueden encontrarse cabeceras con columnas complementarias formateadas para visualización:
  `account,amount,amount unpaid,currency,title,note,date,income,type,category name,subcategory name,color,icon,emoji,budget,objective,extra`
  donde `extra` contiene etiquetas informativas de periodicidad (p. ej. `Repetir cada 1 mes • martes, 10 de marzo`) y `amount unpaid` refleja montos pendientes calculados para la vista.
- Los datos se serializan usando `ListToCsvConverter().convert(csvData)` (`exportCSV.dart:151`).
- El nombre de archivo generado es `cashew-YYYY-MM-DD-HH-mm-ss-ffffff.csv` o `cashew-<timestamp>-<start>-to-<end>.csv`.

#### Mecanismo de Importación (`lib/widgets/importCSV.dart`)
- `ImportCSV` (`importCSV.dart:42-658`) permite seleccionar un archivo `.csv` o ingresar la URL de una hoja de cálculo pública de Google Sheets (`importCSV.dart:573-594`).
- **Detección de codificación:** En plataformas nativas utiliza `CharsetDetector.autoDecode(fileBytes)` (`importCSV.dart:69-70`), manejando UTF-8, Windows-1252/ISO-8859-1, etc. En web decodifica UTF-8 directo.
- **Asignación interactiva de columnas (`_assignColumns`, `importCSV.dart:133-185`):**
  Busca cabeceras requeridas (`date`, `amount`, `category`, `wallet`) y opcionales (`name`/`title`, `note`).
- **Creación sobre la marcha:** Si una categoría o billetera nombrada en el CSV no existe en la base de datos, `_importEntry` (`importCSV.dart:945-1017`) la crea automáticamente con valores predeterminados.
- **Pérdida de identidad:** Asigna claves primarias generadas aleatoriamente (`uuid.v4()`) y marca el método de adición como `MethodAdded.csv` (`importCSV.dart:1094`).

---

### 2.3 Sincronización Multi-dispositivo / Sincronización Cloud (`lib/struct/syncClient.dart`)

- **Naturaleza del formato:** A pesar de llamarse sincronización cliente-servidor, Cashew **no utiliza un endpoint REST con payloads JSON** para sus entidades relacionales.
- **Mecanismo:**
  1. Cada dispositivo sube su base de datos SQLite completa a Google Drive (`appDataFolder`) con el nombre `sync-<clientID>.sqlite` (`syncClient.dart:35-38, 148-150`).
  2. Al sincronizar (`_syncData`, `syncClient.dart:214-548`), descarga los archivos `.sqlite` de los demás clientes.
  3. Abre temporalmente dicha base SQLite secundaria montándola como base `syncdb` (`syncClient.dart:326-356`).
  4. Lee de la base remota las filas con `dateTimeModified > lastSynced` en las tablas:
     `wallets`, `categories`, `budgets`, `category_budget_limits`, `transactions`, `associated_titles`, `scanner_templates`, `objectives` y `delete_logs`.
  5. Consolida estas operaciones en una cola en memoria de objetos `SyncLog` (`syncClient.dart:155-174`) y las aplica localmente con `database.processSyncLogs(syncLogs)` (`syncClient.dart:518`).
  6. Para borrados físicos utiliza `DeleteLog`, que registra `entryPk`, el enum `DeleteLogType` y la fecha de borrado.

---

## 3. Esquema Completo del Formato SQLite (`.sql` / `.sqlite`)

El archivo `.sql` exportado por Cashew es en realidad una **base de datos relacional SQLite 3 binaria** generada por la librería Drift (Moor).

### 3.1 Detección de Versión de Esquema
1. **Pragma estándar de SQLite:**
   ```sql
   PRAGMA user_version;
   ```
   Drift almacena directamente el número entero de la versión de esquema en la cabecera del archivo SQLite. En el código fuente de Cashew, `schemaVersionGlobal` está fijado en `46` (`lib/database/tables.dart:29`), mientras que en versiones recientes de producción alcanza la versión `48` (constatado en respaldos recientes).
2. **Nombre de archivo en nube:** Los respaldos en Google Drive incorporan la versión en el nombre: `db-v46-<device>.sqlite`.
3. **Versión en `app_settings`:** En la tabla `app_settings`, la columna `settings_j_s_o_n` contiene un objeto serializado con campos como `"databaseVersion"` o preferencias de compilación.

---

### 3.2 Tablas, Columnas, Tipos y Codificaciones

A continuación se detalla la estructura física de las 12 tablas presentes en el esquema SQLite de Cashew (`lib/database/tables.dart` y validación DDL):

#### Codificaciones Generales:
- **Identificadores (PK/FK):** `TEXT` conteniendo UUID v4 en formato canónico de 36 caracteres con guiones (p. ej. `a1b2c3d4-e5f6-789a-bcde-f0123456789a`). Excepción: `wallet_fk = '0'` representa la billetera por defecto.
- **Fechas y Tiempos:** `INTEGER` que almacena microsegundos o milisegundos Unix epoch UTC desde 1970 (`dateTime().clientDefault(...)` en Drift convierte `DateTime` a enteros Unix).
- **Booleanos:** `INTEGER` con restricción `CHECK (columna IN (0, 1))`. `0 = false`, `1 = true`.
- **Montos Monetarios:** `REAL` (coma flotante IEEE 754 de 64 bits en SQLite). **Advertencia técnica:** Monetae debe convertir estos valores inmediatamente a `Decimal` de precisión fija.
- **Listas JSON en columnas de texto:** Ciertas columnas usan convertidores de Drift (`TypeConverter<List<...>, String>`) que serializan arrays JSON como cadenas de texto plano (p. ej. `["uuid1", "uuid2"]` o `[0, 1, 2]`).

---

#### Detalle de Tablas

### 1. `wallets` (Cuentas / Billeteras)
- Definición Drift: `lib/database/tables.dart:251-271`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "wallets" (
    "wallet_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "currency" TEXT NULL,
    "currency_format" TEXT NULL,
    "decimals" INTEGER NOT NULL DEFAULT 2,
    "home_page_widget_display" TEXT NULL DEFAULT NULL,
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1)),
    "emoji_icon_name" TEXT NULL
  );
  ```
- **Campos clave para Monetae:**
  - `wallet_pk`: Mapea a `accounts.id` (`UUID`).
  - `name`: Nombre de la cuenta bancaria / efectivo.
  - `currency`: Código ISO 4217 de 3 letras (p. ej. `"PEN"`, `"USD"`). Si es `null`, asume la divisa primaria global.
  - `decimals`: Precisión de decimales (generalmente `2`).
  - `archived`: Estado de archivado (`0` o `1`).

### 2. `categories` (Categorías y Subcategorías)
- Definición Drift: `lib/database/tables.dart:343-373`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "categories" (
    "category_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "method_added" INTEGER NULL,
    "main_category_pk" TEXT NULL DEFAULT NULL REFERENCES categories (category_pk),
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1))
  );
  ```
- **Campos clave para Monetae:**
  - `category_pk`: Mapea a `categories.id`.
  - `main_category_pk`: Si es `NULL`, es categoría padre/raíz. Si tiene valor, apunta a su categoría padre (`categories.parent_id`).
  - `income`: `0 = gasto`, `1 = ingreso`.
  - `archived`: Borrado lógico/archivado.

### 3. `objectives` (Metas de Ahorro y Préstamos en Cashew)
- Definición Drift: `lib/database/tables.dart:515-539`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "objectives" (
    "objective_pk" TEXT NOT NULL PRIMARY KEY,
    "type" INTEGER NOT NULL DEFAULT 0,
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "order" INTEGER NOT NULL,
    "colour" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "end_date" INTEGER NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "pinned" INTEGER NOT NULL DEFAULT 1 CHECK ("pinned" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk)
  );
  ```
- **Semántica crítica (`ObjectiveType`, `tables.dart:52-55`):**
  - `type = 0` (`ObjectiveType.goal`): Meta u objetivo de ahorro tradicional.
  - `type = 1` (`ObjectiveType.loan`): Préstamo a largo plazo.
    - Si `income == 1`: Dinero prestado a un tercero (crédito por cobrar / *lent*).
    - Si `income == 0`: Dinero recibido en préstamo (deuda por pagar / *borrowed*).
  - `amount`: Monto total de la meta o capital del préstamo.
  - `wallet_fk`: Billetera por defecto a la que Cashew asociaba erróneamente todo el préstamo (Problema P3 de Monetae).

### 4. `transactions` (Transacciones)
- Definición Drift: `lib/database/tables.dart:274-340`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "transactions" (
    "transaction_pk" TEXT NOT NULL PRIMARY KEY,
    "paired_transaction_fk" TEXT NULL DEFAULT NULL REFERENCES transactions (transaction_pk),
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "note" TEXT NOT NULL,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "sub_category_fk" TEXT NULL DEFAULT NULL REFERENCES categories (category_pk),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "original_date_due" INTEGER NULL DEFAULT 1753912320,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "period_length" INTEGER NULL,
    "reoccurrence" INTEGER NULL,
    "end_date" INTEGER NULL,
    "upcoming_transaction_notification" INTEGER NULL DEFAULT 1 CHECK ("upcoming_transaction_notification" IN (0, 1)),
    "type" INTEGER NULL,
    "paid" INTEGER NOT NULL DEFAULT 0 CHECK ("paid" IN (0, 1)),
    "created_another_future_transaction" INTEGER NULL DEFAULT 0 CHECK ("created_another_future_transaction" IN (0, 1)),
    "skip_paid" INTEGER NOT NULL DEFAULT 0 CHECK ("skip_paid" IN (0, 1)),
    "method_added" INTEGER NULL,
    "transaction_owner_email" TEXT NULL,
    "transaction_original_owner_email" TEXT NULL,
    "shared_key" TEXT NULL,
    "shared_old_key" TEXT NULL,
    "shared_status" INTEGER NULL,
    "shared_date_updated" INTEGER NULL,
    "shared_reference_budget_pk" TEXT NULL,
    "objective_fk" TEXT NULL REFERENCES objectives (objective_pk),
    "objective_loan_fk" TEXT NULL REFERENCES objectives (objective_pk),
    "budget_fks_exclude" TEXT NULL
  );
  ```
- **Campos críticos y enums (`tables.dart:42-51`):**
  - `type` (`TransactionSpecialType`):
    - `0`: `upcoming` (futuro programado).
    - `1`: `subscription` (suscripción periódica).
    - `2`: `repetitive` (pago repetitivo común).
    - `3`: `credit` (préstamo otorgado / cobro pendiente).
    - `4`: `debt` (préstamo recibido / pago adeudado).
  - `reoccurrence` (`BudgetReoccurence`): `0: custom, 1: daily, 2: weekly, 3: monthly, 4: yearly`.
  - `period_length`: Frecuencia de repetición (ej. cada `1` mes).
  - `paired_transaction_fk`: En transferencias entre cuentas, Cashew genera dos transacciones enlazadas mutuamente por esta clave.
  - `objective_loan_fk`: Enlace directo al préstamo padre en `objectives`. Los pagos o desembolsos asociados llevan esta FK.
  - `objective_fk`: Enlace a meta de ahorro.
  - `budget_fks_exclude`: Array JSON `["uuid", ...]` con IDs de presupuestos que excluyen expresamente este gasto.

### 5. `budgets` (Presupuestos)
- Definición Drift: `lib/database/tables.dart:423-475`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "budgets" (
    "budget_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "colour" TEXT NULL,
    "start_date" INTEGER NOT NULL,
    "end_date" INTEGER NOT NULL,
    "wallet_fks" TEXT NULL,
    "category_fks" TEXT NULL,
    "category_fks_exclude" TEXT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "added_transactions_only" INTEGER NOT NULL DEFAULT 0 CHECK ("added_transactions_only" IN (0, 1)),
    "period_length" INTEGER NOT NULL,
    "reoccurrence" INTEGER NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "pinned" INTEGER NOT NULL DEFAULT 0 CHECK ("pinned" IN (0, 1)),
    "order" INTEGER NOT NULL,
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "budget_transaction_filters" TEXT NULL DEFAULT NULL,
    "member_transaction_filters" TEXT NULL DEFAULT NULL,
    "shared_key" TEXT NULL,
    "shared_owner_member" INTEGER NULL,
    "shared_date_updated" INTEGER NULL,
    "shared_members" TEXT NULL,
    "shared_all_members_ever" TEXT NULL,
    "is_absolute_spending_limit" INTEGER NOT NULL DEFAULT 0 CHECK ("is_absolute_spending_limit" IN (0, 1))
  );
  ```
- **Campos serializados:**
  - `wallet_fks`: Lista JSON de cadenas con billeteras asignadas al presupuesto.
  - `category_fks`: Lista JSON con categorías incluidas.
  - `category_fks_exclude`: Lista JSON con categorías explícitamente excluidas.
  - `budget_transaction_filters`: Lista JSON de enteros correspondientes al enum `BudgetTransactionFilters` (`tables.dart:76-84`).

### 6. `category_budget_limits` (Límites por Categoría dentro de Presupuesto)
- Definición Drift: `lib/database/tables.dart:376-388`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "category_budget_limits" (
    "category_limit_pk" TEXT NOT NULL PRIMARY KEY,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "budget_fk" TEXT NOT NULL REFERENCES budgets (budget_pk),
    "amount" REAL NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk)
  );
  ```

### 7. `associated_titles` (Reglas de Auto-categorización por Título)
- Definición Drift: `lib/database/tables.dart:395-408`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "associated_titles" (
    "associated_title_pk" TEXT NOT NULL PRIMARY KEY,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "title" TEXT NOT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "is_exact_match" INTEGER NOT NULL DEFAULT 0 CHECK ("is_exact_match" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1))
  );
  ```
- **Utilidad:** Reglas heurísticas de coincidencia de texto (subcadena o coincidencia exacta) para asignar categorías automáticamente al ingresar transacciones.

### 8. `app_settings` (Configuraciones de la Aplicación y Estado de Usuario)
- Definición Drift: `lib/database/tables.dart:479-486`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "app_settings" (
    "settings_pk" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "settings_j_s_o_n" TEXT NOT NULL,
    "date_updated" INTEGER NOT NULL
  );
  ```
- **Contenido:** Cadena JSON con todas las preferencias globales (`selectedWalletPk`, monedas secundarias, tasa de cambio FX personalizada, día de inicio de mes, tema visual, etc.).

### 9. `scanner_templates` (Plantillas de Escaneo de Notificaciones / Correos)
- Definición Drift: `lib/database/tables.dart:489-511`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "scanner_templates" (
    "scanner_template_pk" TEXT NOT NULL PRIMARY KEY,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "template_name" TEXT NOT NULL,
    "contains" TEXT NOT NULL,
    "title_transaction_before" TEXT NOT NULL,
    "title_transaction_after" TEXT NOT NULL,
    "amount_transaction_before" TEXT NOT NULL,
    "amount_transaction_after" TEXT NOT NULL,
    "default_category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "ignore" INTEGER NOT NULL DEFAULT 0 CHECK ("ignore" IN (0, 1)),
    "default_title" TEXT NULL DEFAULT (NULL)
  );
  ```

### 10. `delete_logs` (Registro de Entidades Eliminadas)
- Definición Drift: `lib/database/tables.dart:239-248`.
- DDL en SQLite:
  ```sql
  CREATE TABLE "delete_logs" (
    "delete_log_pk" TEXT NOT NULL PRIMARY KEY,
    "entry_pk" TEXT NOT NULL,
    "type" INTEGER NOT NULL,
    "date_time_modified" INTEGER NOT NULL DEFAULT 1753912320
  );
  ```

### 11 y 12. `tags` y `transaction_to_tag_links` (Etiquetas y Vínculos N:M)
- DDL en SQLite (incorporadas en esquemas v47-v48):
  ```sql
  CREATE TABLE "tags" (
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL,
    "order" INTEGER NOT NULL,
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "tag_pk" TEXT NOT NULL PRIMARY KEY
  );

  CREATE TABLE "transaction_to_tag_links" (
    "transaction_pk" TEXT NULL REFERENCES transactions (transaction_pk),
    "tag_pk" TEXT NULL REFERENCES tags (tag_pk),
    PRIMARY KEY ("transaction_pk", "tag_pk")
  );
  ```

---

## 4. Análisis Comparativo: Pérdida y Aplanamiento de Información en CSV vs SQLite

Al contrastar la exportación plana CSV frente a la base SQLite completa, se evidencia una **pérdida estructural masiva de datos**:

| Dimensión | Formato SQLite (`.sql`) | Formato CSV (`.csv`) | Impacto en la Importación de Monetae |
|---|---|---|---|
| **Transacciones no pagadas / pendientes** | **Preserva todas** (`paid == 0` y `paid == 1`). | **PÉRDIDA TOTAL.** El filtro `tbl.paid.equals(true)` en `exportCSV.dart:88` excluye todas las filas con `paid == false`. | Imposible reconstruir deudas activas impagas o transacciones programadas pendientes. |
| **Identificadores (UUIDs)** | **Conserva todas las PKs y FKs originales** (`transaction_pk`, `wallet_pk`, etc.). | **PÉRDIDA TOTAL.** El CSV no exporta ningún PK/FK; solo exporta nombres textuales. | La reimportación de un CSV no puede ser idempotente sin claves subrogadas artificiales; alto riesgo de duplicación. |
| **Transferencias entre cuentas** | **Preserva el par relacional** mediante `paired_transaction_fk`. | **Aplanadas o divididas** en 2 transacciones independientes (gasto en cuenta A, ingreso en cuenta B). | Pierde el enlace transaccional de contrapartida. |
| **Préstamos (`loans` y `objectives`)** | **Preserva la entidad completa:** capital, estado, balance, fechas, tipo de préstamo (`type = 1`), y los enlaces `objective_loan_fk`. | **PÉRDIDA CASI TOTAL.** Solo exporta el nombre del objetivo en la columna textual `objective`. No exporta capital, intereses ni estado de liquidación. | No permite reconstruir el libro mayor de préstamos de Monetae (`P1-P3`). |
| **Suscripciones y Recurrencias** | **Estructura relacional intacta:** `period_length`, `reoccurrence`, `endDate`, `type = 1`. | **Aplanado a texto.** Exporta únicamente el texto formateado en una columna accesoria `extra` o en notas; pierde la regla de periodicidad tipada. | Requiere parsing frágil de cadenas de texto natural para detectar reglas recurrentes. |
| **Presupuestos y Reglas** | **Preserva la tabla `budgets`:** límites de gasto, periodos, filtros avanzados y `category_budget_limits`. | **PÉRDIDA TOTAL.** Solo exporta el nombre del presupuesto en el que cayó la transacción. No exporta montos asignados ni reglas de presupuesto. | Los presupuestos históricos no se pueden restaurar desde un CSV. |
| **Auto-categorizaciones (`associated_titles`)** | **Preserva todas las reglas** y patrones configurados por el usuario. | **PÉRDIDA TOTAL.** No se exporta ninguna regla de auto-categorización. | Se pierde la heurística personalizada del usuario. |
| **Precisión Numérica de Dinero** | Valores numéricos `REAL` con decimales originales exactos. | Valores formateados a cadena mediante `.toString()`. | Posible truncamiento o problemas de localización de separador decimal (coma vs punto). |
| **Etiquetas (`tags`)** | Preserva entidades y tabla intermedia N:M `transaction_to_tag_links`. | No se exportan etiquetas. | Pérdida total de tags aplicados. |

---

## 5. Recomendación Técnica Argumentada para Monetae

### 5.1 Fuente Principal Recomendada: SQLite binario (`.sql` / `.sqlite`)
Se recomienda categóricamente que **el importador de Monetae (`RF-40a`) utilice como fuente primaria de verdad el archivo SQLite (`.sql`)**.

**Argumentos:**
1. **Fidelidad Absoluta (Zero Data Loss):** Es el único formato que contiene el 100% de las entidades: cuentas, categorías con jerarquía padre/hijo, presupuestos, suscripciones tipadas, metas y préstamos.
2. **Reconstrucción del Libro Mayor de Préstamos (`P1`, `P2`, `P3`):**
   Permite migrar directamente cada `Objective` de tipo `loan` a la tabla `loans` de Monetae, y cada transacción vinculada por `objective_loan_fk` a `loan_movements`, conservando su cuenta de desembolso o pago específica (`wallet_fk`), cumpliendo la especificación `docs/SPEC.md §7`.
3. **Idempotencia Garantizada:**
   Al disponer de los UUIDs originales de Cashew (`transaction_pk`, `wallet_pk`, `category_pk`, `budget_pk`), Monetae puede almacenar `external_id = cashew:<transaction_pk>` en una columna de trazabilidad o índice único. Esto permite reejecutar el importador múltiples veces sobre respaldos incrementales sin duplicar transacciones.
4. **Sencillez de Parseo en Python:**
   Python 3.12 incluye de manera nativa la librería `sqlite3`, lo que permite leer el archivo directamente en memoria o conectarse sin dependencias pesadas adicionales ni riesgo de fallos por dialectos CSV.

### 5.2 Fuente Secundaria / de Respaldo: Archivo CSV (`.csv`)
El formato CSV debe tratarse exclusivamente como un **mecanismo de migración de emergencia o de rescate (`RF-40b`)**, para usuarios que solo tengan a disposición su exportación de transacciones o provenientes de software externo (como Mint o Google Sheets).

---

### 5.3 Estrategia de Idempotencia y Claves de Unicidad

Para evitar duplicaciones durante importaciones sucesivas:
1. **Importación desde SQLite (`.sql`):**
   - Utilizar el identificador primario de Cashew:
     ```python
     # Clave de idempotencia
     idempotency_key = f"cashew:sqlite:{transaction_pk}"
     ```
   - Si ya existe una transacción con dicho `cashew:sqlite:<pk>` para el usuario actual, se ejecuta un `UPDATE` (upsert) o se omite (`DO NOTHING`).
2. **Importación desde CSV (`.csv`):**
   - Dado que el CSV carece de IDs, debe calcularse una clave natural determinística mediante un hash criptográfico SHA-256 de los campos canónicos:
     ```python
     # Clave natural determinística para CSV
     raw_signature = f"{wallet_name}|{date_iso}|{amount_str}|{title.strip().lower()}|{note.strip()}"
     idempotency_hash = hashlib.sha256(raw_signature.encode('utf-8')).hexdigest()
     ```
   - Si existen transacciones legítimas duplicadas en el mismo minuto por el mismo concepto e importe, se añade el índice de fila de la primera ocurrencia dentro del archivo.

---

### 5.4 Mitigación de Riesgos y Versionado de Esquema
1. **Detección de Versión de Esquema:**
   Al procesar el archivo `.sql`, el importador debe consultar primero:
   ```sql
   PRAGMA user_version;
   ```
   - Si `user_version >= 40`: Soporta la estructura completa con `objectives` y préstamos enlazados.
   - Si `user_version < 40`: Requiere un adaptador de compatibilidad para esquemas legados (p. ej. versiones v33-v39 donde `objectives` no existía o no tenía FKs en `transactions`).
2. **Monedas y Tasa FX:**
   Cashew almacena montos en la moneda propia de cada billetera pero no congela el tipo de cambio histórico en cada transacción. Monetae exige `fx_rate_to_base` vigente al registrar la transacción (`AGENTS.md §6.3`). El importador deberá resolver la tasa FX hacia la moneda base (`PEN`) consultando la configuración histórica o asumiendo paridad 1.0 si la cuenta ya está en la moneda base.
3. **Mapeo de Float a Decimal:**
   En SQLite los montos son `REAL`. El importador debe deserializar `amount` convirtiendo primero a cadena (`str(row['amount'])`) y luego instanciando `Decimal(str_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`. Jamás operar aritméticamente con floats intermedios.

---

## 6. Propuesta de Fixture Sintético para Pruebas

Para validar el importador de Monetae sin comprometer ningún dato confidencial de Adrian (`AGENTS.md §8`, `docs/SPEC.md §11`), se define la estructura y reglas para la generación de un **respaldo ficticio sintético**.

### 6.1 Estructura del Fixture Sintético
El fixture consistirá en:
1. `tests/fixtures/synthetic_cashew_backup.sql`: Base de datos SQLite sintética (esquema versión 46-48).
2. `tests/fixtures/synthetic_cashew_export.csv`: Archivo CSV sintético equivalente.

### 6.2 Casos de Prueba Cubiertos por el Fixture Sintético

El fixture sintético debe contener datos inventados que cubran exhaustivamente todas las reglas de negocio de Monetae (`SPEC §7`):

1. **Billeteras / Cuentas Multidivisa:**
   - Cuenta 1: `"BCP Soles"` (`PEN`, 2 decimales).
   - Cuenta 2: `"Interbank Dólares"` (`USD`, 2 decimales).
   - Cuenta 3: `"Efectivo Billetera"` (`PEN`, archivada `archived = 1`).
2. **Categorías con Jerarquía:**
   - Categoría principal de gasto: `"Alimentación"` (`income = 0`, color `#FF5722`).
   - Subcategoría: `"Restaurantes"` (`main_category_pk` apuntando a Alimentación).
   - Categoría principal de ingreso: `"Salario"` (`income = 1`).
3. **Préstamo por Cobrar Otorgado (Ejemplo A de SPEC §7 - Caso Adrian prestó S/ 1,000):**
   - Entidad `objectives`: `name = "Préstamo a Juan"`, `type = 1` (`loan`), `income = 1`, `amount = 1000.0`.
   - Transacción 1 (Desembolso): `amount = -1000.0`, `objective_loan_fk` al objetivo, cuenta BCP Soles.
   - Transacción 2 (Abono parcial): `amount = 500.0`, `objective_loan_fk` al objetivo, cuenta BCP Soles.
   - Saldo calculado esperado: S/ 500.0 pendiente (no liquidado).
4. **Préstamo Liquidado con Diferente Cuenta (Ejemplo C de SPEC §7 - Problema P3):**
   - Entidad `objectives`: `name = "Préstamo a María"`, `type = 1`, `income = 1`, `amount = 200.0`.
   - Transacción 1 (Desembolso inicial): `amount = -200.0`, cuenta BCP Soles.
   - Transacción 2 (Pago recibido en otra cuenta): `amount = 200.0`, cuenta Interbank Dólares.
   - Saldo calculado esperado: 0 (estado `settled`, sin botón "liquidar").
5. **Suscripción Periódica (Problema P4 de Monetae):**
   - Transacción recurrente: `name = "Netflix"`, `type = 1` (`subscription`), `reoccurrence = 3` (`monthly`), `period_length = 1`, `amount = -44.90`.
6. **Transferencia entre Cuentas:**
   - Transacción A: Retiro de BCP Soles (`amount = -100.0`).
   - Transacción B: Depósito en Efectivo (`amount = 100.0`, `paired_transaction_fk` a Transacción A).
7. **Presupuesto Mensual:**
   - Entidad `budgets`: `name = "Presupuesto Mensual Global"`, `amount = 2500.0`, filtros de categorías asignados en `category_fks`.

### 6.3 Reglas de Generación del Fixture
- Todos los identificadores deben ser UUIDs v4 válidos sintéticos (p. ej. `00000000-0000-0000-0000-000000000001`).
- Los timestamps Unix deben corresponder a fechas del año en curso con hora fijada a las 12:00:00 UTC.
- Queda terminantemente prohibido utilizar nombres reales, correos electrónicos o cantidades extraídas de `reference/backups/`.
