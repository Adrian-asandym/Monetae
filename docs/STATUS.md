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
| T-105 | Fixture sintético Cashew v48 (relevo a Codex como T-105b tras la caída de Antigravity) | Codex `gpt-6.1-sol` | — | **Aceptada e integrada**: determinista (mismos hashes), verificador 7/7 en Python 3.9 y 3.12 |
| T-101 | Esquema de BD (con `tags`/`transaction_tags`) y `docs/ARCHITECTURE.md` | Claude | T-103, T-104 | **Hecho (v0.2, revisado por Adrian)** |
| T-102 | Contrato OpenAPI (`docs/api/openapi.json`: 86 paths, 127 operaciones, 131 esquemas) | Codex | T-101 | **Aceptada e integrada** (T-102 y T-102b alineada con ARCHITECTURE v0.2; `ec6e08a`) |

Orden: T-103, T-104 y T-105 en paralelo; luego T-101; luego T-102.

**Merge a `main` (hecho):** ver arriba; se fusionó el hash exacto `382425f`, no la punta de `master-dev`.

**Fase 1 cerrada a falta del merge a `main`:** T-101 a T-105 aceptadas. Decision gate `gate_eea4d8d760d3` (Run `run_2cddcd14320c`, `task_5df0e2ee5407`) pide fusionar el commit exacto `7ba8e06`. Se fusiona ese hash, no la punta de `master-dev` (T-203 sigue en curso). El push a `origin` es una decisión aparte de Adrian.

## Run de Fase 2 — backend base — `run_70f5f187fe16`

Agente: Codex en todas. Migraciones Alembic y `pyproject.toml`/`uv.lock`: un solo dueño a la vez (AGENTS.md §10). Los ejemplos A–E y los préstamos son de la Fase 3, no de esta.

| Tarea | Contenido | Estado / depende de |
|-------|-----------|---------------------|
| T-201 | Esqueleto de `services/api`, calidad (ruff, mypy estricto, pytest), `/health`, errores `problem+json`, Docker Compose (`docs/tasks/T-201-api-skeleton.md`) | **Aceptada e integrada** (`ddd4861`) |
| T-202 | `domain/`: `Money`, monedas, redondeo y tipos de cambio, con pruebas exhaustivas (`docs/tasks/T-202-domain-money-fx.md`) | **Aceptada e integrada** (`28ea759`; 120 pruebas, 100 % de cobertura de sus módulos) |
| T-203 | BD: SQLAlchemy base, sesión, Alembic y migración 0001 (users, sessions, accounts, categories, people, tags), repositorio con `user_id` obligatorio y prueba de aislamiento entre dos usuarios (`docs/tasks/T-203-db-alembic-core.md`) | **Aceptada e integrada** (`db5a3ec`; 156 pruebas con PostgreSQL real, 12 restricciones comprobadas a mano) |
| T-204 | Autenticación por correo y contraseña (argon2id), sesiones con cookie opaca, CSRF firmado, límite de intentos, `users/me`, CLI para crear usuarios; migración 0002 (`docs/tasks/T-204-auth-sessions.md`) | **En curso** (Codex `gpt-6.1-sol` high) |
| T-205 | CRUD de cuentas y categorías (con las categorías de sistema de interés) + pruebas de aislamiento | T-204, T-202 |
| T-206 | Transacciones, transferencias, etiquetas y multimoneda (migración 0003, con FK compuestas con `user_id`) | T-205 |

T-202 y T-203 pueden ir en paralelo (archivos disjuntos). Google OIDC, presupuestos, metas y notificaciones son de la Fase 6.

## Notas operativas

- **Entorno (AlmaLinux 9 en WSL), verificado el 2026-10-07:** `uv` 0.12.23 y Python 3.12.15 (usuario); Docker 29.5 con Compose v5 (Docker Desktop; PostgreSQL 16 probado); Flutter 3.47.6 / Dart 3.13 (`flutter build web`, `dart analyze` y `flutter test` probados); `node`, `psql`. El `python3` del sistema sigue siendo 3.9: no usarlo en el proyecto. **Sin Chrome** en WSL (solo hace falta para `flutter run -d chrome`; alternativa `-d web-server` y abrir en el navegador de Windows) y sin Android SDK (V4). Espacio libre ≈ 4 GB en `/` (20 GB, 78 % usado): vigilar.

- Las tareas de UI van a Codex (ChatGPT) y, si se agota la cuota, a Antigravity; Command Code queda de reserva.
- Antigravity pide "trust workspace" en cada worktree nuevo; el CLI no permite fijar su modelo (se cambia en su panel).
- `outcome_unknown` tras lanzar un worker suele significar que sí está trabajando.
- Laguna conocida: P3 en préstamos de largo plazo no está confirmado explícitamente (verificar en Fase 1 con el ejemplo B del fixture T-105).
- Pendiente menor: `docs/SPEC.md` §2 aún dice "a confirmar en la Fase 0" y "Hipótesis"; la Fase 0 la confirmó (se actualiza con el próximo cambio de SPEC aprobado por Adrian).
