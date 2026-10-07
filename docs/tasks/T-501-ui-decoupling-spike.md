# T-501 — Spike de desacople de componentes de Cashew (primera tarea de la Fase 5)

> **Estado: PLANIFICADA — NO LANZAR hasta iniciar la Fase 5.**
> Origen: ADR-001 aceptado (opción A), `docs/decisions/001-ui-strategy.md`.
> Agente sugerido: **Codex** (modelo medio-alto: es razonamiento de refactor, no boilerplate). Relevo si se agota la cuota: Antigravity. Command Code, de reserva.

## Objetivo

Validar con código real la estimación del ADR-001 (6–8 tareas para desacoplar los 12 componentes visuales) desacoplando **3–4 componentes representativos** de Drift, `database.*` y `appStateSettings`, y midiendo el esfuerzo real. El resultado confirma o corrige el plan de la Fase 5 antes de comprometerla.

## Precondiciones (deben cumplirse antes de lanzarla)

- Fase 1 cerrada: `docs/api/openapi.json` con al menos transacciones, categorías y cuentas (para tipar los DTO del mock).
- Flutter instalado en el entorno del worker (`flutter --version`, `dart --version`).
- Adrian ha aprobado el inicio de la Fase 5.

## Contexto a leer

`AGENTS.md` §7, `docs/decisions/001-ui-strategy.md`, `docs/cashew-analysis/04-ui-coupling.md` (§4.3: tabla de acoplamiento por componente, §8: GPL y marca).

## Alcance

Crear el proyecto `apps/web` (Flutter Web, sin código de Cashew aparte de lo copiado abajo) y portar, **desacoplados**, estos componentes de `reference/Cashew/budget/lib/` (solo lectura):

1. **Tema:** `colors.dart` (677 líneas, 49 accesos a `appStateSettings`) → `ThemeExtension`/parámetros; acento configurable, claro/oscuro.
2. **Tarjeta de transacción:** `widgets/transactionEntry/*` (7 archivos importan `tables.dart`) → widget presentacional que recibe un modelo de vista propio (DTO), sin tipos Drift.
3. **Un gráfico:** `widgets/pieChart.dart` (usa `database.`) → widget puro que recibe una lista de datos.
4. *(Opcional si hay tiempo)* `customDelayedCurve.dart` + `fadeIn.dart` (animaciones) o `homePageHeatmap.dart`.

Pantalla de prueba: una página que renderiza los componentes con **datos mock sintéticos** (nada de datos reales), en tema claro y oscuro.

## Archivos permitidos

- `apps/web/**` (proyecto nuevo).
- `NOTICE` en `apps/web/` (atribución y aviso de modificaciones GPL-3.0).
- `docs/cashew-analysis/05-ui-spike-results.md` (resultados y medición).

No tocar: `reference/`, `services/`, `docs/SPEC.md`, `AGENTS.md`, `docs/api/openapi.json`.

## Reglas

- No importar nada de Drift, Firebase, Google Sign-In/Drive ni `appStateSettings`; sin `package:budget/...`.
- Cada archivo derivado de Cashew mantiene su procedencia y lleva el aviso de modificación; el `NOTICE` conserva la atribución al autor original (identificado en `README.md`/`pubspec.yaml` de Cashew, no inventar cabeceras de copyright).
- Sin el nombre "Cashew" ni su ícono en la UI. Textos visibles por i18n (`es`, `en`).
- Tipado estricto; sin lógica de negocio en los widgets.

## Criterios de aceptación

1. `dart analyze` sin advertencias y `flutter test` en verde (al menos un *golden test* o test de widget por componente, con datos mock).
2. `flutter build web` compila; la pantalla de prueba se ve en Chrome en claro y oscuro.
3. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` no devuelve resultados.
4. Comparación visual lado a lado con la app original (capturas o goldens) y lista de diferencias.
5. **Informe `05-ui-spike-results.md`:** por componente, horas/esfuerzo reales, líneas copiadas vs reescritas, dependencias que hubo que reemplazar, y un **nuevo estimado** de las 6–8 tareas de desacople.

## Regla de escalamiento

Si el esfuerzo medido proyecta **más de 1,5×** lo previsto (más de ~12 tareas de desacople para los 12 componentes), el worker reporta `worker_done` con el informe y el coordinador consulta a Adrian antes de seguir con la Fase 5.

## Verificación

```bash
cd apps/web
flutter pub get && dart analyze && flutter test && flutter build web
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
git diff --stat master-dev...HEAD   # solo archivos permitidos
```
