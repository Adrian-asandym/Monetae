# STATUS — Monetae

> Actualizado: 2026-10-07 · Coordinador: Claude · Rama de integración: `master-dev`

## Fase actual

**Fase 0 (análisis de Cashew): completada e integrada en `master-dev`.** Siguiente: Fase 1 (diseño), bloqueada por la decisión ADR-001.

- **Run:** `run_bef8ecfc67a7` (abierto, sin trabajo pendiente; el CLI no tiene comando para cerrarlo).
- **Entregables:** `docs/cashew-analysis.md` (consolidado) + `docs/cashew-analysis/01..04-*.md`, y borrador `docs/decisions/001-ui-strategy.md`.
- **`main`:** sin cambios de la Fase 0. No se hace merge sin decision gate aprobado por Adrian.

## Tareas del Run

| Tarea | ID | Agente | Estado |
|-------|----|--------|--------|
| T-001 modelo de datos | `task_daf931e7254f` (+ corrección `task_0b155ce3922b`) | Antigravity | Aceptada, integrada |
| T-002 préstamos P1–P3 | `task_e2b37fa25442` | Antigravity | Aceptada, integrada |
| T-003 formato de respaldo | `task_42fdd9be5120` (+ corrección `task_682d3935e1c3`) | Antigravity | Aceptada, integrada |
| T-004 acoplamiento de UI | `task_fa350300c31d` (+ corrección `task_b68277ebe61e`) | Antigravity | Aceptada, integrada |

Los worktrees `../Monetae-agy-T-00X-*` y sus ramas `agy/T-00X-*` siguen en disco (ya integradas; limpieza pendiente de OK de Adrian).

## Decisiones pendientes de Adrian

1. **ADR-001 — estrategia de UI** (detalle en `docs/decisions/001-ui-strategy.md`):
   - **A (recomendada):** UI propia en Flutter Web reutilizando y desacoplando los componentes visuales de Cashew. ~24–32 tareas de 1–2 h. Riesgo: fidelidad visual.
   - **B:** fork de Cashew con fachada REST sobre `FinanceDatabase`. ~28–38 tareas; arrastra el modelo de préstamos como objetivos.
   - **C:** fork de Cashew con Drift como caché y sincronización bidireccional. ~36–48 tareas; riesgo crítico.
2. **Versión de `reference/Cashew`:** el respaldo real es schema v48 y la copia es v46. ¿Actualizar al tag/commit correspondiente? (Adrian debe localizarlo.)
3. **Importador:** leer SQLite primero y CSV solo como rescate (el CSV excluye `paid = false`, `exportCSV.dart:88`). Contradice la sugerencia de `AGENTS.md` §4.
4. **Etiquetas (`tags`):** existen en la app real y no están en SPEC. ¿V1, importar como notas, o descartar?
5. **Merge `master-dev` → `main`:** solo documentos; requiere decision gate.

## Borrador del Run de Fase 1 (tras decidir ADR-001)

| Tarea | Contenido | Agente |
|-------|-----------|--------|
| T-101 | Esquema de BD + `docs/ARCHITECTURE.md` | Claude |
| T-102 | Contrato OpenAPI inicial (cuentas, categorías, transacciones, préstamos) | Codex (spec de Claude) |
| T-103 | ADR-003 (interés: caja vs devengado) y ADR-004 (tipo de cambio) | Claude → decide Adrian |
| T-104 | ADR-002, 006 y 007 con opciones y recomendación | Claude → decide Adrian |
| T-105 | Fixture sintético de Cashew v48 con ejemplos A–E de SPEC §7 | Antigravity |

## Notas operativas

- Las tareas de UI van a Codex (ChatGPT) y, si se agota la cuota, a Antigravity; Command Code queda de reserva.
- Antigravity pide "trust workspace" en cada worktree nuevo; el CLI no permite fijar su modelo (se cambia en su panel).
- `outcome_unknown` tras lanzar un worker suele significar que sí está trabajando.
- Laguna conocida: P3 en préstamos de largo plazo no está confirmado explícitamente (verificar en Fase 1 con el ejemplo B).
