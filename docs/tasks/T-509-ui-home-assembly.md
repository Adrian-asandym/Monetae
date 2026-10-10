# T-509 — UI: ensamblado de Inicio y barra de navegación de 4 botones

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-10** (`a6cc347`; verificada por el coordinador: 146 pruebas UI, goldens revisados). Claves de `home_widgets` fijadas por el coordinador vía `ask` (ver `docs/api/README.md` §0.5.0). (Run `run_c2cebe1745b9`; OK de Adrian «P1-A»; SPEC v0.5, contrato 0.5.0). Corre **en paralelo con T-601** (API de presupuestos; archivos disjuntos).
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `high` (ensamblado con fidelidad visual a Cashew).

## Contexto

Adrian describió la disposición de Inicio que quiere, copiada de Cashew, en `docs/ui/home-layout.md` (léelo entero: es la fuente de verdad del orden). Ya existen casi todas las piezas:
- T-503: cliente HTTP y sesión;
- T-504: gráficas, tarjeta de transacción y formato peruano;
- T-507: tarjetas y listas de presupuestos y objetivos;
- T-508: `default_account_id`, `Account.transaction_count` y `CashFlowRow.cumulative_net`.

Esta tarea **arma Inicio en ese orden** y añade la **barra inferior de 4 botones** (RF-49). La API de presupuestos (T-601) y la de metas (T-602) se construyen **en paralelo** y todavía no existen en el servidor: Inicio debe funcionar sin ellas, mostrando un estado vacío.

## Leer primero

- `AGENTS.md` §7 y §11, `docs/SPEC.md` v0.5 (RF-38, RF-48, RF-49 y la regla de fidelidad visual), `docs/ui/home-layout.md`.
- `docs/api/openapi.json` 0.5.0: `CurrentUser`, `UserPreferences` (`home_widgets`, `default_account_id`), `Account`, `CashFlowRow`, `/reports/categories`, `/budgets`, `/goals`, `/transactions`.
- `docs/cashew-analysis/05-ui-spike-results.md`, en especial «Qué necesita T-509 para ensamblar Inicio» (sección T-507).
- Todo `apps/web/lib` (`main.dart`, `pages/home_page.dart`, `api/`, `widgets/`, `presentation/`).

Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`:
- `pages/homePage/homePage.dart`, `homePageUsername.dart`, `homePageWalletSwitcher.dart`, `homePageWalletList.dart`, `homePageObjectives.dart`, `homePageBudgets.dart`, `homePagePieChart.dart`, `homePageLineGraph.dart`, `homeTransactions.dart`;
- `widgets/bottomNavBar.dart`, `struct/navBarIconsData.dart`;
- el botón de añadir transacción de Inicio (búscalo desde `homePage.dart`).

**PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Alcance

1. **Barra inferior de 4 botones**, fiel a `bottomNavBar.dart`: **Inicio, Transacciones, Presupuestos, Más**, con íconos y textos i18n (es/en).
   - **Transacciones:** la página que ya existe.
   - **Presupuestos:** lista vertical de presupuestos (`BudgetCardList` de T-507) alimentada por `GET /budgets`.
   - **Más:** página sencilla con lo que ya existe (ajustes de la tarjeta de transacción, tema, cerrar sesión). Las rutas de demostración con datos sintéticos siguen accesibles desde aquí, marcadas como demo.
   - En pantallas anchas, el patrón de navegación que use Cashew en web (riel lateral si lo usa). Documenta lo que elijas.
2. **Inicio, en este orden exacto** (`docs/ui/home-layout.md`):
   1. **Saludo** con el nombre que exponga `CurrentUser` (sin nombre, saludo genérico), como `homePageUsername.dart`.
   2. **Cuentas** (`GET /accounts`): nombre, saldo con formato peruano, `transaction_count` y color de cada una.
      - Tocar una cuenta la elige como **cuenta por defecto**: `PATCH /users/me` con el objeto `preferences` **completo** (la API lo reemplaza entero: conserva `theme`, `accent_color`, `home_widgets` y `transaction_card`) y con CSRF.
      - La elegida se **resalta con el color de la cuenta**, como en Cashew. Si el `PATCH` falla, se revierte el resaltado y se muestra el error.
   3. **Objetivos** (`GoalCardList`, `GET /goals`) y 4. **Presupuestos** (`BudgetCardList`, `GET /budgets`).
      - Un **404 o 501** de esas rutas (aún no implementadas) se trata como **lista vacía** con su texto i18n, sin error visible. Otros errores muestran el error con «reintentar».
      - Arregla el **carril de la barra de presupuesto en modo oscuro**: en Cashew el carril completo se distingue (nota pendiente de T-507).
   5. **Gráfico circular** de gastos (`/reports/categories`), con leyenda de las **3 categorías con más gasto**.
      - **Deslizar a la izquierda** muestra el de **ingresos**, con las mismas características (carrusel o `PageView`, como Cashew), con indicador de página.
   6. **Gráfico de líneas** acumulado con `cumulative_net` de `/reports/cash-flow`: sube con ingresos y baja con gastos. La UI **no suma**: usa el valor del servidor.
   7. Las **25 últimas transacciones** (`GET /transactions?limit=25`, orden del servidor) con la tarjeta configurable de T-502/T-504.
   8. **Botón cuadrado «+» destacado**, como el de Cashew. Abre la ruta `/transactions/new`, que en esta tarea es solo un **marcador** («Próximamente» i18n). El formulario es T-510.
3. **`home_widgets`:** si la preferencia trae orden u ocultación de bloques, respétala. Si viene vacía, se usa el orden de arriba.
4. **Estados:** carga, error con reintento y vacío por bloque, de modo que un bloque que falla no rompe los demás. Un 401 devuelve al acceso, como hace el cliente actual.
5. **Sin aritmética de dinero** en la UI. Las proporciones de barras y gráficos son solo presentación, igual que en T-507.
6. Los datos sintéticos (`mock_*`) quedan **solo** en las rutas demo y en las pruebas, nunca en el Inicio real.

## Archivos permitidos

`apps/web/**`, `apps/web/NOTICE` y `docs/cashew-analysis/05-ui-spike-results.md` (sección nueva «T-509»).
- No tocar `services/`, `infra/`, `docs/SPEC.md`, `docs/api/`, `docs/ui/`, `docs/tasks/`, `AGENTS.md`, `reference/`, `img/`.
- Sin dependencias nuevas salvo que un componente portado las exija (consúltalo antes con `ask`).
- Si el contrato no basta, **pregunta**, no lo cambies.

## Criterios de aceptación (con salidas en `worker_done`)

1. `dart analyze` sin avisos y `flutter test` en verde. Pruebas nuevas:
   - **Goldens claro y oscuro** de Inicio con datos (cliente falso, datos sintéticos) y de Inicio vacío (presupuestos y metas en 404/501); goldens de la barra de 4 botones y de la página Presupuestos.
   - Orden de los bloques igual a `home-layout.md`, y respeto de `home_widgets`.
   - Elegir la cuenta por defecto envía `PATCH /users/me` con `preferences` **completo** y `X-CSRF-Token`; prueba también que un fallo revierte el resaltado.
   - Deslizar el circular cambia de gastos a ingresos, y la leyenda muestra solo 3 categorías.
   - La línea usa `cumulative_net` tal cual (sin sumar en la UI).
   - Se piden exactamente 25 transacciones.
   - 404/501 en `/budgets` y `/goals` dan estado vacío; 500 da error con reintento; 401 vuelve al acceso.
2. `flutter build web --release` compila. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío. Procedencia y aviso GPL en cada archivo derivado y en `NOTICE`.
3. **Informe (sección T-509):** diferencias frente a Cashew (con el archivo de origen de cada bloque), lo que quede para T-510 y para la revisión de Adrian.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

**Importante:**
- El coordinador hará la prueba con servidor real (pila `monetae-review`, puertos 5433/8000/8080, servida desde `Monetae-master-dev`): **no** la toques ni levantes contenedores. Trabaja solo en tu worktree.
- Disco justo (≈ 3 GB libres): no dupliques cachés; borra tu `build/` si necesitas espacio.

Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante un caso no cubierto, usa `orca orchestration ask`. Reporta `worker_done` una sola vez.
