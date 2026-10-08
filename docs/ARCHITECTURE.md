# ARCHITECTURE.md — Monetae

> Versión 0.3 · 2026-10-07 · Autor: Claude (T-101) · Estado: revisado por Adrian; v0.3 incorpora precisiones de nulabilidad e índices surgidas en T-203
> Fuente funcional: `docs/SPEC.md` v0.3. Reglas de código: `AGENTS.md`. Decisiones: `docs/decisions/`.
> El esquema de este documento es el **contrato de datos** de la Fase 2; las migraciones Alembic lo implementan. Si el código necesita desviarse, se cambia primero este documento.

---

## 1. Visión general

```mermaid
flowchart LR
  subgraph Cliente
    WEB["apps/web<br/>Flutter Web (UI propia, ADR-001)"]
  end
  subgraph Servidor["Docker Compose"]
    API["services/api<br/>FastAPI /api/v1"]
    DB[("PostgreSQL")]
  end
  EXT1["Proveedor de tipo de cambio<br/>(opcional, ADR-004)"]
  EXT2["Google OIDC<br/>(login, ADR-002)"]
  WEB -- "HTTPS + cookie HttpOnly" --> API
  API --> DB
  API -. "solo par de monedas" .-> EXT1
  API -- "authorization code + PKCE" --> EXT2
```

Reservado, sin implementar en V1: `services/bot` (Telegram), `services/ml` (clasificador), asistente MCP, app Android (SPEC §3, §13).

## 2. Decisiones vinculantes

| ADR | Decisión |
|-----|----------|
| 001 | UI propia en Flutter Web que reutiliza y desacopla widgets de Cashew; consume solo la API |
| 002 | Sesión en servidor (cookie `HttpOnly`, `Secure`, `SameSite=Lax`), Google OIDC + correo/contraseña (argon2id); tokens de dispositivo en V2–V4 |
| 003 | Interés en base caja; cada pago se reparte primero a interés y luego a capital, y se guarda el reparto |
| 004 | Tipo de cambio manual manda; sugerencia automática tras la interfaz `RateProvider` |
| 006 | Bloqueo de app: PIN primero, WebAuthn opcional después (barrera de comodidad) |
| 007 | SQLAlchemy 2.0 síncrono + psycopg 3; endpoints `def` |

## 3. Capas y dependencias (`services/api/src/monetae/`)

```
domain/      reglas puras: Money, préstamos, suscripciones, presupuestos, FX. Sin I/O.
db/          modelos SQLAlchemy (Mapped[...]), repositorios, migraciones Alembic.
api/         routers, schemas Pydantic v2 estricto, dependencias (sesión, usuario actual).
importers/   importador de Cashew (lee SQLite en solo lectura).
reports/     consultas agregadas (SQL) para gráficos y herramientas futuras.
```

- `domain` no importa de `api`, `db` ni `importers`. `api`, `db`, `importers` y `reports` dependen de `domain`.
- **Los routers no contienen reglas de negocio:** validan, llaman a un servicio de aplicación y serializan. Un *servicio de aplicación* carga datos con repositorios, invoca funciones de `domain` y persiste.
- **Puertos** (interfaces definidas en `domain`, implementadas fuera): `RateProvider` (tipo de cambio), `Clock` (tiempo inyectable para pruebas), y los repositorios.
- Toda operación de repositorio recibe `user_id` obligatorio; no existe una consulta de negocio sin él (AGENTS.md §6.9). Defensa en profundidad con *Row Level Security* de PostgreSQL: **se evalúa en la Fase 7**, no es requisito de V1.
- Endpoints con `def` (ADR-007). Prohibido bloquear dentro de `async def`.

## 4. Convenciones de datos

| Tema | Regla |
|------|-------|
| Identificadores | `uuid` v4 como PK. Las tablas de negocio llevan `user_id uuid NOT NULL` con FK a `users` |
| Columnas comunes | `id`, `user_id`, `created_at timestamptz`, `updated_at timestamptz`, `deleted_at timestamptz NULL` (borrado lógico). En las tablas siguientes se omiten salvo excepción |
| Dinero | `NUMERIC(18,2)`; nunca `float`. En Python `Decimal`/`Money`, redondeo `ROUND_HALF_UP` |
| Tipo de cambio | `NUMERIC(18,6)` |
| Moneda | `char(3)` ISO 4217 en mayúsculas (`CHECK (currency = upper(currency))`) |
| Tiempo | `timestamptz` en UTC; fechas sin hora como `date`; presentación en `America/Lima` |
| Enumeraciones | `text` con `CHECK (col IN (...))` (más fácil de migrar que `ENUM` de PostgreSQL) |
| Unicidad con borrado lógico | Índices únicos **parciales** `WHERE deleted_at IS NULL` |
| Saldos y estados | Se **calculan** (vistas/consultas), no se guardan como verdad (AGENTS.md §6.8) |
| Actualización | `updated_at` se fija en cada escritura (útil para ADR-005/V4) |

## 5. Esquema de base de datos

### 5.1 Diagrama (entidades centrales)

```mermaid
erDiagram
  users ||--o{ accounts : tiene
  users ||--o{ categories : tiene
  users ||--o{ people : tiene
  accounts ||--o{ transactions : registra
  categories ||--o{ transactions : clasifica
  categories ||--o{ categories : "subcategoría"
  transactions ||--o{ transaction_tags : etiquetada
  tags ||--o{ transaction_tags : etiqueta
  people ||--o{ loans : "participa"
  loans ||--o{ loan_movements : "libro mayor"
  transactions ||--o| loan_movements : "mueve dinero"
  subscriptions ||--o| recurring_rules : "se programa con"
  recurring_rules ||--o{ transactions : genera
  budgets ||--o{ budget_categories : limita
  budgets ||--o{ budget_transactions : incluye
  goals ||--o{ goal_transactions : incluye
  transactions ||--o{ budget_transactions : ""
  transactions ||--o{ goal_transactions : ""
```

### 5.2 Identidad y acceso

**`users`** (no lleva `user_id`; su `id` es el usuario)
| Columna | Tipo | Notas |
|---------|------|-------|
| email | `text NOT NULL` | único parcial en `lower(email)` |
| password_hash | `text NULL` | argon2id; NULL si solo entra con Google |
| google_sub | `text NULL` | único parcial; vinculación solo con correo verificado (ADR-002) |
| timezone | `text NOT NULL DEFAULT 'America/Lima'` | |
| base_currency | `char(3) NOT NULL DEFAULT 'PEN'` | moneda de reporte por defecto |
| locale | `text NOT NULL DEFAULT 'es'` | `es`/`en` |
| pin_hash | `text NULL` | argon2id (ADR-006) |
| pin_failed_attempts | `int NOT NULL DEFAULT 0` | a los 5 se exige login completo |
| lock_after_minutes | `int NULL` | inactividad para bloquear; NULL = sin bloqueo |
| report_currency | `char(3) NOT NULL` | moneda de reporte seleccionada; **sin default de servidor**: la capa de servicio la fija igual a `base_currency` al crear el usuario |
| preferences | `jsonb NOT NULL DEFAULT '{}'` | presentación (RF-38/39): `theme` (`light`/`dark`/`system`), `accent_color`, widgets de inicio y su orden. Se valida con un modelo Pydantic estricto en el borde; no se consulta por SQL |

`base_currency` es **inmutable en cuanto el usuario tiene su primera transacción** (así `fx_rate_to_base` siempre se refiere a la misma moneda). Cambiar de base sería una migración de datos, fuera de V1. La moneda de reporte sí se puede cambiar libremente.

**`sessions`**
| Columna | Tipo | Notas |
|---------|------|-------|
| token_hash | `bytea NOT NULL` | SHA-256 del token de la cookie; el token en claro nunca se guarda |
| last_seen_at, expires_at | `timestamptz` | expiración por inactividad y absoluta |
| user_agent, ip | `text` | para listar dispositivos |
| revoked_at | `timestamptz NULL` | "cerrar sesión en todos los dispositivos" revoca todas las del usuario |

Índice único en `token_hash`; índice `(user_id, revoked_at)`.

**`webauthn_credentials`** *(Fase 6)*: `credential_id bytea UNIQUE`, `public_key bytea`, `sign_count bigint`, `label text`.

### 5.3 Cuentas, categorías, personas, etiquetas

**`accounts`**: `name`, `type` ∈ {`cash`,`bank`,`wallet`,`card`,`other`}, `currency char(3)`, `initial_balance NUMERIC(18,2) DEFAULT 0`, `color`, `icon`, `sort_order int`, `archived_at`.
- `UNIQUE (id, currency)` (para la FK compuesta de `transactions`).
- Único parcial `(user_id, lower(name))` entre cuentas no borradas.
- **Saldo actual** = `initial_balance + SUM(transactions.amount)` de las transacciones `posted` no borradas (RF-02). No existe columna de saldo.

**`categories`**: `parent_id uuid NULL → categories`, `kind` ∈ {`income`,`expense`}, `name`, `icon`, `color`, `is_system bool`, `system_key text NULL`.
- Un solo nivel de subcategorías: `parent_id` debe apuntar a una categoría sin padre, del mismo `kind` y del **mismo `user_id`** (validado en dominio y con trigger de respaldo). El trigger también revalida a los hijos cuando cambia el `kind` o el `parent_id` de un padre y rechaza el cambio que los invalide.
- `is_system` ⇔ `system_key IS NOT NULL` (`CHECK`); `is_system` `DEFAULT false`. (`accounts` y `tags` llevan `sort_order int NOT NULL DEFAULT 0`; `categories` **no** lo tiene todavía, ver §10.)
- Categorías de sistema de interés: `system_key` ∈ {`interest_income`, `interest_expense`}; únicas por usuario; no editables ni borrables. Se crean al registrar al usuario.

**`people`**: `name`, `aliases text[] NOT NULL DEFAULT '{}'`, `note`. Índice GIN en `aliases` y **B-tree** en `lower(name)` (búsqueda exacta por nombre o alias, RF-23; una búsqueda parcial/difusa exigiría `pg_trgm`, no incluido en V1).

**`tags`**: `name`, `color`, `icon`, `emoji`, `sort_order`, `archived_at`. Único parcial `(user_id, lower(name))` entre no archivadas ni borradas (RF-43).

**`transaction_tags`**: `transaction_id`, `tag_id`, columnas comunes (con `deleted_at`: quitar una etiqueta es borrado lógico, RF-44). Único parcial `(transaction_id, tag_id) WHERE deleted_at IS NULL`. Índice `(user_id, tag_id)` para el filtro (RF-45).

### 5.4 Transacciones

**`transactions`** (todo movimiento real de dinero en una cuenta)
| Columna | Tipo | Notas |
|---------|------|-------|
| account_id, currency | `uuid`, `char(3)` | **FK compuesta** `(account_id, currency) → accounts(id, currency)`: la moneda es siempre la de la cuenta |
| kind | `text` | `income`, `expense`, `transfer`, `loan` |
| amount | `NUMERIC(18,2) NOT NULL` | **con signo**: positivo = entra a la cuenta, negativo = sale; nunca 0 |
| category_id | `uuid NULL` | NULL en `transfer` y `loan` |
| occurred_at | `timestamptz` | |
| status | `text` | `posted` (cuenta en saldos) o `scheduled` (próxima, RF-09; no cuenta hasta que ocurre) |
| title, note | `text` | |
| fx_rate_to_base | `NUMERIC(18,6) NOT NULL` | 1 si la moneda es la base; **fijo al registrar, no se recalcula** (SPEC §9.2) |
| fx_rate_source | `text` | `manual` / `auto` |
| transfer_group_id | `uuid NULL` | enlaza las dos patas de una transferencia (mismo `kind='transfer'`, montos reales en ambas monedas) |
| recurring_rule_id | `uuid NULL` | regla que lo generó |
| source | `text` | `web`, `import`, `telegram`, `api` |
| raw_input | `text NULL` | texto original (V2) |
| categorization_source | `text NULL` | `manual`, `rule`, `model`, `llm` (V2) |
| is_initial_data | `bool DEFAULT false` | marca ago–oct 2025 importados (RF-40e) |
| import_external_id | `text NULL` | p. ej. `cashew:sqlite:<transaction_pk>`; único parcial por usuario (idempotencia, RF-40b) |

Restricciones: `CHECK (amount <> 0)`. `category_id` es **nullable** en todos los tipos (se pueden registrar movimientos sin categoría y sugerirla después con reglas); la API exige categoría solo donde el producto lo decida. Una transferencia tiene exactamente 2 filas por `transfer_group_id` (validado en dominio) y una transacción `loan` no lleva categoría.

Índices: `(user_id, occurred_at DESC)`, `(user_id, account_id, occurred_at DESC)`, `(user_id, category_id, occurred_at)`, `(user_id, status, occurred_at)` y, para búsqueda de texto, `GIN (to_tsvector('spanish', title || ' ' || coalesce(note,'')))`. Todos parciales `WHERE deleted_at IS NULL`.

**`attachments`**: `transaction_id`, `filename`, `content_type`, `size_bytes`, `storage_key` (disco local en V1; el almacenamiento externo queda para después).

### 5.5 Préstamos (núcleo, SPEC §7, ADR-003)

**`loans`**: `person_id → people`, `direction` ∈ {`lent`,`borrowed`}, `currency`, `principal NUMERIC(18,2) > 0`, `opened_on date`, `due_on date NULL`, `note`, `import_external_id text NULL` (único parcial). **No existe columna de estado ni de saldo.**

**`loan_movements`** (libro mayor; inmutable salvo edición explícita)
| Columna | Tipo | Notas |
|---------|------|-------|
| loan_id | `uuid` | |
| kind | `text` | `disbursement`, `interest`, `payment`, `adjustment`, `write_off` |
| amount_in_loan_currency | `NUMERIC(18,2)` | `> 0` salvo `adjustment`, que es con signo y `<> 0` |
| transaction_id | `uuid NULL` | transacción real (`kind='loan'`); NULL si no hay dinero (interés registrado, ajuste, condonación) o si es un préstamo importado sin desembolso. **Único** cuando no es NULL |
| interest_part, principal_part | `NUMERIC(18,2) NULL` | solo en `payment` y `write_off`; `interest_part + principal_part = amount_in_loan_currency`, ambos `>= 0` (ADR-003) |
| fx_rate_applied | `NUMERIC(18,6) NULL` | si la cuenta usada tiene otra moneda que el préstamo (Ejemplo C). **Convención: unidades de la moneda de la cuenta por 1 unidad de la moneda del préstamo** (Ej. C: `3.800000` = PEN por USD). `amount_in_loan_currency = |transacción.amount| / fx_rate_applied`, redondeado ROUND_HALF_UP a 2 decimales |
| occurred_at | `timestamptz` | |
| note | `text` | |

Reglas:
- **Cada movimiento con dinero usa su propia cuenta**, porque apunta a su propia `transactions` (resuelve P3). El desembolso y los cobros pueden ir a cuentas y monedas distintas.
- Exactamente un `disbursement` por préstamo, con `amount_in_loan_currency = loans.principal`. El desembolso **no suma al saldo**: el principal ya está en `loans`.
- Estadísticas: el **capital** (desembolso y `principal_part`) no cuenta como gasto ni ingreso; sí cambia el saldo de la cuenta. `interest_part` cuenta como gasto (`borrowed`) o ingreso (`lent`) en la categoría de sistema de interés, **en la fecha del pago** (ADR-003).
- Signo de la transacción real (`kind='loan'`): desembolso negativo si `lent` (sale dinero) y positivo si `borrowed` (entra); pago negativo si `borrowed` (pago al prestamista) y positivo si `lent` (cobro).

**Vista `loan_balances`** (cálculo, nunca columna):
```
saldo = principal
      + SUM(amount) FILTER (kind IN ('interest','adjustment'))
      - SUM(amount) FILTER (kind IN ('payment','write_off'))
estado = CASE WHEN saldo = 0 THEN 'settled' ELSE 'open' END   -- no existe botón "liquidar" (P2)
```
Un saldo negativo no se permite. **Exceso (RF-22, Ejemplo D):** si el importe de un pago supera el saldo, la API responde `422` con un `Problem` que lista las opciones y no guarda nada. El cliente repite la petición (con una `Idempotency-Key` nueva) añadiendo `excess_handling`:
- `adjustment`: en **una sola transacción de base de datos** se crea un `adjustment` por el exceso, fechado inmediatamente antes del pago, y luego el pago completo (el préstamo estaba realmente más alto).
- `income_expense`: se crea el pago por el saldo exacto y, en la misma transacción de BD, una transacción normal de ingreso (si `lent`) o gasto (si `borrowed`) por el exceso en la misma cuenta.
No existe estado intermedio ni reintento parcial.

**Reparto de un pago o condonación (dominio, `domain/loans.py`):** el interés pendiente es `SUM(interest) − SUM(interest_part de pagos y condonaciones)`; el capital pendiente es `principal + SUM(adjustment) − SUM(principal_part de pagos y condonaciones)`. Al registrar un pago de importe `p`: `interest_part = min(p, interés_pendiente)` y `principal_part = p − interest_part`. El usuario puede editar el reparto antes de guardar; el dominio valida que no supere lo pendiente de cada concepto. Una **condonación** (`write_off`) se reparte igual (primero interés), **no mueve dinero ni genera gasto/ingreso**: el interés condonado nunca se reconoce. Un **ajuste** afecta **solo al capital** (positivo lo aumenta, negativo lo reduce) y no puede dejarlo por debajo de 0.

*Ejemplo A (me prestaron S/ 200):* interés 5 % → movimiento `interest` 10, saldo 210. Pago 100 (BCP): `interest_part 10`, `principal_part 90`, saldo 110. Pago 110 (Efectivo): `interest_part 0`, `principal_part 110`, saldo 0 → `settled`. En estadísticas aparece **un solo gasto de S/ 10** ("Intereses"), con fecha del primer pago; Efectivo +200 −110, BCP −100.

### 5.6 Suscripciones y recurrencias

**`recurring_rules`**: plantilla (`account_id`, `kind`, `amount`, `category_id`, `title`, `note`), `period` ∈ {`daily`,`weekly`,`monthly`,`yearly`}, `interval_count int DEFAULT 1`, `next_run_on date`, `end_on date NULL`, `active bool`, `subscription_id uuid NULL`.

**`subscriptions`**: `title`, `amount NUMERIC(18,2)`, `currency`, `account_id` (FK compuesta con la moneda), `category_id`, `period`, `interval_count`, `next_due_on date`, `status` ∈ {`active`,`archived`}, `archived_at`, `archive_reason`, `reminder_days_before int NULL`, `recurring_rule_id`.

**Equivalente mensual/anual** (para totales comparables; se calcula, no se guarda): mensual = `amount × f / interval_count`, con `f` = `30.4375` (diaria), `4.348125` (semanal), `1` (mensual), `1/12` (anual); anual = mensual × 12; ROUND_HALF_UP a 2 decimales solo al final. Los totales por moneda no se mezclan; el total en moneda de reporte usa §5.8.

Reglas (SPEC §8): **archivar** = `status='archived'` + `archived_at` + desactivar la regla + borrado lógico de las transacciones futuras `scheduled` de esa suscripción; **no toca** transacciones pasadas. Los totales mensual/anual y el gráfico consideran solo `status='active'`. Reactivar recrea la regla y las próximas. La sugerencia de reactivar compara el título de una transacción nueva con suscripciones archivadas (el usuario confirma).

### 5.7 Presupuestos y metas

- **`budgets`**: `name`, `period` ∈ {`daily`,`weekly`,`monthly`,`custom`}, `start_on`, `end_on NULL`, `amount NUMERIC(18,2)`, `currency`, `scope` ∈ {`all`,`selected`} (con `selected` solo cuentan las transacciones enlazadas, RF-29).
- **`budget_categories`**: `budget_id`, `category_id`, `limit_amount`.
- **`budget_transactions`**: `budget_id`, `transaction_id` (con `deleted_at`).
- **`goals`**: `kind` ∈ {`spend`,`save`}, `name`, `target_amount`, `currency`, `due_on NULL`. **`goal_transactions`**: `goal_id`, `transaction_id`. Las metas no modelan préstamos (RF-32).
- El gasto de presupuestos y metas se calcula; los préstamos aportan solo `interest_part` (nunca capital).

### 5.8 Reglas de categorización, notificaciones y tipos de cambio

- **`category_rules`** (base V2): `pattern`, `match_type` ∈ {`exact`,`contains`}, `category_id`, `source` ∈ {`manual`,`import`,`model`}, `hits int`.
- **`notifications`**: `kind` (`upcoming_payment`, `subscription_renewal`, `loan_due`, `budget_threshold`), `payload jsonb`, `read_at`, `created_at`. **`notification_prefs`**: `kind`, `enabled`, `lead_days int`, `channel` ∈ {`in_app`,`push`}. **`push_subscriptions`** *(Fase 6)*: endpoint y claves de la suscripción PWA.
- **`exchange_rates`**: `from_currency`, `to_currency`, `rate NUMERIC(18,6)`, `as_of date`, `source` (`manual`, `auto:<proveedor>`). **Excepción documentada:** es una tabla **global** (datos de mercado), **sin `user_id`**; la leen todos los usuarios y la escribe solo el sistema. Único en `(from_currency, to_currency, as_of, source)`. Cada transacción copia su tasa (`fx_rate_to_base`), por lo que esta tabla solo alimenta sugerencias y conversiones a moneda de reporte.
- **Conversión a la moneda de reporte** (SPEC §9.5): para cada transacción se usa su `fx_rate_to_base` y, si la moneda de reporte difiere de la base, la tasa base→reporte de `exchange_rates` con `as_of` **el día de la transacción o el más cercano anterior**. Si no existe ninguna, esa transacción se excluye del total convertido y se informa como «sin tasa» (`unconverted_count`); **nunca se usa la tasa de hoy para el pasado**.
- **`idempotency_keys`**: `user_id`, `key text`, `request_hash bytea`, `response_status int`, `response_body jsonb`, `created_at`, `expires_at` (retención 24 h). Único `(user_id, key)`. Misma clave y mismo cuerpo → se devuelve la respuesta guardada; misma clave con cuerpo distinto → `409`.

### 5.9 Importaciones

- **`import_runs`**: `source_kind` ∈ {`sqlite`,`csv`}, `source_schema_version int NULL` (`PRAGMA user_version`), `file_sha256`, `mode` ∈ {`dry_run`,`apply`}, `started_at`, `finished_at`, `report jsonb` (conteos por entidad, saldos antes/después, elementos sin mapear).
- **`import_review_items`**: `import_run_id`, `kind` (`ambiguous_loan`, `orphan_interest`, `unknown_column`, …), `payload jsonb`, `resolved_at`. Lista los casos de revisión manual de RF-40d; nada ambiguo se adivina.

## 6. Importador de Cashew (`importers/`)

- Entrada: una **copia** del respaldo, abierta con `sqlite3` en modo `mode=ro` (RF-40g). Lee `PRAGMA user_version` y descubre columnas con `PRAGMA table_info`; ignora lo desconocido y lo reporta (RF-40i).
- Mapeo (detalle en `docs/cashew-analysis/01-data-model.md` y `02-loans.md`): `wallets→accounts`, `categories→categories`, `transactions→transactions` (el monto ya viene con signo), `objectives(type=loan)`+`objective_loan_fk`→`loans`+`loan_movements`, `transactions(type=credit/debt)`→`loans` de pago único, `budgets`/`category_budget_limits`→`budgets`/`budget_categories`, `objectives(type=goal)`→`goals`, `associated_titles`→`category_rules`, `tags`/`transaction_to_tag_links`→`tags`/`transaction_tags` (RF-40j), `delete_logs`→se descartan.
- Idempotencia: `import_external_id = 'cashew:sqlite:<pk>'`, upsert por `(user_id, import_external_id)`. Cada import corre en una sola transacción de BD; `--dry-run` hace *rollback* y devuelve el reporte.
- Fechas: se detecta la escala por magnitud (segundos, ms o µs) y se valida con el fixture sintético (T-105).
- Monedas: el saldo de cada cuenta tras importar debe coincidir con el de Cashew (`SUM(amount)` de `paid=1`); si no, el reporte lo señala.
- Préstamos de pago único con `paid=0` (saldados): se crean `loan` + `disbursement` + un `payment` **sintetizado** y se marcan para revisión (no se conoce fecha ni cuenta del cobro).

## 7. API (`/api/v1`)

- **Dinero y tasas en JSON como cadenas decimales** (`"200.00"`, `"3.800000"`), nunca números de coma flotante; Pydantic estricto con `Decimal`. Fechas en ISO 8601 con zona (`timestamptz`) o `date`.
- JSON `snake_case`; todo endpoint con `response_model`; errores `application/problem+json` con `type`, `title`, `status`, `detail` y, en validación, lista de campos.
- **Paginación única** para listados: parámetros `limit` (1–200, por defecto 50) y `cursor` (opaco); respuesta `{ "items": [...], "next_cursor": "..." | null }`. Orden estable `occurred_at DESC, id DESC` en transacciones.
- **Autenticación:** cookie de sesión (ADR-002); todo endpoint exige sesión salvo `POST /auth/login`, `GET /auth/google/callback` y `GET /health`. Peticiones que modifican datos: comprobación de `Origin` y token CSRF.
- **Idempotencia de creación:** `POST` de transacciones y movimientos acepta cabecera `Idempotency-Key` (útil para el bot de V2 y reintentos).
- **Recursos de V1:** `auth`, `users/me`, `accounts`, `categories`, `people`, `tags`, `transactions` (+ `transactions/{id}/tags`, lote), `transfers`, `loans` (+ `loans/{id}/movements`, `loans/{id}/balance`, `loans/summary`), `subscriptions` (+ `archive`, `reactivate`), `recurring-rules`, `budgets`, `goals`, `exchange-rates` (sugerencia), `notifications`, `category-rules` (RF-06), `attachments` (RF-08, subida/descarga/borrado por transacción), `reports/*` (SPEC §10), `imports`, `exports`. **Exportación (RF-41):** JSON completo con un campo `schema_version` y CSV por tabla; la **restauración desde ese JSON no es de V1** (solo se importa Cashew).
- `docs/api/openapi.json` se genera desde FastAPI y se versiona; todo cambio de contrato avisa a quien hace la UI (T-102 lo define antes del código).

## 8. Seguridad (resumen operativo)

- Contraseñas y PIN con argon2id; límite de intentos de login por usuario e IP; respuestas sin revelar si un correo existe.
- Secretos solo por variables de entorno; `.env.example` sin valores reales; CORS restringido al origen de la web.
- Sin telemetría; el único tráfico saliente es el login con Google y, si se activa, el par de monedas al proveedor de tipo de cambio.
- Prueba obligatoria de aislamiento con dos usuarios sobre **cada** recurso (AGENTS.md §6.9).

## 9. Despliegue local (Fase 2)

`infra/docker-compose.yml` con tres servicios: `db` (PostgreSQL con volumen), `api` (FastAPI, migraciones al arrancar con Alembic) y `web` (Flutter Web servido estáticamente o por proxy; la API y la web comparten dominio para la cookie). Respaldos: script `pg_dump` con rotación local (RF-42). El VPS reutiliza el mismo compose con HTTPS delante.

## 10. Puntos abiertos para las fases siguientes

1. Obligatoriedad de `category_id` por tipo de transacción: se refinará con la UI; el esquema lo permite nulo.
2. ADR-005 (sincronización Android) y `If-Match`/versionado optimista: antes de V4.
3. Row Level Security como defensa adicional: evaluar en la Fase 7.
4. Proveedor de tipo de cambio (ADR-004): verificar antes de implementar.
5. Detalle de implementación a cerrar en la Fase 2/6 (anotado por T-102 en `docs/api/README.md`): estado y almacenamiento de PKCE/`state` en el login con Google, reautenticación para configurar PIN, desafíos WebAuthn, conservación y expiración de la copia del respaldo entre `dry-run` y `apply`, y resolución manual de elementos ambiguos de importación.
6. `fx_rate_applied` (convención de §5.5) se confirma con el fixture T-105 (Ejemplo C) y con las pruebas de dominio.
7. **Orden de categorías:** Cashew las ordena (`order`) y su UI permite reordenarlas, pero SPEC no lo pide y ni este esquema ni el contrato lo prevén. Decidir en la Fase 5 con la UI; si se acepta, migración posterior con `categories.sort_order` y mapeo del `order` de Cashew en el importador.
8. **`updated_at`** se refresca vía ORM/Core (`onupdate`), no con SQL crudo. Si el importador masivo o la sincronización de V4 lo exigen, añadir un trigger `set_updated_at` en una migración posterior.
9. **Aislamiento a nivel de FK:** las claves foráneas de la migración 0001 solo apuntan a `users`. Para las tablas con referencias cruzadas (`transactions`, `loan_movements`, …) la migración 0002 usará **FK compuestas con `user_id`** (`UNIQUE (id, user_id)` en el padre) para que ninguna fila pueda referenciar datos de otro usuario aunque falle el repositorio.

## 11. Historial de cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 0.1 | 2026-10-07 | Primera versión (T-101). |
| 0.2 | 2026-10-07 | Revisada por Adrian. `users.report_currency` y `preferences`; moneda base inmutable tras la primera transacción; condonaciones con reparto interés/capital; ajustes solo sobre capital; manejo atómico del exceso (RF-22); convención de `fx_rate_applied`; conversión a moneda de reporte sin usar tasas futuras; equivalente mensual/anual de suscripciones; tabla `idempotency_keys`; `category-rules` y `attachments`; alcance de la exportación. |
| 0.3 | 2026-10-07 | Precisiones de T-203: `lower(people.name)` es B-tree (no GIN); `report_currency` sin default de servidor; `users.locale` limitado a `es`/`en`; coherencia `is_system`/`system_key`; el trigger de categorías exige mismo `user_id` y revalida hijos; nulabilidad y defaults de columnas abreviadas (`name`, `type`, `currency`, `kind`, `initial_balance` y fechas de sesión `NOT NULL`; textos decorativos, `note`, `user_agent`, `ip` `NULL`). |
