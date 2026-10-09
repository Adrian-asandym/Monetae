# T-501 — Spike de desacople de componentes de Cashew (primera tarea de la Fase 5)

> **ESTADO: LANZADA el 2026-10-09** (OK de Adrian al inicio de la Fase 5). Spec revisada ese día contra el repositorio: rutas corregidas, fuente de Cashew por ruta absoluta y criterios visuales que el worker sí puede cumplir.
> Origen: ADR-001 aceptado (opción A), `docs/decisions/001-ui-strategy.md`.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (razonamiento de refactor, no boilerplate). Relevo: Antigravity. Command Code, de reserva.

## Objetivo

Validar con código real la estimación del ADR-001 (6–8 tareas para desacoplar los 12 componentes visuales) desacoplando **3–4 componentes representativos** de Drift, `database.*` y `appStateSettings`, y midiendo el esfuerzo real. El resultado confirma o corrige el plan de la Fase 5 antes de comprometerla.

## Precondiciones (cumplidas el 2026-10-09)

- `docs/api/openapi.json` 0.3.0 con transacciones, categorías y cuentas (para tipar los DTO del mock).
- Flutter 3.47.6 en `~/flutter` (`export PATH="$HOME/flutter/bin:$PATH"`; `flutter --version`, `dart --version`).
- Adrian aprobó el inicio de la Fase 5.

## Fuente de Cashew (SOLO LECTURA) y privacidad

- El código de Cashew **no está en tu worktree** (`reference/` está ignorado por git). Léelo desde la ruta absoluta **`/home/artur/propio2/Monetae/reference/Cashew/budget/`** (en adelante `CASHEW/`). No lo modifiques ni lo copies entero.
- **PROHIBIDO** leer, listar o abrir `/home/artur/propio2/Monetae/reference/backups/`: contiene datos financieros reales de Adrian. Nada fuera de `CASHEW/` dentro de `reference/`.
- Todos los datos de la pantalla y de las pruebas son **mock sintéticos**.

## Contexto a leer

`AGENTS.md` §7, `docs/decisions/001-ui-strategy.md`, `docs/cashew-analysis/04-ui-coupling.md` (§4.3: tabla de acoplamiento por componente; §8: GPL y marca), `docs/api/openapi.json` (esquemas de transacción, categoría y cuenta).

## Alcance

Crear el proyecto `apps/web` (Flutter Web; `flutter create --platforms web`, sin código de Cashew aparte de lo portado abajo) y portar, **desacoplados**, estos componentes de `CASHEW/lib/`:

1. **Tema:** `lib/colors.dart` (677 líneas, 49 accesos a `appStateSettings`) → `ThemeExtension`/parámetros; acento configurable, claro/oscuro.
2. **Tarjeta de transacción:** `lib/widgets/transactionEntry/*` (7 archivos importan `tables.dart`) → widget presentacional que recibe un modelo de vista propio (DTO tipado según el contrato), sin tipos Drift.
3. **Un gráfico:** `lib/widgets/pieChart.dart` (usa `database.`) → widget puro que recibe una lista de datos.
4. *(Opcional si hay tiempo)* `lib/struct/customDelayedCurve.dart` + `lib/widgets/fadeIn.dart` (animaciones) o `lib/pages/homePage/homePageHeatmap.dart`.

Pantalla de prueba: una página que renderiza los componentes con **datos mock sintéticos**, conmutable entre tema claro y oscuro.

## Archivos permitidos

- `apps/web/**` (proyecto nuevo; **no** versionar `build/`, `.dart_tool/` ni artefactos: respeta el `.gitignore` que genera `flutter create`).
- `apps/web/NOTICE` (atribución y aviso de modificaciones GPL-3.0).
- `docs/cashew-analysis/05-ui-spike-results.md` (resultados y medición).

No tocar: `reference/`, `services/`, `infra/`, `docs/SPEC.md`, `AGENTS.md`, `docs/api/openapi.json`. Dependencias nuevas de pub solo si el componente portado las necesita (p. ej. la librería de gráficos que use Cashew, **en su misma versión mayor**); justifícalas en el informe.

## Reglas

- No importar nada de Drift, Firebase, Google Sign-In/Drive ni `appStateSettings`; sin `package:budget/...`.
- Cada archivo derivado de Cashew conserva su procedencia (ruta de origen) y lleva el aviso de modificación; el `NOTICE` conserva la atribución al autor original (identificado en `README.md`/`pubspec.yaml` de Cashew; **no inventes cabeceras de copyright**). Monetae y Cashew son GPL-3.0.
- Sin el nombre "Cashew" ni su ícono en la UI. Textos visibles por i18n (`es`, `en`; `flutter gen-l10n`).
- Tipado estricto; sin lógica de negocio en los widgets.

## Criterios de aceptación

1. `dart analyze` sin advertencias ni *infos* y `flutter test` en verde: al menos un **test de widget y un golden por componente**, en **claro y oscuro**, con datos mock.
2. `flutter build web --release` compila (el coordinador sirve `build/web` y Adrian la revisa en Chrome; tú no necesitas abrir un navegador).
3. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` no devuelve resultados.
4. **Diferencias frente al original** listadas en el informe a partir de la lectura del código de Cashew (qué se conservó, qué cambió y por qué). No intentes compilar ni ejecutar Cashew.
5. **Informe `docs/cashew-analysis/05-ui-spike-results.md`:** por componente, esfuerzo real (tiempo aproximado), líneas copiadas vs reescritas, dependencias que hubo que reemplazar, y un **nuevo estimado** de las 6–8 tareas de desacople.

## Regla de escalamiento

Si el esfuerzo medido proyecta **más de 1,5×** lo previsto (más de ~12 tareas de desacople para los 12 componentes), reporta `worker_done` con el informe; el coordinador consulta a Adrian antes de seguir con la Fase 5. Ante un caso no cubierto: `orca orchestration ask`.

## Verificación (con salidas en `worker_done`)

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web
flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Reporta `worker_done` una sola vez.
