# T-504 — UI: gráficas de ingresos y gastos fieles a Cashew + ajustes de la tarjeta

> **ESTADO: LANZADA el 2026-10-09** (Run `run_c2cebe1745b9`; OK de Adrian al plan G4 + T-504 ∥ T-506). Corre **en paralelo con T-506** (API de reportes; archivos disjuntos). T-507 (presupuestos y metas) va después.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (desacople de varios componentes de Cashew con fidelidad visual).

## Contexto

Adrian aprobó la prueba de T-503 y pide:
1. Las **gráficas de ingresos y gastos**, siempre **fieles a Cashew** (colores, barras de progreso, íconos).
2. Dos ajustes de la tarjeta de transacción:
   - la **etiqueta de la cuenta** (método de pago) con **su propio color**, distinto por cuenta;
   - **sin etiqueta de tipo de moneda**: la moneda se percibe por el **símbolo** del importe.

La API de reportes la implementa T-506 en paralelo. Aquí la UI consume **el contrato 0.4.0** (`/reports/cash-flow`, `/reports/categories`) con `MockClient` y con datos sintéticos.

## Leer primero

- `AGENTS.md` §7 y `docs/SPEC.md` v0.4 (§5.10 RF-38/RF-39 y la regla de **fidelidad visual**, §9 multimoneda).
- `docs/api/openapi.json` 0.4.0: `CashFlowRow`, `CategoryReportRow`, `ReportTotal`, `CurrencyTotal`, parámetros de ambos reportes y `Account.color`.
- `docs/tasks/T-506-api-reports-cashflow-categories.md`, **sección Reglas 4–5**: valores por defecto, periodos vacíos en ceros y orden. La UI debe asumir exactamente eso.
- `docs/cashew-analysis/05-ui-spike-results.md` (estimación y secciones T-502/T-503).
- El código de `apps/web` (cliente `lib/api/`, `transaction_card*.dart`, `transaction_presenter.dart`, tema, `category_pie_chart.dart`).

Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`, en especial:
- `pages/homePage/homePageAllSpendingSummary.dart`;
- `pages/homePage/homePageLineGraph.dart` y `widgets/lineGraph.dart`;
- `widgets/incomeExpenseTabSelector.dart` y `widgets/slidingSelectorIncomeExpense.dart`;
- `widgets/barGraph.dart`;
- `pages/homePage/homePageHeatmap.dart` (opcional);
- `widgets/transactionEntry/transactionEntryTag.dart` y `transactionLabel.dart` (etiqueta de cuenta);
- `struct/defaultPreferences.dart`.

**PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Alcance

1. **Componentes desacoplados (como en T-501).** Sin Drift, `database.*` ni `appStateSettings`; entradas tipadas puras; procedencia y aviso GPL en cada archivo derivado y en `NOTICE`.
   - **Resumen de ingresos y gastos** (`homePageAllSpendingSummary`): totales del periodo con sus colores de ingreso y gasto.
   - **Gráfico de líneas** (`lineGraph`/`homePageLineGraph`): evolución por periodo a partir de `CashFlowRow`.
   - **Selector ingreso/gasto** (`incomeExpenseTabSelector`/`slidingSelectorIncomeExpense`), que alimenta el gráfico circular de T-501 con `CategoryReportRow`.
   - **Gráfico de barras** (`barGraph`), si Cashew lo usa para la misma vista.
   - *(Opcional si hay tiempo)* mapa de calor (`homePageHeatmap`).
2. **Cliente de reportes** en `lib/api/`.
   - Métodos tipados para ambos endpoints con DTO generados desde el contrato.
   - Cada fila trae su desglose `by_currency` y su total en la moneda de reporte; los importes son cadenas decimales, **sin aritmética de dinero en la UI**.
   - Cuando `unconverted_count` es mayor que 0, la vista avisa con un texto i18n discreto.
3. **Pantalla de inicio (primera versión).** Resumen, selector, gráfico de líneas y gráfico circular, con el aspecto de Cashew.
   - Con la sesión real, toma los datos de la API. Si el endpoint aún no existe (404 o 501 mientras T-506 no esté integrada), muestra un estado vacío i18n, sin romper.
   - En la ruta de demostración, usa datos sintéticos.
4. **Ajustes de la tarjeta.**
   - **Etiqueta de la cuenta:** con `show_account` activo, la cuenta se muestra como una **etiqueta coloreada** al estilo de `transactionEntryTag`, con el **color de la cuenta** (`Account.color`). Si el color es nulo o no es válido, usa un color de reserva determinista por cuenta (estable, derivado del id) dentro de la paleta de Cashew.
   - **Símbolo de moneda:** los importes se muestran **siempre con el símbolo** (S/, US$, €…, vía `intl`, con el locale del usuario) y **nunca** con el código ISO; elimina cualquier etiqueta o texto de tipo de moneda en la tarjeta y en las nuevas gráficas.
   - Si dos monedas comparten símbolo en una misma vista (por ejemplo `$`), desambigua con el símbolo de `intl` específico de la moneda (US$, CA$…), nunca con el código. Documenta qué hiciste.

## Archivos permitidos

`apps/web/**`, `apps/web/NOTICE` y `docs/cashew-analysis/05-ui-spike-results.md` (sección «T-504»). No tocar `services/`, `infra/`, `docs/SPEC.md`, `docs/api/`, `AGENTS.md`, `reference/`, `img/`. Dependencias nuevas: solo si un componente portado las exige, y con justificación (si no es trivial, `ask`).

## Criterios de aceptación (con salidas en `worker_done`)

1. `dart analyze` sin avisos y `flutter test` verde. Goldens en **claro y oscuro** de:
   - resumen;
   - gráfico de líneas, con y sin periodos vacíos;
   - selector + gráfico circular;
   - pantalla de inicio de demostración;
   - tarjeta con **etiquetas de cuenta de colores distintos** y con importes PEN/USD/EUR **sin código de moneda**.
2. **Pruebas del cliente con `MockClient`:**
   - parámetros enviados;
   - lectura de `ReportTotal`;
   - aviso de `unconverted_count`;
   - estado vacío ante 404/501.
3. `flutter build web --release` compila; `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío; ningún PNG de categoría de Cashew en el repo.
4. **Informe (sección T-504):** diferencias frente a Cashew por componente y una **estimación actualizada** de lo que falta de la Fase 5.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

**Importante:** hay una pila de revisión de Adrian (`monetae-review`, puertos 5433/8000/8080) que **no** debes tocar. Si quieres probar con servidores reales, usa otro proyecto y otros puertos, y bájalo al terminar.

Commits pequeños en inglés (`feat(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante un caso no cubierto, `orca orchestration ask`. Reporta `worker_done` una sola vez.
