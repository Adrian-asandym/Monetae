# Análisis de Cashew (Fase 0)

> Consolidado por Claude · 2026-10-07 · Run `run_bef8ecfc67a7`.
> Cada sección fue escrita por un worker (Antigravity) y **revisada por el coordinador contra el código** de `reference/Cashew/budget/` (citas de archivo:línea comprobadas con `sed -n`; métricas reproducidas con `grep`/`wc`). Solo se inspeccionó el **esquema** de los respaldos reales, nunca filas ni valores.

| # | Documento | Tema |
|---|-----------|------|
| 1 | [01-data-model.md](cashew-analysis/01-data-model.md) | Tablas Drift, columnas, relaciones, migraciones, correspondencia con SPEC §6 |
| 2 | [02-loans.md](cashew-analysis/02-loans.md) | Cómo Cashew modela préstamos y por qué produce P1–P3 |
| 3 | [03-backup-format.md](cashew-analysis/03-backup-format.md) | Formatos de respaldo (SQLite / CSV), desfase v46 vs v48, fixtures sintéticos |
| 4 | [04-ui-coupling.md](cashew-analysis/04-ui-coupling.md) | Acoplamiento de la UI a Drift/Firebase; insumo de ADR-001 |

## Conclusiones

1. **Hipótesis de SPEC §2 confirmada** (02-loans). Cashew tiene dos modelos de préstamo:
   - *Pago único*: una sola transacción `credit`/`debt`. "Liquidar" solo pone `paid = false` (`lib/struct/upcomingTransactionsFunctions.dart:393`); las sumas de saldo filtran `paid == true` (`lib/database/tables.dart:6773`). Por eso el dinero "vuelve" a la cuenta original (P3) y el préstamo deja de computar (P1). El propio autor dejó comentada la solución (cobro como transacción aparte, `:398-406`).
   - *Largo plazo*: un `Objective` de tipo `loan` + transacciones con `objectiveLoanFk` y polaridad opuesta. El interés como transacción normal no tiene ese vínculo, así que no mueve el saldo (P2).
2. **Modelo de datos** (01-data-model): 10 tablas, PK `text` UUID desde la migración v36→v37, monto **firmado** en BD (`fixTransactionPolarity`, `tables.dart:7579`), sin tabla de tipos de cambio (viven en `AppSettings.settingsJSON`). Monetae no tiene equivalente directo de `people`, `loans`, `loan_movements`, `exchange_rates`.
3. **Respaldos** (03-backup-format): el `.sql` es una base SQLite completa; el `.csv` **excluye `paid = false`** (`lib/widgets/exportCSV.dart:88`), lo que elimina los préstamos únicos saldados. El importador debe leer SQLite primero.
4. **Desfase de versión:** el respaldo real es **schema v48**; la copia en `reference/Cashew` es **v46** (faltan `tags` y `transaction_to_tag_links`, y columnas `archived`, `emoji_icon_name`, `default_title`). El CSV real también trae columnas que el código de referencia no genera.
5. **Acoplamiento de UI** (04-ui-coupling): 84 archivos de UI importan `tables.dart`, 338 llamadas `database.*`, 135 `StreamBuilder`, 1.346 accesos a `appStateSettings`. De 17 componentes visuales candidatos a reutilizar, **solo 3 son copiables tal cual**, 12 requieren desacoplar y 2 reescribir. El fork integral resulta **demasiado invasivo** según CLAUDE.md §6.

## Puntos que requieren decisión de Adrian

- **ADR-001** (estrategia de UI): ver `docs/decisions/001-ui-strategy.md`.
- **Actualizar `reference/Cashew` a la versión que corresponda a schema v48** (tags y columnas nuevas). Afecta al fixture del importador y a qué UI se toma como referencia visual.
- **Fuente del importador:** `AGENTS.md` §4 sugiere preferir el `.csv`; el análisis recomienda SQLite (el CSV pierde préstamos únicos saldados, ids, presupuestos y reglas).
- **Etiquetas (`tags`) existen en la app real de Adrian y no están en SPEC:** ¿entran en V1, se importan como notas/etiquetas de transacción, o se descartan?

## Limitaciones conocidas

- `02-loans.md` analiza P3 a fondo para préstamos únicos; para préstamos de largo plazo no confirma explícitamente cómo se cobra por otra cuenta (las sumas se calculan por billetera, `tables.dart:5627-5672`). Verificar en Fase 1 con el fixture del ejemplo B.
- Las estimaciones de esfuerzo de 04 (24–32, 28–38 y 36–48 tareas) son de orden de magnitud y se solapan entre estrategias 1 y 2; la diferencia real está en calidad y riesgo, no en horas.
