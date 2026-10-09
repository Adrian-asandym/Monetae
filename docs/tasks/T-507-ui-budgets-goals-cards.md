# T-507 — UI: tarjetas de presupuestos y objetivos fieles a Cashew (con barras de progreso)

> **ESTADO: LANZADA el 2026-10-09** (Run `run_c2cebe1745b9`; OK de Adrian; SPEC v0.5, contrato 0.5.0). Corre **en paralelo con T-508** (API; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (desacople con fidelidad visual).

## Contexto

Adrian quiere en Inicio los **objetivos** y los **presupuestos** como en Cashew: con su **color** y su **barra de progreso** (ver `docs/ui/home-layout.md`). La API de presupuestos y metas es de la **Fase 6**, así que aquí se construyen los **componentes presentacionales** con datos **sintéticos**, tipados con los DTO del contrato 0.5.0 (`Budget`, `Goal`, que ahora incluyen `color` y, en las metas, `icon`). El **ensamblado de Inicio** con la disposición completa y la barra de navegación de 4 botones es una tarea posterior (T-509): **no** reorganices Inicio aquí.

## Leer primero

`AGENTS.md` §7, `docs/SPEC.md` v0.5 (§5.6 presupuestos, §5.7 metas, §5.10 y la regla de fidelidad visual), `docs/ui/home-layout.md`, `docs/api/openapi.json` 0.5.0 (`Budget`, `Goal`, `ReportTotal`; `/reports/budgets`, `/reports/goals`), `docs/cashew-analysis/05-ui-spike-results.md` y el código de `apps/web` (tema, `currency_format.dart` con el formato peruano «S/ 1,234.50» de T-504b, `account_color.dart`, `category_icon.dart`, `tool/generate_dtos.py`).

Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`, en especial:
- `widgets/budgetContainer.dart`, `widgets/progressBar.dart` y `widgets/animatedCircularProgress.dart`;
- `pages/homePage/homePageBudgets.dart` y `pages/homePage/homePageObjectives.dart`;
- `pages/objectivesListPage.dart` y `pages/budgetsListPage.dart` (cómo se dibujan objetivo y presupuesto);
- `struct/defaultPreferences.dart`.

**PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Alcance

1. Regenera los DTO desde el contrato **0.5.0** con `tool/generate_dtos.py`.
2. **Tarjeta de presupuesto** (`budgetContainer`):
   - nombre, periodo, gastado / total y restante, con la **barra de progreso** de Cashew en el **color del presupuesto** (o el acento si es nulo);
   - estado «excedido» como lo muestra Cashew;
   - marca del día actual dentro del periodo, si Cashew la dibuja.
3. **Tarjeta de objetivo** (objetivos de Cashew):
   - ícono (catálogo o SVG propio, con el componente de T-502), nombre, progreso / meta, fecha límite si existe;
   - progreso **circular o lineal según Cashew**, en el **color del objetivo**;
   - tipo ahorro o gasto según `Goal.kind`.
4. **Listas horizontales/verticales** como en Inicio de Cashew (`homePageBudgets`, `homePageObjectives`), con estado vacío i18n.
5. **Ruta de demostración** con datos sintéticos: varios presupuestos (en curso, casi agotado, excedido) y objetivos (a medias, completado), en PEN y USD.
6. **Sin aritmética de dinero en la UI:**
   - los importes y restantes vienen del contrato (`spent_amount`, `remaining_amount`, `progress_amount`, `report_total`);
   - la **proporción de la barra** es solo presentación (cociente de decimales del contrato, acotado entre 0 y 1). Documenta cómo la calculas.

## Archivos permitidos

`apps/web/**`, `apps/web/NOTICE` y `docs/cashew-analysis/05-ui-spike-results.md` (sección «T-507»). No tocar `services/`, `infra/`, `docs/SPEC.md`, `docs/api/`, `docs/ui/`, `AGENTS.md`, `reference/`, `img/`. Sin dependencias nuevas salvo que un componente portado las exija (con `ask`).

## Criterios de aceptación (con salidas en `worker_done`)

1. `dart analyze` sin avisos y `flutter test` verde. Goldens **claro y oscuro** de:
   - presupuesto en curso, casi agotado y excedido;
   - objetivo a medias y completado;
   - listas con y sin datos.
   Además, pruebas de la proporción de la barra (0, parcial, 1 y más de 1 acotado) y del formato peruano en las tarjetas.
2. `flutter build web --release` compila; `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío; procedencia y aviso GPL en cada archivo derivado y en `NOTICE`.
3. **Informe (sección T-507):** diferencias frente a Cashew y la lista de lo que necesitará T-509 para el ensamblado de Inicio.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && python3 -I tool/generate_dtos.py && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

**Importante:** hay una pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080) servida desde `Monetae-master-dev/apps/web/build`: **no** la toques. Trabaja solo en tu worktree.

Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
