# ADR-006 — Bloqueo de la app (equivalente web al bloqueo biométrico)

- **Estado:** PROPUESTO (pendiente de decisión de Adrian)
- **Fecha:** 2026-10-07 · **Autor:** Claude
- **Relacionado:** SPEC RF-36; ADR-002; Cashew (`local_auth`, desactivado en web)

## Contexto

Cashew bloquea la app con la huella o el rostro del móvil; en web ese mecanismo (`local_auth`) no existe y Cashew lo desactiva. Monetae necesita un bloqueo equivalente: una vez iniciada la sesión (ADR-002), la app se **bloquea tras inactividad** y se desbloquea con un PIN y/o con la biometría del dispositivo mediante **WebAuthn**.

Importante: es una **barrera de comodidad** contra quien mire o use tu pantalla desbloqueada. No sustituye al login ni protege frente a un atacante con control del navegador. WebAuthn solo funciona en `localhost` o con HTTPS (el VPS tendrá HTTPS).

## Opciones

### A (recomendada) — PIN obligatorio + WebAuthn opcional
- **PIN** de 6 dígitos, guardado como hash (argon2id) en el servidor y verificado allí (el cliente no es de fiar); tras 5 intentos fallidos se exige volver a iniciar sesión.
- **WebAuthn** (autenticador de plataforma con verificación de usuario: huella/rostro/PIN del sistema) como atajo opcional de desbloqueo, verificado en el servidor.
- El PIN es el respaldo si el dispositivo no tiene biometría.
- **Pros:** funciona en cualquier dispositivo; la biometría es opcional; la verificación y los límites viven en el servidor.
- **Contras:** dos mecanismos que mantener; WebAuthn exige HTTPS y una librería (p. ej. `py_webauthn`, dependencia a justificar).

### B — Solo PIN
- **Pros:** simplísimo, sin dependencias nuevas. **Contras:** sin biometría; menos cómodo en móvil.

### C — Solo WebAuthn
- **Contras:** excluye dispositivos sin autenticador de plataforma y deja sin respaldo si se pierde la credencial.

## Recomendación

**Opción A, en dos pasos:** PIN primero (Fase 6) y WebAuthn después, sin cambiar el modelo de datos.

## Consecuencias si se acepta A

- Campos en `users` (hash del PIN, intentos fallidos) y tabla `webauthn_credentials` (`id`, `user_id`, `credential_id`, `public_key`, `sign_count`, `created_at`).
- El tiempo de inactividad y el uso del bloqueo son preferencias del usuario.
- Se documenta que el bloqueo no es una medida de seguridad fuerte.

## Decisión de Adrian

_Pendiente._
