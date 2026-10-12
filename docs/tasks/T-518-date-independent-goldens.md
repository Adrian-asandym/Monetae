# T-518 · Goldens independientes de la fecha

> Lee primero `docs/STATUS.md` y `AGENTS.md`.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo medium.
- **Rama/worktree:** `codex/T-518-date-goldens` en `/home/artur/propio2/Monetae-codex-T-518-date-goldens` (sale de `master-dev`).

## Problema
10 goldens fallan cada día, también en `master-dev`, porque los widgets calculan «X/día para N días» y el estado del periodo con `DateTime.now()`:
`apps/web/lib/widgets/goal_card.dart:78` (`goalPerDayLabel(l, goal, DateTime.now())`) y `apps/web/lib/widgets/budget_card.dart:149,169` (`today ?? DateTime.now()`). Las páginas `home_page.dart:62` y `budgets_page.dart:66` también leen la hora del sistema.
Afectados: `test/budgets_goals_test.dart` (goal half, goals_horizontal/vertical_data), `test/home_v2_test.dart` (Home v2) y `test/home_assembly_test.dart` (assembled home data), en claro y oscuro.

## Qué hacer
- Introduce **un único reloj inyectable** (p. ej. `typedef Now = DateTime Function();` provisto por un `InheritedWidget`/parámetro con valor por defecto `DateTime.now`), y úsalo en `GoalCard`, `BudgetCard`, `HomePage` y `BudgetsPage` en lugar de `DateTime.now()`. Comportamiento en producción idéntico.
- En las pruebas, fija la fecha a un día coherente con los datos sintéticos (octubre de 2026) y regenera **solo** los goldens afectados, con texto visible.
- Sin dependencias nuevas (no añadas el paquete `clock`). Sin cambios de lógica, contrato ni backend.

## Archivos permitidos
`apps/web/lib/widgets/goal_card.dart`, `apps/web/lib/widgets/budget_card.dart`, `apps/web/lib/pages/home_page.dart`, `apps/web/lib/pages/budgets_page.dart`, un archivo nuevo `apps/web/lib/presentation/clock.dart` (o similar), `apps/web/lib/main.dart` si hace falta proveer el reloj, `apps/web/test/**` (pruebas y goldens afectados). Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos y `flutter test` **todo verde** (pega el resumen).
2. Prueba de regresión: las pruebas afectadas pasan aunque el reloj del sistema sea otro día (demuéstralo, p. ej., con una prueba que use dos fechas de sistema distintas o explicando por qué ya no dependen de `DateTime.now()`).
3. `grep -rn "DateTime.now()" lib` solo queda en el valor por defecto del reloj (y en `report_demo_page.dart`, que es una demo, si no la tocas).
4. Goldens regenerados revisables (con texto) y solo los afectados.
5. `flutter build web --release` compila.
6. Formatea solo los archivos que tocas. Un commit `test(web): date-independent goal and budget goldens (T-518)` sin push; `worker_done` con archivos tocados y resumen de verificación.
