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
