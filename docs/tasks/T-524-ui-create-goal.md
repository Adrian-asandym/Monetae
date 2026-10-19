# T-524 · Crear objetivo (meta) desde Inicio (F1 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y las skills `.claude/skills/cashew-inicio-ui/SKILL.md` y `.claude/skills/cashew-form-transaccion/SKILL.md`.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-524-create-goal`, sale de `master-dev` **después** de integrar T-523 (reutiliza su selector de color, su selector de moneda y su patrón de página).
- **Decisión:** Adrian, 2026-10-18 (F1 = A, una tarea por pantalla).

## Contexto
- La tarjeta «añadir» del carrusel de objetivos ya existe (`GoalCardList.onCreate` en `lib/pages/home_page.dart`, hoy `TODO(T-514)`).
- T-523 añadió «Añadir cuenta» (`lib/pages/add_account_page.dart`), un selector de color y el selector de moneda: **reutilízalos** (extráelos a widgets compartidos si quedaron privados, sin cambiar su aspecto).
- Contrato: `POST /api/v1/goals` con `GoalCreate` (`name`, `kind` ∈ `save`/`spend`, `target_amount` positivo en texto decimal, `currency`, `due_on` opcional, `color` `#RRGGBB` opcional, `icon` opcional). Backend ya implementado (T-602).
- Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/pages/addObjectivePage.dart` (orden y estilo: nombre, ícono/color, importe objetivo, fecha de inicio/fin, tipo ahorro/gasto). **Prohibido** `reference/backups/`.

## Qué hacer
1. Tocar la tarjeta «añadir» de objetivos abre la página **«Añadir objetivo»**, fiel a Cashew: nombre (obligatorio), tipo **ahorro/gasto** (por defecto ahorro, como Cashew), importe objetivo (decimal exacto, positivo; hoja de importe del formulario), moneda (por defecto la base), fecha límite opcional, color. Ícono: fuera de alcance (envía `null`, `TODO(F1)`), salvo que Cashew no lo muestre.
2. Al guardar: `POST /goals`; con 201 volver a Inicio y recargar el bloque de objetivos. Errores del servidor visibles; sin doble envío.
3. i18n es/en: inserta tus claves en los `.arb` **justo después de la clave `addGoalLabel`**; añade `createGoal` **al final** de la clase del cliente HTTP.
4. Pruebas: tarjeta abre la página; validación; JSON exacto (`target_amount` como texto, `due_on` `YYYY-MM-DD` o ausente); recarga tras crear; goldens claro/oscuro.

## Archivos permitidos
Página nueva `apps/web/lib/pages/add_goal_page.dart`, `apps/web/lib/pages/home_page.dart` (solo el `onCreate` de objetivos), `apps/web/lib/api/api_client.dart` (solo `createGoal`), `apps/web/lib/api/home_controller.dart` (recarga), los widgets compartidos de T-523 (color/moneda/página) para extraerlos sin cambiar aspecto, DTO de petición en archivo propio, `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques `new_transaction_page.dart`, `transactions_page.dart`, `transaction_form/**`, backend ni contrato. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen).
2. `flutter build web --release` compila.
3. Goldens revisables (con texto); los de «Añadir cuenta» no cambian (si cambian, explica por qué).
4. Formatea solo los archivos que tocas. Un commit `feat(web): create goal from Home (T-524)`, sin push. `worker_done` con archivos tocados, decisiones de fidelidad y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
