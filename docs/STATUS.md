# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-08, ~20:15 (America/Lima)** (sesión de reanudación; el cierre anterior fue ~12:55) |
| **`main`** | **`b3797b1`** — Fase 3 completa. **Ya está publicado**: `origin/main` = `b3797b1` (push a las 17:36:13; no lo hizo el coordinador, presumiblemente Adrian). |
| **`master-dev`** | `6a14a6e` + el commit de esta actualización (`git log -1`). Va **por delante de `main`** solo con documentación y contrato: protocolo de sesión, `STATUS.md`, **contrato 0.3.0** (`f83742f`), **ADR-008 y tareas T-401…T-403** (`6a14a6e`). El código es idéntico al de `main`. |
| **`origin/master-dev`** | `05ff1d9` (desfasado). **Pendiente de publicar** junto con los commits nuevos (D1). |
| **Gate abierto** | `gate_e3b1a2193ba2` (merge de docs a `main` + push). Sin resolver: se resuelve cuando el entorno pueda verificar (D0). |
| **SPEC / ARCHITECTURE / contrato** | SPEC v0.3 · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.3.0** (validado con `check_openapi.py` y Redocly; falta correr `test_contract_subset` con PostgreSQL). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–3. La Fase 3 está en `main` y publicada. |
| 🔄 **En curso** | **Preparación de la Fase 4** (importador de Cashew): ADR-008 y tareas T-401…T-403 **escritas, sin lanzar**. No hay ningún worker ni Run abierto para la Fase 4. |
| ⛔ **Bloqueo** | **Docker no es accesible desde WSL** (D0): sin PostgreSQL no se puede verificar código. Bloquea D2 y el lanzamiento de T-401. |
| ⏳ **Pendiente** | Aprobación del ADR-008 (J1–J3) · OK al Paso 3 · Fase 4 (T-401 → T-402 ∥ T-403) · Fase 5 (UI; `T-501`) · Fase 6 · Fase 7 · despliegue VPS → V2 → V3 → V4. |

Backend actual: **44 de 86 rutas = 71 de 127 operaciones**, 6 migraciones (cabeza `0006`), **713 pruebas**. La Fase 4 añadirá la migración `0007` (T-401). Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (reanudación del 2026-10-08)

- **Verificado el estado real** frente a lo que decía este archivo: `origin/main` ya estaba en `b3797b1`; Adrian quitó los worktrees y ramas de tareas (de 18 a 0) y cerró paneles de Orca; Docker dejó de ser accesible.
- **Contrato 0.3.0 (D3, hecho):** `openapi.json` incorpora `409 loan_already_settled`, `422 movement_kind_immutable` y `fx_rate_to_base` opcional solo de entrada en suscripciones; `check_openapi.py` OK y Redocly válido (`f83742f`, con sección en `docs/api/README.md`).
- **Paso 2 (documentos, `6a14a6e`):** `docs/decisions/008-cashew-loan-import.md` (**propuesto**) y las tareas `T-401` (migración `0007` + núcleo), `T-402` (préstamos) y `T-403` (suscripciones + cuadre), contrastadas con el contrato, el esquema y el código ya integrados. Hallazgo: `import_external_id` solo existía en `transactions` y `loans`; T-401 lo añade a seis tablas más.
- **Diagnóstico de Docker:** `/usr/bin/docker` es un enlace a `/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker`, que **no existe** (`cli-tools` está vacío); `/var/run/docker.sock` existe pero **no responde**; los `.exe` de Windows no se pueden ejecutar desde este shell. Es un problema de la integración de Docker Desktop con WSL (distribución `AlmaLinux-9`), no del repositorio.
- **No se hizo** (a propósito): D2 (cambio de código sin poder correr la suite), el push (D1), ni nada de la Fase 4 más allá de los documentos. No hay Run de la Fase 4 ni workers.

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-08 (tarde) | **«OK»** al plan de reanudación (Pasos 1 y 2) y al conjunto de recomendaciones D1–D6, interpretado por el coordinador como **«todo A»**: D1 publicar docs, D2 cancelar todas las programadas sin publicar al archivar, D3 contrato, D4 alcance acotado de la Fase 4, D4b `/imports` diferido, D5 ADR por redactar, D6 limpieza. *Si no era esa la intención, Adrian debe decirlo.* |
| 2026-10-08 (tarde) | **D6 ejecutada por Adrian:** eliminó los 10 worktrees restantes (y antes, 8); quedan solo `main` y `master-dev`. |
| 2026-10-08 (tarde) | Adrian abrió Docker Desktop; el coordinador comprobó que **sigue sin ser accesible** desde WSL (D0). |
| 2026-10-08 (mañana) | Continuar la Fase 3; aprobar el merge a `main` (gate `gate_621dc454eeee`); protocolo de sesión en `CLAUDE.md` §10. El push de `main` lo hizo alguien a las 17:36. |
| 2026-10-07 | ADR-001 **A** (UI propia en Flutter Web reutilizando widgets de Cashew), ADR-002 **A** (sesión en servidor + cookie), ADR-003 **A** (interés en base caja; pago primero a interés), ADR-004 **A** (tipo de cambio manual manda), ADR-006 **A** (PIN, luego WebAuthn), ADR-007 **A** (SQLAlchemy síncrono). |
| Fases 0–2 (oct 2026) | Importador **SQLite primero**, CSV solo como rescate, siempre sobre una copia; el respaldo real es Cashew **v48**. Etiquetas en V1. Nombres duplicados permitidos en categorías y personas (únicos solo en cuentas y etiquetas). Usuarios solo por CLI en V1. `PATCH /transactions/{id}` admite `account_id` (misma moneda) y `kind`. |
| Fases 0–2 (oct 2026) | Agentes: **Codex** (`gpt-6.1-sol` general / `gpt-6-astra` el más potente / `gpt-6-luna` ligero) para backend y, después, UI; **Antigravity** solo como relevo; **Command Code** de reserva. |

## 5. Decisiones pendientes

Cada una: contexto → opciones (la más recomendable primero) → impacto.

**D0 · Docker accesible desde WSL (acción de Adrian; bloquea todo lo verificable).** Ver diagnóstico en §3.
- **A (recomendada): reactivar la integración.** En Docker Desktop (Windows): *Settings → Resources → WSL integration* → activar **AlmaLinux-9** → *Apply & restart*; esperar a «Engine running». Después, en un PowerShell de Windows: `wsl --shutdown` y volver a abrir la terminal de WSL (el enlace `/usr/bin/docker` se vuelve válido solo cuando Docker Desktop monta `cli-tools`). Comprobación: `docker version` y `docker compose version` desde WSL.
- B: instalar Docker Engine dentro de WSL (`docker.io` + `docker-compose-plugin`, usuario en el grupo `docker`). *Razón:* independiza de Docker Desktop; *costo:* ≈ 1 GB de disco y mantener dos instalaciones.
- *Impacto:* sin esto no hay PostgreSQL, y por tanto ni D2, ni la verificación del contrato 0.3.0, ni T-401.

**D1 · Publicar `master-dev` (y el merge de docs a `main`).** Gate propuesto `gate_e3b1a2193ba2`.
- **A (recomendada): hacerlo al final del Paso 1**, cuando D0 permita correr la suite completa con el contrato 0.3.0 y D2, y repetir la auditoría rápida de seguridad (ya fue limpia para la Fase 3). Sin `--force`. *Razón:* no publicar contrato ni código sin verificar.
- B: publicar ya solo los documentos. *Razón:* respaldo inmediato; *contra:* el contrato 0.3.0 aún no pasó `test_contract_subset`.

**D2 · Cobros vencidos al archivar una suscripción** (aceptada como A por el «OK»; **falta implementarla**).
- **A:** cancelar (borrado lógico) **todas** las `scheduled` sin publicar de la regla al archivar/borrar. 2 líneas en `services/subscriptions.py` (`_cancel_scheduled`), ajustar `test_archive_preserves_past_scheduled_and_ignores_deleted_payments`, 1 prueba nueva, y actualizar la descripción de `archive_subscription` en el contrato.
- B: dejar el comportamiento literal. — *Impacto:* hoy, archivar tras vencer un cobro deja una programada vencida y, al reactivar, aparecen dos.

**D3 · Contrato 0.3.0** — **hecho** (`f83742f`); falta correr `uv run pytest tests/api/test_contract_subset.py` con PostgreSQL (D0).

**D4 · Alcance de la Fase 4** (aceptado como A): se importan cuentas, categorías, etiquetas, transacciones, transferencias, préstamos y suscripciones/recurrentes; presupuestos, límites por categoría, reglas de título, plantillas del escáner y metas se **listan como «pendiente de Fase 6»**. **D4b** (aceptado como A): las rutas `/imports` (subida de archivo) se dejan para las Fases 5–6; la Fase 4 es solo línea de comandos.

**D5 · ADR-008 — decisiones J1, J2 y J3 (pendiente de Adrian)** + permiso para la prueba real. Detalle y razones en `docs/decisions/008-cashew-loan-import.md`.
- **J1** préstamo de pago único ya «liquidado» (`paid = 0`): **A (rec.)** importarlo con un pago sintetizado en la misma cuenta, marcado para revisión · B solo el desembolso (queda abierto) · C no importarlo.
- **J2** pago que supera el saldo: **C (rec.)** partirlo en pago por el saldo + ingreso/gasto ordinario por el exceso (conserva el principal real) · A ajuste de capital · B interés.
- **J3** pago en otra moneda que el préstamo: **A (rec.)** no adivinar la tasa; segunda pasada con `--loan-fx-rates` · B tasa actual de Cashew · C préstamo entero a revisión.
- **Prueba con el respaldo real:** ¿autoriza Adrian, **al final de la Fase 4**, un `--dry-run` sobre una **copia** que devuelva solo conteos y saldos (nunca filas)? Recomendado: sí. Sin su OK solo se usan los fixtures.
- *Impacto:* T-402 está escrita con las opciones recomendadas; si elige otras, se reescribe antes de lanzar.

**D8 · Tasa de cambio de las transacciones en moneda extranjera al importar** (nueva; está en T-401 con este valor por defecto, Adrian puede vetarla): `--fx-rate USD=3.80` (manual); si falta, la tasa global de `app_settings` de Cashew marcada **provisional** (`fx_rate_source='auto'`); si tampoco hay, el comando falla antes de escribir.
- **A (recomendada):** lo descrito. *Razón:* Cashew no guarda tasas históricas; así nada queda inventado y todo lo provisional se cuenta en el reporte (ADR-004: lo manual manda).
- B: exigir siempre `--fx-rate`. — *Impacto:* solo afecta a las estadísticas de las cuentas en USD, no a sus saldos.

**D6 · Limpieza de worktrees** — **hecha por Adrian**.

**D7 · Para más adelante** (no bloquean la Fase 4): **ADR-005** modelo de sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 («a confirmar en la Fase 0») y la redacción «cobros futuros» de §8.1 si se aprueba D2-A, a corregir con el próximo cambio de SPEC aprobado.

## 6. Siguiente paso concreto

**Antes de lanzar nada (en este orden):**
1. **D0** — Adrian deja Docker accesible desde WSL; el coordinador lo comprueba (`docker version`, `docker compose version`).
2. **Paso 1 pendiente (coordinador):** implementar D2 y correr la **suite completa** (≈ 5 min: `ruff`, `mypy`, `pytest`, `alembic`, `check_openapi.py`) con el contrato 0.3.0; sonda con `uvicorn` real del escenario Netflix; actualizar la descripción de `archive_subscription` en el contrato; auditoría de seguridad; resolver el gate `gate_e3b1a2193ba2`, hacer el merge fast-forward a `main` y publicar `main` y `master-dev` (D1-A). Mantener Orca al día: `orca skills get orchestration --full` (Orca se actualizó: relay `0.1.0+0d9e2827fa5f`).
3. **Adrian responde D5** (J1–J3 y el permiso del dry-run) y da el **OK explícito al Paso 3**. El coordinador registra el ADR-008 como aceptado y ajusta T-402 si hace falta.

**Paso 3 — Fase 4** (Run nuevo «Fase 4: importador de Cashew»; todas con Codex; ramas `codex/T-40x-…` desde `master-dev`; el coordinador renombra la rama tras `worker-start`):

| Tarea | Contenido | Agente / modelo / esfuerzo | Depende de | Spec |
|---|---|---|---|---|
| T-401 | Migración `0007`, lector SQLite de solo lectura, cuentas/categorías/etiquetas/transacciones/transferencias, idempotencia, `--dry-run`, reporte y andamiaje | Codex `gpt-6.1-sol` · high | — | `docs/tasks/T-401-importer-core.md` |
| T-402 | Préstamos según ADR-008 (+ segunda pasada de tasas) | Codex `gpt-6.1-sol` · high (`gpt-6-astra` si hay devoluciones) | T-401, ADR-008 aceptado | `docs/tasks/T-402-importer-loans.md` |
| T-403 | Suscripciones/recurrentes, cuadre final con código de salida, documentación | Codex `gpt-6.1-sol` · medium | T-401 | `docs/tasks/T-403-importer-subscriptions.md` |

Orden: **T-401 sola** → verificar y fusionar → **T-402 ∥ T-403** (archivos disjuntos) → verificar cada una → integrar ambas y comprobar el cuadre con **diferido 0** → decision gate hacia `main`.

**Cómo las verificaré:** `ruff`, `mypy --strict`, `pytest` con PostgreSQL y `alembic` (0006↔0007) corridos por mí; fixture contra `expected.json` y ADR-008; **idempotencia** (segunda importación ⇒ 0 creados, 0 modificados); `--dry-run` ⇒ datos financieros intactos; saldos que cuadran (`unexplained = 0.00`); sin datos reales en git, logs ni reportes; y, si Adrian lo autoriza, un `--dry-run` sobre una **copia** de su respaldo mostrando solo conteos y saldos.

**Opcional en paralelo:** `T-501` (spike de desacople de widgets, Fase 5) no toca el backend, pero Flutter pide disco (hoy 3,5 GB libres): solo si Adrian lo pide.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 3: `run_63b520544a30`.** Tareas T-301 `task_d8d91292787f`, T-303 `task_39bd586cd28f`, T-302 `task_112bd988b505` completadas; T-304 `task_3e72e1ff8b03` figura **`blocked`** solo porque cuelga el gate abierto `gate_e3b1a2193ba2` (se vuelve a marcar `completed` al resolverlo); `task_2af7f21c0086` y `task_923219f8ed0e` son intentos antiguos `failed/superseded`. **Workers: ninguno vivo** (4 `exited`, liberados). **No existe Run de la Fase 4**: se crea en el Paso 3. Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`. Al retomar: `orca orchestration run-use --id <run>`.

**Worktrees:** solo `Monetae` → `main` (limpio) y `Monetae-master-dev` → `master-dev` (limpio). No quedan ramas `codex/*` ni `agy/*` (todas estaban fusionadas). Sin contenedores, sin servidores en el puerto 8765, sin `.env` sueltos. Disco: 3,5 GB libres.

**Paneles de Orca abiertos (4):** el del coordinador («Fase 3 de Monetae»), `lupuna` (otro proyecto), «Monetae Cashew analysis phase 0» (sesión antigua; Adrian puede cerrarla si no es la actual) y `…Monetae-codex-T-202-money-fx` (su worktree ya no existe; Adrian puede cerrarlo).

## 8. Limitaciones y riesgos conocidos

- **Contrato 0.3.0** actualizado pero **sin correr** `test_contract_subset` con PostgreSQL (D0).
- **Cobros vencidos al archivar** (D2): decidido, sin implementar.
- **Docker no accesible** desde WSL (D0): sin él no se puede verificar código.
- **La importación de datos reales** nunca se ha probado: el esquema v48 real solo se conoce por el análisis y la fixture sintética (por eso el `--dry-run` sobre una copia, D5).
- **Sin auditoría de seguridad externa**; endurecimiento previsto en la Fase 7.
- La BD admite un `income` con monto negativo si se escribe SQL directo; solo la API garantiza el signo (decidir con el importador; `ARCHITECTURE.md` §10.12).
- El límite de intentos de login usa `request.client.host`: detrás de un proxy hace falta configuración (§10.10). `501 google_login_not_available` no figura en el contrato congelado (§10.11). `updated_at` se refresca vía ORM/Core, no con SQL crudo (§10.8).
- `reactivation_suggestions` solo se rellena al **crear** o **publicar** una transacción de gasto; `GET /transactions` no las calcula.
- Totales de suscripciones: sin proveedor de tipos de cambio (Fase 6) solo se suma la moneda igual a la de reporte; las demás cuentan en `unconverted_count`. La tasa de una suscripción en moneda extranjera es **provisional** (se confirma al publicar cada cobro).
- `end_on` de `recurring_rules` existe pero no se expone; el CRUD de `/recurring-rules` es de la Fase 6.
- La clave secreta por defecto es de ejemplo; en `prod` la app se niega a arrancar con ella o con cookies sin `Secure`.
- **Disco:** 3,5 GB libres en `/` (20 GB). Vigilar antes de Docker/Flutter.
- **Repositorio público:** todo push se audita antes. Los datos reales de Adrian solo viven en `reference/backups/` (ignorado por git).
- La cuota de Claude Pro es limitada: delegar lectura masiva y generación de código.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md (§10), docs/SPEC.md, ADRs y tareas abiertas. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list
git -C ../Monetae log --oneline -1 && git rev-parse --short origin/main   # main = origin/main = b3797b1 · origin/master-dev = 05ff1d9 hasta publicar

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
