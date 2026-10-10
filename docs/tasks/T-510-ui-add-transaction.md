# T-510 — UI: formulario de nueva transacción (gasto/ingreso) fiel a Cashew

> **ESTADO: POR LANZAR** (Run `run_c2cebe1745b9`; OK de Adrian «P1-A»; SPEC v0.5, contrato 0.5.0). Va **después de T-509** (integrada en `master-dev`, `a6cc347`).
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `high`.

## Contexto

T-509 dejó el botón «+» de Inicio abriendo `/transactions/new`, que hoy es un marcador («Próximamente»). Esta tarea construye el formulario real de **gasto o ingreso**, fiel a `addTransactionPage.dart` de Cashew, y propone la **cuenta por defecto** (RF-48). Las transferencias y los préstamos tienen sus propios recursos y **no** entran aquí.

## Leer primero

- `AGENTS.md` §7 y §11, `docs/SPEC.md` v0.5 (§5 transacciones, RF-48, regla de fidelidad visual), `docs/ui/home-layout.md`.
- `docs/api/openapi.json` 0.5.0: `TransactionCreate` (signo: `income > 0`, `expense < 0`; moneda igual a la de la cuenta; `fx_rate_to_base` y `fx_rate_source` obligatorios), `POST /transactions` (cabeceras `X-CSRF-Token` e `Idempotency-Key`, errores), `CurrentUser.base_currency`, `Category`, `Account`.
- `docs/cashew-analysis/05-ui-spike-results.md` (secciones T-503, T-504 y T-509).
- Todo `apps/web/lib`: `api/api_client.dart`, `session/`, `pages/new_transaction_page.dart`, `pages/home_page.dart`, `presentation/currency_format.dart`, `widgets/category_icon.dart`, `presentation/account_color.dart`.

Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`:
- `pages/addTransactionPage.dart` (estructura, orden de campos y cambio gasto/ingreso);
- `widgets/selectAmount.dart` (teclado numérico) y `widgets/selectCategory.dart` (rejilla de categorías);
- `SelectTitle` y el selector de fecha que use esa página.

**PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Alcance

1. **`/transactions/new`** sustituye al marcador. Se abre desde el «+» de Inicio y también desde la pestaña Transacciones, si Cashew tiene allí ese botón.
2. **Campos, en el orden y con el aspecto de Cashew:**
   - **Gasto/ingreso:** conmutador; por defecto, gasto.
   - **Importe:** teclado numérico de `selectAmount.dart`, con un máximo de 2 decimales. Se maneja **siempre como texto decimal**, nunca como `double`. La moneda se ve por el **símbolo** de la cuenta (S/, US$…), sin código ISO, con el formato peruano.
   - **Categoría:** rejilla con los íconos de T-502, alimentada por `GET /categories` y filtrada por gasto o ingreso si el contrato lo permite. Es opcional (`category_id` admite null).
   - **Cuenta:** se preselecciona `preferences.default_account_id`. Si es null, la primera cuenta activa en el orden del servidor. Se puede cambiar; cada cuenta lleva su color.
   - **Título:** opcional, como en Cashew. El contrato acepta `""` (sin `minLength`): si está vacío, se envía `""`; **no inventes un valor por defecto**.
   - **Fecha y hora:** por defecto, ahora en `America/Lima` (zona del usuario).
   - **Nota:** opcional.
   - Las etiquetas quedan **fuera** de esta tarea.
3. **Tipo de cambio:**
   - Si la moneda de la cuenta es igual a `base_currency`: `fx_rate_to_base = "1.000000"` y `fx_rate_source = "manual"` (el contrato `ExchangeRate` exige **exactamente 6 decimales**; corregido el 2026-10-10 tras la pregunta del worker).
   - Si es distinta: campo **obligatorio** de tasa (texto decimal de hasta 6 decimales, mayor que 0, **normalizado a 6 decimales** sobre el texto: «3.8» → `"3.800000"`) con `fx_rate_source = "manual"`. La sugerencia automática no existe aún (Fase 6).
4. **Estado:** `posted`. Si la fecha elegida es **futura**, `scheduled`, como las «próximas» de Cashew. Que quede visible en el formulario.
5. **Envío:**
   - Cuerpo exacto de `TransactionCreate`. El **signo** se pone sobre el texto decimal (`"-12.50"` en un gasto); sin aritmética de coma flotante.
   - `X-CSRF-Token` y un `Idempotency-Key` UUID por intento de guardado. **Reintentar el mismo envío reutiliza la misma clave**; editar el formulario genera una nueva.
   - **Éxito (201):** volver a Inicio, que se **recarga** (cuentas, gráficos y últimas transacciones), con un aviso i18n.
   - **Errores:**
     - 422 junto al campo correspondiente cuando se pueda identificar; si no, un aviso general;
     - 401 vuelve al acceso;
     - 409 y 5xx muestran un error con opción de reintentar.
6. **Validación local** antes de enviar: importe mayor que 0, cuenta elegida y tasa válida cuando hace falta. El botón de guardar está desactivado mientras se envía (sin doble envío).

## Archivos permitidos

`apps/web/**`, `apps/web/NOTICE` y `docs/cashew-analysis/05-ui-spike-results.md` (sección nueva «T-510»).
- No tocar `services/`, `infra/`, `docs/SPEC.md`, `docs/api/`, `docs/ui/`, `docs/tasks/`, `AGENTS.md`, `reference/`, `img/`.
- Sin dependencias nuevas salvo que un componente portado las exija (consúltalo antes con `ask`). Para el UUID, mira primero si ya hay uno disponible.

## Criterios de aceptación (con salidas en `worker_done`)

1. `dart analyze` sin avisos y `flutter test` en verde. Pruebas nuevas:
   - **Goldens claro y oscuro** del formulario en gasto y en ingreso, y con cuenta en moneda extranjera (campo de tasa visible).
   - La cuenta por defecto viene preseleccionada; sin preferencia, se elige la primera activa.
   - El **cuerpo del `POST`** es exacto: gasto `"-12.50"` e ingreso `"12.50"`; moneda de la cuenta; tasa `"1.000000"` en PEN y la tasa escrita, normalizada a 6 decimales, en USD; `scheduled` con fecha futura.
   - El teclado no produce más de 2 decimales y se trabaja con texto, sin `double`.
   - El reintento reutiliza el `Idempotency-Key` y un cambio en el formulario lo renueva.
   - Doble pulsación = un solo envío.
   - 422 se muestra; 401 vuelve al acceso; con 201 se vuelve a Inicio y se recarga.
2. `flutter build web --release` compila. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío. Procedencia y aviso GPL en cada archivo derivado y en `NOTICE`.
3. **Informe (sección T-510):** diferencias frente a Cashew y lo que quede pendiente (etiquetas, transferencias, préstamos, sugerencia de tasa).

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

**Importante:**
- El coordinador hará la prueba con servidor real (`POST /transactions` con CSRF, en la pila `monetae-review`): **no** la toques ni levantes contenedores. Trabaja solo en tu worktree.
- Disco justo (≈ 3 GB libres): borra tu `build/` al terminar si necesitas espacio.

Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante un caso no cubierto, usa `orca orchestration ask`. Reporta `worker_done` una sola vez.
