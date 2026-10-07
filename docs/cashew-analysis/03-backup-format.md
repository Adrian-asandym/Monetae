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

> **Confirmación de privacidad:** No se extrajo, visualizó ni copió ningún valor financiero real, registro personal, nombre de cuenta o monto privado. Toda la estructura y nombres provienen del DDL de SQLite y del código fuente.

---

## 2. Desfase de Versión: Esquema Drift v46 (Código) vs Respaldo v48 (Base de Datos Real)

### 2.1 Evidencia del Desfase
Existe una divergencia técnica comprobable entre la copia local del código de Cashew disponible en `reference/Cashew/budget/` y el respaldo real de producción:
- En el código fuente (`lib/database/tables.dart:29`), la versión global está fijada en `int schemaVersionGlobal = 46;` y el historial de Drift Schemas (`drift_schemas/`) culmina en `drift_schema_v46.json`.
- En el respaldo real (`reference/backups/cashew-2026-10-05-21-02-50-406966.sql`), la cabecera binaria SQLite (bytes 60-64) y `PRAGMA user_version;` reportan unívocamente **`user_version = 48`**.
- La copia del repositorio en `reference/Cashew/` está **desactualizada** respecto a la versión de la aplicación móvil donde se generó el respaldo.

### 2.2 Diferencias Estructurales de Tablas (DDL v48 vs Código v46)
El DDL del respaldo SQLite contiene **12 tablas de negocio** (excluyendo la tabla interna `sqlite_sequence`):
- **10 tablas presentes en el código Drift (`tables.dart:679-691`) y en `drift_schema_v46.json`:**
  `wallets`, `transactions`, `categories`, `category_budget_limits`, `associated_titles`, `budgets`, `app_settings`, `scanner_templates`, `delete_logs`, `objectives`.
- **2 tablas adicionales presentes ÚNICAMENTE en el DDL del respaldo v48 (ausentes en `@DriftDatabase` de `tables.dart`):**
  1. `tags`: almacena etiquetas definidas por el usuario.
  2. `transaction_to_tag_links`: tabla de unión para relaciones N:M entre transacciones y etiquetas.

| Tabla | En `drift_schema_v46.json` / `tables.dart` | En DDL Respaldo (`user_version = 48`) | Estado |
|---|---|---|---|
| `wallets` | Sí | Sí | Coincide (con columnas añadidas) |
| `categories` | Sí | Sí | Coincide (con columna añadida) |
| `objectives` | Sí | Sí | Idéntica |
| `transactions` | Sí | Sí | Idéntica |
| `budgets` | Sí | Sí | Idéntica |
| `category_budget_limits` | Sí | Sí | Idéntica |
| `associated_titles` | Sí | Sí | Coincide (con columna añadida) |
| `app_settings` | Sí | Sí | Idéntica |
| `scanner_templates` | Sí | Sí | Coincide (con columna añadida) |
| `delete_logs` | Sí | Sí | Idéntica |
| `tags` | **No** | **Sí** | **Añadida en v47/v48** |
| `transaction_to_tag_links` | **No** | **Sí** | **Añadida en v47/v48** |

### 2.3 Diferencias de Columnas por Tabla (DDL v48 vs Código v46)
Comparando `drift_schema_v46.json` contra las columnas del DDL extraídas de `sqlite_master`:

| Tabla | Columnas añadidas en Respaldo v48 (Ausentes en código v46) | Columnas eliminadas |
|---|---|---|
| `wallets` | `archived` (`INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1))`), `emoji_icon_name` (`TEXT NULL`) | Ninguna |
| `categories` | `archived` (`INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1))`) | Ninguna |
| `associated_titles` | `archived` (`INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1))`) | Ninguna |
| `scanner_templates` | `default_title` (`TEXT NULL DEFAULT NULL`) | Ninguna |
| `tags` (nueva) | `tag_pk`, `name`, `colour`, `icon_name`, `emoji_icon_name`, `date_created`, `date_time_modified`, `order`, `archived` | N/A |
| `transaction_to_tag_links` (nueva)| `transaction_pk`, `tag_pk` | N/A |

### 2.4 Diferencias en Cabecera CSV vs Código `exportCSV.dart`
- **Cabecera exportada según código `exportCSV.dart:110-140` (15 columnas):**
  `account`, `amount`, `currency`, `title`, `note`, `date`, `income`, `type`, `category name`, `subcategory name`, `color`, `icon`, `emoji`, `budget`, `objective`.
- **Cabecera en archivo real `reference/backups/cashew-2026-10-06-18-17-57-084794.csv` (17 columnas):**
  `account,amount,amount unpaid,currency,title,note,date,income,type,category name,subcategory name,color,icon,emoji,budget,objective,extra`
- **Columnas no generadas por el código disponible en `reference/`:**
  - `amount unpaid`: Ausente en `exportCSV.dart` del commit actual. Representa un cálculo de saldo pendiente exportado en versiones posteriores de Cashew.
  - `extra`: Ausente en `exportCSV.dart`. Contiene cadenas de texto con resúmenes de periodicidad/fechas de repetición formateadas para visualización.
  - Esto confirma que el ejecutable de Cashew del cual Adrian obtuvo el CSV corresponde a una versión compilada más reciente que el código en `reference/`.

### 2.5 Impacto en el Importador de Monetae
1. **Detección dinámica de versión:** El importador debe consultar `PRAGMA user_version;` al abrir la base SQLite.
2. **Tolerancia a esquemas evolutivos (Forward-compatibility):** Al mapear tablas con SQLAlchemy/Pydantic, el importador debe consultar dinámicamente las columnas existentes vía `PRAGMA table_info` o inspección reflectiva, ignorando silenciosamente columnas accesorias desconocidas o mapeando `archived` si existe.
3. **Manejo de Etiquetas (`tags`):** En esquemas v48, el importador puede migrar las etiquetas a tags de Monetae si se habilitan en el dominio, o ignorar la tabla si no es requerida en V1.

> [!WARNING] **Decisión pendiente de Adrian**  
> Se recomienda actualizar la copia de `reference/Cashew/` en el repositorio a la versión de código fuente o tag correspondiente a la versión 48 de la base de datos de Cashew. Esto garantizará que el código analizado coincida exactamente con la aplicación móvil en producción utilizada para los respaldos.

---

## 3. Esquema de los Formatos y Codificaciones

### 3.1 Unidad y Codificación de Fechas (`DateTime`)

#### Análisis Técnico de Configuración y Código
1. **Configuración de Drift (`build.yaml` y dependencias):**
   - Se verificó que **no existe ningún archivo `build.yaml`** en `reference/Cashew/budget/` (`[Verificado en código]`).
   - Drift utiliza por defecto la representación numérica en enteros SQLite (`INTEGER`) para columnas declaradas mediante `dateTime()`.
   - La opción de guardar fechas como cadenas ISO-8601 (`store_date_time_values_as_text`) **no está activada** (`[Verificado en código]`).
2. **DDL de SQLite:**
   Todas las columnas temporales (`date_created`, `date_time_modified`, `original_date_due`, `end_date`, `start_date`, `date_updated`) están declaradas como `INTEGER` (`[Verificado en DDL]`).
3. **Escala y Unidad de Medida:**
   - En Drift estándar para Dart/Flutter sin conversores personalizados, `dateTime()` serializa objetos `DateTime` a **segundos Unix epoch** (o milisegundos en configuraciones JS/Web) (`[Verificado en especificación de Drift / Código Dart]`).
   - Por ejemplo, en el DDL de migraciones (`tables.dart:952-1168`), los valores por defecto asignados por Drift a `date_time_modified` aparecen como enteros de 10 dígitos (p. ej. `1753912320`), lo cual corresponde exactamente a **segundos Unix epoch** (10 dígitos representan años en el rango 1970–2038+).
4. **Regla de Inferencia Robusta para el Importador (`[Inferencia]`):**
   Para garantizar que el importador maneje cualquier respaldo (sea originado en cliente móvil nativo o en cliente web/IndexedDB con serializaciones de distinta escala), se establece la siguiente regla algorítmica de detección por magnitud:
   ```python
   def parse_cashew_timestamp(val: int | None) -> datetime | None:
       if val is None:
           return None
       # Si el valor tiene magnitud de segundos (< 1e11, aprox. hasta el año 5138)
       if val < 100_000_000_000:
           return datetime.fromtimestamp(val, tz=timezone.utc)
       # Si tiene magnitud de milisegundos (< 1e14)
       elif val < 100_000_000_000_000:
           return datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
       # Si tiene magnitud de microsegundos
       else:
           return datetime.fromtimestamp(val / 1_000_000.0, tz=timezone.utc)
   ```

---

### 3.2 Otras Codificaciones y Tipos
- **Identificadores (PK/FK):** `TEXT` conteniendo UUID v4 en formato canónico de 36 caracteres con guiones (`uuid.v4()`, `[Verificado en código: tables.dart:240, 252, 275]`). Excepción: `wallet_fk = '0'` representa la billetera inicial/por defecto.
- **Booleanos:** `INTEGER` con restricción `CHECK (columna IN (0, 1))`. `0 = false`, `1 = true` (`[Verificado en código y DDL]`).
- **Montos Monetarios:** `REAL` (coma flotante IEEE 754 de 64 bits en SQLite, `[Verificado en código: tables.dart:281, 426, 519]`). Monetae debe convertirlos inmediatamente a `Decimal` de precisión fija redondeando a 2 decimales (`ROUND_HALF_UP`).
- **Listas JSON en columnas de texto:** Convertidores como `StringListInColumnConverter` (`tables.dart:185-199`) y `BudgetTransactionFiltersListInColumnConverter` (`tables.dart:145-163`) serializan arrays como cadenas JSON (ej. `["uuid1", "uuid2"]` o `[0, 1, 2]`).

---

### 3.3 Esquema Detallado de Tablas SQLite (12 Tablas)

#### 1. `wallets` (10 cols en código v46; 12 cols en DDL v48)
- Código Drift: `lib/database/tables.dart:251-271`.
- DDL en v48:
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

#### 2. `categories` (10 cols en código v46; 11 cols en DDL v48)
- Código Drift: `lib/database/tables.dart:343-373`.
- DDL en v48:
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

#### 3. `objectives` (15 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:515-539`.
- DDL en v48:
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

#### 4. `transactions` (31 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:274-340`.
- DDL en v48:
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

#### 5. `budgets` (27 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:423-475`.
- DDL en v48:
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

#### 6. `category_budget_limits` (6 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:376-388`.
- DDL en v48:
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

#### 7. `associated_titles` (7 cols en código v46; 8 cols en DDL v48)
- Código Drift: `lib/database/tables.dart:395-408`.
- DDL en v48:
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

#### 8. `app_settings` (3 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:479-486`.
- DDL en v48:
  ```sql
  CREATE TABLE "app_settings" (
    "settings_pk" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "settings_j_s_o_n" TEXT NOT NULL,
    "date_updated" INTEGER NOT NULL
  );
  ```

#### 9. `scanner_templates` (12 cols en código v46; 13 cols en DDL v48)
- Código Drift: `lib/database/tables.dart:489-511`.
- DDL en v48:
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

#### 10. `delete_logs` (4 cols en código v46 y DDL v48)
- Código Drift: `lib/database/tables.dart:239-248`.
- DDL en v48:
  ```sql
  CREATE TABLE "delete_logs" (
    "delete_log_pk" TEXT NOT NULL PRIMARY KEY,
    "entry_pk" TEXT NOT NULL,
    "type" INTEGER NOT NULL,
    "date_time_modified" INTEGER NOT NULL DEFAULT 1753912320
  );
  ```

#### 11. `tags` (Solo en DDL v48, ausente en código v46)
- DDL en v48:
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
  ```

#### 12. `transaction_to_tag_links` (Solo en DDL v48, ausente en código v46)
- DDL en v48:
  ```sql
  CREATE TABLE "transaction_to_tag_links" (
    "transaction_pk" TEXT NULL REFERENCES transactions (transaction_pk),
    "tag_pk" TEXT NULL REFERENCES tags (tag_pk),
    PRIMARY KEY ("transaction_pk", "tag_pk")
  );
  ```

---

## 4. Análisis Comparativo: Pérdida y Aplanamiento en CSV frente a SQLite

| Dimensión | Formato SQLite (`.sql`) | Formato CSV (`.csv`) | Impacto en Monetae |
|---|---|---|---|
| **Transacciones no pagadas / pendientes** | **Preserva todas** (`paid == 0` y `paid == 1`). | **PÉRDIDA TOTAL.** El filtro `tbl.paid.equals(true)` en `exportCSV.dart:88` omite todas las filas con `paid == false`. | Imposible recuperar deudas activas impagas ni transacciones programadas pendientes. |
| **Identificadores (UUIDs)** | **Conserva todas las PKs y FKs originales** (`transaction_pk`, `wallet_pk`, etc.). | **PÉRDIDA TOTAL.** El CSV no exporta ningún PK/FK; solo exporta nombres textuales. | La reimportación de un CSV no puede ser idempotente sin claves subrogadas artificiales; alto riesgo de duplicación. |
| **Transferencias entre cuentas** | **Preserva el par relacional** mediante `paired_transaction_fk`. | **Aplanadas o divididas** en 2 transacciones independientes. | Pierde el enlace transaccional de contrapartida. |
| **Préstamos (`loans` y `objectives`)** | **Preserva la entidad completa:** capital, estado, balance, fechas, tipo de préstamo (`type = 1`), y los enlaces `objective_loan_fk`. | **PÉRDIDA CASI TOTAL.** Solo exporta el nombre del objetivo en la columna textual `objective`. No exporta capital, intereses ni estado de liquidación. | No permite reconstruir el libro mayor de préstamos de Monetae (`P1-P3`). |
| **Suscripciones y Recurrencias** | **Estructura relacional intacta:** `period_length`, `reoccurrence`, `endDate`, `type = 1`. | **Aplanado a texto.** En versiones recientes exporta una columna accesoria `extra` con texto de periodicidad localizado (o notas); pierde la regla de periodicidad tipada. | Requiere parsing frágil de cadenas de texto natural para detectar reglas recurrentes. |
| **Presupuestos y Reglas** | **Preserva la tabla `budgets`:** límites de gasto, periodos, filtros avanzados y `category_budget_limits`. | **PÉRDIDA TOTAL.** Solo exporta el nombre del presupuesto en el que cayó la transacción. | Los presupuestos históricos no se pueden restaurar desde un CSV. |
| **Auto-categorizaciones (`associated_titles`)** | **Preserva todas las reglas** y patrones configurados por el usuario. | **PÉRDIDA TOTAL.** No se exporta ninguna regla de auto-categorización. | Se pierde la heurística personalizada del usuario. |
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
   Al disponer de los UUIDs originales de Cashew (`transaction_pk`, `wallet_pk`, `category_pk`, `budget_pk`), Monetae puede almacenar `external_id = cashew:sqlite:<transaction_pk>` en una columna de trazabilidad con índice único. Esto permite reejecutar el importador múltiples veces sobre respaldos incrementales sin duplicar transacciones.
4. **Sencillez de Parseo en Python:**
   Python 3.12 incluye de manera nativa la librería `sqlite3`, lo que permite leer el archivo directamente sin dependencias pesadas adicionales ni riesgo de fallos por dialectos CSV.

---

### 5.2 Fuente Secundaria: Archivo CSV (`.csv`) y Contradicción con AGENTS.md

> [!IMPORTANT] **Decisión pendiente de Adrian: SQLite vs CSV en AGENTS.md §4**  
> `AGENTS.md §4` indica:
> > *"backups/ # respaldos reales de Adrian (preferible usa el .csv por si los demás no los puedes procesar)"*  
> 
> Sin embargo, el análisis técnico del código de Cashew demuestra una limitación crítica:
> `lib/widgets/exportCSV.dart:88` aplica estrictamente `tbl.paid.equals(true)`. Esto implica que:
> 1. Todas las deudas activas o préstamos únicos pendientes se exportan con `paid = false` cuando están vigentes, o mutan a `paid = false` cuando se liquidan en Cashew (`upcomingTransactionsFunctions.dart:393`).
> 2. **Cualquier transacción con `paid = false` es excluida por completo del CSV.**  
> 3. Los préstamos y deudas desaparecen del CSV, reproduciendo e intensificando el problema **P1**.
> 
> **Recomendación:** Mantener SQLite (`.sql`) como fuente primaria mandataria para la importación completa (`RF-40a`). El soporte CSV debe implementarse únicamente como un importador secundario de rescate/transacciones simples (`RF-40b`), advirtiendo al usuario que no restaurará presupuestos, suscripciones ni préstamos.

---

### 5.3 Estrategia de Idempotencia y Claves de Unicidad
1. **Importación desde SQLite (`.sql`):**
   ```python
   # Clave de idempotencia determinística
   idempotency_key = f"cashew:sqlite:{transaction_pk}"
   ```
   Si ya existe un registro con dicha clave externa para el `user_id`, se ejecuta un `UPSERT` o se omite (`DO NOTHING`).
2. **Importación desde CSV (`.csv`):**
   Dado que el CSV carece de IDs, debe calcularse un hash SHA-256 de campos canónicos:
   ```python
   raw_signature = f"{wallet_name}|{date_iso}|{amount_str}|{title.strip().lower()}|{note.strip()}"
   idempotency_hash = hashlib.sha256(raw_signature.encode('utf-8')).hexdigest()
   ```

---

## 6. Propuesta de Fixture Sintético para Pruebas

Para validar el importador de Monetae sin utilizar datos confidenciales reales (`AGENTS.md §8`, `docs/SPEC.md §11`), se define la estructura y reglas de un fixture sintético (`tests/fixtures/synthetic_cashew_backup.sql`).

El fixture representará fielmente cómo Cashew almacena en su esquema Drift los casos descritos en `docs/SPEC.md §7` (Ejemplos A a E), más suscripciones, transferencias y presupuestos.

### 6.1 Catálogo Base Sintético
- **Cuentas (`wallets`):**
  - `wallet-1`: `"BCP Soles"` (Moneda: `PEN`, `decimals: 2`).
  - `wallet-2`: `"Interbank Dólares"` (Moneda: `USD`, `decimals: 2`).
  - `wallet-3`: `"Efectivo"` (Moneda: `PEN`, `decimals: 2`).
  - `wallet-4`: `"Yape"` (Moneda: `PEN`, `decimals: 2`).
- **Categorías (`categories`):**
  - `cat-1`: `"Alimentación"` (`income = 0`, color `#FF5722`).
  - `cat-2`: `"Restaurantes"` (`income = 0`, `main_category_pk = cat-1`).
  - `cat-3`: `"Intereses"` (`income = 0`, categoría para intereses de préstamos).
  - `cat-4`: `"Servicios"` (`income = 0`, para suscripciones).
  - `cat-5`: `"Salario"` (`income = 1`, ingresos laborales).

---

### 6.2 Representación de los Ejemplos de Préstamos (SPEC §7) en el Esquema de Cashew

#### 1. Ejemplo A: Préstamo recibido con interés del 5 % (SPEC §7)
- **Historia:** Carlos me presta S/ 200 en Efectivo. Interés del 5 % (S/ 10). Pago S/ 100 desde BCP y S/ 110 desde Efectivo (total S/ 210 pagados).
- **Representación en Cashew:**
  - `objectives`: Fila con `name: "Carlos"`, `type: 1` (`loan`), `income: false` (`borrowed`), `amount: 0.0`, `wallet_fk: wallet-3`.
  - `transactions` (Desembolso inicial): `amount: 200.0`, `income: true`, `wallet_fk: wallet-3` (Efectivo), `objective_loan_fk: objective_carlos_pk`.
  - `transactions` (Pago 1): `amount: -100.0`, `income: false`, `wallet_fk: wallet-1` (BCP), `objective_loan_fk: objective_carlos_pk`.
  - `transactions` (Pago 2): `amount: -110.0`, `income: false`, `wallet_fk: wallet-3` (Efectivo), `objective_loan_fk: objective_carlos_pk`.
  - `transactions` (Interés - Transacción normal huérfana en Cashew, origen de P2): `amount: -10.0`, `income: false`, `category_fk: cat-3` (Intereses), `objective_loan_fk: NULL`.
- **Clasificación para Monetae:** Caso con amortización acumulada de 210 vs capital de 200. **Marcado como Caso Ambiguo 2 y 3 para revisión manual** (sobrepago de S/ 10 y transacción de interés huérfana).

#### 2. Ejemplo B: Préstamo otorgado desde un medio y cobrado por otros (SPEC §7, Problemas P1 y P3)
- **Historia:** Presto S/ 500 desde Yape a Roberto. Roberto me paga S/ 300 en Efectivo y S/ 200 en BCP.
- **Representación en Cashew:**
  - `objectives`: Fila con `name: "Roberto"`, `type: 1` (`loan`), `income: true` (`lent`), `amount: 0.0`, `wallet_fk: wallet-4` (Yape).
  - `transactions` (Desembolso): `amount: -500.0`, `income: false`, `wallet_fk: wallet-4` (Yape), `objective_loan_fk: objective_roberto_pk`.
  - `transactions` (Cobro parcial 1): `amount: 300.0`, `income: true`, `wallet_fk: wallet-3` (Efectivo), `objective_loan_fk: objective_roberto_pk`.
  - `transactions` (Cobro parcial 2): `amount: 200.0`, `income: true`, `wallet_fk: wallet-1` (BCP), `objective_loan_fk: objective_roberto_pk`.
- **Clasificación para Monetae:** Caso perfectamente estructurado en Cashew a largo plazo. Al importar, genera 1 préstamo en `loans` y 3 movimientos en `loan_movements` con sus respectivas cuentas independientes.

#### 3. Ejemplo C: Préstamo en USD cobrado en PEN con tipo de cambio (SPEC §7)
- **Historia:** Presto US$ 100 desde Interbank Dólares a Daniel. Daniel paga S/ 380 en BCP Soles con tipo de cambio pactado 3.80.
- **Representación en Cashew:**
  - `objectives`: Fila con `name: "Daniel"`, `type: 1` (`loan`), `income: true` (`lent`), `wallet_fk: wallet-2` (Interbank Dólares).
  - `transactions` (Desembolso USD): `amount: -100.0`, `income: false`, `wallet_fk: wallet-2` (USD), `objective_loan_fk: objective_daniel_pk`.
  - `transactions` (Cobro PEN): `amount: 380.0`, `income: true`, `wallet_fk: wallet-1` (PEN), `objective_loan_fk: objective_daniel_pk`.
- **Clasificación para Monetae:** **Marcado como Caso Ambiguo para revisión manual**. Cashew suma directamente `380` con `-100` sin conversión de divisa nativa en el objetivo, produciendo distorsión de balance. El importador debe detectar el cambio de moneda entre la cuenta USD y la cuenta PEN y requerir confirmación de la tasa 3.80.

#### 4. Ejemplo D: Pago mayor al saldo (SPEC §7)
- **Historia:** Saldo pendiente US$ 50 con Lucía. Se recibe un pago de US$ 60 (exceso de US$ 10).
- **Representación en Cashew:**
  - `objectives`: Fila con `name: "Lucía"`, `type: 1` (`loan`), `income: true` (`lent`), `wallet_fk: wallet-2` (USD).
  - `transactions` (Desembolso): `amount: -50.0`, `income: false`, `wallet_fk: wallet-2`.
  - `transactions` (Cobro en exceso): `amount: 60.0`, `income: true`, `wallet_fk: wallet-2`.
- **Clasificación para Monetae:** **Marcado como Caso Ambiguo 2 para revisión manual** (`sum(pagos) > principal`).

#### 5. Ejemplo E: Pagos pequeños y variables (SPEC §7)
- **Historia:** Préstamo de S/ 1,000 a Manuel. Pagos escalonados de S/ 50, S/ 120, S/ 30 y S/ 800 en fechas distintas hasta llegar a saldo 0.
- **Representación en Cashew:**
  - `objectives`: Fila con `name: "Manuel"`, `type: 1` (`loan`), `income: true`, `wallet_fk: wallet-1`.
  - `transactions` (Desembolso): `amount: -1000.0`.
  - `transactions` (Abonos 1..4): 4 transacciones con `amount: 50.0`, `120.0`, `30.0` y `800.0`, todas con `objective_loan_fk: objective_manuel_pk`.
- **Clasificación para Monetae:** Flujo determinístico directo hacia `loans` y `loan_movements`. Saldo final 0 (`settled`).

#### 6. Préstamo Único Liquidado en Cashew (Variante de Pago Único, Origen de P1)
- **Historia:** Préstamo puntual a Fernando por S/ 150 que en Cashew fue marcado con el botón "Settle".
- **Representación en Cashew:**
  - `transactions`: Fila única con `name: "Préstamo Fernando"`, `type: 3` (`credit`), `amount: -150.0`, `paid: 0` (`paid: false`, desactivado por `settleTransactions`). Sin fila en `objectives`.
- **Clasificación para Monetae:** **Marcado como Caso Ambiguo 1 para revisión manual** (requiere sintetizar el movimiento de pago al no existir contrapartida en Cashew).

---

### 6.3 Suscripciones, Transferencias y Presupuestos en el Fixture

#### 7. Suscripción Periódica (SPEC §8 y tables.dart:42, 303-306)
- **Parámetros verificados contra `BudgetReoccurence` (`tables.dart:42`):**
  - `0`: custom, `1`: daily, `2`: weekly, `3`: monthly, `4`: yearly.
- **Representación en Cashew:**
  - `transactions`: `name: "Servicio de Streaming"`, `amount: -44.90`, `income: false`, `wallet_fk: wallet-1`, `type: 1` (`TransactionSpecialType.subscription`), `reoccurrence: 3` (`monthly`), `period_length: 1`, `category_fk: cat-4`, `paid: 1`.

#### 8. Transferencia entre Cuentas
- **Representación en Cashew:**
  - `tx-transf-1`: Retiro de BCP Soles (`amount: -200.0`, `income: false`, `wallet_fk: wallet-1`, `paired_transaction_fk: tx-transf-2`).
  - `tx-transf-2`: Depósito en Efectivo (`amount: 200.0`, `income: true`, `wallet_fk: wallet-3`, `paired_transaction_fk: tx-transf-1`).

#### 9. Presupuesto Mensual
- **Representación en Cashew:**
  - `budgets`: `budget_pk: b-1`, `name: "Presupuesto Mensual"`, `amount: 2500.0`, `period_length: 1`, `reoccurrence: 3` (`monthly`), `category_fks: '["cat-1", "cat-4"]'`.

---

### 6.4 Reglas para Generar el Archivo Ficticio
1. **Identificadores determinísticos:** UUIDs sintéticos canónicos (ej. `00000000-0000-0000-0000-000000000001`).
2. **Timestamps:** Enteros en segundos Unix correspondientes a fechas controladas de 2026 a las 12:00:00 UTC.
3. **Privacidad absoluta:** Ningún nombre, cuenta o cifra real; exclusivamente las personas ficticias Carlos, Roberto, Daniel, Lucía, Manuel y Fernando.
