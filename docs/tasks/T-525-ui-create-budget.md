# T-525 · Crear presupuesto desde Inicio y Presupuestos (F1 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y las skills `.claude/skills/cashew-inicio-ui/SKILL.md` y `.claude/skills/cashew-form-transaccion/SKILL.md`.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-525-create-budget`, sale de `master-dev` **después** de integrar T-524 (reutiliza sus widgets compartidos de color, moneda, importe y página).
- **Decisión:** Adrian, 2026-10-18 (F1 = A, una tarea por pantalla).

## Contexto
- La tarjeta «añadir» del carrusel de presupuestos ya existe (`BudgetCardList.onCreate` en `lib/pages/home_page.dart` y en `lib/pages/budgets_page.dart`, hoy `TODO(T-514)` o sin conectar).
- Contrato: `POST /api/v1/budgets` con `BudgetCreate`: `name`, `period` ∈ `daily`/`weekly`/`monthly`/`custom`, `start_on` (fecha), `end_on` (obligatoria y ≥ `start_on` solo si `custom`), `amount` positivo (texto con dos decimales), `currency`, `scope` ∈ `all`/`selected` («solo transacciones añadidas»), `category_limits` opcional (`[{category_id, limit_amount}]`), `color` `#RRGGBB` opcional. Backend ya implementado (T-601). Lee su servicio para saber qué hace `category_limits` antes de exponerlo.
- Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/pages/addBudgetPage.dart` (nombre, importe, periodo y repetición, fechas, categorías incluidas, «solo transacciones añadidas», color). **Prohibido** `reference/backups/`.

## Qué hacer
1. Tocar «añadir» en el carrusel de presupuestos (Inicio y la pestaña Presupuestos) abre **«Añadir presupuesto»**, fiel a Cashew en orden y estilo: nombre (obligatorio), importe (positivo, exacto; hoja de importe), moneda (por defecto la base), periodo (diario/semanal/mensual/personalizado; Cashew permite «cada N»: el contrato no, así que N = 1 fijo, `TODO(F1)`), fecha de inicio (por defecto hoy, zona del usuario), fecha de fin solo si es personalizado, «solo transacciones añadidas» (`scope`), color.
2. Categorías: si `category_limits` en el backend significa «categorías incluidas», ofrécelo como en Cashew (selección de categorías de gasto); si significa otra cosa o no está claro, **pregunta** (`ask`) antes de exponerlo.
3. Al guardar: `POST /budgets`; con 201 volver y recargar el bloque o la página de presupuestos. Errores del servidor visibles; sin doble envío.
4. i18n es/en: inserta tus claves en los `.arb` **justo después de la clave `addBudgetLabel`**; añade `createBudget` **al final** de la clase del cliente HTTP.
5. Pruebas: abre desde Inicio y desde Presupuestos; validación (nombre, importe > 0, fin ≥ inicio en personalizado); JSON exacto (`amount` con dos decimales, fechas `YYYY-MM-DD`, `end_on` ausente salvo personalizado); recarga; goldens claro/oscuro.

## Archivos permitidos
Página nueva `apps/web/lib/pages/add_budget_page.dart`, `apps/web/lib/pages/home_page.dart` (solo el `onCreate` de presupuestos), `apps/web/lib/pages/budgets_page.dart` (solo el `onCreate`), `apps/web/lib/api/api_client.dart` (solo `createBudget`), `apps/web/lib/api/home_controller.dart` (recarga), los widgets compartidos de T-523/T-524 sin cambiar su aspecto, DTO de petición en archivo propio, `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques `new_transaction_page.dart`, `transactions_page.dart`, `transaction_form/**`, backend ni contrato. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen).
2. `flutter build web --release` compila.
3. Goldens revisables (con texto); los de «Añadir cuenta» y «Añadir objetivo» no cambian (si cambian, explica por qué).
4. Formatea solo los archivos que tocas. Un commit `feat(web): create budget (T-525)`, sin push, sin merge ni rebase sobre `master-dev`. `worker_done` con archivos tocados, decisiones de fidelidad y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
