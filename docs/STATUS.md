# STATUS — Monetae

> Actualizado: 2026-10-07 · Coordinador: Claude · Rama de integración: `master-dev`

## Fase actual

**Fase 0 (análisis de Cashew): completada y fusionada en `main`.** Decisiones de cierre tomadas por Adrian el 2026-10-07. Siguiente: **Fase 1 (diseño)**, pendiente del OK de Adrian al Run propuesto abajo.

- **Run Fase 0:** `run_bef8ecfc67a7` (sin trabajo pendiente; el CLI no permite cerrarlo).
- **SPEC:** v0.3 (2026-10-07), con etiquetas, importador SQLite-first y ADR-002/003/004/006/007 aceptados. Historial en `docs/SPEC.md` §18.
- **Merge a `main`:** hecho el 2026-10-07 en fast-forward hasta `382425f` (gate `gate_fcbcb29461e9` resuelto: aprobado). `main` no se ha subido a `origin` (queda 16 commits por delante; push pendiente de OK de Adrian). Lo posterior (ADR aceptados, SPEC v0.3) vive en `master-dev` y requiere un nuevo gate.

## Notas operativas

- Las tareas de UI van a Codex (ChatGPT) y, si se agota la cuota, a Antigravity; Command Code queda de reserva.
- Antigravity pide "trust workspace" en cada worktree nuevo; el CLI no permite fijar su modelo (se cambia en su panel).
- `outcome_unknown` tras lanzar un worker suele significar que sí está trabajando.
- Laguna conocida: P3 en préstamos de largo plazo no está confirmado explícitamente (verificar en Fase 1 con el ejemplo B del fixture T-105).
- Pendiente menor: `docs/SPEC.md` §2 aún dice "a confirmar en la Fase 0" y "Hipótesis"; la Fase 0 la confirmó (se actualiza con el próximo cambio de SPEC aprobado por Adrian).
