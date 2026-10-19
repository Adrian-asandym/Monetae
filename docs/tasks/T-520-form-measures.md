# T-520 · Medidas de los ajustes 1 y 2 del formulario iguales a Cashew (TAM = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y la skill `.claude/skills/cashew-form-transaccion/SKILL.md` (sección de medidas: px de captura vs dp).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo medium.
- **Rama:** `codex/T-520-form-measures`, sale de `master-dev`.
- **Decisión:** Adrian, 2026-10-18 (TAM = A).

## Problema
En las pautas v2 del formulario (piezas 7 y 8 de T-515) se usaron números literales que en realidad son px de la captura (escala 1,25), no dp:
- **Ajuste 1** (commit `fdb955e`): nombre de la categoría bajo el monto en la cabecera de importe: hoy **20 dp y una línea**. Cashew: **18 dp, hasta 2 líneas** (`addTransactionPage.dart` ~1973).
- **Ajuste 2** (commit `3fa1af9`): filas de la hoja «Seleccionar Cuenta» (`lib/widgets/transaction_form/account_selection_sheet.dart`): hoy nombre **20 dp** y radio de fila **12**. Cashew: nombre **18 dp** y radio **15** (`widgets/radioItems.dart`).

Código de Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/`. **Prohibido** leer o copiar nada de `reference/backups/`. Las capturas de Adrian no están en el VPS: manda el código de Cashew.

## Qué hacer
1. Iguala las medidas de los ajustes 1 y 2 a las de Cashew (tamaño, número de líneas y elipsis, radio, y cualquier padding de esas filas que en Cashew sea distinto: compruébalo en el código citado, no lo adivines).
2. Regenera **solo** los goldens afectados y revísalos (con texto visible).
3. Actualiza la tabla de medidas de la skill `cashew-form-transaccion` si cita los valores viejos.

## Archivos permitidos
`apps/web/lib/pages/new_transaction_page.dart` y `apps/web/lib/widgets/transaction_form/**` (solo lo necesario para estas medidas), `apps/web/test/**` (pruebas y goldens afectados), `.claude/skills/cashew-form-transaccion/SKILL.md`. Otro archivo: pregunta (`ask`). No toques `api_client.dart`, `home_*`, l10n ni backend.

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen con el número de pruebas; hoy son 343).
2. Una prueba de widget comprueba los valores nuevos (18 dp, 2 líneas para la categoría; 18 dp y radio 15 en la fila de cuenta).
3. Goldens regenerados solo los afectados.
4. `flutter build web --release` compila.
5. Formatea solo los archivos que tocas (nunca `dart format lib`). Un commit `fix(web): match Cashew measures for category name and account rows (T-520)`, sin push. `worker_done` con archivos tocados, valores antes/después y la cita del código de Cashew usada.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`. Si el shell tiene umask 077, no importa para esta tarea (no usa Docker).
