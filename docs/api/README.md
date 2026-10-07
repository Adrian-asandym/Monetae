# Contrato OpenAPI inicial de Monetae

`openapi.json` es el contrato **contract-first** de V1: OpenAPI 3.1.0, basado en
`docs/SPEC.md` v0.3, `docs/ARCHITECTURE.md` v0.1 y ADR-002/003/004/006 aceptadas.
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
que dinero, tasas o porcentajes se serialicen como flotantes. Las nueve pruebas
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
  desembolso atómico) y movimiento; mismo usuario/operación/cuerpo devuelve el
  resultado previo, clave repetida con otro cuerpo da 409.
- Préstamos: `principal` ya incluye el desembolso; este no vuelve a sumar al saldo.
  `status` y `outstanding` son `readOnly`. Cada desembolso/pago indica su propia
  cuenta, importe original y tasa histórica. Interés/ajuste/condonación no mueven
  dinero. Las propuestas de reparto e interés no persisten nada. Al guardar un
  pago se envían `interest_part` y `principal_part` editables; se valida suma y
  límites. Capital no cuenta en gasto/ingreso; interés pagado sí, en categoría de
  sistema y fecha de pago (ADR-003). No existe operación de liquidación.
- RF-22: un pago excesivo propuesto devuelve 409 `loan_overpayment`, saldo, exceso,
  moneda y opciones `adjustment` / `income_expense`. No se persiste saldo negativo.
  El cliente presenta opciones y permite resolver y reintentar; 409 no es una
  prohibición definitiva del cobro. Automatizar esa resolución requiere ratificar
  su reparto y atomicidad (observaciones siguientes).
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
  idempotencia por usuario. Exportación es descarga de JSON completo o CSV por tabla.
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
| D | USD 50 sin cambios al rechazar 60 | Problem 409 con exceso USD 10 y ambas salidas RF-22 |
| E | PEN 1000 → 950 → 830 → 800 → 0 | Pagos variables 50, 120, 30 y 800 en fechas distintas |

A, B, C y E terminan `settled`; D sigue `open` mientras no se resuelva el exceso.
El ejemplo A contiene cuatro movimientos de libro mayor y tres transacciones
monetarias: el interés registrado no crea una transacción (ADR-003).

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

Estas observaciones no modifican SPEC, ARCHITECTURE ni decisiones aceptadas:

1. **Orientación de `fx_rate_applied`**: ARCHITECTURE §10.3 pide confirmarla en T-105.
   Este contrato explicita la convención ilustrada por C (moneda de cuenta por
   unidad de préstamo, PEN/USD 3.800000), con `account_amount / fx_rate_applied`.
   Debe ratificarse antes del backend; un cociente inverso requiere cambiar contrato
   y fixtures juntos. No se eligió proveedor automático (ADR-004).
2. **Ajustes y condonaciones**: el reparto entre interés y capital no está definido
   (ARCHITECTURE §10.2). Se exponen movimientos y fórmulas existentes, sin inventar
   nuevos campos de asignación. RF-22 ofrece opciones y el ejemplo D valida el
   rechazo, pero falta precisar reparto, registro conjunto y política de reintento
   de la resolución del exceso para que RF-22 no genere flujos inconsistentes.
3. **Preferencias de presentación**: RF-38/39 exige widgets, tema y acento;
   ARCHITECTURE `users` no incluye almacenamiento para estos campos. El contrato
   los declara bajo preferences; el coordinador debe ampliar el esquema antes
   de migraciones. Cambio de moneda base tampoco define cómo preservar tasas
   `fx_rate_to_base` cuyo destino anterior no está persistido explícitamente.
4. **Conversión a moneda de reporte seleccionada**: SPEC §9.5 la requiere, pero
   el esquema guarda solo tasa hacia la base. Falta la política para cruces
   históricos sin tasa, especialmente si cambia la base; nunca usar la tasa de hoy.
5. **Normalización mensual/anual**: daily/weekly e intervalos tienen contrato,
   pero faltan convenciones exactas de días/semanas para totales comparables.
   No se fija una fórmula contable nueva ni ejemplos que la presupongan.
6. **OIDC y reautenticación**: el estado/PKCE pre-login y su almacenamiento,
   confirmación de vinculación de cuenta, y la prueba de reautenticación para PIN
   (sobre todo usuario solo Google) requieren detalle en implementación.
   `current_password` es opcional en forma, pero la operación exige reautenticación
   por contraseña u OIDC. No se puede configurar PIN solo enviando el PIN.
7. **Bloqueo Fase 6**: estado por sesión, desafío WebAuthn, nombres exactos de los
   objetos estándar y payload de cada aviso se precisan antes de implementar.
   Las rutas iniciales siguen exigiendo sesión; PIN no sustituye login y cinco
   fallos obligan a volver a autenticar. PIN obligatorio es el respaldo si se
   habilita bloqueo/WebAuthn; no se ofrece eliminarlo ni dejar solo WebAuthn.
8. **Importación**: conservación temporal de la copia para apply, expiración de
   dry-run y resolución manual de elementos ambiguos no están especificadas.
   El contrato liga hash y dry-run y conserva reporte; no supone que reconocer
   una advertencia resuelva automáticamente un préstamo ambiguo.
9. **Idempotencia**: retención y almacenamiento de claves quedan para Fase 2;
   ARCHITECTURE no describe tabla de claves. Cuenta y moneda del movimiento
   pertenecen a su transacción, sin añadir columnas al libro mayor desde aquí.
10. **RF-06 y adjuntos RF-08**: existen category_rules/attachments en arquitectura,
    pero no están en los recursos asignados a T-102. No se han añadido operaciones
    fuera de alcance; asignar contratos de administración/almacenamiento si la UI
    los necesita. Export completo necesita esquema de archivo versionado antes
    de ofrecer restauración JSON (solo importación Cashew está contratada aquí).

## Resultado de validación

- Redocly: contrato válido, **0 errores**, aviso local justificado arriba.
- `python3 -I scripts/check_openapi.py`: **81 paths, 118 operaciones, 121 esquemas**;
  todas las comprobaciones pasan con Python 3.9.
- `python3 -I scripts/check_openapi.py --self-test`: **9 pruebas** pasan.
- Se validan también ruff, formato, mypy estricto y pytest del script, usando
  herramientas en un entorno temporal fuera del repo; sin dependencias nuevas
  en el proyecto. Los checks backend completos no aplican: no se ha creado backend.
