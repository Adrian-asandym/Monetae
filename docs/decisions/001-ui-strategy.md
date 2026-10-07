# ADR-001 — Estrategia de interfaz de usuario

- **Estado:** PROPUESTO (pendiente de decisión de Adrian)
- **Fecha:** 2026-10-07
- **Autor:** Claude (coordinador)
- **Insumo:** `docs/cashew-analysis.md` y `docs/cashew-analysis/04-ui-coupling.md`

## Contexto

SPEC §1 pide la misma experiencia visual de Cashew sobre un backend propio. AGENTS.md §3 asumía un fork de Cashew (Flutter) con la capa de datos sustituida por la API. La Fase 0 midió ese supuesto:

- La UI no tiene capa de repositorio: 84 archivos importan `tables.dart`, 338 llamadas directas `database.*`, 135 `StreamBuilder` ligados a streams de Drift, 1.346 accesos a un `Map<String, dynamic>` global (`appStateSettings`).
- `tables.dart` (7.668 líneas) mezcla esquema, lógica de negocio y consultas, e importa páginas y widgets de UI además de Firestore.
- Firebase (auth, firestore), Google Drive y Google Sign-In están integrados en sincronización y adjuntos.
- Los préstamos (origen de P1–P3) están en la UI y en la base como "objetivos" (`addObjectivePage`, `objectivePage`, `objectivesListPage`); un fork obligaría a reescribirlos igualmente.
- De 17 componentes visuales que se quieren conservar (gráficos, tarjeta de transacción, tema, animaciones): 3 copiables tal cual, 12 requieren desacoplar, 2 reescribir.
- Corregido en revisión: las PK de Cashew **sí son UUID texto**, así que no hay incompatibilidad de identificadores.

CLAUDE.md §6 exige consultar a Adrian cuando el fork resulta demasiado invasivo. Este ADR es esa consulta.

## Opciones

### A (recomendada) — UI propia en Flutter Web, reutilizando y desacoplando los componentes visuales de Cashew
Cliente generado desde `docs/api/openapi.json`; se copian a `apps/web` solo tema, gráficos (`fl_chart`), tarjeta de transacción, animaciones e iconos, desacoplándolos de Drift y de `appStateSettings`.
- **Pros:** sin Drift, Firebase ni Drive; toda la lógica en el backend (AGENTS.md §6–7); P1–P5 se construyen contra `/loans`, `/subscriptions` y export propio, sin heredar el modelo de objetivos; tipado fuerte.
- **Contras:** hay que maquetar la navegación y las pantallas; fidelidad visual depende de cuánto se reutilice (riesgo para el criterio "interfaz reconocible", SPEC §14).
- **Esfuerzo (orden de magnitud):** 24–32 tareas de 1–2 h.
- **Obligación GPL:** los archivos derivados de Cashew mantienen GPL-3.0, `NOTICE` con atribución y aviso de modificaciones; sin nombre ni ícono Cashew (AGENTS.md §7). *No es asesoría legal.*

### B — Fork de Cashew con fachada REST que reemplaza `FinanceDatabase`
Conserva las 54 pantallas y su navegación.
- **Pros:** máxima fidelidad visual inmediata; no hay SQLite/WASM en el navegador.
- **Contras:** hay que reimplementar ~261 métodos (105 `Stream`, 156 `Future`) con consultas agregadas sin equivalente REST directo; se arrastran `appStateSettings`, el acoplamiento circular y el modelo de préstamos como objetivos, que hay que reescribir de todos modos; difícil cumplir "la UI no contiene reglas de negocio".
- **Esfuerzo:** 28–38 tareas. Riesgo medio-alto.

### C — Fork de Cashew con Drift como caché local y sincronización REST bidireccional
- **Pros:** la UI casi no cambia y funciona offline.
- **Contras:** duplica la lógica de negocio en el cliente (contradice AGENTS.md §6–7), exige resolver conflictos entre SQLite y PostgreSQL, `sql-wasm` en la web, y `syncClient.dart` solo intercambia archivos SQLite completos vía Drive (P5 no se resuelve).
- **Esfuerzo:** 36–48 tareas. Riesgo crítico. Adelanta el problema de sincronización de ADR-005 (V4).

## Recomendación

**Opción A.** Las estimaciones de A y B se solapan en horas; la diferencia está en que A no hereda deuda (Drift, estado global, objetivos-préstamo) y cumple las reglas de arquitectura desde el principio. El costo real de A es de fidelidad visual, y se mitiga empezando por los componentes de mayor valor (tema, gráficos de inicio, tarjeta de transacción) y validando con capturas de Cashew.

## Consecuencias si se acepta A

- `apps/web` es un proyecto Flutter nuevo con arquitectura por capas y cliente OpenAPI; la carpeta `budget/` de Cashew no se copia entera.
- Primera tarea de UI: *spike* de desacople de 3–4 componentes (tema, `transactionEntry`, un gráfico) contra datos mock, para confirmar la estimación antes de comprometer toda la Fase 5.
- Las tareas de UI las toma Codex (ChatGPT) y, si se agota la cuota, Antigravity; Command Code queda de reserva.
- Se actualiza `AGENTS.md` §3/§4 (la UI ya no es "fork") y se documenta el `NOTICE` GPL.

## Decisión de Adrian

_Pendiente._
