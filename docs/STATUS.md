# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-08, ~20:50 (America/Lima)** — Fase 4 en curso |
| **`origin`** | `origin/main` = `origin/master-dev` = **`0e74c67`** (Fase 3 + contrato 0.3.0 + ADR-008 y tareas T-401…T-403). |
| **`main`** | `0e74c67`. |
| **`master-dev`** | `0e74c67` **+ el commit de registro de decisiones y lanzamiento de la Fase 4** (`git log -1`), aún **sin publicar**; se publicará con el gate de la Fase 4. |
| **SPEC / ARCHITECTURE / contrato** | SPEC v0.3 · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.3.0**. |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–3, publicadas en `origin/main`. |
| 🔄 **En curso** | **Fase 4 — importador de Cashew** (Run `run_f5e95406186a`, lanzada el 2026-10-08). Ver §6 y §7 para la tarea activa. |
| ⏳ **Pendiente** | Resto de la Fase 4 (T-402 ∥ T-403 tras T-401) · decision gate hacia `main` · `--dry-run` sobre copia del respaldo real (autorizado) · Fase 5 (UI; `T-501`) · Fase 6 · Fase 7 · despliegue VPS → V2 → V3 → V4. |

Backend actual: **44 de 86 rutas = 71 de 127 operaciones**, 6 migraciones (cabeza `0006`), **715 pruebas**. La Fase 4 añade la migración `0007` (T-401). Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-08, reanudación)

- **Estado real verificado** frente a este archivo: `origin/main` ya estaba en `b3797b1` (push de Adrian); Adrian eliminó todos los worktrees de tareas; Docker dejó de ser accesible hasta que Adrian ejecutó `wsl --shutdown` y reabrió WSL: **Docker 29.5.2 / Compose v5.1.4 operativos**, no hizo falta instalar Docker Engine.
- **D3 – contrato 0.3.0** (`f83742f`): `409 loan_already_settled`, `422 movement_kind_immutable`, `fx_rate_to_base` opcional solo de entrada en suscripciones.
- **D2 – cobros vencidos** (`7922d09`): archivar o borrar una suscripción cancela (borrado lógico) **todas** las programadas sin publicar de la regla, vencidas incluidas; lo publicado no se toca. Dos pruebas anteriores que fijaban el comportamiento viejo se reescribieron y se añadieron 3. Sonda con `uvicorn` real: tras archivar `[]` (antes quedaba la vencida), tras reactivar **una** programada (antes dos).
- **Paso 2 (documentos, `6a14a6e`):** ADR-008 (propuesto) y tareas T-401, T-402 y T-403, contrastadas con contrato, esquema y código.
- **Verificación completa** sobre el árbol final: `ruff`, `mypy --strict`, **715 pruebas** con PostgreSQL real, `alembic` 0005↔0006 con `check` limpio, `check_openapi.py`; auditoría de seguridad de los commits publicados.

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-08 (noche) | **«Acepto todas tus recomendaciones. OK, puedes continuar con el Paso 3».** Queda **ADR-008 ACEPTADO** con **J1-A, J2-C, J3-A** (la letra de J2 se aclaró: la recomendada es la C). **Autoriza un `--dry-run` sobre una copia de su respaldo real al final de la Fase 4** (solo conteos y saldos, nunca filas). **Lanza la Fase 4.** |
| 2026-10-08 (noche) | **«Todo A»** a las recomendaciones: **D1-A** (publicar tras verificar), **D2-A** (cancelar todas las programadas sin publicar), **D3-A**, **D4-A**, **D4b-A**, **D5: J1-A y J3-A**, **D8-A** (tasa de importación: `--fx-rate`, o la de `app_settings` como provisional). **J2 queda por aclarar**: la recomendada es la **C** y «A» es otra opción (ver §5). Confirmó que **el push de las 17:36 fue suyo**. Ejecutó `wsl --shutdown` para restablecer Docker. |
| 2026-10-08 (tarde) | **«OK»** al plan de reanudación (Pasos 1 y 2) y al conjunto de recomendaciones D1–D6, interpretado por el coordinador como **«todo A»**: D1 publicar docs, D2 cancelar todas las programadas sin publicar al archivar, D3 contrato, D4 alcance acotado de la Fase 4, D4b `/imports` diferido, D5 ADR por redactar, D6 limpieza. *Si no era esa la intención, Adrian debe decirlo.* |
| 2026-10-08 (tarde) | **D6 ejecutada por Adrian:** eliminó los 10 worktrees restantes (y antes, 8); quedan solo `main` y `master-dev`. |
| 2026-10-08 (tarde) | Adrian abrió Docker Desktop; el coordinador comprobó que **sigue sin ser accesible** desde WSL (D0). |
| 2026-10-08 (mañana) | Continuar la Fase 3; aprobar el merge a `main` (gate `gate_621dc454eeee`); protocolo de sesión en `CLAUDE.md` §10. El push de `main` lo hizo alguien a las 17:36. |
| 2026-10-07 | ADR-001 **A** (UI propia en Flutter Web reutilizando widgets de Cashew), ADR-002 **A** (sesión en servidor + cookie), ADR-003 **A** (interés en base caja; pago primero a interés), ADR-004 **A** (tipo de cambio manual manda), ADR-006 **A** (PIN, luego WebAuthn), ADR-007 **A** (SQLAlchemy síncrono). |
| Fases 0–2 (oct 2026) | Importador **SQLite primero**, CSV solo como rescate, siempre sobre una copia; el respaldo real es Cashew **v48**. Etiquetas en V1. Nombres duplicados permitidos en categorías y personas (únicos solo en cuentas y etiquetas). Usuarios solo por CLI en V1. `PATCH /transactions/{id}` admite `account_id` (misma moneda) y `kind`. |
| Fases 0–2 (oct 2026) | Agentes: **Codex** (`gpt-6.1-sol` general / `gpt-6-astra` el más potente / `gpt-6-luna` ligero) para backend y, después, UI; **Antigravity** solo como relevo; **Command Code** de reserva. |

## 5. Decisiones pendientes

Cada una: contexto → opciones (la más recomendable primero) → impacto.

*(Ninguna bloquea la Fase 4. Todas las anteriores quedaron resueltas el 2026-10-08.)*

**D7 · Para más adelante:** **ADR-005** modelo de sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 («a confirmar en la Fase 0») y la redacción «cobros futuros» de SPEC §8.1, que tras D2 debería decir «cobros programados sin publicar», a corregir con el próximo cambio de SPEC aprobado.

**Decisiones que aparecerán durante la Fase 4** (las plantea el coordinador cuando lleguen): cualquier regla de negocio que los workers pregunten con `ask` y no cubra el ADR-008; el decision gate de la Fase 4 hacia `main`.

## 6. Siguiente paso concreto

**Fase 4 en marcha** (Run `run_f5e95406186a`; todas con Codex; ramas `codex/T-40x-…` desde `master-dev`; el coordinador renombra la rama tras `worker-start`):

| Tarea | Contenido | Agente / modelo / esfuerzo | Depende de | Estado |
|---|---|---|---|---|
| T-401 | Migración `0007`, lector SQLite de solo lectura, cuentas/categorías/etiquetas/transacciones/transferencias, idempotencia, `--dry-run`, reporte y andamiaje | Codex `gpt-6.1-sol` · high | — | **lanzada** (`docs/tasks/T-401-importer-core.md`) |
| T-402 | Préstamos según ADR-008 (+ segunda pasada de tasas) | Codex `gpt-6.1-sol` · high (`gpt-6-astra` si hay devoluciones) | T-401 | planificada (`docs/tasks/T-402-importer-loans.md`) |
| T-403 | Suscripciones/recurrentes, cuadre final con código de salida, documentación | Codex `gpt-6.1-sol` · medium | T-401 | planificada (`docs/tasks/T-403-importer-subscriptions.md`) |

Orden: **T-401 sola** → verificar y fusionar → **T-402 ∥ T-403** (archivos disjuntos) → verificar cada una → integrar ambas y comprobar el cuadre con **diferido 0** → `--dry-run` sobre copia del respaldo real (solo conteos y saldos) → decision gate hacia `main` y publicación.

**Cómo las verifico:** `ruff`, `mypy --strict`, `pytest` con PostgreSQL y `alembic` (0006↔0007) corridos por mí; fixture contra `expected.json` y ADR-008; **idempotencia** (segunda importación ⇒ 0 creados, 0 modificados); `--dry-run` ⇒ datos financieros intactos; saldos que cuadran (`unexplained = 0.00`); sin datos reales en git, logs ni reportes; lectura completa del código del importador (no confiar en el resumen del worker).

**Al retomar:** `orca orchestration run-use --id run_f5e95406186a`; una sola espera `check --wait` (<10 min).

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 4: `run_f5e95406186a`** (creado el 2026-10-08). T-401 lanzada (ver `orca orchestration task-list`). **Run de la Fase 3:** `run_63b520544a30` (cerrado en la práctica: 4 tareas `completed`, ningún worker vivo). Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`.

**Worktrees:** `Monetae` → `main`, `Monetae-master-dev` → `master-dev`, más el de cada tarea en curso (`Monetae-codex-T-40x-…`, creado por Orca con `new-child`). Docker operativo; disco ≈ 3,7 GB libres (vigilar: cada worker crea su `.venv`).

**Paneles de Orca:** el del coordinador, `lupuna` (otro proyecto), «Monetae Cashew analysis phase 0» y `…Monetae-codex-T-202-money-fx` (sesión y panel antiguos; Adrian puede cerrarlos), y los terminales de los workers de la Fase 4.

## 8. Limitaciones y riesgos conocidos

- **Docker Desktop depende de la integración con WSL** (distro `AlmaLinux-9`): si tras reiniciar `/usr/bin/docker` apunta a un destino inexistente, hay que reactivar *Settings → Resources → WSL integration* y hacer `wsl --shutdown`.
- **La importación de datos reales** nunca se ha probado: el esquema v48 real solo se conoce por el análisis y la fixture sintética (por eso el `--dry-run` sobre una copia, D5).
- **Sin auditoría de seguridad externa**; endurecimiento previsto en la Fase 7.
- La BD admite un `income` con monto negativo si se escribe SQL directo; solo la API garantiza el signo (decidir con el importador; `ARCHITECTURE.md` §10.12).
- El límite de intentos de login usa `request.client.host`: detrás de un proxy hace falta configuración (§10.10). `501 google_login_not_available` no figura en el contrato congelado (§10.11). `updated_at` se refresca vía ORM/Core, no con SQL crudo (§10.8).
- `reactivation_suggestions` solo se rellena al **crear** o **publicar** una transacción de gasto; `GET /transactions` no las calcula.
- Totales de suscripciones: sin proveedor de tipos de cambio (Fase 6) solo se suma la moneda igual a la de reporte; las demás cuentan en `unconverted_count`. La tasa de una suscripción en moneda extranjera es **provisional** (se confirma al publicar cada cobro).
- `end_on` de `recurring_rules` existe pero no se expone; el CRUD de `/recurring-rules` es de la Fase 6.
- La clave secreta por defecto es de ejemplo; en `prod` la app se niega a arrancar con ella o con cookies sin `Secure`.
- **Disco:** ≈ 3,7 GB libres en `/` (20 GB). Vigilar antes de Docker/Flutter.
- **Repositorio público:** todo push se audita antes. Los datos reales de Adrian solo viven en `reference/backups/` (ignorado por git).
- La cuota de Claude Pro es limitada: delegar lectura masiva y generación de código.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md (§10), docs/SPEC.md, ADRs y tareas abiertas. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list
git -C ../Monetae log --oneline -1 && git rev-parse --short origin/main   # main = master-dev = origin/main = origin/master-dev

# 1) Herramientas (a nivel de usuario; el Python del sistema es 3.9, NO usarlo para el proyecto)
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
uv --version && docker compose version && flutter --version | head -1   # si 'docker' no existe: D0 (Docker Desktop no está integrado con WSL)
orca status --json | head -5                           # ok: true
orca orchestration run-use --id run_63b520544a30       # solo para consultar la Fase 3

# 2) Verificar el backend (≈ 5 min; necesita PostgreSQL en Docker)
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 715 passed
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

## Anexo A · Qué incluye el backend (verificado sobre la cabeza de `master-dev`)

FastAPI síncrono (ADR-007) en `services/api`: **44 de 86 rutas = 71 de 127 operaciones** (Fase 2: 29 rutas / 48 operaciones; Fase 3: +15 / +23).

- **Acceso:** login por correo y contraseña (argon2id), sesiones opacas con cookie `HttpOnly`, CSRF firmado con HMAC + comprobación de `Origin`, límite de intentos persistente, `users/me`, cierre de sesión. Usuarios solo por CLI: `python -m monetae.cli create-user`.
- **Catálogos:** cuentas, categorías (con las 2 de sistema de interés), personas con alias, etiquetas.
- **Libro mayor:** transacciones (CRUD, filtros, etiquetas, saldos calculados, idempotencia, borrado/restauración lógica), transferencias de dos patas (también entre monedas), lotes atómicos, publicar programadas.
- **Préstamos (T-301/T-302):** `loans` + `loan_movements` (desembolso, interés, pago, ajuste, condonación); saldo y estado **calculados**, sin «liquidar»; pago primero a interés; exceso con `adjustment` o `income_expense`; cada movimiento afecta a **su** cuenta (también otra moneda); edición/borrado con revalidación de todo el libro (`409 ledger_inconsistent`); borrado lógico atómico; resumen por persona y moneda. 15 operaciones.
- **Suscripciones (T-303/T-304):** `subscriptions` + `recurring_rules`; archivado reversible (conserva el historial, cancela todas las programadas sin publicar, fuera de listado y totales); reactivación; próxima `scheduled` materializada y avanzada al publicar; totales por moneda; sugerencia de reactivación por título normalizado. 8 operaciones.
- **Base de datos:** migraciones `0001` identidad y catálogos · `0002` intentos de login · `0003` transacciones · `0004` integridad de transferencias · `0005` préstamos · `0006` suscripciones y reglas. FK **compuestas con `user_id`**: la BD rechaza datos de otro usuario.
- **Calidad:** 715 pruebas con PostgreSQL real, `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`.
- **No implementado (operaciones del contrato):** usuarios 9 (PIN/bloqueo/WebAuthn), reportes 8, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, Google OIDC 1, exportaciones 1, sugerencia de tipo de cambio 1.

## Anexo B · GitHub

`origin` = `https://github.com/Adrian-asandym/Monetae.git` (público). Antes de cada push se verifica el historial (sin `.env`, claves, `reference/`, respaldos; únicos `.sqlite`/`.csv` versionados: los 3 fixtures sintéticos de `services/api/tests/fixtures/cashew_v48/`; sin correos reales). `origin/main` ya contiene la Fase 3 (`b3797b1`). Comando: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev` (sin `--force`; `gh` autenticado como `Adrian-asandym`).

## Anexo C · Lecciones operativas (no repetir errores)

- **Verificar, no confiar en el resumen del worker:** correr yo `ruff`, `mypy`, `pytest`, leer el servicio entero y hacer pruebas manuales. Así aparecieron: un bloqueo `FOR UPDATE` por petición (5,6 s → 0,03 s), duplicados de nombre mal aplicados, citas inventadas, errores de conteo y el `commit` posterior a la respuesta.
- **`TestClient` no es un servidor:** espera a que la app termine por completo y oculta errores de orden respuesta/commit. Probar además con `uvicorn` real y `httpx`.
- **Releer la spec contra el contrato y el código antes de lanzar:** en la Fase 3 corregí mi propia spec dos veces al lanzar. Las preguntas del worker (`ask`) fueron todas legítimas: responderlas con el contrato abierto.
- **Reglas de bloqueo:** las lecturas no toman bloqueos de fila; las escrituras usan bloqueos consultivos con orden fijo.
- **Orca:** `worker-start` puede devolver `outcome_unknown` aunque el worker trabaje; Antigravity pide «trust workspace» en cada worktree; Codex puede mostrar un menú «Update available» que solo Adrian puede saltar; `gate-create` no acepta `--run` y deja la tarea en `ready` (marcarla `completed` a mano); al abrir sesión hay que re-vincular el Run (`run-use --id`); solo **una** espera `check --wait` por Run (`waiter_exists` si queda una colgada), y menos de 10 min por llamada; no se pueden editar las especificaciones de una tarea ya creada (crear otra y marcar la vieja `failed/superseded`).
- **Shell:** nunca `pkill -f` ni `pgrep -f` con un texto que aparezca en el propio comando (mata el shell, código 144); parar servidores por puerto con `ss -ltnp`.
- **Modelos Codex** (`~/.codex/models_cache.json`): `gpt-6.1-sol` (general), `gpt-6-astra` (el más potente), `gpt-6-luna` (ligero; sirve para CRUD pero exige revisar las reglas).
- **Privacidad:** nunca leer filas de `reference/backups/`; trabajar sobre una copia; los fixtures son sintéticos.
