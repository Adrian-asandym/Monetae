# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-09, ~19:40 (America/Lima)** — cierre de sesión («Continuaremos en otro momento») |
| **`origin`** | `origin/main` = `origin/master-dev` = **`1736d7a`** (Fases 0–4, T-405, Fase 5 hasta T-504/T-506; SPEC v0.4 publicada). |
| **`main`** | `1736d7a`. |
| **`master-dev`** | **`9444819` + el commit de este cierre (`git log -1`)**, por delante de `main`: SPEC v0.5 + contrato 0.5.0 + `docs/ui/home-layout.md`, T-507 y T-508. **Sin publicar.** |
| **Gate abierto** | **G6 `gate_70e14ac5abc1`** (publicar lo anterior): **propuesta sin resolver**, pendiente de Adrian. Resueltos hoy: G1 `gate_1e81cf0fd994`, G2 `gate_10f2135dac21`, G3 `gate_abde30232929`, G4 `gate_a079e8e6d920`, G5 `gate_600e9631a8a2`. |
| **SPEC / ARCHITECTURE / contrato** | SPEC **v0.5** · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.5.0** (89 paths, 131 operaciones; validado con `check_openapi.py`). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–4 (importador de Cashew + T-405). **Fase 5 (UI Flutter Web), primera parte:** T-501 spike, T-502 marca/tarjeta/íconos, T-503 cliente HTTP + sesión + nginx, T-504(+b) gráficas, T-505/T-506/T-508 API (preferencias, reportes, campos de Inicio), T-507 tarjetas de presupuestos y objetivos. |
| 🔄 **En curso** | Nada ejecutándose. Ningún worker vivo. |
| ⏳ **Pendiente** | **G6** (publicar) · **T-509** ensamblado de Inicio según `docs/ui/home-layout.md` + barra de 4 botones + botón «+» · **T-510** formulario de nueva transacción · **API de presupuestos y metas (Fase 6)** para revisar Inicio con datos reales · resto de la Fase 5 (12–17 tareas estimadas por el informe T-504) · Fase 6 (íconos SVG API RF-46, adjuntos, presupuestos, metas, notificaciones, login Google, PIN/WebAuthn, proveedor de tipo de cambio) · Fase 7 · importación real definitiva (D9-A: cuando haya base persistente y pantallas) · despliegue VPS → V2 → V3 → V4. |

Backend: **46 de 89 rutas = 73 de 131 operaciones**, 8 migraciones (cabeza **`0008`**), **1032 pruebas**. UI `apps/web`: **116 pruebas** (64 goldens claro/oscuro). Detalle en el Anexo A.

## 3. Trabajo hecho en esta sesión (2026-10-09)

- **Fase 4 cerrada:** G1 publicado; **T-405 (L1-A)** préstamos de largo plazo sin desembolso; G2 publicado. Corregí una recomendación mía: el principal se corrige con `adjustment`, no con el `PUT` del desembolso.
- **Fase 5 iniciada:** Run `run_c2cebe1745b9`.
  - **T-501** spike de desacople: estimación 8–10 tareas, bajo el umbral de 1,5×.
  - **T-502** marca por modo (favicon e ícono con los SVG de Adrian), tarjeta configurable e íconos SVG en la UI.
  - **T-503** cliente HTTP tipado, sesión en el mismo origen (servicio `web` nginx en compose) y primera pantalla real.
  - **T-504 + T-504b** gráficas de ingresos y gastos, etiqueta de cuenta con color y formato peruano «S/ 1,234.50».
  - **T-505** preferencia `transaction_card`.
  - **T-506** reportes `cash-flow` y `categories`, más la migración **`0008` `exchange_rates`**, tabla diseñada en la Fase 1 que nunca se había creado.
  - **T-507** tarjetas de presupuestos y objetivos.
  - **T-508** `default_account_id`, `transaction_count` y `cumulative_net`.
- **SPEC v0.4 y v0.5, contrato 0.4.0 y 0.5.0:**
  - RF-46 íconos SVG propios (saneados);
  - RF-47 tarjeta configurable;
  - RF-48 cuenta por defecto;
  - RF-49 navegación de 4 botones;
  - disposición de Inicio en `docs/ui/home-layout.md`;
  - color en presupuestos y metas;
  - se corrigieron dos textos obsoletos de la SPEC (§2 y §8).
- **Publicaciones:** G3, G4 y G5, cada una tras una auditoría de seguridad (sin secretos ni datos reales; SVG sin scripts; JPG sin GPS).
- **Verificación:** cada tarea la verifiqué yo (pruebas completas, sondas con servidor real, goldens revisados). Probé las integraciones T-503 (nginx + CSRF), T-504 con T-506 y T-508 con servidores reales.
- **Pila de revisión `monetae-review`:** sirvió a Adrian para revisar con datos sintéticos. Está **detenida**; su volumen de datos se conserva (ver §7).

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-10 | Reanudación: STATUS contrastado con git y Orca (coincide); Docker volvió a estar accesible tras reactivarlo Adrian. «**OK para continuar**» al plan propuesto = **G6-A** (publicar) y **P1-A** (T-509 Inicio ∥ T-601 API presupuestos → T-602 API metas → T-510 formulario de transacción). |
| 2026-10-09 (noche) | **Cierre de sesión** («Continuaremos en otro momento»). Adrian **eliminó los worktrees de Codex** de la Fase 5. G6 queda como propuesta sin resolver. |
| 2026-10-09 (noche) | «**OK**» a **G5** (publicar T-504/T-506) y **T-507**. El diseño «sigue bien, como prueba». Adrian describe la **disposición de Cashew** que quiere (detalle en `docs/ui/home-layout.md`): barra inferior de 4 botones (Inicio, Transacciones, Presupuestos, Más) y, en Inicio, de arriba abajo: saludo, cuentas (nombre, saldo, nº de transacciones, color y **cuenta por defecto elegible desde Inicio**, resaltada con su color), objetivos, presupuestos (color y barra), circular de gastos con leyenda de las 3 categorías con más gasto y **deslizar a la izquierda** para ingresos, gráfico de líneas que **sube con ingresos y baja con gastos**, las **25 últimas transacciones** y un botón cuadrado «+» destacado para crear transacción. Esperará a que estén todas las integraciones para revisar posiciones y fidelidad. |
| 2026-10-09 (noche) | Revisión de T-503 en Chrome: «**OK, me parece bien (como prueba)**». OK a **G4** (publicar), **T-504** (gráficas) ∥ **T-506** (API de reportes) y luego **T-507** (presupuestos y metas). Ajustes pedidos: (1) la **etiqueta de la cuenta** (método de pago) se muestra con **su color** (distinto por cuenta); (2) **sin etiqueta de tipo de moneda**: la moneda se percibe por el **símbolo** del importe (S/, US$, €…), nunca por el código ISO. Van en T-504. |
| 2026-10-09 (noche) | «**OK, todo A**»: **G3-A** (publicar T-501 e imágenes), **D10-A** (íconos SVG propios en V1: contrato 0.4.0 ya, API en la Fase 6 con adjuntos, SVG saneado; catálogo base abierto, sin copiar los PNG de Cashew), **D11-A** (detalles de la tarjeta de transacción como preferencia en el servidor). Plan: SPEC v0.4 + contrato 0.4.0, luego T-502 (marca + tarjeta configurable) ∥ T-503 (cliente HTTP + sesión), después T-504+. |
| 2026-10-09 (noche) | **Revisión visual de T-501 por Adrian: le agrada.** Preferencias: **superficie azul en modo oscuro** (mantener); la UI debe ser **siempre fiel a Cashew** (colores, barras de progreso, íconos) en gráficas de ingresos/gastos, objetivos y presupuestos. Pide: (1) **subir SVG propios como íconos de categoría**; (2) **favicon e ícono de la app según el modo** con `img/icono-Monetae.svg` y `img/icono-Monetae-dark.svg` (añadió también `Monetae-Logo-dark.jpg` y `Monetae-Logo-Nombre-dark.jpg`, versionados en `f31f19c`); (3) **personalizar qué detalles muestra la tarjeta de transacción** (fecha/hora, botones de acción, notas…). (1) y (3) cambian SPEC y contrato: ver D10 y D11. |
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

**G6 · Publicar en `main`** (`gate_70e14ac5abc1`): SPEC v0.5 + contrato 0.5.0 + `docs/ui/home-layout.md`, T-507 y T-508, todo verificado e integrado.
- **A (recomendada): aprobar el merge y el push** tras repetir la auditoría. *Razón:* respaldo remoto de trabajo verificado.
- B: esperar a T-509.

**P1 · Orden de lo siguiente** (propuesto a Adrian el 2026-10-09, aún sin su OK):
- **A (recomendada):**
  1. **T-509** ensamblado de Inicio + barra de 4 botones + «+»;
  2. **T-510** formulario de nueva transacción con la cuenta por defecto;
  3. **API de presupuestos y metas (Fase 6)**;
  4. revisión de Inicio por Adrian con datos reales.
  *Razón:* Adrian quiere revisar posiciones y fidelidad con todo integrado.
- B: hacer primero la API de presupuestos y metas. *Contra:* Inicio sigue sin armarse.

**D7 · Para más adelante:** ADR-005 sincronización Android (antes de V4) · orden de categorías · credenciales OAuth de Google Cloud y proveedor de tipo de cambio (Fase 6) · proxy del VPS para la IP real en el límite de login (`ARCHITECTURE.md` §10.10) · corregir el principal de un desembolso sin dinero sin crear efectivo (hoy solo con `adjustment`).

*Resueltas en esta sesión:* G1–G5, L1, X1, X2, D9, D10, D11 (ver §4).

## 6. Siguiente paso concreto

**Al reanudar:** Adrian responde **G6** y **P1** (basta la letra). Con «A»:

| Paso | Qué | Agente / modelo / esfuerzo | Rama | Cómo lo verifico |
|---|---|---|---|---|
| 1 | G6: auditoría, `gate-resolve gate_70e14ac5abc1`, ff de `main`, push sin `--force`, marcar `task_6ff18605f937` `completed` | coordinador | — | `git ls-remote origin` |
| 2 | **T-509** Inicio según `docs/ui/home-layout.md` (saludo; cuentas con saldo, nº de transacciones, color y **selección de cuenta por defecto** resaltada; objetivos; presupuestos; circular de gastos con top-3 y **deslizar** a ingresos; línea **acumulada** con `cumulative_net`; 25 últimas transacciones; botón «+» cuadrado) + barra **Inicio/Transacciones/Presupuestos/Más** + carril visible de la barra de presupuesto en oscuro (nota de T-507). Spec por escribir: **releer contra el código y Cashew** (`homePage*.dart`, `bottomNavBar.dart`) | Codex `gpt-6.1-sol` · high | `codex/T-509-ui-home-assembly` | `dart analyze`, `flutter test` + goldens claro/oscuro, `flutter build web`; prueba real con la pila de revisión |
| 3 | **T-510** formulario de nueva transacción (fiel a `addTransactionPage` de Cashew; propone la cuenta por defecto) | Codex `gpt-6.1-sol` · high | `codex/T-510-ui-add-transaction` (después de T-509; comparten `main.dart`) | ídem + `POST /transactions` real con CSRF |
| 4 | **API de presupuestos y metas (Fase 6)**, incluido `color`/`icon` del contrato 0.5.0; en paralelo con T-509 si los archivos no se solapan (backend vs `apps/web`) | Codex `gpt-6.1-sol` · high | `codex/T-6xx-api-budgets-goals` | `ruff`, `mypy`, `pytest` con PostgreSQL, `alembic` (migración `0009`), sonda real |

**Antes de lanzar:** `orca skills get orchestration --full`, `orca status --json`, `docker version`, `git worktree list`, disco ≥ 3 GB y puertos libres. Codex muestra el aviso «Update available» al lanzar: enviar *Esc* y reintentar (Anexo C). Usar `check --ack <delivery>` tras procesar cada entrega.

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 5: `run_c2cebe1745b9`.** Tareas `completed`: T-501 `task_5df2d0fe6f4d`, T-502 `task_fd5d51af5bd1`, T-503 `task_23b103463ac4`, T-504 `task_2cb692365da5` (+T-504b `task_0d2f31697cba`), T-505 `task_98c4de4ea74a`, T-506 `task_46d3c202cc60`, T-507 `task_e8282e2fc9df`, T-508 `task_6ff18605f937` (puede figurar `blocked` por el gate G6; marcar `completed` al resolverlo). **Ningún worker vivo** (sin procesos de Codex; `worker-list` solo muestra registros liberados). Run de la Fase 4: `run_f5e95406186a` (todo `completed`). Anteriores: `run_63b520544a30` (F3), `run_70f5f187fe16` (F2), `run_2cddcd14320c` (F1), `run_bef8ecfc67a7` (F0). El CLI no cierra Runs; no usar `orchestration reset`.

**Worktrees:** solo `Monetae` → `main` y `Monetae-master-dev` → `master-dev` (Adrian borró los de Codex). Sin ramas `codex/*`. Sin `.env` sueltos.

**Contenedores:** ninguno en marcha. Queda el **volumen** `monetae-review_postgres_data` (usuario sintético `adrian-review@example.test` + datos de la fixture; la contraseña se dio a Adrian en el chat y **no** se versiona). Para relanzar la pila de revisión desde `Monetae-master-dev`: `cd apps/web && flutter build web --release && cd ../.. && cp .env.example .env && sed -i 's/^MONETAE_COOKIE_SECURE=true$/MONETAE_COOKIE_SECURE=false/' .env && COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml up -d --build db api web` (y `alembic upgrade head` en `api`). Bajar con `down` (o `down -v` para borrar sus datos) y `rm -f .env`.

**Paneles de Orca abiertos:** el del coordinador y `lupuna` (otro proyecto, no se toca). Ningún panel de Codex.

## 8. Limitaciones y riesgos conocidos

- **Docker Desktop depende de la integración con WSL** (distro `AlmaLinux-9`): si `/usr/bin/docker` apunta a un destino inexistente, reactivar *Settings → Resources → WSL integration* y `wsl --shutdown`.
- **Importación real:** el `apply` nunca se ha ejecutado (solo `--dry-run` sobre copias, cuadre exacto); espera a D9-A. El importador es **solo inserción**. Préstamos con principal supuesto (L1-A) aparecen `settled` hasta corregirlos con `adjustment` (el `PUT` del desembolso crea efectivo).
- **UI:** Inicio aún no está ensamblado según la disposición de Adrian; presupuestos y metas solo con datos sintéticos hasta su API (Fase 6). `intl` no trae el formato peruano: está fijado a mano en `currency_format.dart` («S/ 1,234.50» en español). El favicon sigue el modo del **sistema/navegador**, no el tema de la app.
- **Íconos de Cashew:** sus 277 PNG de categoría tienen licencia dudosa; **no** copiarlos (SPEC RF-46).
- **Reportes:** sin proveedor de tipo de cambio (Fase 6), con moneda de reporte ≠ base todo cae en `unconverted_count` salvo tasas insertadas a mano en `exchange_rates`.
- **Sin auditoría de seguridad externa** (Fase 7). La BD admite un `income` negativo por SQL directo (`ARCHITECTURE.md` §10.12). Límite de login detrás de proxy (§10.10). `501 google_login_not_available` fuera del contrato (§10.11).
- **Disco:** ≈ 3,1 GB libres en `/` (20 GB). Flutter + Docker lo consumen rápido: borrar artefactos (`build/`, `.dart_tool/`, `.venv/`) de worktrees ya fusionados.
- **Repositorio público:** todo push se audita antes; los datos reales solo viven en `reference/backups/` (ignorado).
- La cuota de Claude Pro es limitada: delegar generación de código; reservar al coordinador specs, revisión e integración.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md (§10), docs/SPEC.md v0.5, docs/ui/home-layout.md, ADRs y tareas. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list
git -C ../Monetae log --oneline -1 && GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' ls-remote origin refs/heads/main refs/heads/master-dev

# 1) Herramientas (el Python del sistema es 3.9: NO usarlo para el proyecto)
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
uv --version && docker compose version && flutter --version | head -1
orca status --json | head -5 && orca orchestration run-use --id run_c2cebe1745b9
orca orchestration gate-list --json | grep -A3 gate_70e14ac5abc1     # G6 pendiente

# 2) Backend (≈ 8 min; BD propia)
cp .env.example .env && MONETAE_DB_PORT=5433 COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 1032 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0008
cd ../.. && python3 -I scripts/check_openapi.py         # 89 paths, 131 operaciones
COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) UI
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release   # esperado: 116 pruebas
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo limpio

# 4) Recorrido real web+API por nginx (sin navegador): apps/web/tool/e2e_session.sh (proyecto monetae-t503, puertos 5444/8001/8081)
```

## Anexo A · Qué incluye el backend (verificado sobre la cabeza de `master-dev`)

FastAPI síncrono (ADR-007) en `services/api`: **46 de 89 rutas = 73 de 131 operaciones**.

- **Acceso:**
  - login por correo y contraseña (argon2id);
  - sesiones opacas con cookie `HttpOnly` y CSRF con HMAC + `Origin`;
  - límite de intentos;
  - `users/me` con preferencias: tema, acento, widgets, `transaction_card` (RF-47) y `default_account_id` (RF-48).
  - Usuarios solo por CLI.
- **Catálogos:** cuentas (con saldo y `transaction_count` calculados), categorías (2 de sistema de interés), personas con alias y etiquetas.
- **Libro mayor:** transacciones, transferencias (también entre monedas), lotes y programadas.
- **Préstamos (T-301/T-302):** saldo y estado calculados; interés primero; exceso con `adjustment` o `income_expense`; revalidación del libro.
- **Suscripciones (T-303/T-304):** archivado reversible y totales por moneda.
- **Reportes (T-506/T-508):** `cash-flow` (con `cumulative_net`) y `categories`.
  - **Base caja:** el interés cuenta en la fecha del pago y el capital nunca.
  - **Multimoneda:** `fx_rate_to_base` + `exchange_rates` del día o anterior, con `unconverted_count`.
  - **Periodos:** zona horaria del usuario, semanas ISO.
- **Base de datos:**
  - Migraciones: `0001` identidad y catálogos, `0002` intentos, `0003` transacciones, `0004` transferencias, `0005` préstamos, `0006` suscripciones, `0007` importador, `0008` `exchange_rates` (tabla global).
  - FK compuestas con `user_id`.
- **Importador de Cashew** (`python -m monetae.cli import-cashew`): SQLite v48 en solo lectura sobre una copia; idempotente; `--dry-run`; cuadre atómico; préstamos ADR-008 + L1-A. Documentación en `docs/importers/`.
- **Calidad:** 1032 pruebas con PostgreSQL real; `ruff`, `mypy --strict` y `alembic check` limpios; cero `type: ignore`.
- **No implementado (operaciones del contrato):** usuarios 9 (PIN/WebAuthn), reportes 6, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, íconos 4, Google OIDC 1, exportaciones 1 y sugerencia de tipo de cambio 1.

**UI `apps/web` (Flutter Web):**
- **Componentes de Cashew desacoplados:** tema, tarjeta, circular, líneas, resumen, selector, presupuestos y objetivos. Cada uno conserva su procedencia y el aviso GPL; `NOTICE` y `LICENSE` vienen de Cashew.
- **Datos:** DTO generados del contrato y cliente HTTP con CSRF.
- **Pantallas:** acceso, lista de transacciones e Inicio provisional.
- **Demos:** `/#/demo/home` y `/#/demo/budgets-goals`.
- **Textos y marca:** i18n es/en; marca por modo.
- **Despliegue:** servida por nginx (`infra/web/default.conf`) en el mismo origen que la API.

## Anexo B · GitHub

`origin` = `https://github.com/Adrian-asandym/Monetae.git` (público). Antes de cada push se verifica el historial (sin `.env`, claves, `reference/`, respaldos; únicos `.sqlite`/`.csv` versionados: los 3 fixtures sintéticos de `services/api/tests/fixtures/cashew_v48/`; sin correos reales). `origin/main` está en `1736d7a` (G5). Comando: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev` (sin `--force`; `gh` autenticado como `Adrian-asandym`).

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
- **Orca, entregas:** `check --wait` vuelve a entregar la misma *Delivery* hasta confirmarla con `check --ack <delivery_id>`; tras responder (`reply --id <msg> --run <run>`) o procesar un `worker_done`, confirmar en la siguiente llamada.
- **`reference/` no existe en los worktrees** (está ignorado): dar a los workers la ruta absoluta `/home/artur/propio2/Monetae/reference/Cashew/budget/` y **prohibir** `reference/backups/` en cada spec de UI.
- **Revisar las capturas (goldens) yo mismo:** así apareció la regresión del formato de importes («170,00 S/»). `intl` no trae el formato peruano ni con `es_PE`.
- **Contrato por delante del backend:** al cambiar un esquema ya implementado, `test_contract_subset` falla a propósito hasta integrar la tarea del backend; decirlo en `STATUS` y en la spec.
- **Adrian deja a veces archivos sin commit en ambas carpetas** (p. ej. imágenes en `img/`): versionarlos en `master-dev` y, antes del ff de `main`, quitar las copias **idénticas** (comprobar hash) de la carpeta de `main`.
- **Disco:** borrar solo artefactos ignorados (`git check-ignore`) de worktrees fusionados; las carpetas las borra Adrian.
- **Pila de revisión:** proyecto Compose propio (`monetae-review`), usuario `@example.test`, datos de la **fixture sintética**, contraseña solo en el chat; para servidores locales por HTTP, `MONETAE_COOKIE_SECURE=false` solo en `.env`.
