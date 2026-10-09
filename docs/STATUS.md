# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-08, ~21:00 (America/Lima)** |
| **`main` / `master-dev` / `origin`** | Tras el push de esta sesión, `main` = `master-dev` = `origin/main` = `origin/master-dev` = **el commit que contiene este archivo** (`git log -1`). Antes: `origin/main` = `b3797b1` (Fase 3, que **publicó Adrian** a las 17:36) y `origin/master-dev` = `05ff1d9`. |
| **Gate** | `gate_e3b1a2193ba2` (merge de docs a `main` + push): **resuelto** con la aprobación de Adrian («todo A», D1-A) tras verificar. |
| **SPEC / ARCHITECTURE / contrato** | SPEC v0.3 · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.3.0** (validado con `check_openapi.py`, Redocly y `test_contract_subset` con PostgreSQL). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–3, publicadas en `origin/main`. Paso 1 de la reanudación (D0 Docker, D2, D3, publicación). |
| 🔄 **En curso** | **Preparación de la Fase 4** (importador de Cashew): ADR-008 y tareas T-401…T-403 escritas, **sin lanzar**. No hay Run de la Fase 4 ni workers. |
| ⏳ **Pendiente** | Confirmar **J2** del ADR-008 y el permiso del dry-run · **OK explícito de Adrian al Paso 3** · Fase 4 (T-401 → T-402 ∥ T-403) · Fase 5 (UI; `T-501`) · Fase 6 · Fase 7 · despliegue VPS → V2 → V3 → V4. |

Backend actual: **44 de 86 rutas = 71 de 127 operaciones**, 6 migraciones (cabeza `0006`), **715 pruebas**. La Fase 4 añadirá la migración `0007` (T-401). Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-08, reanudación)

- **Estado real verificado** frente a este archivo: `origin/main` ya estaba en `b3797b1` (push de Adrian); Adrian eliminó todos los worktrees de tareas; Docker dejó de ser accesible hasta que Adrian ejecutó `wsl --shutdown` y reabrió WSL: **Docker 29.5.2 / Compose v5.1.4 operativos**, no hizo falta instalar Docker Engine.
- **D3 – contrato 0.3.0** (`f83742f`): `409 loan_already_settled`, `422 movement_kind_immutable`, `fx_rate_to_base` opcional solo de entrada en suscripciones.
- **D2 – cobros vencidos** (`7922d09`): archivar o borrar una suscripción cancela (borrado lógico) **todas** las programadas sin publicar de la regla, vencidas incluidas; lo publicado no se toca. Dos pruebas anteriores que fijaban el comportamiento viejo se reescribieron y se añadieron 3. Sonda con `uvicorn` real: tras archivar `[]` (antes quedaba la vencida), tras reactivar **una** programada (antes dos).
- **Paso 2 (documentos, `6a14a6e`):** ADR-008 (propuesto) y tareas T-401, T-402 y T-403, contrastadas con contrato, esquema y código.
- **Verificación completa** sobre el árbol final: `ruff`, `mypy --strict`, **715 pruebas** con PostgreSQL real, `alembic` 0005↔0006 con `check` limpio, `check_openapi.py`; auditoría de seguridad de los commits publicados.

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
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

**D5 · ADR-008, J2 — hay que aclarar la letra** (bloquea solo T-402, no T-401). Pago que supera el saldo del préstamo (casos A y D de la fixture):
- **C (recomendada): partir el pago** en «pago por el saldo exacto» + «ingreso o gasto ordinario por el exceso». *Razón:* conserva el principal real (50 siguen siendo 50), el préstamo termina en 0/`settled` y el efectivo cuadra, sin declarar interés que Cashew no etiquetó.
- A: `adjustment` positivo por el exceso y pago completo. *Contra:* el principal pasa de 50 a 60; se altera el dato «cuánto presté».
- B: `interest` por el exceso. *Contra:* reconoce como gasto un interés no etiquetado y puede duplicar el «interés suelto».
- *Pregunta concreta:* ¿**C** (recomendada) o **A** literal? Mientras no se aclare, el ADR sigue en «propuesto».

**D5b · Permiso para un `--dry-run` sobre una copia del respaldo real** (solo conteos y saldos, nunca filas), al final de la Fase 4. Recomendado: sí. *Razón:* es la única forma de validar «los saldos coinciden con Cashew» (RF-40c) con datos reales. Sin responder; no bloquea nada hasta el final de la Fase 4. Sin permiso solo se usan los fixtures.

**D7 · Para más adelante** (no bloquean la Fase 4): **ADR-005** modelo de sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 («a confirmar en la Fase 0») y la redacción «cobros futuros» de SPEC §8.1, que tras D2 debería decir «cobros programados sin publicar», a corregir con el próximo cambio de SPEC aprobado.

**Resueltas hoy:** D0 (Docker), D1 (publicado), D2 (hecho), D3 (hecho), D4/D4b (aceptadas; reflejadas en T-401…T-403), D5-J1=A y J3=A, D6 (hecha por Adrian), D8=A.

## 6. Siguiente paso concreto

**Para lanzar el Paso 3 falta solo:** (1) Adrian aclara **J2**, que bloquea únicamente T-402; (2) el **OK explícito** de Adrian a lanzar. T-401 no depende de J2 y puede salir primero.

Antes de crear el Run: `orca skills get orchestration --full` (Orca se actualizó), `orca status --json`, `docker version`, `git worktree list` (solo `main` y `master-dev`), disco (≥ 3 GB libres).

**Paso 3 — Fase 4** (Run nuevo «Fase 4: importador de Cashew»; todas con Codex; ramas `codex/T-40x-…` desde `master-dev`; el coordinador renombra la rama tras `worker-start`):

| Tarea | Contenido | Agente / modelo / esfuerzo | Depende de | Spec |
|---|---|---|---|---|
| T-401 | Migración `0007`, lector SQLite de solo lectura, cuentas/categorías/etiquetas/transacciones/transferencias, idempotencia, `--dry-run`, reporte y andamiaje | Codex `gpt-6.1-sol` · high | — | `docs/tasks/T-401-importer-core.md` |
| T-402 | Préstamos según ADR-008 (+ segunda pasada de tasas) | Codex `gpt-6.1-sol` · high (`gpt-6-astra` si hay devoluciones) | T-401, **J2 aclarado** | `docs/tasks/T-402-importer-loans.md` |
| T-403 | Suscripciones/recurrentes, cuadre final con código de salida, documentación | Codex `gpt-6.1-sol` · medium | T-401 | `docs/tasks/T-403-importer-subscriptions.md` |

Orden: **T-401 sola** → verificar y fusionar → **T-402 ∥ T-403** (archivos disjuntos) → verificar cada una → integrar ambas y comprobar el cuadre con **diferido 0** → decision gate hacia `main`. Si T-402 se retrasa por J2, T-403 puede ir sola tras T-401.

**Cómo las verificaré:** `ruff`, `mypy --strict`, `pytest` con PostgreSQL y `alembic` (0006↔0007) corridos por mí; fixture contra `expected.json` y ADR-008; **idempotencia** (segunda importación ⇒ 0 creados, 0 modificados); `--dry-run` ⇒ datos financieros intactos; saldos que cuadran (`unexplained = 0.00`); sin datos reales en git, logs ni reportes; y, si Adrian lo autoriza (D5b), un `--dry-run` sobre una **copia** de su respaldo mostrando solo conteos y saldos.

**Opcional en paralelo:** `T-501` (spike de desacople de widgets, Fase 5) no toca el backend, pero Flutter pide disco (hoy ≈ 3,7 GB libres): solo si Adrian lo pide.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 3: `run_63b520544a30`.** Tareas T-301 `task_d8d91292787f`, T-303 `task_39bd586cd28f`, T-302 `task_112bd988b505` y T-304 `task_3e72e1ff8b03` completadas (T-304 se marcó `completed` tras resolver el gate); `task_2af7f21c0086` y `task_923219f8ed0e` son intentos antiguos `failed/superseded`. **Workers: ninguno vivo.** **No existe Run de la Fase 4** (se crea en el Paso 3). Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`. Al retomar: `orca orchestration run-use --id <run>`.

**Worktrees:** solo `Monetae` → `main` y `Monetae-master-dev` → `master-dev`, ambos limpios; no quedan ramas `codex/*` ni `agy/*`. Sin contenedores, sin servidores en el puerto 8765, sin `.env` sueltos. Disco: ≈ 3,7 GB libres.

**Paneles de Orca abiertos:** el del coordinador, `lupuna` (otro proyecto), «Monetae Cashew analysis phase 0» (sesión antigua) y `…Monetae-codex-T-202-money-fx` (su worktree ya no existe): Adrian puede cerrar los dos últimos.

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
