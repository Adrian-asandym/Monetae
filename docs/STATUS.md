# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-08, ~23:25 (America/Lima)** — cierre de sesión; Fase 4 integrada en `master-dev`, a la espera de decision gate |
| **`origin`** | `origin/main` = `origin/master-dev` = **`0e74c67`** (Fase 3 + contrato 0.3.0 + ADR-008 y tareas). **No incluye la Fase 4.** |
| **`main`** | `0e74c67`. |
| **`master-dev`** | **`8dcb65d` + el commit de este cierre (`git log -1`)**, con toda la Fase 4 (migración `0007`, importador de Cashew y su CLI) y sin publicar. Va por delante de `main` con código, pruebas y documentación. |
| **Gate abierto** | `gate_1e81cf0fd994`: merge de la Fase 4 a `main` y push. **Pendiente de Adrian.** |
| **SPEC / ARCHITECTURE / contrato** | SPEC v0.3 · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.3.0** (la Fase 4 no cambió el contrato HTTP: el importador es solo línea de comandos). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–3, publicadas. **Fase 4 (importador de Cashew)** integrada en `master-dev`: T-401, T-402, T-403 y T-404 aceptadas, cada una con su seguimiento; verificada con el `--dry-run` sobre una copia del respaldo real. |
| 🔄 **En curso** | Nada ejecutándose. No hay workers vivos. |
| ⏳ **Pendiente** | **Decision gate de la Fase 4** hacia `main` y publicación · decisiones L1 y X1 (§5) · la **importación real definitiva** (`apply` contra la base de Adrian, no el dry-run) · Fase 5 (UI Flutter; `T-501`) · Fase 6 (incluye presupuestos, metas y reglas de título, hoy listados como «pendiente de Fase 6» por el importador) · Fase 7 · despliegue VPS → V2 → V3 → V4. |

Backend actual: **44 de 86 rutas = 71 de 127 operaciones**, 7 migraciones (cabeza `0007`), **898 pruebas** con PostgreSQL real, más el comando `python -m monetae.cli import-cashew`. Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-08 noche)

- **Decisiones de Adrian registradas** y ADR-008 aceptado (J1-A, J2-C, J3-A). **Paso 3 lanzado** con su OK explícito.
- **T-401 (+T-401b)** migración `0007` (auditoría + identidades externas), lector SQLite de solo lectura, mapeo, ejecutor atómico y CLI. El seguimiento hizo que una fila anómala (importe 0, cuenta huérfana, tipo desconocido) **no aborte** la importación y que mande el **signo del importe**, que es lo que suma Cashew.
- **T-402 (préstamos)** según ADR-008, con segunda pasada de tasas (`--loan-fx-rates`).
- **T-403 (+T-403b)** suscripciones y recurrentes, **cuadre atómico** (si algún saldo no cuadra no se guarda nada financiero: código 5; `--allow-balance-diff` lo permite). El seguimiento corrigió un defecto de diseño que la fixture no mostraba: **Cashew guarda cada ocurrencia de una suscripción como una fila encadenada** (`pk::predict::N`), no una sola fila; ahora se agrupan en series.
- **T-404 (transferencias)**: Cashew empareja las transferencias en **un solo sentido**, no de forma recíproca; se aceptan ambas y cada fila sin emparejar lleva su motivo.
- **`--dry-run` real** (autorizado por Adrian, sobre una copia fuera del repositorio, original intacto por hash, copia borrada): terminó con código 0 y **el cuadre de todas las cuentas fue exacto**. Reveló los dos defectos anteriores (series y transferencias unidireccionales) y dos casos que requieren decisión (§5).
- **Infraestructura:** `infra/docker-compose.yml` admite `MONETAE_DB_PORT` y `COMPOSE_PROJECT_NAME` para que dos workers no compartan base de datos (un `down -v` borraría la del otro).

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-09 | «**OK, todo A**»: **G1-A** (aprobar merge a `main` y push de la Fase 4), **L1-A** (T-405: préstamos de largo plazo sin desembolso con desembolso sin dinero, principal = suma de pagos, ítem `principal_assumed`), **X1-A** (transferencias entre monedas distintas, después de V1), **X2** (borrar los 4 worktrees de la Fase 4: **los borró Adrian él mismo**, junto con sus ramas `codex/T-40x`; el coordinador comprobó que sus 4 commits están en `master-dev`). |
| 2026-10-08 (noche) | «**Acepto todas tus recomendaciones. OK, puedes continuar con el Paso 3**»: ADR-008 **J1-A, J2-C, J3-A**; autorizó un `--dry-run` sobre una **copia** del respaldo real **solo con conteos y saldos**; lanzó la Fase 4. |
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

> **Resueltas el 2026-10-09 (Adrian, «todo A»): G1-A, L1-A, X1-A, X2.** Se conservan las opciones como registro.

**G1 · Decision gate de la Fase 4: merge `master-dev` → `main` y publicación — RESUELTA: A.** Auditoría de seguridad de lo que se publica: sin `.env`, claves ni `reference/`; solo los 3 fixtures sintéticos; sin datos del respaldo real.
- **A (recomendada): aprobar y publicar** (sin `--force`). *Razón:* 898 pruebas, el dry-run real cuadra al céntimo y es la forma de tener respaldo fuera de la máquina.
- B: esperar a resolver L1 y X1 y publicar todo junto.

**L1 · Préstamos de largo plazo SIN desembolso registrado — RESUELTA: A (T-405).** En el respaldo real los préstamos de largo plazo no tienen su desembolso como transacción enlazada (solo cobros o pagos). Hoy fallan con `MissingDisbursementError`: se importan como transacciones **ordinarias** (el saldo cuadra), pero un cobro de préstamo se cuenta como **ingreso** (justo el problema P1) y el préstamo no aparece.
- **A (recomendada): crear el préstamo con un desembolso sin dinero** (`transaction_id` nulo, permitido por `ARCHITECTURE.md`/el `CHECK`), con **principal = suma de los pagos vinculados** (queda saldado), fecha justo antes del primer pago, y un ítem de revisión `principal_assumed`; los pagos se importan como pagos reales en sus cuentas. Adrian corrige el principal después con el `PUT` del desembolso. *Razón:* el préstamo, sus pagos y su historial quedan visibles, el capital no cuenta como ingreso y todo es corregible.
- B: importar los cobros/pagos como transacciones `kind='loan'` sin préstamo + revisión. *Razón:* no se inventa ningún principal; *contra:* no hay préstamo visible.
- C: dejarlo como hoy (ordinarias). *Contra:* distorsiona las estadísticas.
- *Impacto:* tarea corta T-405 (`loans.py`); la importación real definitiva debe esperar a esta decisión porque el importador es solo-inserción.

**X1 · Transferencias entre monedas distintas — RESUELTA: A (después de V1; no hay T-406).** Se importan como un gasto y un ingreso ordinarios (con motivo `currency_mismatch`); Monetae sí soporta transferencias entre monedas.
- **A (recomendada): dejarlo para después de V1** (son pocas; no hay reportes hasta la Fase 6 y se puede re-vincular entonces).
- B: implementarlo ahora (T-406): emparejar con la tasa implícita del par. *Contra:* más trabajo y riesgo antes de ver reportes; y el importador es solo-inserción, así que re-importar no corregiría las ya importadas.

**D7 · Para más adelante:** **ADR-005** sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 y la redacción «cobros futuros» de SPEC §8.1 (tras D2 debería decir «cobros programados sin publicar»), a corregir con el próximo cambio de SPEC aprobado.

## 6. Siguiente paso concreto

**Primero, Adrian responde G1, L1 y X1 (§5; basta la letra).** Después, según lo que elija:

| Si… | Se hace | Agente / modelo / esfuerzo | Rama y BD | Cómo lo verifico |
|---|---|---|---|---|
| **L1 = A** | **T-405**: en `importers/cashew/loans.py`, los préstamos de largo plazo sin desembolso enlazado se crean con un desembolso **sin dinero** (`transaction_id` nulo), principal = suma de sus pagos, fecha justo antes del primer pago, ítem de revisión `principal_assumed`; los pagos se importan como pagos reales. La spec (`docs/tasks/T-405-…`) la escribe el coordinador **contrastada con `loans.py` y el ADR-008** antes de lanzar. | Codex `gpt-6.1-sol` · medium | `codex/T-405-importer-longterm-loans` desde `master-dev`; BD propia: `MONETAE_DB_PORT=5440 COMPOSE_PROJECT_NAME=monetae-t405` | `ruff`, `mypy`, `pytest` con PostgreSQL y `alembic` corridos por mí; lectura del código; sonda manual con copias de la fixture y rarezas; **repetir el `--dry-run` real** (copia en el scratchpad, solo agregados) y comprobar que el cuadre sigue en 0,00 |
| **L1 = B o C** | B: tarea equivalente (cobros como `kind='loan'` sin préstamo); C: nada | — | — | — |
| **X1 = B** | **T-406**: emparejar transferencias entre monedas con la tasa implícita (después de T-405) | Codex `gpt-6.1-sol` · medium | `codex/T-406-importer-fx-transfers`, BD `5441` / `monetae-t406` | igual que arriba |
| **G1 = A** | Auditoría de seguridad repetida sobre lo que se publique, `gate-resolve`, `git merge --ff-only master-dev` en el worktree de `main`, push sin `--force` (`GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev`) y marcar `task_9450f697ce8a` como `completed` | coordinador | — | `git ls-remote origin` debe mostrar ambas ramas en la cabeza nueva |

**Después, Fase 5 (UI Flutter):** primera tarea `T-501` (spike de desacople de widgets de Cashew, `docs/tasks/T-501-ui-decoupling-spike.md`, ya escrita): Codex (modelo medio-alto), rama `codex/T-501-ui-decoupling-spike`. Flutter pide disco (hoy ≈ 3,5 GB libres): **borrar antes los 4 worktrees fusionados de la Fase 4**, con OK de Adrian.

**La importación real definitiva** (`apply` sobre la base de Adrian) va **después de L1 y X1**: el importador es solo-inserción y no corrige lo ya importado. Procedimiento: copia del respaldo fuera de `reference/backups`, `--dry-run` previo, `apply`, borrar la copia.

**Antes de lanzar cualquier tarea:** `orca skills get orchestration --full` (Orca se actualiza), `orca status --json`, `docker version`, `git worktree list`, disco ≥ 3 GB y el puerto de la BD de la tarea libre.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 4: `run_f5e95406186a`.** Tareas T-401 `task_e32a402a4dec` (+T-401b `task_83ae6f5c2bbc`), T-402 `task_8e0dc0347237`, T-403 `task_9b25b87c9b93` (+T-403b `task_03fd94d8705d`) `completed`; **T-404 `task_9450f697ce8a` figura `blocked`** solo porque cuelga el gate abierto `gate_1e81cf0fd994` (se marca `completed` al resolverlo). **Ningún worker vivo**: verificado con `worker-list` (sin terminales por reclamar), sin procesos de agentes ni servidores y sin contenedores. Las filas `unverifiable` de `worker-list` corresponden a terminales ya liberados, no a agentes en ejecución. Run de la Fase 3: `run_63b520544a30`. Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`. Al retomar: `orca orchestration run-use --id run_f5e95406186a`.

**Worktrees:** solo `Monetae` → `main` y `Monetae-master-dev` → `master-dev`. Adrian borró (2026-10-09) los 4 de la Fase 4 y sus ramas `codex/T-40x`; sus commits siguen en `master-dev`. Sin `.env` sueltos ni copias del respaldo real. Disco ≈ 3,7 GB libres.

**Paneles de Orca abiertos (2):** el del coordinador y `lupuna` (otro proyecto, no se toca). Adrian ya cerró los paneles antiguos.

## 8. Limitaciones y riesgos conocidos

- **Docker Desktop depende de la integración con WSL** (distro `AlmaLinux-9`): si tras reiniciar `/usr/bin/docker` apunta a un destino inexistente, hay que reactivar *Settings → Resources → WSL integration* y hacer `wsl --shutdown`.
- **La importación de datos reales** nunca se ha probado: el esquema v48 real solo se conoce por el análisis y la fixture sintética (por eso el `--dry-run` sobre una copia, D5).
- **Importador (Fase 4):** solo línea de comandos; **solo inserción** (no corrige lo ya importado: por eso conviene resolver L1/X1 antes de la importación real). Presupuestos, metas y reglas de título de Cashew no se importan hasta la Fase 6 (se listan como pendientes). Los 3 hechos que la fixture sintética **ocultó** y solo el respaldo real mostró: series de suscripciones encadenadas, emparejado de transferencias unidireccional y préstamos de largo plazo sin desembolso.
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
uv run pytest -q                                        # esperado: 898 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0007
cd ../.. && python3 -I scripts/check_openapi.py         # contrato: 86 paths, 127 operaciones
docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 2b) Importador (humo sobre COPIA de la fixture, nunca el original):
#    cp services/api/tests/fixtures/cashew_v48/synthetic_v48.sqlite /tmp/c.sqlite
#    uv run python -m monetae.cli import-cashew --file /tmp/c.sqlite --user-email yo@example.test --fx-rate USD=3.8 --dry-run
#    (códigos de salida: 0 ok, 2 uso/ruta prohibida, 3 archivo inválido, 4 error, 5 saldos no cuadran)
#    Varias BD en paralelo: MONETAE_DB_PORT=<puerto libre> COMPOSE_PROJECT_NAME=<nombre único> docker compose ...

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
- **Calidad:** 898 pruebas con PostgreSQL real, `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`.
- **Importador de Cashew (Fase 4, `python -m monetae.cli import-cashew`):** lee un SQLite de Cashew (v48) **en solo lectura y sobre una copia**; importa cuentas, categorías, etiquetas, transacciones (posted y scheduled), transferencias, préstamos (ADR-008), suscripciones y recurrentes (series); idempotente (solo inserción), `--dry-run`, cuadre de saldos atómico, reporte con ítems de revisión. Documentación: `docs/importers/cashew.md` y `docs/importers/cashew-loans.md`.
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
- **La fixture sintética no basta:** en la Fase 4 ocultó tres supuestos falsos sobre los datos reales de Cashew (series de ocurrencias, emparejado unidireccional, préstamos sin desembolso). Antes de dar por buena una suposición sobre datos ajenos, leer el código de referencia (`reference/Cashew`) y correr un `--dry-run` real agregado. **No poner cifras del respaldo real en archivos versionados** (el repositorio es público).
- **Orca/Codex:** si `worker-start` falla en `agent_readiness` por el aviso «Update available», enviar *Esc* a la terminal (`orca terminal send --terminal <h> --text $'\x1b'`; nunca «Update now» ni «Skip until next version») y reintentar con `worker-start --task <id> --retry-of <dispatch> --worktree path:<dir> --terminal <h>`. Para un seguimiento en la misma terminal: `worker-start --spec ... --worktree path:<dir> --terminal <h>`.
- **Shell:** en `--body "..."` no usar acentos graves (el shell los ejecuta); usar comillas simples.
- **Bases de datos en paralelo:** nunca compartir proyecto/puerto de Compose entre workers; asignar `MONETAE_DB_PORT` y `COMPOSE_PROJECT_NAME` propios.
