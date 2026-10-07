# ADR-002 — Autenticación y sesiones

- **Estado:** PROPUESTO (pendiente de decisión de Adrian)
- **Fecha:** 2026-10-07 · **Autor:** Claude
- **Relacionado:** SPEC RF-35, RF-37, §12; AGENTS.md §9; ADR-006

## Contexto

V1 es web (una sola aplicación servida por nuestro backend) con login por **Google (OpenID Connect)** y por **correo y contraseña** (para desarrollo local sin Google). Debe haber sesiones con expiración y **cierre de sesión en todos los dispositivos** (RF-37), límite de intentos de login y contraseñas con argon2 (SPEC §12). Más adelante llegan el bot de Telegram y herramientas MCP (V2/V3) y la app Android (V4), que **no** usan cookies de navegador.

## Opciones

### A (recomendada) — Sesión en servidor con cookie `HttpOnly`
- Tras el login (Google con *authorization code* + PKCE, o correo/contraseña con argon2id) el servidor crea una **sesión opaca** guardada en PostgreSQL y la entrega en una cookie `HttpOnly`, `Secure`, `SameSite=Lax`.
- Expiración por inactividad y absoluta; "cerrar sesión en todos los dispositivos" = borrar las filas de sesión del usuario (inmediato y verificable).
- Protección CSRF para métodos que modifican datos (comprobación de `Origin` + token). La web y la API comparten dominio detrás del proxy.
- Para V2–V4 se añaden **tokens personales / de dispositivo** (Bearer, revocables) con su propia tabla, sin tocar el flujo web.
- **Pros:** la revocación es trivial; el token nunca es legible desde JavaScript (mitiga robo por XSS); es lo más simple de hacer bien.
- **Contras:** consulta a BD por petición (irrelevante a esta escala); cookies exigen cuidar CSRF.

### B — JWT de acceso corto + *refresh token* rotativo
- Acceso de ~15 min y *refresh* rotativo guardado en BD (en cookie `HttpOnly`).
- **Pros:** encaja directo con móvil y herramientas externas. **Contras:** más piezas (rotación, detección de reutilización, revocación vía refresh); complejidad que V1 no necesita.

### C — JWT largo en `localStorage`
- Se descarta: cualquier XSS lo roba y no se puede revocar de forma fiable.

## Política común (cualquiera de A/B)

- Contraseñas con argon2id; límite de intentos por usuario e IP con bloqueo temporal; mensajes de error que no revelan si el correo existe.
- Vincular una cuenta de Google a un usuario existente solo si el correo viene **verificado** por Google y el usuario lo confirma. `users.google_sub` es único.
- Ningún endpoint sin autenticar salvo login, callback de OIDC y salud.

## Recomendación

**Opción A para V1**, diseñada para añadir tokens de dispositivo en V2–V4 (opción B se reserva para cuando exista cliente móvil).

## Consecuencias si se acepta A

- Tabla `sessions` (`id`, `user_id`, `created_at`, `last_seen_at`, `expires_at`, `user_agent`, `ip`) y, más adelante, `api_tokens`.
- Dependencias a justificar al implementar: librería OIDC (p. ej. Authlib) y `argon2-cffi`.
- Google OIDC requiere crear credenciales en Google Cloud (acción de Adrian); en local se usa correo/contraseña.

## Decisión de Adrian

_Pendiente._
