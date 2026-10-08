# T-204 — Autenticación por correo y contraseña, sesiones y CSRF

> Fase 2. Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (seguridad: cada detalle importa; yo la reviso con lista de seguridad).
> Depende de T-203 (integrada). Eres el **único dueño de las migraciones** durante esta tarea: creas la `0002`.

## Objetivo

Implementar el acceso a la API: login con correo y contraseña (argon2id), sesión en servidor con cookie opaca, protección CSRF, listado y revocación de sesiones, cierre de sesión en todos los dispositivos, límite de intentos y `users/me`. Google (OIDC), PIN y WebAuthn son de la Fase 6 y **no** se implementan aquí.

## Leer primero

`AGENTS.md` (§6, §9), `docs/decisions/002-auth-sessions.md` y `006-app-lock.md` (contexto), `docs/ARCHITECTURE.md` (§3, §5.2, §7, §8), `docs/api/openapi.json` (rutas `/auth/*` y `/users/me`, esquemas `PasswordLogin`, `LoginResult`, `AuthenticatedSession`, `Session`, `CurrentUser`, `Problem`, parámetro `CsrfToken`) y `docs/api/README.md` (§ sesión y CSRF).

## Decisiones ya tomadas (no las cambies)

1. **No hay endpoint público de registro en V1.** Los usuarios se crean con un comando: `uv run python -m monetae.cli create-user --email ... [--base-currency PEN] [--locale es]`; la contraseña se pide con `getpass` (dos veces) o con `--password-stdin`; **nunca como argumento de línea de comandos**. (Cuentas de familiares: V2.)
2. **CSRF por doble envío firmado.** Cookie `monetae_csrf` (no `HttpOnly`, `Secure`, `SameSite=Lax`) con valor `nonce.hmac`, donde `hmac = HMAC-SHA256(secret_key, nonce || session_token_hash_o_"pre")`; el middleware la emite en cualquier respuesta si falta. Toda petición `POST/PUT/PATCH/DELETE` (incluido el login) exige la cabecera `X-CSRF-Token` igual al valor válido de la cookie **y** un `Origin` (o, en su defecto, `Referer`) cuyo origen esté en `cors_origins`/el propio host. Tras el login se emite un token ligado a la sesión nueva; `GET /auth/csrf` devuelve el token vigente. Fallos ⇒ `403` `Problem` con `code: csrf_failed`. Comparaciones en tiempo constante (`hmac.compare_digest`).
3. **Sesión:** token opaco de 32 bytes aleatorios (`secrets.token_urlsafe`), cookie `monetae_session` (`HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`); en BD solo se guarda `sha256(token)` en `sessions.token_hash`. Se emite **un token nuevo en cada login** (sin fijación de sesión). Expiración por inactividad (`session_idle_minutes`, 14 días por defecto, deslizante) y absoluta (`session_absolute_days`, 30 por defecto), ambas en `Settings`. `last_seen_at` se actualiza como máximo una vez por minuto. `logout` revoca la sesión actual; `logout-all` revoca todas las del usuario; `DELETE /auth/sessions/{id}` revoca una del propio usuario (la de otro usuario ⇒ `404`).
4. **Contraseñas:** argon2id (`argon2-cffi`, parámetros por defecto del perfil recomendado); longitud 12–128; rehash transparente en login si `check_needs_rehash`. **Anti-enumeración:** correo inexistente y contraseña errónea devuelven la misma respuesta `401` (`code: invalid_credentials`) y el mismo trabajo (verifica contra un hash ficticio).
5. **Límite de intentos** persistido en BD: tabla nueva `login_attempts` (migración **0002**): `id`, `email_lower text`, `ip text`, `succeeded bool`, `attempted_at timestamptz`. Regla: 5 fallos por correo o 20 fallos por IP en 15 minutos ⇒ `429` con cabecera `Retry-After` y `code: too_many_attempts`; un login correcto no cuenta como fallo. Se purgan filas de más de 7 días de forma oportunista. (Excepción documentada: es un registro de seguridad, sin `user_id` obligatorio.)
6. **Alcance de rutas** (solo estas; el resto del contrato llega en otras tareas): `POST /auth/login` (solo `method: "password"`; `method: "google"` ⇒ `501` Problem `code: google_login_not_available`), `POST /auth/logout`, `POST /auth/logout-all`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`, `GET /auth/csrf`, `GET /users/me`, `PATCH /users/me` (solo `locale`, `timezone`, `report_currency`, `lock_after_minutes`, `preferences`; `base_currency` ⇒ `409` `code: base_currency_locked` hasta que T-206 defina la regla "sin transacciones"). Las rutas tienen **el mismo `operationId`, seguridad y códigos de estado** que el contrato.
7. **Crear usuario (servicio):** `report_currency = base_currency`; se crean para el usuario las dos categorías de sistema (`system_key` `interest_income` e `interest_expense`, `is_system=true`) con nombres en español configurables ("Intereses (ingreso)", "Intereses (gasto)").

## Archivos permitidos

```
services/api/src/monetae/config.py                         # añadir secret_key, cookie_secure, session_idle_minutes, session_absolute_days
.env.example                                              # añadir MONETAE_SECRET_KEY (valor claramente falso)
services/api/src/monetae/cli.py
services/api/src/monetae/domain/passwords.py              # política de contraseñas y reglas de bloqueo (puras, sin hashing ni I/O)
services/api/src/monetae/services/__init__.py
services/api/src/monetae/services/auth.py                  # login, sesiones, rate limit, creación de usuario
services/api/src/monetae/db/models/security.py             # LoginAttempt
services/api/src/monetae/db/models/__init__.py             # solo exportar
services/api/src/monetae/db/session_store.py               # operaciones de sesiones/intentos (opcional, o dentro de services)
services/api/alembic/versions/0002_login_attempts.py
services/api/src/monetae/api/security.py                   # cookies, CSRF, dependencias current_user
services/api/src/monetae/api/routers/auth.py
services/api/src/monetae/api/routers/users.py
services/api/src/monetae/api/schemas/__init__.py
services/api/src/monetae/api/schemas/auth.py               # Pydantic estricto, espejo del contrato
services/api/src/monetae/api/main.py                       # registrar routers/middleware
services/api/tests/conftest.py                             # SOLO para compartir fixtures de BD/cliente entre tests/db y tests/api
services/api/tests/db/conftest.py                          # SOLO si hace falta para ese refactor (los tests de T-203 deben seguir pasando)
services/api/tests/api/__init__.py
services/api/tests/api/conftest.py
services/api/tests/api/test_auth_login.py
services/api/tests/api/test_auth_sessions.py
services/api/tests/api/test_csrf.py
services/api/tests/api/test_rate_limit.py
services/api/tests/api/test_users_me.py
services/api/tests/api/test_cli.py
services/api/tests/api/test_contract_subset.py             # rutas implementadas ⊆ docs/api/openapi.json
services/api/tests/domain/test_passwords.py
docs/api/README.md                                         # SOLO una sección "Implementación de sesión y CSRF (T-204)" con lo decidido arriba
```

No tocar `pyproject.toml`/`uv.lock` (no hacen falta dependencias nuevas), `docs/api/openapi.json`, `domain/money.py` ni `fx.py`.

## Pruebas obligatorias (contra PostgreSQL real, `MONETAE_REQUIRE_DB=1`)

- Login correcto ⇒ `200`, cookies con las banderas exactas, token **distinto** en cada login, `sessions.token_hash` ≠ token y sin el token en claro en BD ni en logs.
- Credenciales erróneas / correo inexistente ⇒ misma respuesta `401`; tiempos comparables (verifica que se llama al hash ficticio, no el reloj).
- Sesión expirada por inactividad y por límite absoluto (reloj inyectable `Clock`) ⇒ `401`; sesión revocada ⇒ `401`.
- `logout`, `logout-all` (varias sesiones en varios clientes), `DELETE /auth/sessions/{id}`; **dos usuarios:** A no puede listar ni revocar sesiones de B (`404`) y `users/me` devuelve solo al usuario de la sesión.
- CSRF: sin cabecera ⇒ `403`; token manipulado ⇒ `403`; `Origin` ajeno ⇒ `403`; `GET` exento; el login también lo exige; token ligado a la sesión (un token de otra sesión no sirve).
- Límite de intentos: 5 fallos por correo ⇒ `429` + `Retry-After`; un login correcto no cuenta; ventana de 15 min (reloj inyectable); IP.
- Contraseña: política 12–128, rehash cuando cambian los parámetros.
- CLI: crea usuario con contraseña por stdin; no acepta contraseña como argumento; segundo usuario con el mismo correo ⇒ error claro; crea las 2 categorías de sistema.
- Contrato: todas las rutas montadas existen en `openapi.json` con el mismo `operationId` y esquema de seguridad.
- Migración 0002 reversible y `alembic check` sin diferencias; las pruebas de T-203 siguen pasando.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade 0001 && uv run alembic upgrade head
cd ../.. && docker compose -f infra/docker-compose.yml up -d --build   # arranca migrado; probar login con curl tras crear usuario con la CLI
docker compose -f infra/docker-compose.yml down -v && rm -f .env
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`feat(auth):`, `test(auth):`). Actualiza tu rama con `master-dev` antes de reportar. **No registres contraseñas, tokens ni correos completos en logs.** Dudas que bloqueen → `orca orchestration ask`. Si el contrato te parece inconsistente con esto, **no lo cambies**: pregunta o anótalo en `worker_done`. Reporta `worker_done` una sola vez.
