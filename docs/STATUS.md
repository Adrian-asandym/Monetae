# STATUS — Monetae

> Actualizado: 2026-10-07 · Coordinador: Claude · Rama de integración: `master-dev`

## Fase actual

**Fase 0 (análisis de Cashew): completada y fusionada en `main`.** Decisiones de cierre tomadas por Adrian el 2026-10-07. **Fase 1 (diseño) en curso**, Run aprobado por Adrian (ver abajo).

- **Run Fase 0:** `run_bef8ecfc67a7` (sin trabajo pendiente; el CLI no permite cerrarlo).
- **SPEC:** v0.3 (2026-10-07), con etiquetas, importador SQLite-first y ADR-002/003/004/006/007 aceptados. Historial en `docs/SPEC.md` §18.
- **Merge a `main`:** hecho el 2026-10-07 en fast-forward hasta `382425f` (gate `gate_fcbcb29461e9` aprobado por Adrian y resuelto). `main` **no se ha subido a `origin`** (16 commits por delante; push pendiente de OK de Adrian). Lo posterior (ADR aceptados, SPEC v0.3, ARCHITECTURE) vive en `master-dev` y requiere un nuevo gate.

## Decisiones tomadas (2026-10-07)

| # | Decisión | Dónde quedó |
|---|----------|-------------|
| 1 | **ADR-001: opción A** (UI propia en Flutter Web reutilizando y desacoplando widgets de Cashew). ACEPTADO. | `docs/decisions/001-ui-strategy.md` |
| 2 | **`reference/Cashew` no se actualiza.** Ninguna versión pública (ni 5.2.9+366 ni 5.3.4+396, ambas esquema 46) tiene esquema 47/48 ni tablas de etiquetas; la app de Adrian va por delante del código público. El esquema real es el DDL de T-003. | `docs/cashew-analysis.md` |
| 3 | **Importador: SQLite primero, CSV solo de rescate, siempre sobre una copia.** | SPEC §11 (RF-40a, g, h, i), `AGENTS.md` §4 y §9 |
| 4 | **Etiquetas:** se importan y guardan (`tags`, `transaction_tags`), con asignación y filtro básicos en V1. | SPEC RF-43 a RF-45, RF-40j, §6, §14 |
| 5 | **Merge a `main`** tras actualizar lo anterior, con decision gate. | **Hecho** (fast-forward a `382425f`, gate aprobado) |

## Plan ya definido

- **T-501 — Spike de desacople (primera tarea de la Fase 5):** 3–4 componentes de Cashew (tema, tarjeta de transacción, un gráfico) desacoplados de Drift contra datos mock. **No se lanza hasta iniciar la Fase 5.** Si proyecta >1,5× el esfuerzo previsto, se consulta a Adrian. Spec: `docs/tasks/T-501-ui-decoupling-spike.md`.

## Tareas del Run de Fase 0 (cerradas)

| Tarea | ID | Agente | Estado |
|-------|----|--------|--------|
| T-001 modelo de datos | `task_daf931e7254f` (+ corrección `task_0b155ce3922b`) | Antigravity | Aceptada, integrada |
| T-002 préstamos P1–P3 | `task_e2b37fa25442` | Antigravity | Aceptada, integrada |
| T-003 formato de respaldo | `task_42fdd9be5120` (+ corrección `task_682d3935e1c3`) | Antigravity | Aceptada, integrada |
| T-004 acoplamiento de UI | `task_fa350300c31d` (+ corrección `task_b68277ebe61e`) | Antigravity | Aceptada, integrada |

Los worktrees `../Monetae-agy-T-00X-*` y sus ramas `agy/T-00X-*` siguen en disco (ya integradas; limpieza pendiente de OK de Adrian).

## Run de Fase 1 (APROBADO por Adrian el 2026-10-07) — `run_2cddcd14320c`

Las tareas de UI no empiezan hasta la Fase 5. Ninguna tarea de la Fase 1 toca UI.

| Tarea | Contenido | Agente | Depende de | Estado |
|-------|-----------|--------|------------|--------|
| T-103 | ADR-003 (interés) y ADR-004 (tipo de cambio) | Claude → decide Adrian | — | **Aceptado (opción A, 2026-10-07)** |
| T-104 | ADR-002 (auth), ADR-006 (bloqueo), ADR-007 (SQLAlchemy) | Claude → decide Adrian | — | **Aceptados (opción A, 2026-10-07)** |
| T-105 | Fixture sintético Cashew v48 (`task_8f0a3298376d`, dispatch `ctx_e7cb5a99872c`) | Antigravity | — | Lanzada; **bloqueada por "trust workspace"** en `../Monetae-agy-T-105-cashew-fixture` |
| T-101 | Esquema de BD (con `tags`/`transaction_tags`) y `docs/ARCHITECTURE.md` | Claude | T-103, T-104 | **Hecho (borrador v0.1; pendiente de revisión de Adrian)** |
| T-102 | Contrato OpenAPI inicial (`task_3b5d1a6f2fb7`, dispatch `ctx_9af6923e7e37`; spec en `docs/tasks/T-102-openapi-initial.md`) | Codex | T-101 | **En curso** en `../Monetae-codex-T-102-openapi` (`codex/T-102-openapi-initial`) |

Orden: T-103, T-104 y T-105 en paralelo; luego T-101; luego T-102.

**Merge a `main` (hecho):** ver arriba; se fusionó el hash exacto `382425f`, no la punta de `master-dev`.

## Notas operativas

- **Entorno (AlmaLinux 9 en WSL):** Python del sistema 3.9.25; faltan `uv`, Python 3.12+, `pip`, `docker` (dentro de WSL) y `flutter`/`dart`. Hay `node`/`npm`, `psql` y `pg_dump`. Los scripts de la Fase 1 deben ser compatibles con 3.9; la Fase 2 necesita `uv` + Python 3.12 + Docker, y la Fase 5 necesita Flutter. Pendiente de Adrian.

- Las tareas de UI van a Codex (ChatGPT) y, si se agota la cuota, a Antigravity; Command Code queda de reserva.
- Antigravity pide "trust workspace" en cada worktree nuevo; el CLI no permite fijar su modelo (se cambia en su panel).
- `outcome_unknown` tras lanzar un worker suele significar que sí está trabajando.
- Laguna conocida: P3 en préstamos de largo plazo no está confirmado explícitamente (verificar en Fase 1 con el ejemplo B del fixture T-105).
- Pendiente menor: `docs/SPEC.md` §2 aún dice "a confirmar en la Fase 0" y "Hipótesis"; la Fase 0 la confirmó (se actualiza con el próximo cambio de SPEC aprobado por Adrian).
