# T-503 — UI: cliente HTTP tipado, sesión y primera pantalla con datos reales

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-09** (verificada por el coordinador: analyze limpio, 47 pruebas, build web y recorrido real por nginx). (Run `run_c2cebe1745b9`; plan aprobado por Adrian, «todo A»). Depende de T-502 y T-505, ya integradas en `master-dev`.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `high` (sesión, CSRF y proxy: errores sutiles). Sin otra tarea en paralelo que toque `apps/web` o `infra/`.

## Objetivo

Que `apps/web` hable con la API real en el **mismo origen** (ADR-002: cookie de sesión `HttpOnly`, `SameSite=Lax`, CSRF con cookie `monetae_csrf` + cabecera `X-CSRF-Token` + comprobación de `Origin`): inicio y cierre de sesión, lista de transacciones reales con la `TransactionCard` de T-502, y la preferencia `transaction_card` (RF-47) **guardada en el servidor**.

## Leer primero

`AGENTS.md` §7, `docs/decisions/002-*.md`, `docs/ARCHITECTURE.md` (§7 API y el apartado de despliegue/compose), `docs/SPEC.md` v0.4 (RF-37, RF-47), `docs/api/openapi.json` 0.4.0 (`/auth/login`, `/auth/logout`, `/users/me`, `/accounts`, `/categories`, `/transactions`, `Problem`), `docs/api/README.md` (sesión y CSRF, T-204; 0.4.0), `services/api/src/monetae/api/security.py` (cookies y `trusted_origin`), `infra/docker-compose.yml`, `.env.example`, y `apps/web` (en especial `lib/data/api_dtos.dart`, `lib/widgets/transaction_card*.dart`, `lib/main.dart`, `tool/generate_dtos.py`).

Cashew (solo lectura, para la fidelidad visual de la pantalla de acceso y la lista): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/`. **PROHIBIDO** leer o listar `/home/artur/propio2/Monetae/reference/backups/`.

## Alcance

1. **Mismo origen en local.**
   - Servicio `web` en `infra/docker-compose.yml`: nginx (imagen oficial, versión fija) que sirve `apps/web/build/web` (montado en solo lectura; la compilación se hace en el host con `flutter build web`) y reenvía `/api/` a `api:8000`.
   - **Obligatorio en nginx:** `proxy_set_header Host $http_host;` (con puerto) y `X-Forwarded-*`. La API compara `Origin` con su propia URL base (`trusted_origin`); sin el `Host` correcto **todas las escrituras darían 403**. No abras `MONETAE_CORS_ORIGINS` para esquivarlo.
   - Puertos parametrizables para no chocar entre workers: `MONETAE_WEB_PORT` (por defecto 8080) y `MONETAE_API_PORT` (por defecto 8000), ambos en `127.0.0.1`. Documenta en `.env.example` que en local por HTTP se usa `MONETAE_COOKIE_SECURE=false` (o explica por qué no hace falta en `localhost`); **no** cambies el valor por defecto seguro.
2. **Cliente HTTP tipado** en `apps/web/lib/api/`.
   - Usa los DTO generados del contrato 0.4.0 y `package:http`; ninguna URL absoluta: rutas relativas `/api/v1/...`.
   - Lee `monetae_csrf` (no es `HttpOnly`) para la cabecera `X-CSRF-Token` en métodos que escriben.
   - Traduce `Problem` (RFC 7807) a errores tipados: 401 ⇒ volver al acceso; 403/409/422 ⇒ mensaje i18n. Sin lógica de negocio ni cálculos de dinero en la UI (los importes son cadenas decimales del contrato).
3. **Acceso.** Pantalla de inicio de sesión con correo y contraseña, fiel al estilo de Cashew y con el logo por modo de T-502. Cierre de sesión. Al arrancar, `GET /users/me` decide si se muestra el acceso o la app.
4. **Primera pantalla real.**
   - Lista de transacciones (`GET /transactions`, paginada por cursor) agrupada por día, con cuentas y categorías resueltas desde sus endpoints, usando `TransactionCard`.
   - Las categorías con `icon = custom:<uuid>` muestran el ícono de reserva del catálogo (la API de íconos llega en la Fase 6).
5. **Preferencia RF-47 persistida.**
   - El panel de T-502 lee `preferences.transaction_card` de `/users/me` y lo guarda con `PATCH /users/me`.
   - **`PATCH` reemplaza `preferences` completo** (T-505): envía siempre el objeto `preferences` entero (tema, acento, widgets y tarjeta), nunca solo la tarjeta, o se borrarían las demás preferencias. Cúbrelo con una prueba.
6. **Modo demostración.** Conserva la pantalla de componentes con datos sintéticos de T-501/T-502 (por ejemplo, en una ruta aparte), útil para goldens y revisión.

## Archivos permitidos

`apps/web/**`, `infra/docker-compose.yml`, `infra/web/**` (nuevo: configuración de nginx), `.env.example` (solo variables y comentarios nuevos), `docs/cashew-analysis/05-ui-spike-results.md` (sección «T-503») y `apps/web/README.md`. No tocar `services/`, `docs/SPEC.md`, `docs/api/`, `AGENTS.md`, `reference/`, `img/`. Dependencias nuevas: `http` y, si hace falta para leer cookies, `web`; cualquier otra, con `ask`.

## Pruebas obligatorias

- **Widget y unidad**, con `package:http/testing` (`MockClient`):
  - el cliente añade `X-CSRF-Token` en escrituras y no en lecturas;
  - un 401 lleva al acceso;
  - `Problem` 422 muestra el mensaje;
  - el `PATCH` de preferencias envía el objeto completo;
  - la lista agrupa por día y respeta las seis preferencias;
  - goldens claro/oscuro de la pantalla de acceso.
- **Extremo a extremo con servidores reales** (sin navegador; evidencia en `worker_done`).
  - **Arranque:** `flutter build web --release`; luego `docker compose up -d db api web` con proyecto y puertos propios (`COMPOSE_PROJECT_NAME=monetae-t503`, `MONETAE_DB_PORT=5444`, `MONETAE_API_PORT=8001`, `MONETAE_WEB_PORT=8081`); migraciones; usuario creado con la CLI (`create-user`, correo `@example.test`).
  - **Comprobaciones con `curl` contra el puerto de **web** (8081):**
    - `index.html` se sirve;
    - el login devuelve 200 y deja las cookies;
    - `GET /api/v1/users/me` devuelve 200;
    - un `PATCH /api/v1/users/me` con `Origin: http://localhost:8081` y el token CSRF devuelve 200;
    - el mismo `PATCH` **sin** token devuelve 403.
  - **Limpieza:** `down -v` del proyecto propio.
- **Privacidad:** solo datos sintéticos; ningún correo ni dato real.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release && cd ../..
grep -rE "drift|firebase|appStateSettings|package:budget/" apps/web/lib || echo "limpio"
# extremo a extremo descrito arriba (proyecto monetae-t503, puertos 5444/8001/8081), y al final:
COMPOSE_PROJECT_NAME=monetae-t503 docker compose -f infra/docker-compose.yml down -v && rm -f .env
git status --short && git diff --stat master-dev...HEAD   # solo archivos permitidos; sin build/
```

## Reglas

Commits pequeños en inglés (`feat(web):`, `test(web):`, `chore(infra):`, `docs(ui):`). Actualiza tu rama con `master-dev` antes de reportar. **No inventes reglas de negocio** ni relajes la seguridad de la API para que algo funcione: ante un bloqueo, `orca orchestration ask`. Reporta `worker_done` una sola vez.
