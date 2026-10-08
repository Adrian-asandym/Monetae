# Contrato OpenAPI inicial de Monetae

`openapi.json` es el contrato **contract-first** de V1: OpenAPI 3.1.0, basado en
`docs/SPEC.md` v0.3, `docs/ARCHITECTURE.md` v0.2 y ADR-002/003/004/006 aceptadas.
Permite generar un cliente tipado de Flutter y servir mocks antes del backend.
No implica que los endpoints ya estén implementados. Presupuestos, metas,
notificaciones y bloqueo PIN/WebAuthn tienen un contrato inicial para la Fase 6.

## Lectura y validación

Todas las rutas incluyen `/api/v1`; `servers` contiene solo el origen. Los esquemas,
parámetros, respuestas de error y ejemplos se reutilizan desde `components`.
Las descripciones están en español; campos, recursos y `operationId` en inglés.

Desde la raíz del repositorio:

```bash
npx --yes @redocly/cli@latest lint docs/api/openapi.json
python3 -I scripts/check_openapi.py
python3 -I scripts/check_openapi.py --self-test
git diff --stat master-dev...HEAD
```

Redocly se ejecuta como herramienta efímera, sin agregar dependencias al repo.
El comprobador requiere solamente Python 3.9+ y biblioteca estándar; resuelve
referencias JSON Pointer, valida seguridad, CSRF, errores, paginación e aislamiento
de cuerpos de petición. Prohíbe `type: number` en todo el contrato para evitar
que dinero, tasas o porcentajes se serialicen como flotantes. Las quince pruebas
internas alteran contratos para comprobar que detecta errores reales. El script
no sustituye a un validador general de OpenAPI/JSON Schema ni demuestra aislamiento
real de BD: ese requiere los tests de dos usuarios en la Fase 2.

Redocly termina sin errores y con **un aviso aceptado** `no-server-example.com`:
`http://localhost:8000` es deliberadamente el servidor de desarrollo de V1,
no una URL pública inventada. No se desactiva la regla ni se agrega configuración.

Para un mock local opcional:

```bash
npx --yes @stoplight/prism-cli mock docs/api/openapi.json
```

Un mock reproduce formas y ejemplos; no implementa el libro mayor, la idempotencia
ni las reglas aritméticas. Para explorar préstamos, los ejemplos reutilizables
`A_movement_1`…`E_movement_5`, `A_balance`…`E_balance` y `D_overpayment`
están conectados a request/response `examples` de movements/balance.
`x-loan-scenarios` enlaza secuencias sintéticas y saldos intermedios para verificación.
No contiene datos financieros reales. Los desembolsos iniciales se envían dentro
de los ejemplos `A_loan_create`…`E_loan_create`, al crear el préstamo atómicamente;
no se reenvían luego a movements si el desembolso ya existe.

## Convenciones

- Dinero: cadenas con dos decimales; tasas: cadenas positivas con seis decimales.
  Monedas: `^[A-Z]{3}$`; UUID; instantes con zona horaria, respuestas en UTC.
  Cálculos con `Decimal`, `ROUND_HALF_UP`; no se revalúa el pasado con tasas actuales.
- Transacciones: monto **con signo**, entrada positiva y salida negativa, distinto
  de cero; moneda igual a la cuenta. `posted` afecta al saldo, `scheduled` todavía
  no. El CRUD directo crea solo ingresos/gastos; transfers y loan movements
  generan sus transacciones asociadas y conservan invariantes de forma atómica.
- Listados: `limit` 1–200, defecto 50, `cursor` opaco y `{items, next_cursor}`
  con cursor nulo al terminar. Agregados enumerables también usan este formato.
  Transacciones: orden `occurred_at DESC, id DESC`. Filtro `tag_ids` repetido con
  `style=form`, `explode=true`; coincidencia OR (RF-45).
- Todas las operaciones declaran errores `application/problem+json`, esquema
  `Problem`, y operaciones con riesgo de intentos repetidos añaden 429. Un recurso
  o UUID ajeno responde 404; no se acepta `user_id` en peticiones ni se expone en
  respuestas. Los IDs de negocio siempre pertenecen al usuario de la sesión.
- Sesión opaca en cookie `monetae_session`, `HttpOnly`, `Secure`, `SameSite=Lax`.
  Solo login, callback Google y health son públicos. POST/PUT/PATCH/DELETE requieren
  `X-CSRF-Token` y validación de `Origin`, incluido login. El servidor que entrega
  la web facilita el token pre-login; `/auth/csrf` requiere sesión. El inicio de
  Google se solicita con `POST /auth/login`, `{method: "google"}`, que devuelve
  `authorization_url`; así no se introduce otro endpoint público. Callback valida
  state/nonce/PKCE y no vincula cuentas existentes sin confirmación explícita.
- `Idempotency-Key` opcional en creación de transacción, préstamo (incluye
  desembolso atómico) y movimiento; retención **24 h**, única por usuario y clave
  (no por endpoint). Misma clave/cuerpo devuelve status y respuesta guardados;
  clave repetida con otro cuerpo da 409 (ARCHITECTURE §5.8).
- Préstamos: `principal` ya incluye el desembolso; este no vuelve a sumar al saldo.
  `status` y `outstanding` son `readOnly`. Cada desembolso/pago indica su propia
  cuenta, importe original y tasa histórica. Interés/ajuste/condonación no mueven
  dinero. Las propuestas de reparto e interés no persisten nada. Al guardar un
  pago se envían `interest_part` y `principal_part` editables; se valida suma y
  límites. El reparto puede omitirse en el pago para que el servidor lo calcule;
  si se envía, ambos campos deben estar presentes. Condonaciones también incluyen
  reparto, primero interés, sin mover dinero ni reconocer gasto/ingreso. Ajustes
  afectan solo capital, con signo, nunca dejándolo bajo cero (ARCHITECTURE §5.5).
  Capital no cuenta en gasto/ingreso; interés pagado sí, en categoría de sistema
  y fecha de pago (ADR-003). No existe operación de liquidación.
- RF-22: pago excesivo sin `excess_handling` devuelve **422** `loan_overpayment`,
  sin guardar nada, con saldo, exceso, moneda y opciones que informan `applied_amount`.
  Reintento con **Idempotency-Key nueva** y elección `adjustment` o `income_expense`.
  `adjustment` crea ajuste positivo de capital inmediatamente antes del pago completo;
  `income_expense` aplica saldo exacto y crea ingreso (lent) o gasto (borrowed) por
  exceso, en misma cuenta. Todo ocurre en una sola transacción de BD, sin estado
  intermedio ni reintento parcial. La petición describe el importe físico total
  convertido en `amount_in_loan_currency`; el reparto opcional (ambos campos o
  ninguno) refiere solo al pago aplicado, calculado por servidor si se omite.
  La respuesta devuelve el `LoanMovement` aplicado y `side_effects` con
  `adjustment_id` o transacción extra. En otra moneda, pago de cuenta = ROUND_HALF_UP
  del aplicado × tasa; exceso de cuenta = resto hasta el importe físico, conservando
  todos los céntimos (precisión confirmada por el coordinador para T-102b).
- Borrado siempre lógico; restore deshace y recalcula. Transferencias se modifican
  y restauran por grupo. Movimientos modifican su transacción asociada en la misma
  operación. Edición de desembolso actualiza principal; no se puede borrar solo
  el único desembolso. Editar la historia que invalida repartos posteriores da 409.
  Borrar un préstamo no borra sus transacciones; `include_deleted` permite consultar
  préstamo/saldo/historial propios. Los préstamos saldados permanecen en listados.
- Archivar suscripción desactiva su regla y borra lógicamente futuras `scheduled`;
  mantiene pagos pasados. Listado defecto `status=active`; totales/gráfico solo
  activos. `status=archived` muestra importe histórico, última fecha y archivo.
  Nueva transacción puede ofrecer IDs de suscripciones para reactivar: el usuario
  confirma con reactivate; nunca se reactiva automáticamente.
- Importación: upload de **copia** en dry-run (SQLite solo lectura, CSV rescate),
  reporte con conteos/saldos/advertencias y apply ligado a `dry_run_id` y hash.
  No se adivinan casos ambiguos; ids externos o hash determinista aseguran
  idempotencia por usuario. Exportación es descarga de JSON completo con
  `schema_version` o CSV por tabla; restaurar ese JSON **no es de V1** (§7).
- Perfil: `report_currency` cambia libremente; `preferences` guarda tema, acento
  y `home_widgets` en orden de array. `base_currency` es de solo lectura con
  historial: intentar cambiarla tras la primera transacción devuelve 409
  `base_currency_locked`; no hay migración de base en V1 (ARCHITECTURE §5.2).
- Conversión de reportes: usa la tasa propia de cada transacción hacia base, y
  base→reporte del día de la transacción o el más cercano anterior. Si no existe,
  excluye del total convertido e informa `unconverted_count`; el desglose por
  moneda conserva esos importes. Nunca usa tasas futuras ni de hoy para el pasado
  (ARCHITECTURE §5.8). Los totales convertidos reutilizan `ReportTotal`.
- Suscripciones: mensual = amount × factor / interval_count; factores daily
  `30.4375`, weekly `4.348125`, monthly `1`, yearly `1/12`. Anual = mensual
  **sin redondear** × 12; ROUND_HALF_UP a dos decimales solo al final (§5.6).
- `category-rules`: CRUD RF-06 de patrones exact/contains, categoría propia;
  servidor asigna `source` y acumula `hits`, ambos solo lectura. V1 no ejecuta ML.
- `attachments`: subida multipart, listado paginado, descarga y borrado lógico
  por transacción propia. **10 MiB por archivo**, **5 activos por transacción**;
  MIME `image/jpeg`, `image/png`, `image/webp`, `application/pdf`. Exceso de tamaño
  devuelve 413 Problem, MIME no permitido 415 Problem y límite de cantidad 422.
  Estos límites fueron confirmados por el coordinador en T-102b; almacenamiento
  local en V1 y `storage_key` interno, sin exponer rutas del servidor.
- Los mapas abiertos de WebAuthn y notificaciones son bordes iniciales explícitos,
  no permisos para aceptar cualquier campo en entidades financieras. Requests
  financieros usan `additionalProperties=false`.

## Ejemplos A–E

El comprobador recalcula la fórmula de ARCHITECTURE §5.5 con `Decimal`, verifica
los repartos en base caja y el efecto por cuenta, sin volver a sumar desembolsos.

| Ejemplo | Saldos tras movimientos | Verificación adicional |
|---|---|---|
| A | PEN 200 → 210 → 110 → 0 | Efectivo +90, BCP −100; solo PEN 10 de interés en primer pago |
| B | PEN 500 → 200 → 0 | Yape −500, Efectivo +300, BCP +200 |
| C | USD 100 → 0 | Cuenta PEN +380; 380 / 3.800000 = USD 100 aplicado |
| D | USD 50 sin cambios al rechazar 60; luego 0 con cada opción | Problem 422; adjustment +10 y payment 60, o payment 50 e income 10 |
| E | PEN 1000 → 950 → 830 → 800 → 0 | Pagos variables 50, 120, 30 y 800 en fechas distintas |

A, B, C y E terminan `settled`; D sigue `open` mientras no se resuelva el exceso.
El ejemplo A contiene cuatro movimientos de libro mayor y tres transacciones
monetarias: el interés registrado no crea una transacción (ADR-003).

Además, el comprobador verifica los ejemplos de D con cada `excess_handling`:
`D_adjustment_request/response/balance` y `D_income_expense_request/response/balance`.
La variante `D_income_expense_foreign_*` recibe PEN 228.01 para un préstamo USD,
con tasa 3.800000: el total convertido es USD 60.00, el pago aplicado USD 50.00
crea PEN 190.00 y el ingreso por exceso es el **resto PEN 38.01**, de modo que
190.00 + 38.01 = 228.01; no se pierden céntimos por redondear el exceso separado.
Los repartos de esa variante se omiten y los calcula el servidor.

La condonación sintética parte de capital 100 e interés 10, ajusta capital −25
y condona 30 repartidos en interés 10 y capital 20: saldo final 55, sin movimientos
de cuenta ni reconocimiento de interés. Una suscripción semanal de PEN 10 produce
mensual **43.48** y anual **521.78**; calcular el anual desde el mensual ya
redondeado daría 521.76 y la regresión lo detecta.

## Regeneración en Fase 2

Hasta que exista FastAPI, este JSON es la fuente del contrato. Al implementar,
routers y modelos estrictos deben reproducirlo; el servidor es responsable de
los `response_model`, de validar invariantes y de filtrar por usuario.

Cuando exista `monetae.api.main:app`, desde `services/api`:

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from monetae.api.main import app

contract = app.openapi()
Path('../../docs/api/openapi.json').write_text(
    json.dumps(contract, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
)
PY
```

Configurar FastAPI para conservar nombres de esquemas, seguridad cookie, patrones
decimales, Problem, CSRF, ejemplos y `x-loan-scenarios` mediante
`openapi_extra`/personalización de `app.openapi()`. El comando anterior es futuro,
no ejecutable aún: el backend no existe en este checkout. Revisar el diff, ejecutar
ambos validadores y los checks backend antes de aceptar la regeneración. Avisar
al responsable de UI ante todo cambio de contrato; no sobrescribir ejemplos
ni convenciones por la salida automática predeterminada de FastAPI.

## Observaciones para el coordinador

**RESUELTAS por ARCHITECTURE v0.2** (se conservan números de T-102):

1. **FX aplicada — RESUELTA (§5.5)**: moneda de cuenta por unidad de préstamo;
   aplicado = importe físico / tasa, ROUND_HALF_UP. C verificado; T-105 debe
   confirmar la misma convención en fixture y pruebas de dominio, sin cambiarla.
2. **Ajustes, condonaciones y RF-22 — RESUELTA (§5.5)**: ajustes solo capital,
   condonaciones con reparto interés primero y sin caja, exceso con elección
   atómica y 422 sin persistencia si falta. Coordinador precisó reparto opcional
   sobre pago aplicado, `applied_amount`, `side_effects` y resto en moneda de cuenta;
   ambas salidas de D y variante multimoneda están verificadas.
3. **Preferencias y cambio de base — RESUELTA (§5.2)**: preferences jsonb,
   report_currency libre y base inmutable tras primera transacción; conflicto 409.
4. **Conversión histórica — RESUELTA (§5.8)**: tasa del día o anterior más cercano,
   ausencia excluida del convertido e informada por `unconverted_count`.
5. **Equivalentes mensual/anual — RESUELTA (§5.6)**: factores exactos e intervalo,
   sin redondeos intermedios; ejemplo semanal verificado.
9. **Idempotencia — RESUELTA (§5.8)**: tabla idempotency_keys, unicidad usuario/clave,
   retención 24 h, misma clave/cuerpo devuelve respuesta guardada y cuerpo distinto 409.
10. **RF-06, RF-08 y exportación — RESUELTA (§7)**: category-rules y attachments
    incluidos en V1; JSON exportado con schema_version, restauración fuera de V1.
    Campos de reglas/adjuntos en §5.8/§5.4; límites MIME/tamaño/cantidad confirmados
    explícitamente por el coordinador durante T-102b.

### Pendientes de implementación

6. **OIDC y reautenticación**: estado/almacenamiento de PKCE y state, confirmación
   de vinculación y prueba de reautenticación para PIN, especialmente usuarios
   solo Google. Configurar PIN requiere contraseña u OIDC; enviar solo PIN
   no constituye reautenticación (ARCHITECTURE §10.5).
7. **Bloqueo Fase 6**: estado por sesión, desafíos WebAuthn, detalle de objetos
   estándar y payloads de avisos. PIN sigue siendo respaldo obligatorio del bloqueo,
   no sustituye login, y cinco fallos exigen volver a autenticar (§10.5, ADR-006).
8. **Importación**: conservación y expiración de copia entre dry-run/apply y
   resolución manual de ambiguos. El hash liga la misma copia; reconocer una
   advertencia no resuelve por sí solo un préstamo ambiguo (§10.5).

## Resultado de validación

- Redocly: contrato válido, **0 errores**, aviso local justificado arriba.
- `python3 -I scripts/check_openapi.py`: **86 paths, 127 operaciones, 131 esquemas**;
  comprobaciones originales y nuevas de v0.2 pasan con Python 3.9.
- `python3 -I scripts/check_openapi.py --self-test`: **15 pruebas** pasan, incluyendo
  regresiones de pago aplicado, céntimos de exceso multimoneda, condonación,
  redondeo anual, ausencia de unconverted_count y operación de adjuntos.
- Ruff, formato, mypy estricto y pytest del script se ejecutan con herramientas
  temporales fuera del repo, sin agregar dependencias al proyecto. Los checks
  backend completos no aplican: no se ha creado backend en esta tarea.

## Implementación de sesión y CSRF (T-204)

V1 permite contraseña y correo; Google devuelve `501 google_login_not_available`
(excepción temporal a los códigos del contrato, sin modificar `openapi.json`). No
hay registro público: `uv run python -m monetae.cli create-user --email ...`
pide la contraseña dos veces con `getpass`, o lee una línea con `--password-stdin`.
Dentro del contenedor, usar `docker compose -f infra/docker-compose.yml exec -T api
python -m monetae.cli create-user --email ... --password-stdin` (o `uv run --no-sync`),
pues la imagen solo instala dependencias de producción y su venv pertenece a root.
Nunca acepta contraseñas como argumentos. La política es de 12 a 128 caracteres,
argon2id con el perfil recomendado y actualización de hash al iniciar sesión.
El alta copia base a moneda de reporte y crea las categorías de sistema de interés.

Cada login genera 32 bytes aleatorios; PostgreSQL conserva exclusivamente SHA-256
del token. La cookie `monetae_session` es `HttpOnly`, `Secure`, `SameSite=Lax`,
`Path=/`, con `Max-Age=session_absolute_days × 86400` para conservarla al cerrar
el navegador o PWA; logout la expira con `Max-Age=0` y las mismas banderas.
El servidor sigue imponiendo ambos límites aunque la cookie siga presente.
Inactividad por defecto: 14 días; límite absoluto: 30 días. Los ajustes
`MONETAE_SESSION_IDLE_MINUTES` y `MONETAE_SESSION_ABSOLUTE_DAYS` los controlan;
`last_seen_at` y la expiración deslizante se actualizan como máximo una vez por
minuto mediante UPDATE condicional atómico y commit inmediato, antes de que el
handler escriba. La autenticación lee usuario y sesión sin bloqueos de fila;
la transacción del handler puede permanecer abierta sin serializar las peticiones
del mismo usuario o sesión. Solo login y revocación toman el bloqueo exclusivo
del usuario para ordenar altas y logout-all; una petición ya autenticada puede
continuar si su sesión se revoca después. Logout revoca filas, logout-all revoca
todas las del usuario y la revocación individual exige propiedad del recurso. Los listados paginados
solo devuelven sesiones activas, nunca token ni hash.

El middleware emite `monetae_csrf` cuando falta o su firma no es válida; un GET
de salud permite obtenerla antes del login. Es legible por JavaScript, `Secure`,
`SameSite=Lax`, `Path=/`; valor `nonce.hmac`, HMAC-SHA256 con
`MONETAE_SECRET_KEY` sobre nonce concatenado con hash hexadecimal del token
de sesión, o `pre` antes del login. POST/PUT/PATCH/DELETE, incluido login,
exigen `X-CSRF-Token` igual a la cookie con firma válida y `Origin` de CORS o del
propio host; `Referer` sirve solo cuando falta `Origin`. Comparaciones constantes;
rechazo `403 csrf_failed`. El login rota CSRF y lo liga a la nueva sesión;
logout lo vuelve a ligar a `pre`. `/auth/csrf` exige sesión y devuelve
`AuthenticatedSession`, incluido el token vigente. Respuestas de auth/perfil
usan `Cache-Control: no-store`.

`MONETAE_COOKIE_SECURE=false` sirve únicamente para pruebas locales sobre HTTP;
en producción se exige un secreto real de al menos 32 caracteres y cookies
Secure. `.env.example` contiene un secreto explícitamente falso. El servidor
usa la IP de la conexión, sin confiar en cabeceras de IP del cliente; detrás de
un proxy, este debe restringir los emisores de cabeceras reenviadas.

La migración 0002 crea `login_attempts`, registro de seguridad sin `user_id` ni
borrado lógico: cinco fallos por correo normalizado o veinte por IP en quince
minutos bloquean con `429 too_many_attempts` y `Retry-After`. Los aciertos no
cuentan; se purgan registros de más de siete días al intentar login. Bloqueos
transaccionales por ambos criterios evitan carreras entre procesos. Correo
inexistente y contraseña incorrecta verifican argon2 y devuelven la misma
respuesta `401 invalid_credentials`, sin registrar secretos ni correos completos.
`PATCH /users/me` rechaza por ahora toda petición con `base_currency` con
`409 base_currency_locked`, hasta la regla de transacciones de T-206.

## Catálogos (T-205)

`accounts`, `categories`, `people` y `tags` requieren sesión. Toda escritura requiere
`Origin` confiable y `X-CSRF-Token` válido. Las respuestas de error usan
`application/problem+json`; un recurso ajeno o inexistente devuelve `404`, y los
cuerpos que incluyen `user_id` se rechazan con `422`.

Los cuatro listados aceptan `limit` de 1 a 200 (por defecto 50) y un `cursor`
opaco. La respuesta es `{ "items": [...], "next_cursor": "..." | null }`.
La paginación usa llaves deterministas: cuentas y etiquetas por
`(sort_order, lower(name), id)`, categorías por `(kind, lower(name), id)` y
personas por `(lower(name), id)`. Un cursor alterado, de otro recurso o de otro
filtro devuelve `400 invalid_cursor`.

Las cuentas y etiquetas activas rechazan nombres duplicados sin distinguir
mayúsculas con `409 duplicate_name`, conforme a sus índices únicos parciales; el
nombre puede reutilizarse después del borrado lógico y, en etiquetas, también
cuando la anterior está archivada. Las categorías y personas sí permiten nombres
repetidos: una categoría puede llamarse igual bajo distintos padres y dos personas
pueden compartir nombre y distinguirse por sus alias.
El saldo de una cuenta equivale temporalmente a `initial_balance`; T-206 lo
calculará sumando las transacciones. La moneda de cuenta no se puede cambiar aún
y devuelve `409 account_currency_locked`. Archivar cuentas o etiquetas las oculta
de manera predeterminada; `include_archived=true` las incluye y reactivate vuelve
a mostrarlas. Reactivar una etiqueta que choque con otra activa devuelve
`409 duplicate_name`. El borrado de todos los recursos es lógico.

Las categorías de sistema no se editan ni eliminan (`409 system_category_immutable`).
Solo se admite un nivel de subcategorías y el padre debe ser propio y del mismo
tipo; una jerarquía inválida devuelve `422`. Una categoría con hijas activas no se
puede borrar ni cambiar de tipo (`409 category_has_children`). `PATCH` no permite
escribir `is_system` ni `system_key`.

Las personas aceptan nombres de 1 a 120 caracteres y hasta 20 alias normalizados
con recorte de espacios, únicos sin distinguir mayúsculas y de 1 a 60 caracteres.
La búsqueda `q` encuentra nombres por prefijo o alias exacto, sin distinguir
mayúsculas; los caracteres `%` y `_` se interpretan literalmente.

## Cambios del contrato durante la Fase 2

| Fecha | Cambio | Motivo |
|-------|--------|--------|
| 2026-10-08 | `TransactionUpdate` admite `account_id` (solo a una cuenta de la misma moneda; otra ⇒ `422 currency_mismatch`) y `kind` (`income`/`expense`, con signo de `amount` coherente). | Corregir la cuenta o el tipo de una transacción mal registrada es habitual (Cashew lo permite); lo detectó T-206a al implementar. Cambio aditivo y compatible. |

## Transacciones (T-206a)

Se implementan `POST/GET /transactions`, `GET/PATCH/DELETE /transactions/{id}`,
`POST /transactions/{id}/restore` y `PUT /transactions/{id}/tags`, bajo `/api/v1`.
Todas requieren sesión y las escrituras requieren `Origin` y `X-CSRF-Token`.
El CRUD directo crea ingresos positivos y gastos negativos, distintos de cero;
transferencias y préstamos se gestionarán por sus propios recursos.

Importes y tasas son cadenas de dos y seis decimales. La moneda debe coincidir
con la cuenta (`422 currency_mismatch`); en moneda base la tasa debe ser exactamente
`1.000000` (`422 invalid_fx_rate`). En otras monedas se conserva la tasa histórica
proporcionada. `PATCH` permite cambiar `account_id` a una cuenta de la misma moneda,
y cambiar `kind` junto con un importe de signo coherente. Campos de procedencia,
importación, dato inicial y grupo de transferencia son de solo lectura.
Los timestamps requieren zona horaria y las respuestas se entregan en UTC.

El listado se ordena por `(occurred_at DESC, id DESC)` y pagina mediante cursor
firmado, ligado al usuario y a todos los filtros. Acepta `date_from` inclusivo,
`date_to` exclusivo, cuenta, categoría, moneda, tipo, estado, `tag_ids` repetido
con coincidencia OR, búsqueda `q` y `include_deleted`. `q` combina texto completo
en español y subcadenas de título/nota sin distinguir mayúsculas; `%`, `_` y `\`
se tratan literalmente en la búsqueda de subcadenas. Los filtros `loan_id` y
`person_id` devuelven página vacía hasta la implementación de préstamos en Fase 3.
Cada página carga las etiquetas en una consulta adicional.

El borrado es lógico. La consulta individual también acepta `include_deleted=true`.
Restore conserva el identificador y recalcula saldos; referencias a cuenta o
categoría borrada producen `409 restore_conflict`. Reemplazar etiquetas retira
vínculos mediante borrado lógico y reutiliza los vínculos previos al añadirlos.
Etiquetas ajenas o borradas producen `404`; las borradas no aparecen en `tag_ids`.
Archivar conserva vínculos existentes, pero añadir uno nuevo a una etiqueta
archivada produce `422 tag_archived`.

`Idempotency-Key` es opcional, de 1 a 128 caracteres, con retención de 24 horas.
Una clave propia con el mismo cuerpo canónico devuelve el estado y la respuesta
originales, incluso si la transacción fue editada después. Otra petición produce
`409 idempotency_conflict`. El cuerpo canónico incluye la operación, normaliza
zona horaria, valores opcionales y orden de etiquetas. Las claves comparten
espacio por usuario entre operaciones; las expiradas se purgan oportunamente.
Un bloqueo consultivo por usuario/clave mantiene creación y respuesta en la misma
transacción de BD, evitando duplicados simultáneos. El componente reutilizable
está en `services/idempotency.py`.

El saldo de cuentas se calcula como saldo inicial más suma de transacciones
`posted` no borradas. El listado usa una sola suma agrupada para toda la página.
La moneda de cuenta y la moneda base pueden cambiar antes de la primera
transacción; el historial borrado también bloquea cambios posteriores con
`409 account_currency_locked` o `409 base_currency_locked`. Cambiar la moneda
base conserva `report_currency`. Borrar una cuenta o categoría con transacciones
no borradas produce `409 account_in_use` (se sugiere archivar) o
`409 category_in_use`.

La migración `0003` añade claves compuestas de dueño y moneda, índices parciales
y las tablas `transactions`, `transaction_tags` e `idempotency_keys`. Es reversible
a `0002`, incluyendo la retirada de las unicidades `(id, user_id)` añadidas a los
catálogos. `recurring_rule_id` queda sin FK hasta crear su tabla. ARCHITECTURE
§10.9 menciona `0002` para estas claves: la revisión correcta es `0003`, porque
`0002` ya registra intentos de login; no se modifica el documento de arquitectura.

## Transferencias, lotes y programadas (T-206b)

`POST/GET /transfers`, `GET/PATCH/DELETE /transfers/{id}` y
`POST /transfers/{id}/restore` requieren sesión; toda escritura exige CSRF y
Origin confiable. El ID público es `transfer_group_id`. Una transferencia crea
exactamente dos transacciones `posted`, de origen `web`, sin categoría: salida
negativa y entrada positiva. Cada pata conserva su propia tasa histórica a base;
la tasa en moneda base debe ser `1.000000`. Las cuentas deben ser distintas y
propias, sin borrado lógico. En la misma moneda los importes deben coincidir
(`422 transfer_amount_mismatch`); las comisiones se registran como gasto aparte.
Entre monedas, `implicit_rate` es destino/origen, con seis decimales ROUND_HALF_UP;
una tasa que redondea a cero produce `422 invalid_fx_rate`.

PATCH combina los campos enviados con los valores actuales y revalida el grupo
completo. Cambiar una cuenta a otra moneda exige enviar la tasa de esa pata.
Crear, editar, borrar y restaurar modifica ambas patas en una transacción de BD;
el borrado devuelve `affected_count: 2`. Restore conserva ambos IDs y falla con
`409 restore_conflict` si alguna cuenta está borrada. Las transferencias borradas
no se listan ni se obtienen individualmente. Editar, borrar o restaurar una pata
por el CRUD directo produce `409 transaction_flow_required`.

El listado ordena por `(occurred_at DESC, transfer_group_id DESC)` y usa cursor
firmado ligado al usuario, con límites de 1 a 200. Carga las dos patas de cada
página en una única consulta. Las escrituras toman un bloqueo consultivo por
usuario/grupo, seguido de referencias a cuentas con FOR SHARE en orden UUID.
Las lecturas usan MVCC y no toman bloqueos de fila. La migración reversible
`0004` exige grupo si y solo si el tipo es `transfer`, y garantiza mediante
índices únicos parciales como máximo una pata viva de cada signo por grupo.
La existencia de exactamente dos patas la garantiza el servicio atómico.

`POST /transactions/batch` acepta de 1 a 200 IDs únicos y aplica todo o nada.
Cualquier ID ajeno, inexistente o borrado (salvo restore) produce `404`;
transferencias o préstamos producen `409 transaction_flow_required`. Las acciones
son `delete`, `restore`, `add_tags`, `remove_tags` y `edit`. Solo edit permite y
exige `changes`; solo las acciones de etiquetas permiten y exigen `tag_ids`
no vacío. Edit admite exclusivamente `category_id`, `occurred_at`, `status`,
`title` y `note`; otros campos producen `422 batch_field_not_allowed`. Restore
exige cuenta y categoría sin borrar; las etiquetas deben ser propias, sin borrar,
y solo se permite una archivada si ya estaba vinculada a cada fila afectada.
Los bloqueos consultivos de las transacciones se toman en orden UUID para evitar
interbloqueos entre lotes solapados. La respuesta es ActionResult con el número
de transacciones seleccionadas.

`POST /transactions/{id}/post` confirma únicamente ingresos/gastos directos
`scheduled`; otro tipo o una fila ya publicada produce `409 not_scheduled`.
Acepta un TransactionUpdate opcional, valida los cambios con las reglas del CRUD
y pasa a `posted` en la misma transacción: el saldo cambia solo al publicar.
Puede confirmar importe, fecha, cuenta y tasa histórica al pagar. V1 no permite
volver de posted a scheduled (`409 already_posted` en PATCH y batch edit).

Diferencia respecto al contrato congelado: `/post` admite omitir el cuerpo (o
null), según la decisión explícita de T-206b; `openapi.json` todavía lo marca
obligatorio. Se conserva el JSON sin regenerarlo. No se añaden dependencias.

Verificación de T-206b: `uv sync --frozen`, `uv lock --check`, Ruff (lint y
formato), mypy estricto y PostgreSQL real con `MONETAE_REQUIRE_DB=1`. Se comprueba
`0003→0004→0003→0004` y `alembic check` sin diferencias, incluida inserción SQL
directa contra las tres restricciones. Compose arranca automáticamente en 0004.
Con curl autenticado del mismo usuario, durante un `pg_sleep(6)` que mantiene
el bloqueo consultivo y FOR UPDATE sobre ambas patas, GET /transfers respondió
HTTP 200 en **33,2 ms** y GET /transactions en **26,6 ms**, viendo el estado
confirmado anterior. Para HTTP local se usó `MONETAE_COOKIE_SECURE=false` solo en
el `.env` temporal; después se retiran Compose, volumen sintético y `.env`.

Los tests anteriores conservan su lógica: `test_migration_0003.py` sube a head
antes de comparar metadata porque la nueva cabeza es 0004; los helpers de API
permiten crear cuentas en otras monedas y transferencias; el subconjunto del
contrato aumenta de 40 a 48 operaciones y comprueba los esquemas nuevos.
`test_account_balance.py` solo añade un caso de transferencias. La prueba HTTP
de concurrencia prepara el pool antes de medir para separar el coste de conexión
inicial de una espera por bloqueo, manteniendo el umbral de 300 ms.

Resultado final: **404 tests pasan** (333 anteriores + 71 nuevos), con PostgreSQL
real obligatorio; solo permanece el aviso previo de Starlette/httpx. Ruff,
formato y mypy pasan; no hay `type: ignore` en `src`. La rama está actualizada
con `master-dev` y el diff contiene únicamente los 22 archivos autorizados.
