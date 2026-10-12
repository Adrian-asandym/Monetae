# T-519 · Pantalla «Transferir saldo» y tipo de cambio con sugerencia (ajustes 4 y 5 de Adrian)

> Lee primero `docs/STATUS.md`, `AGENTS.md`, `docs/SPEC.md` v0.7 (**RF-03**), la skill `.claude/skills/cashew-form-transaccion/SKILL.md` y `docs/tasks/T-515-ui-transaction-form.md` (reglas de estilo, tokens y hojas ya hechas). Backend listo en T-604: `POST/GET /api/v1/balance-corrections` (contrato **0.7.0**, `docs/api/openapi.json`).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama/worktree:** `codex/T-519-transfer-balance` en `/home/artur/propio2/Monetae-codex-T-519-transfer-balance` (sale de `master-dev`).
- **Dos piezas, una por lanzamiento**, un commit cada una, sin push: **10** (pantalla y guardado) → **11** (hoja «Tipo De Cambio» y sugerencia). Detente al terminar cada pieza.
- Capturas (solo lectura, ignoradas por git): `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/24.png` (pantalla) y `25.png` (diálogo ⓘ); izquierda Monetae, derecha Cashew (escala 1,25 px/dp: **las medidas en dp de esta spec son aproximadas; manda el código de Cashew + la captura**, y anota en `worker_done` la medida final y su fuente). Código de Cashew (solo lectura, GPL-3.0, cita el origen en la cabecera): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/` (busca `TransferBalancePopup` / `transferBalance` en `pages/addTransactionPage.dart`, `pages/walletDetailsPage.dart`, `pages/editWalletsPage.dart`). **Prohibido** leer o tocar `reference/backups/`. Los nombres y saldos de las capturas son de Adrian: **no los copies** a código, pruebas ni goldens.

## Qué es
Transferir saldo entre dos cuentas cualesquiera del mismo usuario (A → B). Cambiar de moneda (soles ↔ dólares) es solo el caso en que las cuentas tienen monedas distintas. Se guarda con **`POST /balance-corrections`**: dos transacciones independientes («Corrección de saldo»), un gasto en origen y un ingreso en destino, creadas a la vez. **No se guarda la tasa**: queda reflejada en los dos montos.

## Pieza 10 · Pantalla «Transferir saldo» (capturas 24 y 25)
- **Navegación:** con el ajuste del menú ⋮ «Pestaña de transferencia de saldo» activo, tocar la pestaña **Transferir** abre una **pantalla aparte** (ruta propia, sin las pestañas) con flecha atrás que vuelve al formulario. Verifícalo en Cashew.
- **AppBar:** flecha atrás, título «Transferir saldo» centrado en negrita y un ⓘ en círculo a la derecha.
- **Diálogo ⓘ (captura 25):** diálogo centrado (no hoja) sobre scrim, radio ≈ 28 dp, fondo gris muy oscuro (calibra), padding ≈ 20 dp; contenido centrado: icono ⇄ grande (≈ 56 dp, gris claro), título «Transferir saldo» negrita ≈ 28 dp y el texto exacto (≈ 18 dp): «Transfiere un importe de una cuenta a otra. Al realizar una transferencia, se crean dos transacciones de "Corrección de saldo": una de "salida de cuenta" y otra de "entrada de cuenta". Cada una es una transacción independiente y puede editarse en cualquier momento desde la lista de transacciones.» Debajo, dos botones apilados a todo el ancho (≈ 48 dp, radio ≈ 20 dp, gris azulado con texto oscuro): «OK» cierra; «Corrección De Saldo» (tono más apagado). **Verifica en Cashew qué hace «Corrección De Saldo»** (hipótesis: abre la lista o el detalle de esa categoría). Si la lista de transacciones de Monetae (`pages/transactions_page.dart`) ya puede filtrar por categoría, conéctalo; si no, handler vacío con `TODO(T-519)` y repórtalo.
- **Tarjeta de origen (arriba):** radio ≈ 18 dp, fondo gris oscuro, borde ≈ 2 dp del color de la cuenta. Título «<nombre de la cuenta> • <código>» (≈ 22 dp). Debajo, en gris pequeño, «<saldo> − <monto>» y en una segunda línea en negrita gris «= <saldo resultante>», en vivo, con el formato de montos de la skill. A la derecha: botón circular con ✕ y píldora **roja** «▼ <monto que sale>». La píldora abre la hoja «Introduce El Importe» existente. **Verifica qué hace el ✕** (hipótesis: limpiar el monto).
- **Entre las tarjetas:** botón circular con ↓ a la izquierda (**verifica en Cashew**; hipótesis: intercambia origen y destino) y, a la derecha, el campo de tasa «× 0.2916» en una caja redondeada oscura (con punto decimal, como en Cashew). En esta pieza el campo es **editable en línea**; la pieza 11 lo convierte en la hoja «Tipo De Cambio».
- **Tarjeta de destino:** mismo estilo, «<saldo> + <monto>», «= <resultado>» y píldora **verde** «▲ <monto que entra>». El monto de destino también es editable (abre la hoja de importe).
- **Cuentas:** tocar una tarjeta abre la hoja **«Seleccionar Cuenta»** de la pieza 8 (`widgets/transaction_form/account_selection_sheet.dart`). No se puede elegir la misma cuenta en origen y destino. Origen por defecto: la cuenta activa del formulario; destino: la primera cuenta distinta.
- **Misma moneda:** tasa 1, destino = origen, y se ocultan el campo «× …» y el botón «Tipos de cambio». **Verifica en Cashew qué oculta exactamente.**
- **Zona inferior:** divisoria fina; fila de fecha igual a la del formulario (calendario + «Hoy» + hora); campo de título prellenado en gris «Transferir saldo» (si queda vacío, se guarda ese título); botón píldora «Tipos de cambio» centrado (en esta pieza enfoca el campo de tasa; en la 11 abre la hoja); barra inferior **«Transferir cantidad»** con el estilo del botón principal de la skill.
- **Llegada diferida (pedido de Adrian, no está en Cashew):** por defecto ambas transacciones llevan la misma fecha y hora. Bajo la fila de fecha, una línea discreta «Llegada: igual que la salida» que al tocarse permite elegir fecha y hora de llegada (≥ salida) y volver a «igual». Se envía como `to_occurred_at`. Hoy la UI no tiene edición de transacciones existentes, por eso va aquí.
- **Guardado:** `POST /balance-corrections` con `Idempotency-Key` (reutiliza el patrón de `NewTransactionController`: un intento = una clave, reintentos, 401, errores 422 por campo). Montos con 2 decimales exactos (nunca `double`). `from_fx_rate_to_base` / `to_fx_rate_to_base`: 1 para la pierna en la moneda base del usuario; si una pierna es base y la otra no, deriva la de la otra del par (p. ej. base PEN, 40 PEN → 11,66 USD ⇒ USD a base = 40 / 11,66, 6 decimales); si **ninguna** es base, pide la tasa a base con el campo «Tipo de cambio manual» que ya existe en el formulario. `fx_rate_source` `manual`. Validación: monto > 0 y origen ≠ destino. Al guardar, vuelve a Inicio y refresca como hace el formulario.
- Commit: `feat(web): transfer balance screen with balance corrections (T-519 piece 10)`.

## Pieza 11 · Tipo de cambio ajustable con sugerencia (captura 24)
- El campo «× tasa» y el botón «Tipos de cambio» solo aparecen si las monedas son distintas.
- **Valor interno único:** la tasa es el multiplicador de origen a destino (la del «× 0.2916»). Tocar el campo o el botón abre la **misma hoja** «Tipo De Cambio» (estilo de las demás hojas):
  - indicador del origen del valor: «Sugerido · tu última compra (<fecha>)», «Sugerido · mercado» o «Manual»;
  - campo editable en **convención peruana cuando hay PEN**: «1 USD = [3,4294] PEN» (soles por unidad extranjera); en otros pares «1 [origen] = [x] [destino]»; debajo, en gris, el equivalente interno «× 0.2916»; acepta coma y punto;
  - vista previa «40 S/. → 11,66 $»;
  - botones «Aplicar» (principal), «Usar sugerido» (secundario, solo si el valor es Manual) y enlace «Ver todos los tipos de cambio» (**Monetae aún no tiene esa lista**: handler vacío + `TODO(T-519)`).
- **Edición bidireccional:** editar la tasa recalcula el destino; editar el destino recalcula la tasa (sin redondear) y la marca Manual; editar el origen recalcula el destino con la tasa vigente. Montos a 2 decimales; tasa > 0. Aritmética decimal exacta (sin `double`).
- **La tasa no se persiste** (solo existe en la pantalla).
- **Sugerencia por defecto**, en este orden, con `GET /balance-corrections` (filtros `from_account_id`, `to_account_id`, `from_currency`, `to_currency`; usa `implicit_rate`):
  1. la de la última transferencia entre **las mismas dos cuentas** (misma dirección);
  2. si no hay, la última entre **el mismo par de monedas y dirección**, aunque sean otras cuentas → «Sugerido · tu última compra (<fecha>)»;
  3. si solo existe en la **dirección contraria**, invertida, y márcalo;
  4. tasa de mercado: **no existe todavía** en Monetae (proveedor de la Fase 6; `GET /exchange-rates/suggestion` no está implementada) → salta al paso 5 y deja `TODO(T-519)`;
  5. si no hay nada, campo vacío y obligatorio.
  El par ya viene enlazado por el servidor (`transfer_group_id`): no hace falta emparejar por fecha.
- Commit: `feat(web): exchange rate sheet with suggested rate (T-519 piece 11)`.

## Reglas
- Todo color/medida nuevo en `TransactionFormColors` / `TransactionFormTokens`; textos en `app_es.arb`/`app_en.arb` (`flutter gen-l10n`), títulos de hoja en Title Case como Cashew. Formatea solo los archivos que tocas.
- Archivos permitidos: `apps/web/lib/pages/**` (página nueva + enganche en `new_transaction_page.dart`), `apps/web/lib/widgets/transaction_form/**`, `apps/web/lib/api/**` (controlador nuevo + métodos de `ApiClient`), `apps/web/lib/data/**` (DTOs de las rutas nuevas, siguiendo cómo se generan/escriben hoy), `apps/web/lib/presentation/**`, `apps/web/lib/main.dart` (ruta), `apps/web/lib/theme/monetae_theme.dart`, `apps/web/lib/l10n/*`, `apps/web/test/**`. Nada de backend ni contrato: si algo falta en la API, `ask`.

## Criterios de aceptación (por pieza)
1. Coincide con las capturas a 400×642 en oscuro (claro coherente).
2. `cd apps/web && dart analyze` sin avisos y `flutter test` **todo verde** (en `master-dev` ya no hay goldens rotos por la fecha); no dejes `test/failures/`.
3. Pruebas nuevas: navegación pestaña → pantalla → atrás; cuentas iguales bloqueadas; misma moneda oculta tasa; cálculo en vivo de saldos; cuerpo exacto de `POST /balance-corrections` (montos, `to_occurred_at`, tasas a base, título por defecto, idempotencia); en la 11, conversión peruana ↔ multiplicador, edición bidireccional y el orden de la sugerencia (1–5) con un `ApiClient` falso.
4. Goldens nuevos con texto visible (pantalla, diálogo, hoja de tasa), datos sintéticos.
5. `flutter build web --release` compila.
6. `worker_done` con archivos, verificación, TODO, diferencias con Cashew y respuestas a lo que se pide verificar (✕, ↓, «Corrección De Saldo», qué se oculta con misma moneda).
