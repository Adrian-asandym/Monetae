# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Actualizado: **2026-10-08 (Fase 3 en curso)** · Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador) y `docs/SPEC.md` (qué se construye).

## 1. Dónde estamos

| | |
|---|---|
| **Fase actual** | **Fase 2 (backend base): COMPLETA.** **Fase 3 (préstamos y suscripciones): EN CURSO** (lanzada el 2026-10-08 con la aprobación de Adrian). T-301, T-302 y T-303 **integradas en `master-dev`**; T-304 **en ejecución**. |
| **Fases cerradas** | Fase 0 (análisis de Cashew), Fase 1 (diseño: ADR, esquema, OpenAPI, fixture), Fase 2 (backend base). |
| **Ramas** | `main` = `origin/main` = **`05ff1d9`** (cierre de la Fase 2 + traspaso). `master-dev` va **por delante** con la Fase 3 (dominio de préstamos y suscripciones, API de préstamos y un arreglo de `commit`; 647 pruebas verificadas con PostgreSQL); **no se ha hecho merge a `main`** (requiere decision gate de Adrian). `origin/master-dev` está en `05ff1d9` hasta que se vuelva a subir. |
| **GitHub (`origin`)** | Ver §8. Si `git status -sb` muestra `ahead N`, el push está pendiente. |
| **Versión de la SPEC** | v0.3 (2026-10-07). Historial en `docs/SPEC.md` §18. |
| **Arquitectura** | `docs/ARCHITECTURE.md` v0.3. Puntos abiertos en su §10 (1–13). |

## 2. Qué incluye la Fase 2 (verificado sobre el commit integrado)

Backend FastAPI síncrono (ADR-007) en `services/api`, **29 de las 86 rutas (paths) del contrato = 48 de 127 operaciones**:

- **Acceso:** login por correo y contraseña (argon2id), sesiones opacas con cookie `HttpOnly`, CSRF firmado con HMAC + comprobación de `Origin`, límite de intentos persistente, `users/me`, cierre de sesión (una / todas). **Los usuarios se crean solo por CLI** (no hay registro público): `python -m monetae.cli create-user`.
- **Catálogos:** cuentas, categorías (con las 2 de sistema de interés), personas con alias, etiquetas.
- **Libro mayor:** transacciones (CRUD, filtros, etiquetas, saldos calculados, idempotencia, borrado/restauración lógica), transferencias de dos patas (también entre monedas), lotes atómicos, publicar programadas.
- **Base de datos:** 4 migraciones Alembic reversibles (`0001` identidad y catálogos, `0002` intentos de login, `0003` transacciones, `0004` integridad de transferencias). Claves foráneas **compuestas con `user_id`**: la BD rechaza referenciar datos de otro usuario.
- **Dominio puro:** `Money`, `ExchangeRate`, reglas de transacciones y transferencias.
- **Calidad:** **404 pruebas** con PostgreSQL real, `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`; migraciones 0→4→0→4 probadas; contrato validado con Redocly + `scripts/check_openapi.py`.

**No implementado todavía (por grupo, operaciones del contrato):** préstamos 15, usuarios 9 (PIN/bloqueo/WebAuthn), reportes 8, suscripciones 8, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, Google OIDC 1, exportaciones 1, sugerencia de tipo de cambio 1.

## 3. Decisiones ya tomadas (no reabrir sin Adrian)

| Tema | Decisión |
|------|----------|
| UI | **ADR-001 opción A:** UI propia en Flutter Web reutilizando y desacoplando widgets de Cashew. Spike previo: `docs/tasks/T-501-ui-decoupling-spike.md` (primera tarea de la Fase 5, no lanzado). |
| Auth | ADR-002 A: sesión en servidor + cookie; Google OIDC y correo/contraseña (Google en Fase 6). |
| Interés | ADR-003 A: base **caja**; cada pago se reparte **primero a interés**, luego a capital; el reparto se guarda en el movimiento. |
| Tipo de cambio | ADR-004 A: manual manda; sugerencia automática detrás de una interfaz (proveedor por verificar, Fase 6). |
| Bloqueo de app | ADR-006 A: PIN primero, WebAuthn después (barrera de comodidad). |
| ORM | ADR-007 A: SQLAlchemy síncrono + psycopg 3, endpoints `def`. |
| Importador | **SQLite primero**, CSV solo como rescate, **siempre sobre una copia** del respaldo. El esquema real del respaldo es Cashew **v48** (el código en `reference/Cashew` es v46: no se actualiza). |
| Etiquetas | En V1 (`tags`, `transaction_tags`), con asignación y filtro básicos. |
| Nombres | Duplicados **permitidos** en categorías y personas; únicos solo en cuentas y etiquetas. |
| Registro de usuarios | Solo por CLI en V1. |
| Contrato | `PATCH /transactions/{id}` admite `account_id` (misma moneda) y `kind`; registrado en `docs/api/README.md`. |
| Agentes | Codex (modelos `gpt-6.1-sol` / `gpt-6-luna` / `gpt-6-astra`) para backend y, después, UI; Antigravity solo como relevo; Command Code de reserva. |

## 4. Decisiones y acciones pendientes de Adrian

1. ~~Aprobar el plan de la Fase 3~~ — **aprobada el 2026-10-08**. Pendiente: **decision gate de Adrian** para el merge de la Fase 3 a `main` y el push, cuando T-304 esté aceptada.
2. **ADR-005** (modelo de sincronización para Android, V4): antes de V4.
3. **Orden de categorías** (Cashew permite reordenarlas; la SPEC no lo pide): decidir en la Fase 5.
4. **Google Cloud** (Fase 6): crear las credenciales OAuth (acción de Adrian) y decidir el proveedor de tipo de cambio.
5. **Despliegue en el VPS:** configurar el proxy para que el límite de intentos por IP vea la IP real (`ARCHITECTURE.md` §10.10).
6. **Limpieza de worktrees y terminales** (§7): opcional, la hace Adrian o lo pide al coordinador.
7. **Texto obsoleto en `docs/SPEC.md` §2** («a confirmar en la Fase 0», «Hipótesis»): la Fase 0 ya lo confirmó; actualizar con el próximo cambio de SPEC aprobado.

## 5. Limitaciones conocidas de la Fase 2

- La BD admite un `income` con monto negativo si se escribe SQL directo; solo la API garantiza el signo (decidir con el importador, Fase 4; `ARCHITECTURE.md` §10.12).
- El límite de intentos de login usa `request.client.host`: detrás de un proxy hace falta configuración (§10.10).
- `501 google_login_not_available` no figura en el contrato congelado (§10.11).
- `updated_at` se refresca vía ORM/Core, no con SQL crudo (§10.8).
- `loan_id` y `person_id` en `GET /transactions` devuelven página vacía hasta la Fase 3 (`TODO(phase-3)`).
- `reactivation_suggestions` en `Transaction` está vacío hasta que existan suscripciones (T-304).
- No ha habido auditoría de seguridad externa; hay una pasada de endurecimiento prevista en la Fase 7.
- **Corregido en `4b62d7c` (2026-10-08):** la Fase 2 hacía el `commit` de la sesión *después* de enviar la respuesta (FastAPI ≥ 0.118 con dependencias `yield`): con un servidor real, `login` + petición inmediata daba 401 en 34/40 intentos. `TestClient` lo ocultaba. Ahora `Database` usa `scope="function"` y hay una prueba que registra el orden real ASGI.
- La clave secreta por defecto es de ejemplo y solo sirve en local; en `prod` la app se niega a arrancar con ella o con cookies sin `Secure`.

## 6. Plan de la Fase 3 — escrito, **NO lanzado**

Objetivo: resolver P1–P4 (préstamos como libro mayor; suscripciones archivables). Ejemplos A–E de SPEC §7 como pruebas literales.

| Tarea | Contenido | Agente / modelo sugerido | Depende de | Spec |
|-------|-----------|--------------------------|-----------|------|
| T-301 ✅ | Dominio puro de préstamos (saldo calculado, reparto interés/capital, exceso, reabrir) — **aceptada e integrada** (`246a6d5`; 114 pruebas, 100 % de líneas) | Codex `gpt-6.1-sol` high | — | `docs/tasks/T-301-domain-loans.md` |
| T-303 ✅ | Dominio puro de suscripciones (archivar/reactivar, equivalentes, fechas, sugerencias) — **aceptada e integrada** (`9b1e347`; 73 pruebas, 100 % de líneas) | Codex `gpt-6.1-sol` medium | — | `docs/tasks/T-303-domain-subscriptions.md` |
| T-302 ✅ | Migración `0005`, servicios y API de préstamos (15 operaciones) — **aceptada e integrada** (`79fc715`; 646 pruebas; spec corregida al lanzar: columna interna `sequence`). Ampliaciones de contrato a registrar: `409 loan_already_settled`, `422 movement_kind_immutable` (ver `docs/api/README.md`) | Codex `gpt-6.1-sol` high | T-301 ✅ | `docs/tasks/T-302-loans-api.md` |
| T-304 🔄 | Migración `0006`, reglas recurrentes y API de suscripciones — **en ejecución** (rama `codex/T-304-subscriptions-api`, task `task_3e72e1ff8b03`, dispatch `ctx_c6510b5c94c9`; spec corregida contra el contrato) | Codex `gpt-6.1-sol` high | T-302 ✅, T-303 ✅ | `docs/tasks/T-304-subscriptions-api.md` |

Orden: **T-301 ∥ T-303 (hecho)** → **T-302 (hecho)** → T-304 (en curso) → gate a `main`. Archivos permitidos disjuntos entre T-301 y T-303; T-302 y T-304 son secuenciales (migraciones y `main.py`). Después de la Fase 3: Fase 4 (importador, usa `services/api/tests/fixtures/cashew_v48/`), Fase 5 (UI, empieza con T-501), Fase 6, Fase 7.

## 7. Estado de Runs, workers, terminales y worktrees

**Runs de Orca** (el CLI **no tiene comando para cerrarlos**; no usar `orchestration reset`): `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2) — todas con tareas aceptadas o descartadas. **Run de la Fase 3: `run_63b520544a30`** (activo; T-304 en ejecución, dispatch `ctx_c6510b5c94c9`). El coordinador solo puede consumir un Run a la vez: `orca orchestration run-use --id run_63b520544a30` al retomar.

**Dispatches fallidos o retenidos** (solo historial; sus terminales son de Adrian): intentos que chocaron con avisos de «trust workspace» o actualización, y el intento de Antigravity de T-105 (`ctx_b30eb2754ca3`, sustituido por Codex como T-105b).

**Worktrees** (cada uno en `/home/artur/propio2/`): `Monetae` (**main**), `Monetae-master-dev` (**master-dev**, integración), y 14 de tareas ya integradas — `Monetae-agy-T-001/002/003/004/105-*` y `Monetae-codex-T-102/105/201/202/203/204/205/206a/206b-*`. Todas sus ramas están **fusionadas en `master-dev`**; se pueden borrar con `git worktree remove` + `git branch -d` cuando Adrian lo apruebe (nunca se borran solas).

**Terminales/paneles que Adrian puede cerrar** (ninguno tiene trabajo pendiente): todos los paneles `artur@…:~/propio2/Monetae-agy-T-*` y `Monetae-codex-T-*` de Orca (incluido el de `Monetae-codex-T-201-a…`, que aún tiene un Codex inactivo del primer intento), y las sesiones `Monetae Cashew analysis phase 0` que no sean la del coordinador actual. El panel `lupuna` no pertenece a este proyecto.

## 8. GitHub

`origin` = `https://github.com/Adrian-asandym/Monetae.git`. Antes de cada push se verifica el historial completo (sin `.env`, claves, `reference/`, respaldos; únicos `.sqlite`/`.csv` versionados: los 3 fixtures sintéticos de `services/api/tests/fixtures/cashew_v48/`). Los resultados del último push están en el mensaje de cierre de la sesión del 2026-10-08 y en `git log origin/main`.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md, docs/SPEC.md. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list

# 1) Herramientas (instaladas a nivel de usuario; Python del sistema = 3.9, NO usarlo para el proyecto)
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
uv --version && docker compose version && flutter --version | head -1
orca status --json | head -5                           # ok: true

# 2) Verificar el backend (≈ 3 min; necesita PostgreSQL en Docker)
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 404 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0004
cd ../.. && python3 -I scripts/check_openapi.py         # contrato: 86 paths, 127 operaciones
docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) Probar el stack a mano (opcional)
cp .env.example .env && echo 'MONETAE_COOKIE_SECURE=false' >> .env
docker compose -f infra/docker-compose.yml up -d --build
echo 'una-contraseña-larga-123' | docker compose -f infra/docker-compose.yml exec -T api python -m monetae.cli create-user --email yo@example.test --password-stdin
#   curl: GET /api/v1/health (da la cookie CSRF) y luego cabeceras Origin + X-CSRF-Token en POST/PATCH/DELETE
docker compose -f infra/docker-compose.yml down -v && rm -f .env     # SIEMPRE limpiar
```

**Siguiente paso concreto (Fase 3 en curso):** `orca orchestration run-use --id run_63b520544a30`; `orca orchestration check --wait --types worker_done,escalation,question` (solo UNA espera a la vez por Run: `waiter_exists` si queda una colgada; no uses `pkill -f`/`pgrep -f` con texto que aparezca en tu propio comando, mata tu shell). Cuando T-304 (`codex/T-304-subscriptions-api`) reporte `worker_done`: revisar el diff, **correr yo** `ruff`, `mypy`, `pytest` con PostgreSQL, `alembic upgrade/check/downgrade 0005/upgrade` y una **sonda con `uvicorn` real + `httpx`** (ciclo crear → archivar → listar → reactivar, Netflix de SPEC §8); merge `--no-ff` a `master-dev`; actualizar este archivo; y pedir a Adrian el **decision gate** para `main` + push (incluye: ampliaciones de contrato de T-302, regenerar/registrar cambios en `docs/api/` si procede, y el arreglo `4b62d7c`).

## 10. Lecciones operativas (no repetir errores)

- **Verificar, no confiar en el resumen del worker:** correr yo `ruff`, `mypy`, `pytest`, leer el servicio entero y hacer pruebas manuales (curl, SQL directo, latencia). Así aparecieron: un bloqueo `FOR UPDATE` por petición que serializaba al usuario (5,6 s → 0,03 s), duplicados de nombre mal aplicados, citas inventadas, y errores de conteo en documentos.
- **Leer el contrato antes de escribir una especificación** (me contradije con él dos veces: fechas del filtro y obligatoriedad de `fx_rate_*`).
- **Reglas de bloqueo:** las lecturas no toman bloqueos de fila; las escrituras usan bloqueos consultivos con orden fijo.
- **Orca:** `worker-start` puede devolver `outcome_unknown` aunque el worker trabaje; Antigravity pide «trust workspace» en cada worktree y puede caerse por red; Codex puede mostrar un menú «Update available» que solo Adrian puede saltar; `gate-create` no acepta `--run`; al abrir sesión hay que re-vincular el Run (`run-use --id`); `check --wait` de un Run distinto da `consumer_fenced`.
- **Modelos Codex** (de `~/.codex/models_cache.json`): `gpt-6.1-sol` (trabajo general), `gpt-6-astra` (el más potente), `gpt-6-luna` (ligero; sirve para CRUD pero exige revisar las reglas).
- **`TestClient` no es un servidor:** espera a que la app termine por completo (incluido el `commit`), así que oculta errores de orden respuesta/commit. Para cambios de sesión/transacción, prueba además con `uvicorn` real y `httpx` (login → petición inmediata; escritura → lectura inmediata).
- **Disco:** ≈ 4 GB libres en `/` (20 GB). Vigilar antes de Flutter/Docker.
- **Privacidad:** nunca leer filas de `reference/backups/`; trabajar sobre una copia; los fixtures son sintéticos.
