# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Actualizado: **2026-10-08 (Fase 3 completa, esperando decision gate)** · Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador) y `docs/SPEC.md` (qué se construye).

## 1. Dónde estamos

| | |
|---|---|
| **Fase actual** | **Fase 2 (backend base): COMPLETA.** **Fase 3 (préstamos y suscripciones): COMPLETA en `master-dev`** (T-301 a T-304 aceptadas e integradas el 2026-10-08); **pendiente el decision gate de Adrian** para pasarla a `main` y subirla a GitHub. La siguiente es la **Fase 4** (importador de Cashew). |
| **Fases cerradas** | Fase 0 (análisis de Cashew), Fase 1 (diseño: ADR, esquema, OpenAPI, fixture), Fase 2 (backend base). |
| **Ramas** | `main` = `origin/main` = **`05ff1d9`** (cierre de la Fase 2 + traspaso). `master-dev` va **por delante** con toda la Fase 3 (ver `git log --oneline 05ff1d9..master-dev`); 713 pruebas verificadas con PostgreSQL. **No se ha hecho merge a `main` ni push** (requiere decision gate). `origin/master-dev` sigue en `05ff1d9`. |
| **GitHub (`origin`)** | Ver §8. Si `git status -sb` muestra `ahead N`, el push está pendiente. |
| **Versión de la SPEC** | v0.3 (2026-10-07). Historial en `docs/SPEC.md` §18. |
| **Arquitectura** | `docs/ARCHITECTURE.md` v0.3. Puntos abiertos en su §10 (1–13). |

## 2. Qué incluye la Fase 2 (verificado sobre el commit integrado)

Backend FastAPI síncrono (ADR-007) en `services/api`, **44 de las 86 rutas (paths) del contrato = 71 de 127 operaciones** (Fase 2: 29 rutas / 48 operaciones; Fase 3: +15 rutas / +23 operaciones):

- **Acceso:** login por correo y contraseña (argon2id), sesiones opacas con cookie `HttpOnly`, CSRF firmado con HMAC + comprobación de `Origin`, límite de intentos persistente, `users/me`, cierre de sesión (una / todas). **Los usuarios se crean solo por CLI** (no hay registro público): `python -m monetae.cli create-user`.
- **Catálogos:** cuentas, categorías (con las 2 de sistema de interés), personas con alias, etiquetas.
- **Libro mayor:** transacciones (CRUD, filtros, etiquetas, saldos calculados, idempotencia, borrado/restauración lógica), transferencias de dos patas (también entre monedas), lotes atómicos, publicar programadas.
- **Préstamos (Fase 3, T-301/T-302):** libro mayor `loans` + `loan_movements` (desembolso, interés, pago, ajuste, condonación) con saldo y estado **calculados** (sin columna de saldo, sin «liquidar»); reparto de pagos primero a interés; exceso con `adjustment` o `income_expense`; cada movimiento afecta a **su** cuenta (también otra moneda); edición/borrado con revalidación de todo el libro (`409 ledger_inconsistent`); borrado lógico atómico de préstamo y transacciones; resumen por persona y moneda; 15 operaciones.
- **Suscripciones (Fase 3, T-303/T-304):** `subscriptions` + `recurring_rules`; archivado reversible (conserva el historial, cancela los cobros futuros, fuera de listado y totales); reactivación; próxima transacción `scheduled` materializada y avanzada al publicar; totales por moneda; sugerencia de reactivación por título normalizado; 8 operaciones.
- **Base de datos:** 6 migraciones Alembic reversibles (`0001` identidad y catálogos, `0002` intentos de login, `0003` transacciones, `0004` integridad de transferencias, `0005` préstamos, `0006` suscripciones y reglas). Claves foráneas **compuestas con `user_id`**: la BD rechaza referenciar datos de otro usuario.
- **Dominio puro:** `Money`, `ExchangeRate`, reglas de transacciones y transferencias.
- **Calidad:** **713 pruebas** con PostgreSQL real (404 de la Fase 2 + dominio + API de préstamos y suscripciones + prueba de orden commit/respuesta), `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`; migraciones 0005↔0006 probadas con datos; contrato validado con Redocly + `scripts/check_openapi.py`.

**No implementado todavía (por grupo, operaciones del contrato):** usuarios 9 (PIN/bloqueo/WebAuthn), reportes 8, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, Google OIDC 1, exportaciones 1, sugerencia de tipo de cambio 1.

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
| Ampliaciones de contrato de la Fase 3 (**por aprobar en el gate**; aún NO están en `docs/api/openapi.json`) | (1) `409 loan_already_settled`: `income_expense` sobre un préstamo ya saldado; (2) `422 movement_kind_immutable`: el `PUT` de un movimiento no cambia su `kind`; (3) `fx_rate_to_base` **opcional, solo de entrada**, en `SubscriptionCreate`/`SubscriptionUpdate` (obligatoria con `422 fx_rate_required` en moneda ≠ base; provisional, se confirma al publicar). Detalle en `docs/api/README.md`. |
| Suscripciones | Títulos duplicados permitidos; sin unicidad de título entre activas. |
| Agentes | Codex (modelos `gpt-6.1-sol` / `gpt-6-luna` / `gpt-6-astra`) para backend y, después, UI; Antigravity solo como relevo; Command Code de reserva. |

## 4. Decisiones y acciones pendientes de Adrian

1. ~~Aprobar el plan de la Fase 3~~ — aprobada el 2026-10-08. **Decision gate de la Fase 3** (merge `master-dev` → `main` + push): pendiente de Adrian; incluye aprobar las 3 ampliaciones de contrato (§3), tras lo cual el coordinador debe **actualizar `docs/api/openapi.json`** (CLAUDE.md §8) y avisar a quien haga la UI.
1b. **Pregunta de producto (cobros vencidos al archivar):** hoy `archive`/`delete` cancelan solo las programadas con fecha ≥ ahora (literal de SPEC §8.1 «cobros futuros»). Si archivas justo después de que *venza* el cobro y antes de marcarlo pagado, queda una `scheduled` vencida y, al reactivar, aparecen dos. **Recomendación del coordinador:** cancelar (borrado lógico) **todas** las programadas sin publicar de la regla al archivar/borrar; las publicadas no se tocan. Es un cambio de 2 líneas + 1 prueba (`services/subscriptions.py`, `_cancel_scheduled(future_only=...)`). Esperando respuesta de Adrian.
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
- `reactivation_suggestions` solo se rellena en la respuesta de **crear** o **publicar** una transacción de gasto (SPEC §8.4); `GET /transactions` no las calcula.
- Totales de suscripciones: sin proveedor de tipos de cambio (Fase 6) solo se suma la moneda igual a la de reporte; las demás cuentan como `unconverted_count`.
- `end_on` de `recurring_rules` existe pero no se expone aún; el CRUD genérico `/recurring-rules` es de la Fase 6.
- La tasa de cambio de una suscripción en moneda extranjera es **provisional**: se guarda en la regla y el usuario la confirma al publicar cada cobro.- No ha habido auditoría de seguridad externa; hay una pasada de endurecimiento prevista en la Fase 7.
- **Corregido en `4b62d7c` (2026-10-08):** la Fase 2 hacía el `commit` de la sesión *después* de enviar la respuesta (FastAPI ≥ 0.118 con dependencias `yield`): con un servidor real, `login` + petición inmediata daba 401 en 34/40 intentos. `TestClient` lo ocultaba. Ahora `Database` usa `scope="function"` y hay una prueba que registra el orden real ASGI.
- La clave secreta por defecto es de ejemplo y solo sirve en local; en `prod` la app se niega a arrancar con ella o con cookies sin `Secure`.

## 6. Fase 3 — **COMPLETA** (T-301 a T-304 integradas en `master-dev`)

Objetivo: resolver P1–P4 (préstamos como libro mayor; suscripciones archivables). Ejemplos A–E de SPEC §7 como pruebas literales.

| Tarea | Contenido | Agente / modelo sugerido | Depende de | Spec |
|-------|-----------|--------------------------|-----------|------|
| T-301 ✅ | Dominio puro de préstamos (saldo calculado, reparto interés/capital, exceso, reabrir) — **aceptada e integrada** (`246a6d5`; 114 pruebas, 100 % de líneas) | Codex `gpt-6.1-sol` high | — | `docs/tasks/T-301-domain-loans.md` |
| T-303 ✅ | Dominio puro de suscripciones (archivar/reactivar, equivalentes, fechas, sugerencias) — **aceptada e integrada** (`9b1e347`; 73 pruebas, 100 % de líneas) | Codex `gpt-6.1-sol` medium | — | `docs/tasks/T-303-domain-subscriptions.md` |
| T-302 ✅ | Migración `0005`, servicios y API de préstamos (15 operaciones) — **aceptada e integrada** (`79fc715`; 646 pruebas; spec corregida al lanzar: columna interna `sequence`). Ampliaciones de contrato a registrar: `409 loan_already_settled`, `422 movement_kind_immutable` (ver `docs/api/README.md`) | Codex `gpt-6.1-sol` high | T-301 ✅ | `docs/tasks/T-302-loans-api.md` |
| T-304 ✅ | Migración `0006`, reglas recurrentes y API de suscripciones (8 operaciones) — **aceptada e integrada** (`7dd01dd`; 713 pruebas; spec corregida al lanzar contra el contrato; sonda real `uvicorn`+`httpx` del escenario Netflix de SPEC §8 verificada) | Codex `gpt-6.1-sol` high | T-302 ✅, T-303 ✅ | `docs/tasks/T-304-subscriptions-api.md` |

Orden seguido: T-301 ∥ T-303 → T-302 → T-304. Pendiente: gate a `main`. Después: Fase 4 (importador; usa `services/api/tests/fixtures/cashew_v48/`), Fase 5 (UI, empieza con T-501), Fase 6, Fase 7.

## 7. Estado de Runs, workers, terminales y worktrees

**Runs de Orca** (el CLI **no tiene comando para cerrarlos**; no usar `orchestration reset`): `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2) — todas con tareas aceptadas o descartadas. **Run de la Fase 3: `run_63b520544a30`** (Fase 3; sus 4 tareas están aceptadas y **no queda ningún worker en ejecución**). El coordinador solo puede consumir un Run a la vez: `orca orchestration run-use --id run_63b520544a30` al retomar.

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
uv run pytest -q                                        # esperado: 713 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0006
cd ../.. && python3 -I scripts/check_openapi.py         # contrato: 86 paths, 127 operaciones
docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) Probar el stack a mano (opcional)
cp .env.example .env && echo 'MONETAE_COOKIE_SECURE=false' >> .env
docker compose -f infra/docker-compose.yml up -d --build
echo 'una-contraseña-larga-123' | docker compose -f infra/docker-compose.yml exec -T api python -m monetae.cli create-user --email yo@example.test --password-stdin
#   curl: GET /api/v1/health (da la cookie CSRF) y luego cabeceras Origin + X-CSRF-Token en POST/PATCH/DELETE
docker compose -f infra/docker-compose.yml down -v && rm -f .env     # SIEMPRE limpiar
```

**Siguiente paso concreto:** (1) Adrian responde el gate de la Fase 3 y la pregunta 1b (§4); (2) si aprueba: `orca orchestration gate-resolve …`, `git -C ../Monetae merge --ff-only master-dev` (en el worktree de `main`), verificar el historial (sin `.env`, claves, `reference/`, solo los 3 fixtures sintéticos) y `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev` con `GIT_TERMINAL_PROMPT=0`; (3) actualizar `docs/api/openapi.json` con las ampliaciones aprobadas y correr `python3 -I scripts/check_openapi.py` (+ Redocly); (4) abrir el Run de la **Fase 4** (importador SQLite de Cashew v48: idempotente, `--dry-run`, cuadre de saldos, revisión manual de préstamos ambiguos) escribiendo antes las tareas T-4xx **contrastadas con el contrato y con el código ya integrado** (lección de T-302/T-304).

## 10. Lecciones operativas (no repetir errores)

- **Verificar, no confiar en el resumen del worker:** correr yo `ruff`, `mypy`, `pytest`, leer el servicio entero y hacer pruebas manuales (curl, SQL directo, latencia). Así aparecieron: un bloqueo `FOR UPDATE` por petición que serializaba al usuario (5,6 s → 0,03 s), duplicados de nombre mal aplicados, citas inventadas, y errores de conteo en documentos.
- **Leer el contrato antes de escribir una especificación** (me contradije con él dos veces: fechas del filtro y obligatoriedad de `fx_rate_*`).
- **Reglas de bloqueo:** las lecturas no toman bloqueos de fila; las escrituras usan bloqueos consultivos con orden fijo.
- **Orca:** `worker-start` puede devolver `outcome_unknown` aunque el worker trabaje; Antigravity pide «trust workspace» en cada worktree y puede caerse por red; Codex puede mostrar un menú «Update available» que solo Adrian puede saltar; `gate-create` no acepta `--run`; al abrir sesión hay que re-vincular el Run (`run-use --id`); `check --wait` de un Run distinto da `consumer_fenced`.
- **Modelos Codex** (de `~/.codex/models_cache.json`): `gpt-6.1-sol` (trabajo general), `gpt-6-astra` (el más potente), `gpt-6-luna` (ligero; sirve para CRUD pero exige revisar las reglas).
- **Releer la spec contra el contrato y el código antes de lanzar:** en la Fase 3 corregí mi propia spec dos veces al lanzar (columna `sequence` por empates de `func.now()`; `status` solo `active|archived`, `reactivate` sin cuerpo, sin campos de tasa en `SubscriptionCreate`). Las preguntas del worker (`ask`) fueron todas legítimas: respóndelas con el contrato abierto.
- **`TestClient` no es un servidor:** espera a que la app termine por completo (incluido el `commit`), así que oculta errores de orden respuesta/commit. Para cambios de sesión/transacción, prueba además con `uvicorn` real y `httpx` (login → petición inmediata; escritura → lectura inmediata).
- **Disco:** ≈ 4 GB libres en `/` (20 GB). Vigilar antes de Flutter/Docker.
- **Privacidad:** nunca leer filas de `reference/backups/`; trabajar sobre una copia; los fixtures son sintéticos.
