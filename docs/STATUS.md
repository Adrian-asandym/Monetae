# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-09, tarde (America/Lima)** — Fase 4 publicada (G1) y T-405 (L1-A) integrada en `master-dev`; a la espera del gate G2 para publicarla |
| **`origin`** | `origin/main` = `origin/master-dev` = **`b0a80ae`** (Fase 4 completa publicada tras G1-A). **No incluye T-405.** |
| **`main`** | `b0a80ae`. |
| **`master-dev`** | **`fa06542` (merge de T-405) + los commits de documentación posteriores (`git log -1`)**, sin publicar. |
| **Gate abierto** | G2 (merge de T-405 a `main` y push): ver el id en §7. **Pendiente de Adrian.** Resuelto: `gate_1e81cf0fd994` (G1-A, 2026-10-09). |
| **SPEC / ARCHITECTURE / contrato** | SPEC v0.3 · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.3.0** (la Fase 4 no cambió el contrato HTTP: el importador es solo línea de comandos). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–3 y **Fase 4 (importador de Cashew)**, publicadas en `origin/main` (`b0a80ae`). **T-405 (L1-A)** aceptada e integrada en `master-dev` (`fa06542`), aún sin publicar. |
| 🔄 **En curso** | **Fase 5 iniciada (2026-10-09):** `T-501` (spike de desacople de widgets) lanzada con Codex `gpt-6.1-sol` high, Run `run_c2cebe1745b9`, tarea `task_5df2d0fe6f4d`, rama `codex/T-501-ui-decoupling-spike`, terminal `term_8475022b-01dd-4067-8cbc-a3583edd1e79`. |
| ⏳ **Pendiente** | **Gate G2** (publicar T-405) · decidir **cuándo** hacer la importación real definitiva (§5, D9) · Fase 5 (UI Flutter; `T-501`) · Fase 6 (incluye presupuestos, metas y reglas de título, hoy listados como «pendiente de Fase 6» por el importador) · Fase 7 · despliegue VPS → V2 → V3 → V4. |

Backend actual: **44 de 86 rutas = 71 de 127 operaciones**, 7 migraciones (cabeza `0007`), **914 pruebas** con PostgreSQL real, más el comando `python -m monetae.cli import-cashew`. Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-09)

- **Reanudación:** estado de `STATUS.md` contrastado con git, Orca, Docker y disco; todo coincidía. Adrian respondió **«todo A»** y borró él mismo los 4 worktrees de la Fase 4 (sus commits siguen en `master-dev`).
- **G1 resuelto y publicado:** auditoría de seguridad repetida sobre los 35 commits (sin `.env`, claves, `reference/`, ni cifras reales; solo los 3 fixtures sintéticos), `gate_1e81cf0fd994` resuelto, `main` avanzado por fast-forward y push sin `--force` a `b0a80ae`; T-404 marcada `completed`.
- **T-405 (L1-A):** spec contrastada con `loans.py`, `replay`, el esquema y la API; la contrastación destapó un error de mi recomendación (el `PUT` del desembolso es un movimiento **con dinero**; la corrección sin dinero es un `adjustment`; corregido en ADR-008 adenda, STATUS y docs). Codex `gpt-6.1-sol` medium; aceptada tras verificar yo: `ruff`, `mypy --strict`, **914 pruebas** (898 + 16), `alembic check`, contrato; sonda con `uvicorn` real (importación, reimportación sin cambios, `adjustment` sin mover saldos, `PUT` que sí mueve saldos); y `--dry-run` real sobre una copia (original intacto por hash, copia borrada): los préstamos de largo plazo antes omitidos ahora se crean (con su ítem `principal_assumed`), sus cobros pasan a ser pagos reales y dejan de contar como ingreso, y las transacciones y el cuadre de todas las cuentas quedan idénticos y exactos. *(Las cifras exactas no se versionan: repositorio público; constan en el gate de Orca.)*

### Sesión anterior (2026-10-08 noche)

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
| 2026-10-09 (tarde) | «**OK, todo A**»: **G2-A** (publicar T-405 en `main`), **D9-A** (la importación real definitiva espera a una base persistente y a las primeras pantallas de la Fase 5), y OK a arrancar la Fase 5 con `T-501`. **Adrian borró él mismo el worktree de T-405** y su rama; sus commits siguen en `master-dev`. |
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

**G2 · Decision gate de T-405: merge `master-dev` → `main` y publicación** (`gate_10f2135dac21`) — **RESUELTA: A (2026-10-09).** T-405 solo toca `importers/cashew/loans.py`, sus pruebas y documentación; sin cambios de contrato, migración ni API. Verificada por el coordinador (914 pruebas, sonda con servidor real, `--dry-run` real con cuadre exacto). La auditoría de seguridad de lo que se publique se repite antes del push.
- **A (recomendada): aprobar el merge y el push** (sin `--force`). *Razón:* verificación completa y es la forma de tener el respaldo fuera de la máquina.
- B: aprobar solo el merge local, sin push.
- C: esperar. *Contra:* nada la bloquea; solo retrasa la copia remota.

**D9 · ¿Cuándo hacer la importación real definitiva (`apply`)? — RESUELTA: A (2026-10-09).** Aún no hay una base persistente (la de Compose se borra con `down -v`; la del VPS llega en el hito de despliegue) y el importador es solo-inserción: si algo sale mal hay que vaciar la base y repetir. Los ítems de revisión (préstamos con principal supuesto, pagos sintetizados, transferencias sin emparejar, personas provisionales…) hoy solo se ven por SQL o API; la UI para revisarlos llega en las Fases 5–6.
- **A (recomendada): esperar a tener una base persistente y las primeras pantallas de la Fase 5** (o al despliegue); entonces copia → `--dry-run` → `apply`. *Razón:* esperar no pierde nada (el respaldo es una foto fija), evita importar a una base desechable y permite revisar los ítems con la UI.
- B: importar ya a una base local desechable solo para explorar con la API o SQL. *Contra:* no es la definitiva y hay que borrarla.
- C: hacer ya la importación definitiva en una base local persistente. *Contra:* sin UI no se pueden corregir los ítems; riesgo de repetir trabajo.

> **Resueltas el 2026-10-09 (Adrian, «todo A»): G1-A, L1-A, X1-A, X2.** Se conservan las opciones como registro.

**G1 · Decision gate de la Fase 4: merge `master-dev` → `main` y publicación — RESUELTA: A.** Auditoría de seguridad de lo que se publica: sin `.env`, claves ni `reference/`; solo los 3 fixtures sintéticos; sin datos del respaldo real.
- **A (recomendada): aprobar y publicar** (sin `--force`). *Razón:* 898 pruebas, el dry-run real cuadra al céntimo y es la forma de tener respaldo fuera de la máquina.
- B: esperar a resolver L1 y X1 y publicar todo junto.

**L1 · Préstamos de largo plazo SIN desembolso registrado — RESUELTA: A (T-405).** En el respaldo real los préstamos de largo plazo no tienen su desembolso como transacción enlazada (solo cobros o pagos). Hoy fallan con `MissingDisbursementError`: se importan como transacciones **ordinarias** (el saldo cuadra), pero un cobro de préstamo se cuenta como **ingreso** (justo el problema P1) y el préstamo no aparece.
- **A (recomendada): crear el préstamo con un desembolso sin dinero** (`transaction_id` nulo, permitido por `ARCHITECTURE.md`/el `CHECK`), con **principal = suma de los pagos vinculados** (queda saldado), fecha justo antes del primer pago, y un ítem de revisión `principal_assumed`; los pagos se importan como pagos reales en sus cuentas. El principal se corrige después con un movimiento `adjustment` sin dinero (**no** con el `PUT` del desembolso: la API lo trata como un movimiento con dinero y crearía una transacción en una cuenta; corregido el 2026-10-09). *Razón:* el préstamo, sus pagos y su historial quedan visibles, el capital no cuenta como ingreso y todo es corregible.
- B: importar los cobros/pagos como transacciones `kind='loan'` sin préstamo + revisión. *Razón:* no se inventa ningún principal; *contra:* no hay préstamo visible.
- C: dejarlo como hoy (ordinarias). *Contra:* distorsiona las estadísticas.
- *Impacto:* tarea corta T-405 (`loans.py`); la importación real definitiva debe esperar a esta decisión porque el importador es solo-inserción.

**X1 · Transferencias entre monedas distintas — RESUELTA: A (después de V1; no hay T-406).** Se importan como un gasto y un ingreso ordinarios (con motivo `currency_mismatch`); Monetae sí soporta transferencias entre monedas.
- **A (recomendada): dejarlo para después de V1** (son pocas; no hay reportes hasta la Fase 6 y se puede re-vincular entonces).
- B: implementarlo ahora (T-406): emparejar con la tasa implícita del par. *Contra:* más trabajo y riesgo antes de ver reportes; y el importador es solo-inserción, así que re-importar no corregiría las ya importadas.

**D7 · Para más adelante:** **ADR-005** sincronización Android (antes de V4) · orden de categorías (Fase 5) · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · texto obsoleto en `docs/SPEC.md` §2 y la redacción «cobros futuros» de SPEC §8.1 (tras D2 debería decir «cobros programados sin publicar»), a corregir con el próximo cambio de SPEC aprobado.

## 6. Siguiente paso concreto

**Primero, Adrian responde G2 y D9 (§5; basta la letra).** Después:

| Si… | Se hace | Quién | Cómo se verifica |
|---|---|---|---|
| **G2 = A** | Auditoría de seguridad repetida sobre lo que se publique (`git diff origin/main..master-dev`), `gate-resolve` de `gate_10f2135dac21`, `git merge --ff-only master-dev` en el worktree de `main`, push sin `--force` (comando en el Anexo B) y marcar `task_3206ef52f01d` como `completed` | coordinador | `git ls-remote origin` muestra ambas ramas en la cabeza nueva |
| **G2 = B / C** | Solo el merge local (B) o nada (C) | coordinador | — |

**Fase 5 (UI Flutter), arranque:** primera tarea `T-501` (spike de desacople de widgets de Cashew, `docs/tasks/T-501-ui-decoupling-spike.md`, ya escrita; **releerla contra el código antes de lanzar**, lección del Anexo C): Codex (modelo medio-alto), rama `codex/T-501-ui-decoupling-spike`. Flutter pide disco (hoy ≈ 3,7 GB libres): antes hay que **quitar el worktree y la rama de T-405** (`Monetae-codex-T-405-importer-longterm-loans`, ya fusionada) con OK de Adrian, que además cierra su panel.

**Importación real definitiva:** según D9 (recomendado esperar a una base persistente y a las primeras pantallas). Procedimiento cuando llegue: copia del respaldo fuera de `reference/backups`, `--dry-run` previo, `apply`, borrar la copia; los ítems `principal_assumed` se corrigen con `adjustment`, no con `PUT`.

**Antes de lanzar cualquier tarea:** `orca skills get orchestration --full` (Orca se actualiza), `orca status --json`, `docker version`, `git worktree list`, disco ≥ 3 GB y el puerto de la BD de la tarea libre.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 5: `run_c2cebe1745b9`** (T-501 `task_5df2d0fe6f4d` en curso). G2 `gate_10f2135dac21` resuelto; T-405 publicada (`a87f06b`).

**Run de la Fase 4: `run_f5e95406186a`.** Tareas completadas: T-401 `task_e32a402a4dec` (+T-401b `task_83ae6f5c2bbc`), T-402 `task_8e0dc0347237`, T-403 `task_9b25b87c9b93` (+T-403b `task_03fd94d8705d`), T-404 `task_9450f697ce8a` y T-405 `task_3206ef52f01d`. **Gate G2 `gate_10f2135dac21` abierto** (cuelga de T-405: puede figurar `blocked`; se marca `completed` al resolverlo). Gate G1 `gate_1e81cf0fd994` resuelto. **Ningún worker vivo**: el de T-405 terminó; su terminal sigue abierta pero inactiva. Run de la Fase 3: `run_63b520544a30`. Runs anteriores: `run_bef8ecfc67a7` (Fase 0), `run_2cddcd14320c` (Fase 1), `run_70f5f187fe16` (Fase 2). El CLI **no cierra Runs**; no usar `orchestration reset`. Al retomar: `orca orchestration run-use --id run_f5e95406186a`.

**Worktrees:** `Monetae` → `main`, `Monetae-master-dev` → `master-dev` (Adrian borró el de T-405 y su rama el 2026-10-09). Sin `.env` sueltos, sin contenedores ni servidores, sin copias del respaldo real (las de las pruebas se borraron). Disco ≈ 3,7 GB libres.

**Paneles de Orca abiertos:** el del coordinador, `lupuna` (otro proyecto, no se toca) y el de Codex de T-405 (`…Monetae-codex-T-405-importer-longterm-loans`), que Adrian puede cerrar.

## 8. Limitaciones y riesgos conocidos

- **Docker Desktop depende de la integración con WSL** (distro `AlmaLinux-9`): si tras reiniciar `/usr/bin/docker` apunta a un destino inexistente, hay que reactivar *Settings → Resources → WSL integration* y hacer `wsl --shutdown`.
- **El `apply` real nunca se ha ejecutado**: solo `--dry-run` sobre copias del respaldo (cuadre exacto). La importación definitiva depende de D9.
- **Importador (Fase 4):** solo línea de comandos; **solo inserción** (no corrige lo ya importado: por eso conviene resolver L1/X1 antes de la importación real). Presupuestos, metas y reglas de título de Cashew no se importan hasta la Fase 6 (se listan como pendientes). Los 3 hechos que la fixture sintética **ocultó** y solo el respaldo real mostró: series de suscripciones encadenadas, emparejado de transferencias unidireccional y préstamos de largo plazo sin desembolso (resuelto con T-405).
- **Préstamos con principal supuesto (L1-A):** aparecen `settled` hasta que se corrijan. Si queda capital pendiente se añade un `adjustment` sin dinero. **El `PUT` del desembolso no sirve** para eso: la API lo trata como un movimiento con dinero y crea una transacción en una cuenta (comprobado con servidor real). Decidir en la Fase 5/6 si el contrato debe permitir corregir el principal de un desembolso sin dinero.
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
uv run pytest -q                                        # esperado: 914 passed
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
- **Calidad:** 914 pruebas con PostgreSQL real, `ruff`, `mypy --strict`, `alembic check` limpios, cero `type: ignore`.
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
