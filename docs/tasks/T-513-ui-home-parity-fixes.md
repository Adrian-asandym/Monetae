# T-513 — UI: ajustes finales de Inicio (seguimiento de T-512)

> **ESTADO: LANZADA el 2026-10-10** (Run `run_c2cebe1745b9`). Adrian pidió **pasar el trabajo de UI de Antigravity a Codex** por la demora y las entregas fallidas de T-512.
> Agente: **Codex**, modelo `gpt-6.1-sol`, esfuerzo `high`.

## Contexto

T-512 aplicó la skill `.claude/skills/cashew-inicio-ui/SKILL.md` a Inicio y está integrada en `master-dev` (`2903271`). Quedan cuatro detalles conocidos frente a la skill. Las observaciones de la revisión visual de Adrian llegarán después, en otra tarea; aquí **no** cambies nada más.

## Leer primero

- La skill completa, `docs/tasks/T-512-ui-home-cashew-parity.md` y la sección «T-512» de `docs/cashew-analysis/05-ui-spike-results.md`.
- El código de `apps/web/lib`: `pages/home_page.dart`, la lista de transacciones de Inicio (`HomeTransactionRow` y su lista), `presentation/budget_calculations.dart`, `presentation/currency_format.dart` y los clientes de reportes (`api/report_feed.dart`, `api/report_query.dart`).
- Cashew (solo lectura): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/` → `widgets/budgetContainer.dart` (`getAmountPerDayString`), `pages/objectivesListPage.dart` (~línea 947), `pages/homePage/homeTransactions.dart` y la cabecera de día de `widgets/transactionEntries.dart`.
- **Capturas** (solo lectura, datos reales; **nunca** copiarlas al repositorio): `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/5.png` y `6.png`.
- **PROHIBIDO** `/home/artur/propio2/Monetae/reference/backups/`.

## Cambios (solo estos)

1. **Botón final de la lista:** el texto debe ser **«Ver todas las transacciones»** (i18n es/en), con la píldora de la skill §7. Lleva a la pestaña Transacciones.
2. **Encabezado de día:** fecha **sin año cuando es el año en curso** («jueves, 8 de octubre»). Con un año anterior, sí lo muestra. Usa la zona del usuario.
3. **Total neto del día** a la derecha del encabezado, en gris, con el formato de montos de la skill.
   - Sale de `GET /reports/cash-flow?period=daily` para el rango de fechas de las transacciones mostradas (campo `net`, moneda de reporte). **No lo sumes en la UI.**
   - Si el reporte falla, el encabezado se muestra sin total y el resto de Inicio sigue funcionando.
4. **Redondeo de «X/día»** (presupuestos y objetivos): Cashew calcula `(total − objetivo) / días` y lo **redondea al formatear**, no hacia arriba.
   - Usa redondeo **medio-arriba a 2 decimales** con `Decimal` (sin `double`): 1265,50 / 23 = 55,0217… → «55,02».
   - Prueba también un caso que termine en ,xx5.

## Archivos permitidos

`apps/web/**` y `docs/cashew-analysis/05-ui-spike-results.md` (sección nueva «T-513»).
- No tocar `services/`, `infra/`, `scripts/`, `docs/SPEC.md`, `docs/api/`, `docs/tasks/`, `.claude/`, `reference/`.
- Sin dependencias nuevas.

## Criterios de aceptación (con salidas reales en `worker_done`)

1. `dart analyze` → «No issues found!» y `flutter test` todo en verde. Pruebas nuevas:
   - texto del botón e intención de navegación;
   - fecha con y sin año;
   - el total del día viene del reporte (cliente falso) y no de sumar en la UI;
   - el encabezado sin total cuando el reporte falla;
   - redondeo 55,02 y el caso ,xx5.
2. **Goldens claro y oscuro** de Inicio regenerados **y versionados en el mismo commit**. Abre los PNG y confirma que **se ve el texto** (fuente DM Sans, no rectángulos).
3. `flutter build web --release` compila. `grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib` vacío.
4. Al terminar, `git status --short` vacío: sin goldens sin commit, sin `test/failures/`, sin scripts sueltos.

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo "limpio"
cd ../.. && git status --short && git diff --stat master-dev...HEAD
```

**Importante:**
- No toques la pila de revisión de Adrian (`monetae-review`, 5433/8000/8080). Si necesitas ver la app, usa una pila propia (`COMPOSE_PROJECT_NAME=monetae-t513`, puertos 5471/8011/8091) con `scripts/seed_review_data.py`, y bájala al terminar.
- Disco justo (≈ 2,4 GB): borra `build/` al terminar.

Commits pequeños en inglés (`fix(web):`, `test(web):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. Ante una duda real, `orca orchestration ask`. Reporta `worker_done` una sola vez.
