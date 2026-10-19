# T-526 · Pantalla de detalle de categorías (F1 = A)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y la skill `.claude/skills/cashew-inicio-ui/SKILL.md` (sección del gráfico circular: «la lista de categorías con porcentajes y el selector de mes no van en Inicio: irán a una pantalla de detalle que se abre al tocar la tarjeta»).

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama:** `codex/T-526-category-detail`, sale de `master-dev` **después** de integrar T-522 (usa su filtro por categoría en Transacciones).
- **Decisión:** Adrian, 2026-10-18 (F1 = A, una tarea por pantalla).

## Contexto
- Inicio muestra el circular de gastos/ingresos (`lib/widgets/home_category_carousel.dart`). El widget `lib/widgets/home_category_details.dart` (lista ordenada con porcentajes + selector de mes) quedó **sin conectar** (`TODO(T-514)`).
- Datos: `GET /api/v1/reports/categories` (ya usado por Inicio, ver `lib/api/home_controller.dart` y `report_query.dart`), en la zona horaria del usuario.
- T-522 añadió a Transacciones un filtro por una o varias categorías (`category_id` repetido, contrato 0.8.0). Para el mes, usa `date_from`/`date_to` si el filtro de T-522 no los expone aún (extiéndelo de forma mínima).
- Cashew (solo lectura): `/home/dev/propio2/Monetae/reference/Cashew/budget/lib/pages/homePage/homePagePieChart.dart` (~345: tocar una categoría abre `TransactionsSearchPage` filtrada por categoría y periodo) y `pages/walletDetailsPage.dart` (resumen de gasto por categorías con selector de periodo). **Prohibido** `reference/backups/`.

## Qué hacer
1. Tocar la tarjeta del circular en Inicio abre **«Detalle de categorías»**: selector de mes (anterior/siguiente), el circular del mes, alternar gastos/ingresos como en Inicio, y la lista ordenada de categorías con importe y porcentaje (reutiliza `HomeCategoryDetails` y los componentes existentes; quita su `TODO`).
2. Tocar una categoría de la lista abre **Transacciones filtrada por esa categoría y ese mes** (como Cashew).
3. Moneda y conversiones como en Inicio (moneda de reporte; `unconverted_count` visible si existe, como ya lo trate Inicio).
4. i18n es/en: inserta tus claves en los `.arb` **justo después de la clave `categoryDistribution`**.
5. Pruebas: abre desde Inicio; cambiar de mes pide el rango correcto (zona del usuario); alternar ingresos; tocar categoría abre Transacciones con `category_id` y fechas; goldens claro/oscuro.

## Archivos permitidos
Página nueva `apps/web/lib/pages/category_detail_page.dart`, `apps/web/lib/widgets/home_category_details.dart`, `apps/web/lib/widgets/home_category_carousel.dart` (solo el toque de la tarjeta), `apps/web/lib/pages/home_page.dart` (solo pasar el toque), `apps/web/lib/pages/transactions_page.dart` y `apps/web/lib/api/transaction_feed.dart` (solo si el filtro necesita fechas), `apps/web/lib/api/home_controller.dart` o un controlador nuevo para el detalle, `apps/web/lib/l10n/**`, `apps/web/test/**`. **No** toques backend ni contrato. Otro archivo: pregunta (`ask`).

## Criterios de aceptación
1. `cd apps/web && dart analyze` sin avisos; `flutter test` todo verde (pega el resumen).
2. `flutter build web --release` compila.
3. Goldens revisables (con texto).
4. Formatea solo los archivos que tocas. Un commit `feat(web): category detail screen (T-526)`, sin push, sin merge ni rebase sobre `master-dev`. `worker_done` con archivos tocados, decisiones de fidelidad y la salida de verificación.

## Entorno
`export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"`.
