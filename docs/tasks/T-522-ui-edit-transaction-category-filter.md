# T-522 · Editar transacciones guardadas y filtrar la lista por categoría (F2 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` (§6 reglas de negocio) y la skill `.claude/skills/cashew-form-transaccion/SKILL.md`.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-522-edit-transaction`, sale de `master-dev` **después** de integrar T-520, T-521 y T-523.
- **Decisión:** Adrian, 2026-10-18 (F2 = A).

## Contexto
- La UI solo crea transacciones: `NewTransactionPage(editing: true)` hoy solo cambia el título (`lib/pages/new_transaction_page.dart:55`).
- La llegada diferida de una «Corrección de saldo» (transferencia a lo Cashew, T-604/T-519) solo se fija al crear; el contrato permite editar cada pierna por separado.
- El botón «Corrección De Saldo» del diálogo ⓘ de «Transferir saldo» no hace nada (`lib/pages/transfer_balance_page.dart:318`) porque la lista no filtra por categoría.
- Contrato **0.8.0** (T-521): `GET /api/v1/transactions?category_id=…` acepta **uno o varios** uuid (OR); `GET/PATCH /api/v1/transactions/{id}` (`TransactionUpdate`: `account_id`, `kind`, `category_id`, `amount`, `occurred_at`, `status`, `title`, `note`, `fx_rate_to_base`, `fx_rate_source`, `tag_ids`). Las piernas de una corrección conservan `kind` y categoría (`422 correction_role_immutable`). Transferencias (`/transfers`) y movimientos de préstamo se editan por su propio recurso.
- Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/pages/addTransactionPage.dart` (modo edición: misma página precargada). **Prohibido** `reference/backups/`.

## Qué hacer
1. **Abrir una transacción guardada:** tocar una tarjeta en la lista de Transacciones y en «Últimas transacciones» de Inicio abre el formulario en **modo editar**, precargado (tipo, importe exacto, cuenta, categoría, título, notas, fecha y hora, tasa, etiquetas si las hay), con el título «Editar transacción» como en Cashew.
2. **Guardar:** `PATCH /transactions/{id}` solo con los campos cambiados, decimales exactos (nunca `double` en la ruta de envío), CSRF como el resto. Al volver, la lista e Inicio se recargan (usa el mecanismo de revisión de la sesión que ya existe).
3. **Casos especiales:**
   - **Pierna de «Corrección de saldo»** (categoría con `system_key` `balance_correction_*`): tipo y categoría **bloqueados** (visibles, no editables); fecha y hora (llegada diferida), importe, título y notas editables.
   - **Transferencia** (`kind = transfer`) o **préstamo** (`loan_id` no nulo): abrir en solo lectura con una nota breve (la edición va por su recurso; `TODO(F2)`), sin botón de guardar.
4. **Filtro por categoría en Transacciones:** la página acepta un filtro de una o varias categorías, lo muestra como chip con ✕ para quitarlo y pide al servidor `category_id` repetido. Un botón de filtro abre la hoja de categorías existente para elegir una.
5. **Conectar el botón «Corrección De Saldo»** del diálogo ⓘ: abre Transacciones filtrada por las **dos** categorías de sistema de corrección (búscalas por `system_key`, nunca por nombre).
6. **i18n** es/en de los textos nuevos. Para evitar conflictos con otra tarea paralela, inserta tus claves nuevas en los `.arb` **justo después de la clave `transferCorrectionCategory`**, y añade tus métodos del cliente HTTP **junto a `createTransaction`**.
7. **Pruebas:** precarga exacta; PATCH solo con cambios (JSON exacto); pierna de corrección con tipo/categoría bloqueados y fecha editable; transferencia/préstamo en solo lectura; filtro con dos categorías (query con `category_id` repetido); botón del diálogo; recarga tras guardar; goldens del modo editar en claro y oscuro.

## Archivos permitidos
`apps/web/lib/pages/new_transaction_page.dart`, `apps/web/lib/api/new_transaction_controller.dart`, `apps/web/lib/pages/transactions_page.dart`, `apps/web/lib/api/transaction_feed.dart`, `apps/web/lib/pages/transfer_balance_page.dart` (solo el botón del diálogo), `apps/web/lib/api/api_client.dart` (`transaction(id)`, `updateTransaction`, filtro de categorías), `apps/web/lib/widgets/transaction_card_list.dart` y `transaction_card.dart` (solo para pasar el toque), `apps/web/lib/pages/home_page.dart` (solo el toque de la lista de Inicio), `apps/web/lib/widgets/transaction_form/**` si hace falta bloquear controles, un DTO de petición nuevo en archivo propio si el generado no sirve, `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques backend, contrato ni `api_dtos.dart`. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen).
2. `flutter build web --release` compila.
3. Goldens nuevos revisables (con texto).
4. Formatea solo los archivos que tocas. Un commit `feat(web): edit saved transactions and filter list by category (T-522)`, sin push. `worker_done` con archivos tocados y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
