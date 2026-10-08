# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Cierre de sesión** | **2026-10-08, ~12:55 (America/Lima)** · gate de cierre **pendiente**: `gate_e3b1a2193ba2` (merge de docs a `main` + push; ver D1) |
| **`main`** | **`b3797b1`** — Fase 3 completa (merge fast-forward aprobado por Adrian el 2026-10-08). **Local: 25 commits por delante de `origin/main`.** |
| **`master-dev`** | `01b20f9` (protocolo de sesión en `CLAUDE.md`) **+ el commit de cierre que contiene este archivo** (`git log -1`). Sobre `main` solo hay documentación (`CLAUDE.md`, `STATUS.md`, cabeceras de `docs/tasks/`); **el código es idéntico**. |
| **`origin`** | `origin/main` = `origin/master-dev` = **`05ff1d9`** (cierre de la Fase 2). **El push de la Fase 3 NO se ha hecho** (Adrian aprobó el merge; el push queda pendiente, §5 D1). |
| **SPEC / ARCHITECTURE** | SPEC v0.3 (2026-10-07; historial en `docs/SPEC.md` §18) · `docs/ARCHITECTURE.md` v0.3 (puntos abiertos en su §10, 1–13). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fase 0 (análisis de Cashew) · Fase 1 (diseño: ADR, esquema, OpenAPI, fixture) · Fase 2 (backend base) · **Fase 3 (préstamos y suscripciones)**: T-301, T-302, T-303 y T-304 aceptadas e integradas. |
| 🔄 **En curso** | Nada. **No hay ningún worker ejecutándose.** |
| ⏳ **Pendiente** | **Fase 4** (importador de Cashew) — sin lanzar, sin tareas escritas · Fase 5 (UI Flutter; empieza con `T-501`, ya escrita) · Fase 6 (presupuestos, metas, notificaciones, Google OIDC, bloqueo PIN/WebAuthn) · Fase 7 (endurecimiento y aceptación V1). Después: despliegue en VPS → V2 → V3 → V4. |

Backend actual: **44 de las 86 rutas del contrato = 71 de 127 operaciones**, 6 migraciones (cabeza `0006`), **713 pruebas** con PostgreSQL real. Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-08)

- **Fase 3 completa.** Dominio de préstamos (T-301) y de suscripciones (T-303) en paralelo; API de préstamos con migración `0005` (T-302); API de suscripciones con migración `0006` (T-304). Cada una verificada por el coordinador: `ruff`, `mypy --strict`, pruebas con PostgreSQL, `alembic`, y **sondas con `uvicorn` real + `httpx`** (ejemplos A–E de préstamos y escenario Netflix de SPEC §8).
- **Hallazgo grave de la Fase 2, corregido (`4b62d7c`):** el `commit` de la sesión se hacía *después* de enviar la respuesta (FastAPI ≥ 0.118 con dependencias `yield`). Con servidor real, `login` + petición inmediata daba 401 en 34/40 intentos; `TestClient` lo ocultaba. Ahora `Database` usa `scope="function"` y hay una prueba de orden ASGI. Sondas reales tras el arreglo: 0/40 y 0/150 fallos.
- **Dos especificaciones propias corregidas al lanzar** (T-302: columna interna `sequence`; T-304: `status` solo `active|archived`, `reactivate` sin cuerpo, sin tasas en `SubscriptionCreate`).
- **Gate de la Fase 3 resuelto** (`gate_621dc454eeee`): merge fast-forward `master-dev` → `main` hecho en local. Auditoría de seguridad de los 25 commits nuevos: limpia.
- **Protocolo de sesión** añadido a `CLAUDE.md` §10 (commit `01b20f9`).
- Este archivo se reorganizó en las secciones fijas del protocolo; cabeceras de `docs/tasks/T-301…T-304` actualizadas a «aceptada e integrada».

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-08 | **Continuar con la Fase 3** (lanzar T-301 a T-304). |
| 2026-10-08 | **Aprobar el merge a `main`** de la Fase 3 (gate `gate_621dc454eeee`). **No** aprobó explícitamente el push. |
| 2026-10-08 | **Protocolo de sesión** (dos comandos de cierre y reanudación) en `CLAUDE.md` §10. |
| 2026-10-07 | ADR-001 **A** (UI propia en Flutter Web reutilizando widgets de Cashew), ADR-002 **A** (sesión en servidor + cookie), ADR-003 **A** (interés en base caja; pago primero a interés), ADR-004 **A** (tipo de cambio manual manda), ADR-006 **A** (PIN, luego WebAuthn), ADR-007 **A** (SQLAlchemy síncrono). |
| Fases 0–2 (oct 2026) | Importador **SQLite primero**, CSV solo como rescate, siempre sobre una copia; el respaldo real es Cashew **v48**. Etiquetas en V1. Nombres duplicados permitidos en categorías y personas (únicos solo en cuentas y etiquetas). Usuarios solo por CLI en V1. `PATCH /transactions/{id}` admite `account_id` (misma moneda) y `kind`. |
| Fases 0–2 (oct 2026) | Agentes: **Codex** (`gpt-6.1-sol` general / `gpt-6-astra` el más potente / `gpt-6-luna` ligero) para backend y, después, UI; **Antigravity** solo como relevo; **Command Code** de reserva. |

**Aceptadas por el merge, pero aún no reflejadas en `docs/api/openapi.json`** (Adrian las vio en el resumen del gate; ver D3): `409 loan_already_settled`, `422 movement_kind_immutable` y `fx_rate_to_base` opcional solo de entrada en `SubscriptionCreate`/`SubscriptionUpdate`. Detalle en `docs/api/README.md`.

## 5. Decisiones pendientes

Cada una: contexto → opciones (la más recomendable primero) → impacto.

**D1 · Push a GitHub de `main` y `master-dev` (gate propuesto `gate_e3b1a2193ba2`, sin resolver; incluye el merge fast-forward de los commits de documentación posteriores a `b3797b1`).** Repo **público**. Auditoría de seguridad de la Fase 3 ya hecha (sin `.env`, claves ni `reference/`; solo los 3 fixtures sintéticos); falta repetirla sobre los commits de documentación nuevos.
- **A (recomendada): subir ahora**, sin `--force`, tras repetir la auditoría rápida. *Razón:* hay 25 commits solo en tu máquina; subirlos es el respaldo.
- B: esperar a decidir D2 y D3 y subir todo junto. *Razón:* historial más limpio, pero más tiempo sin respaldo.
- *Impacto:* lo publicado en un repo público queda indexable aunque se borre después.

**D2 · Cobros vencidos al archivar una suscripción.** Hoy `archive` y `delete` cancelan solo las `scheduled` con fecha ≥ ahora (literal de SPEC §8.1, «cobros futuros»). Si archivas justo después de que *venza* un cobro y antes de marcarlo pagado, queda una programada vencida y, al reactivar, aparecen dos (verificado con `uvicorn` real).
- **A (recomendada): cancelar (borrado lógico) todas las `scheduled` sin publicar de la regla** al archivar/borrar. *Razón:* mantiene el invariante de una sola programada por regla y la reactivación queda limpia; es reversible (borrado lógico) y no toca lo publicado.
- B: dejar el comportamiento literal y documentarlo.
- *Impacto de A:* 2 líneas en `services/subscriptions.py` (`_cancel_scheduled(future_only=...)`) + ajustar la prueba `test_archive_preserves_past_scheduled_and_ignores_deleted_payments` + 1 prueba nueva.

**D3 · Ampliaciones de contrato de la Fase 3 en `openapi.json`.**
- **A (recomendada): incorporar las 3 ampliaciones** a `docs/api/openapi.json`, correr `scripts/check_openapi.py` (+ Redocly) y avisar a la UI. *Razón:* `CLAUDE.md` §8 exige que el contrato sea la verdad para generar el cliente.
- B: revertirlas en el código. *Razón:* ninguna; rompería la función de suscripciones en moneda extranjera.
- *Impacto:* tarea corta del coordinador; sin riesgo para el código.

**D4 · Alcance de la Fase 4 respecto a presupuestos, metas y reglas.** SPEC RF-40a pide importar también presupuestos, metas y reglas, pero esas tablas no existen hasta la Fase 6.
- **A (recomendada): importar ahora lo que ya tiene destino** (cuentas, categorías, etiquetas, transacciones, préstamos, suscripciones) y **listar en el reporte lo demás como «pendiente de Fase 6»**; ampliar el importador en la Fase 6. *Razón:* evita crear tablas a medias y mantiene la fase acotada.
- B: crear ahora las tablas de presupuestos/metas/reglas. *Razón:* import completo de una vez; *costo:* adelanta la Fase 6 y alarga la 4.
- *Impacto:* define el tamaño de T-401…T-403.

**D5 · ADR-008: heurística para convertir los préstamos de Cashew** (SPEC RF-40d exige un ADR; **aún no existe**) y permiso para la prueba real.
- **A (recomendada):** el coordinador redacta el ADR a partir de `docs/cashew-analysis/02-loans.md` y del fixture sintético; **Adrian lo aprueba antes de lanzar la tarea de préstamos (T-402)**. *Razón:* es una regla de negocio que "adivina" estructura de datos reales; los casos ambiguos van a revisión manual, no se adivinan.
- Sobre el respaldo real: **¿autorizas un `--dry-run` sobre una copia, que solo devuelva conteos y saldos (nunca filas)?** Recomendado *sí*, al final de la fase, porque es la única forma de validar «los saldos coinciden con Cashew» (RF-40c). Sin tu OK solo se usan los fixtures.

**D6 · Limpieza de worktrees y ramas.** 18 worktrees de tareas ya fusionadas (≈ 0,7 GB con sus `.venv`; disco libre 3,3 GB).
- **A (recomendada): borrarlos tras D1** (`git worktree remove` + `git branch -d`; el historial queda en `main`). *Razón:* libera disco antes de Docker/Flutter.
- B: conservarlos. *Impacto:* riesgo de quedarte sin disco en la Fase 5. Dos tienen archivos sin versionar de workers (`agy-T-001`: 4 `scratch*`; `agy-T-105`: `scripts/` y `services/`), que se pierden al borrar (son basura, ya sustituida).

**D7 · Para más adelante** (no bloquean la Fase 4): **ADR-005** modelo de sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6, acción de Adrian) · proxy del VPS para ver la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 («a confirmar en la Fase 0», «Hipótesis»), a corregir con el próximo cambio de SPEC aprobado.

## 6. Siguiente paso concreto

**Antes de lanzar nada**, tras el OK de Adrian a D1–D6: (1) push si se aprueba D1; (2) D3, actualizar `openapi.json`; (3) D2 si se aprueba, como tarea trivial del coordinador; (4) el coordinador **redacta ADR-008 y las tareas T-401…T-403 contrastándolas con el contrato y con el código integrado** (lección de T-302/T-304) y las presenta en un gate.

**Fase 4 propuesta** (Run nuevo; todas con Codex; ramas `codex/T-40x-…` desde `master-dev`; el coordinador renombra la rama tras `worker-start`):

| Tarea | Contenido | Agente / modelo / esfuerzo | Depende de |
|---|---|---|---|
| T-401 | Migración `0007` (`import_runs`, `import_review_items`), lector SQLite de solo lectura con descubrimiento de esquema (RF-40i), mapeo de cuentas, categorías, etiquetas y transacciones, idempotencia por `import_external_id`, `is_initial_data`, CLI `--dry-run` con reporte de saldos antes/después | Codex `gpt-6.1-sol` · high | — |
| T-402 | Conversión de préstamos según ADR-008 (usa `domain/loans.py`), casos ambiguos a `import_review_items` | Codex `gpt-6.1-sol` · high (`gpt-6-astra` si T-401 pidió devoluciones) | T-401, ADR-008 aprobado |
| T-403 | Suscripciones/recurrentes importadas, cuadre de saldos y rutas `/imports` (4 operaciones) | Codex `gpt-6.1-sol` · medium | T-401 |

T-402 y T-403 pueden ir **en paralelo** después de T-401 solo si sus archivos permitidos son disjuntos (el registro de pasos del importador es el punto de choque: se define en T-401).

**Cómo las verificaré:** `ruff`, `mypy --strict`, `pytest` con PostgreSQL y `alembic` (0006↔0007) corridos por mí; importación del fixture `services/api/tests/fixtures/cashew_v48/` contra `expected.json`; **idempotencia** (importar dos veces ⇒ cero cambios); `--dry-run` ⇒ BD intacta; saldos que cuadran; **sonda con `uvicorn` real + `httpx`** para `/imports`; privacidad (nada del respaldo real en git, logs ni reportes). Decision gate antes de `main`.

**Opcional en paralelo:** `T-501` (spike de desacoplo de widgets, Fase 5) no toca el backend, pero **Flutter pide disco**: solo después de D6.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 3: `run_63b520544a30`.** Tareas: T-301 `task_d8d91292787f`, T-303 `task_39bd586cd28f`, T-302 `task_112bd988b505`, T-304 `task_3e72e1ff8b03` — las cuatro `completed`; `task_2af7f21c0086` y `task_923219f8ed0e` son intentos antiguos `failed/superseded` (solo historial). **Workers: ninguno vivo** (4 `exited`, todos liberados); sin mensajes ni gates pendientes. Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`. Al retomar: `orca orchestration run-use --id <run>`; la Fase 4 abrirá un Run nuevo.

**Worktrees** (en `/home/artur/propio2/`): `Monetae` → `main` (limpio) · `Monetae-master-dev` → `master-dev` (limpio) · 18 de tareas, **todas fusionadas** en `master-dev`: `agy-T-001/002/003/004/105`, `codex-T-102/105/201/202/203/204/205/206a/206b/301/302/303/304`. Con archivos sin versionar (basura de workers): `Monetae-agy-T-001-data-model` y `Monetae-agy-T-105-cashew-fixture`. Sin contenedores Docker, sin servidores en el puerto 8765, sin `.env` sueltos.

**Paneles de Orca abiertos (11):** el del coordinador («Fase 3 de Monetae») y `lupuna` (otro proyecto) **no se tocan**. **Adrian puede cerrar los otros 9**, ninguno tiene trabajo pendiente: `…Monetae-agy-T-001`, `-T-002`, `-T-003`, `-T-004`, `-T-105` (dos: el panel y `worker-task_8f0a3298376d`), `…Monetae-codex-T-102`, `-T-201` (aún tiene un Codex inactivo) y `-T-206b`. Los terminales de los workers T-301 a T-304 ya no existen.

## 8. Limitaciones y riesgos conocidos

- **Contrato desfasado** respecto al código en 3 puntos (D3) hasta actualizar `openapi.json`.
- **Cobros vencidos al archivar** (D2).
- **Sin auditoría de seguridad externa**; endurecimiento previsto en la Fase 7.
- La BD admite un `income` con monto negativo si se escribe SQL directo; solo la API garantiza el signo (decidir con el importador; `ARCHITECTURE.md` §10.12).
- El límite de intentos de login usa `request.client.host`: detrás de un proxy hace falta configuración (§10.10). `501 google_login_not_available` no figura en el contrato congelado (§10.11). `updated_at` se refresca vía ORM/Core, no con SQL crudo (§10.8).
- `reactivation_suggestions` solo se rellena al **crear** o **publicar** una transacción de gasto; `GET /transactions` no las calcula.
- Totales de suscripciones: sin proveedor de tipos de cambio (Fase 6) solo se suma la moneda igual a la de reporte; las demás cuentan en `unconverted_count`. La tasa de una suscripción en moneda extranjera es **provisional** (se confirma al publicar cada cobro).
- `end_on` de `recurring_rules` existe pero no se expone; el CRUD de `/recurring-rules` es de la Fase 6.
- La clave secreta por defecto es de ejemplo; en `prod` la app se niega a arrancar con ella o con cookies sin `Secure`.
- **Disco:** 3,3 GB libres en `/` (20 GB). Vigilar antes de Docker/Flutter (D6).
- **Repositorio público:** todo push se audita antes. Los datos reales de Adrian solo viven en `reference/backups/` (ignorado por git).
- La cuota de Claude Pro es limitada: delegar lectura masiva y generación de código.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md (§10), docs/SPEC.md, ADRs y tareas abiertas. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list
git -C ../Monetae log --oneline -1 && git rev-parse --short origin/main   # main = b3797b1 · origin/main = 05ff1d9 hasta que se haga el push

# 1) Herramientas (a nivel de usuario; el Python del sistema es 3.9, NO usarlo para el proyecto)
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
uv --version && docker compose version && flutter --version | head -1
orca status --json | head -5                           # ok: true
orca orchestration run-use --id run_63b520544a30       # solo para consultar la Fase 3

# 2) Verificar el backend (≈ 5 min; necesita PostgreSQL en Docker)
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 713 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0006
cd ../.. && python3 -I scripts/check_openapi.py         # contrato: 86 paths, 127 operaciones
docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) Sonda con servidor real (obligatoria para cambios de sesión/transacción; TestClient no basta)
#    con la BD de (2) levantada: variables MONETAE_DATABASE_URL, MONETAE_SECRET_KEY, MONETAE_COOKIE_SECURE=false;
#    crear usuario: echo '<clave>' | uv run python -m monetae.cli create-user --email yo@example.test --password-stdin
#    uv run uvicorn monetae.api.main:app --port 8765   y   httpx: login -> petición inmediata (debe dar 200).
#    Parar el servidor por PUERTO (ss -ltnp | grep :8765), NUNCA con pkill -f / pgrep -f.
docker compose -f infra/docker-compose.yml down -v && rm -f .env     # SIEMPRE limpiar
```

## Anexo A · Qué incluye el backend (verificado sobre `b3797b1`)

FastAPI síncrono (ADR-007) en `services/api`: **44 de 86 rutas = 71 de 127 operaciones** (Fase 2: 29 rutas / 48 operaciones; Fase 3: +15 / +23).

- **Acceso:** login por correo y contraseña (argon2id), sesiones opacas con cookie `HttpOnly`, CSRF firmado con HMAC + comprobación de `Origin`, límite de intentos persistente, `users/me`, cierre de sesión. Usuarios solo por CLI: `python -m monetae.cli create-user`.
- **Catálogos:** cuentas, categorías (con las 2 de sistema de interés), personas con alias, etiquetas.
- **Libro mayor:** transacciones (CRUD, filtros, etiquetas, saldos calculados, idempotencia, borrado/restauración lógica), transferencias de dos patas (también entre monedas), lotes atómicos, publicar programadas.
- **Préstamos (T-301/T-302):** `loans` + `loan_movements` (desembolso, interés, pago, ajuste, condonación); saldo y estado **calculados**, sin «liquidar»; pago primero a interés; exceso con `adjustment` o `income_expense`; cada movimiento afecta a **su** cuenta (también otra moneda); edición/borrado con revalidación de todo el libro (`409 ledger_inconsistent`); borrado lógico atómico; resumen por persona y moneda. 15 operaciones.
- **Suscripciones (T-303/T-304):** `subscriptions` + `recurring_rules`; archivado reversible (conserva el historial, fuera de listado y totales); reactivación; próxima `scheduled` materializada y avanzada al publicar; totales por moneda; sugerencia de reactivación por título normalizado. 8 operaciones.
- **Base de datos:** migraciones `0001` identidad y catálogos · `0002` intentos de login · `0003` transacciones · `0004` integridad de transferencias · `0005` préstamos · `0006` suscripciones y reglas. FK **compuestas con `user_id`**: la BD rechaza datos de otro usuario.
- **Calidad:** 713 pruebas con PostgreSQL real, `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`.
- **No implementado (operaciones del contrato):** usuarios 9 (PIN/bloqueo/WebAuthn), reportes 8, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, Google OIDC 1, exportaciones 1, sugerencia de tipo de cambio 1.

## Anexo B · GitHub

`origin` = `https://github.com/Adrian-asandym/Monetae.git` (público). Antes de cada push se verifica el historial (sin `.env`, claves, `reference/`, respaldos; únicos `.sqlite`/`.csv` versionados: los 3 fixtures sintéticos de `services/api/tests/fixtures/cashew_v48/`; sin correos reales). Comando: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev` (sin `--force`; `gh` autenticado como `Adrian-asandym`).

## Anexo C · Lecciones operativas (no repetir errores)

- **Verificar, no confiar en el resumen del worker:** correr yo `ruff`, `mypy`, `pytest`, leer el servicio entero y hacer pruebas manuales. Así aparecieron: un bloqueo `FOR UPDATE` por petición (5,6 s → 0,03 s), duplicados de nombre mal aplicados, citas inventadas, errores de conteo y el `commit` posterior a la respuesta.
- **`TestClient` no es un servidor:** espera a que la app termine por completo y oculta errores de orden respuesta/commit. Probar además con `uvicorn` real y `httpx`.
- **Releer la spec contra el contrato y el código antes de lanzar:** en la Fase 3 corregí mi propia spec dos veces al lanzar. Las preguntas del worker (`ask`) fueron todas legítimas: responderlas con el contrato abierto.
- **Reglas de bloqueo:** las lecturas no toman bloqueos de fila; las escrituras usan bloqueos consultivos con orden fijo.
- **Orca:** `worker-start` puede devolver `outcome_unknown` aunque el worker trabaje; Antigravity pide «trust workspace» en cada worktree; Codex puede mostrar un menú «Update available» que solo Adrian puede saltar; `gate-create` no acepta `--run` y deja la tarea en `ready` (marcarla `completed` a mano); al abrir sesión hay que re-vincular el Run (`run-use --id`); solo **una** espera `check --wait` por Run (`waiter_exists` si queda una colgada), y menos de 10 min por llamada; no se pueden editar las especificaciones de una tarea ya creada (crear otra y marcar la vieja `failed/superseded`).
- **Shell:** nunca `pkill -f` ni `pgrep -f` con un texto que aparezca en el propio comando (mata el shell, código 144); parar servidores por puerto con `ss -ltnp`.
- **Modelos Codex** (`~/.codex/models_cache.json`): `gpt-6.1-sol` (general), `gpt-6-astra` (el más potente), `gpt-6-luna` (ligero; sirve para CRUD pero exige revisar las reglas).
- **Privacidad:** nunca leer filas de `reference/backups/`; trabajar sobre una copia; los fixtures son sintéticos.
