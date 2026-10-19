# T-527 · Reordenar y ocultar componentes de Inicio (botón «Editar») (F1 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y la skill `.claude/skills/cashew-inicio-ui/SKILL.md` (§1 «Saludo y botón Editar»).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo medium.
- **Rama:** `codex/T-527-edit-home`, sale de `master-dev`.
- **Decisión:** Adrian, 2026-10-18 (F1 = A, una tarea por pantalla).

## Contexto
- La píldora «Editar» de Inicio existe y no hace nada (`lib/pages/home_page.dart`, `HomeEditButton`, `TODO(T-514)`).
- El orden y la visibilidad viven en el servidor: `preferences.home_widgets` (lista ordenada de claves visibles; `defaultHomeWidgets` y `visibleHomeWidgets` en `home_page.dart`; claves documentadas en `docs/api/README.md`). Se guarda con `ApiClient.updatePreferences` (`PATCH /users/me`), igual que la tarjeta de transacción.
- Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/pages/editHomePage.dart` (lista con asa de arrastre e interruptor por componente). **Prohibido** `reference/backups/`.

## Qué hacer
1. «Editar» abre la página **«Editar Inicio»**, fiel a Cashew: una fila por componente conocido (cuentas, objetivos, presupuestos, gráfico de categorías, gráfico de línea, últimas transacciones) con su nombre, interruptor de visibilidad y asa para **reordenar por arrastre** (`ReorderableListView`). Componentes ocultos al final, en el orden por defecto.
2. Guardado como en Cashew (inmediato al cambiar o al salir: elige lo que haga Cashew y dilo en el `worker_done`), enviando `home_widgets` = claves visibles en orden, conservando el resto de preferencias. Al menos un componente visible (no permitas ocultar el último).
3. Al volver, Inicio refleja el nuevo orden sin recargar la página del navegador. Errores de guardado visibles y estado revertido.
4. i18n es/en: inserta tus claves en los `.arb` **justo después de la clave `editHome`**. No añadas métodos al cliente HTTP salvo que sea imprescindible (ya existe `updatePreferences`).
5. Pruebas: abre desde «Editar»; reordenar envía el JSON exacto; ocultar y mostrar; no se puede ocultar el último; error revierte; goldens claro/oscuro de la página.

## Archivos permitidos
Página nueva `apps/web/lib/pages/edit_home_page.dart`, `apps/web/lib/pages/home_page.dart` (solo el `onPressed` de «Editar» y, si hace falta, exponer los nombres de los componentes), `apps/web/lib/session/session_controller.dart` (solo si la actualización de preferencias necesita un método nuevo), `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques `new_transaction_page.dart`, `transactions_page.dart`, `transaction_form/**`, `budgets_page.dart`, backend ni contrato. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen).
2. `flutter build web --release` compila.
3. Goldens revisables (con texto).
4. Formatea solo los archivos que tocas. Un commit `feat(web): edit Home order and visibility (T-527)`, sin push, sin merge ni rebase sobre `master-dev`. `worker_done` con archivos tocados, decisiones de fidelidad y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
