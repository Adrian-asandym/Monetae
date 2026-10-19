# T-523 · Crear cuenta desde Inicio (F1, pedido de Adrian)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y las skills `.claude/skills/cashew-inicio-ui/SKILL.md` y `.claude/skills/cashew-form-transaccion/SKILL.md` (la UI debe ser fiel a Cashew).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-523-create-account`, sale de `master-dev`.
- **Pedido de Adrian (2026-10-18):** un botón para crear cuentas en Inicio, igual que la tarjeta «añadir» de objetivos y presupuestos, con un formulario de **nombre, color, moneda y saldo inicial** («a partir de cuánto dinero empieza la cuenta», **por defecto 0**).

## Referencias
- Cashew (solo lectura, `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/`): `pages/homePage/homePageWalletSwitcher.dart` (`AddButton` al final del carrusel de cuentas, líneas ~74 y ~198), `pages/addWalletPage.dart` (página «Añadir cuenta»: nombre, selector de color, moneda y «Empieza en» ~265–290 y ~615–645), `widgets/selectColor.dart` (selector de color). **Prohibido** leer o copiar nada de `reference/backups/`. Las capturas de Adrian no están en el VPS: manda el código de Cashew.
- Monetae: `apps/web/lib/widgets/home_accounts.dart` (carrusel de cuentas), `HomeAddCard` y `_CardStrip` en `lib/widgets/budget_goal_lists.dart` (tarjeta «añadir» ya hecha para objetivos/presupuestos: **reutilízala**, no la copies), `lib/pages/home_page.dart`, `lib/api/api_client.dart`, `lib/presentation/account_color.dart`, `lib/presentation/currency_format.dart`, `lib/presentation/decimal_input.dart` / `exact_decimal.dart`, la hoja de importe del formulario (`lib/widgets/decimal_number_pad.dart`, `lib/widgets/transaction_form/form_sheet.dart`).
- Contrato 0.7.0: `POST /api/v1/accounts` con `AccountCreate` (`name` obligatorio, `type` ∈ cash/bank/wallet/card/other, `currency` ISO de 3 letras, `initial_balance` decimal en texto, `color`, `icon`, `sort_order`). El backend ya lo implementa. Nombres de cuenta **únicos** por usuario (el servidor responde error si se repite: muéstralo legible en el formulario).

## Qué hacer
1. **Tarjeta «añadir» al final del carrusel de cuentas** de Inicio (como `AddButton` de Cashew y con el mismo estilo que la de objetivos/presupuestos). Con 0 cuentas, el bloque muestra la tarjeta en vez del texto vacío.
2. **Página «Añadir cuenta»** (pantalla completa, como `addWalletPage.dart`), fiel a Cashew en orden y estilo:
   - **Nombre** (obligatorio, sin espacios sobrantes).
   - **Color**: selector como `selectColor.dart`; guarda el color en el mismo formato que ya interpreta `presentationColor`/`accountColor`. Por defecto, el primero de la paleta o «sin color» como en Cashew.
   - **Moneda**: por defecto la `base_currency` del usuario; lista = las monedas con símbolo en `currency_format.dart` (base primero). El símbolo se ve como en el resto de la app (nunca solo el código ISO en el importe).
   - **Saldo inicial** («Empieza en»): **por defecto 0**, decimal **exacto** (nada de `double` en la ruta de envío; usa los helpers decimales existentes), con la precisión de la moneda; reutiliza la hoja de importe del formulario. Si Cashew permite saldo inicial negativo (tarjetas de crédito), permítelo igual.
   - **Tipo**: el contrato lo exige pero Cashew no lo pide: envía `type: "other"` sin mostrar campo.
   - Botón inferior «Añadir cuenta» (deshabilitado sin nombre; evita el doble envío).
3. Al guardar: `POST /accounts` (cliente con CSRF como las demás escrituras); al responder 201, volver a Inicio y **recargar** el bloque de cuentas para que aparezca la nueva (no cambiar la cuenta por defecto). Errores del servidor visibles en el formulario.
4. **i18n** es/en para todos los textos nuevos (`lib/l10n/app_es.arb`, `app_en.arb` y regenerar).
5. **Pruebas:** widget (tarjeta visible al final y con 0 cuentas; validación de nombre; saldo por defecto 0; envío del JSON exacto con `initial_balance` como texto decimal, p. ej. `"1234.50"` y `"0"`; error 409/422 mostrado; recarga tras crear) y goldens claro/oscuro de la página y del carrusel con la tarjeta.

## Archivos permitidos
`apps/web/lib/widgets/home_accounts.dart`, `apps/web/lib/pages/home_page.dart`, una página nueva `apps/web/lib/pages/add_account_page.dart` (y widgets nuevos que necesite, p. ej. `lib/widgets/color_picker.dart`), `apps/web/lib/api/api_client.dart` (solo añadir `createAccount`), `apps/web/lib/api/home_controller.dart` (si hace falta recargar cuentas), un DTO de petición nuevo en archivo propio `apps/web/lib/data/account_create_dto.dart` (**no** edites `api_dtos.dart`: lo regenera otra tarea), `apps/web/lib/widgets/budget_goal_lists.dart` (solo si hay que exponer `HomeAddCard`), `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques `lib/widgets/transaction_form/**` ni `new_transaction_page.dart` (otra tarea en paralelo), ni backend ni contrato. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen; hoy son 343).
2. `flutter build web --release` compila.
3. Goldens nuevos revisables (con texto) en claro y oscuro.
4. Sin dependencias nuevas.
5. Formatea solo los archivos que tocas (nunca `dart format lib`). Un commit `feat(web): create account from Home (T-523)`, sin push. `worker_done` con archivos tocados, decisiones de fidelidad (qué copiaste de Cashew y dónde) y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
