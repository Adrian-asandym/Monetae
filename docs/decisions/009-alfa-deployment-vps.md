# ADR-009 — Despliegue de la versión alfa en el VPS

- **Estado:** **ACEPTADO** (a–d, f y g aplicados en el despliegue alfa; c confirmado en Full (strict); en d falta la corrección de la IP real; e es un **plan sin ejecutar** para beta). Decidido por Adrian el 2026-10-16.
- **Fecha:** 2026-10-16 · **Autor:** Claude
- **Relacionado:** `docs/deploy-alfa.md` (runbook), `docs/ARCHITECTURE.md` §9 y §10.10, tarea T-701 (preparación de Docker), `.env.alfa.example`, SPEC §3 (hito de despliegue).

> El repositorio es público: aquí solo hay marcadores (`<DOMINIO_ALFA>`, `<DOMINIO_RAIZ>`, `<RUTA_PRODUCCION>`, `<USUARIO_ADMIN>`, `<USUARIO_DEV>`, `<IP_VPS>`). El dominio real de alfa está en `.env.alfa.example`.

## Contexto

Monetae alfa se publica en `https://<DOMINIO_ALFA>` desde un VPS propio (AlmaLinux 10, SELinux activo, firewalld). Cadena de tráfico:

```
Navegador → Cloudflare (proxy activo) → Caddy en el host (80/443, TLS de Let's Encrypt)
          → 127.0.0.1:8090 → nginx del contenedor web (80 interno) → api (FastAPI/Uvicorn) → db (PostgreSQL 16)
```

En el mismo VPS trabajan los agentes de desarrollo, y más adelante podría convivir una instancia beta.

## Decisiones

### a) Subdominio de un solo nivel

`alfa-<nombre>.<DOMINIO_RAIZ>` en vez de `alfa.<nombre>.<DOMINIO_RAIZ>`.
**Por qué:** el certificado gratuito de Cloudflare (Universal SSL) solo cubre `*.<DOMINIO_RAIZ>` (un nivel). Con el proxy activo, un subdominio de dos niveles daría error SSL.

### b) Caddy en el host como proxy inverso

En vez de exponer el 8090 directamente.
**Por qué:** Cloudflare solo hace proxy a ciertos puertos (80, 443, 8080, 8443…), no al 8090. Caddy obtiene y renueva el certificado solo, y permite varias instancias (alfa, beta) en el mismo VPS, cada una con su subdominio y su puerto en loopback.

### c) Evitar el modo SSL «Flexible» de Cloudflare

**Por qué:** «Flexible» manda HTTP sin cifrar al origen y provoca bucles de redirección con Caddy, que redirige HTTP a HTTPS.
**Estado:** **fijado en Full (strict)** por Adrian el 2026-10-16 (antes la zona estaba en «Automático»). El origen tiene un certificado válido de Let's Encrypt. Es un ajuste de **toda la zona `<DOMINIO_RAIZ>`**, no solo de alfa.

### d) Caddy con `trusted_proxies` = rangos de IP de Cloudflare

**Por qué:** así llega a la app la IP real del cliente y el límite de intentos de login (por IP) no queda compartido entre todos los usuarios. Sin esto, la IP registrada sería la del borde de Cloudflare.
La lista oficial (`https://www.cloudflare.com/ips/`) cambia con el tiempo: **se descarga al configurar**, no se copia en el repositorio.
Del lado de la app (T-701), nginx toma la IP de `X-Forwarded-For` solo si viene de un par de loopback o de una red privada, y Uvicorn confía solo en la red interna de Compose (ver `ARCHITECTURE.md` §10.10).
**Por confirmar:** comprobar que `login_attempts.ip` guarda la IP real del cliente y no una de Cloudflare.

### e) Un solo repositorio; alfa y beta son instancias — *plan, sin ejecutar para beta*

Todas las versiones salen del mismo código. Alfa y beta son **instancias** distintas, separadas por su carpeta en el VPS, su `.env`, su puerto en loopback, su volumen de BD y su subdominio.
- **Alfa** corre desde `main`.
- **Beta** aún no existe. Plan recomendado: promoverla desde alfa **fijándola a un tag** (p. ej. `v0.1.0`).
- Una tercera versión monetizable es muy poco probable (no es el objetivo principal).

### f) Producción y desarrollo separados

Producción vive en `<RUTA_PRODUCCION>` y la controla `<USUARIO_ADMIN>` (con sudo) en el Docker del sistema. Los agentes trabajan con `<USUARIO_DEV>` en un **Docker rootless**, sin acceso a producción.
**Consecuencia:** el puerto **8090** es de alfa, y la pila de revisión de desarrollo pasó al **8091**: los dos Docker comparten el loopback del host y no pueden publicar el mismo puerto.

### g) Datos de PostgreSQL en el volumen Docker `postgres_data`

Los datos están en el volumen con nombre `postgres_data`, no en `<RUTA_PRODUCCION>`. **Aceptado para alfa.**
**Pendiente:** política de respaldos (`pg_dump` programado) antes de cargar datos reales importados de Cashew.

## Consecuencias

- Solo el servicio `web` publica puerto, y solo `127.0.0.1:8090`. `db` y `api` no publican nada; en desarrollo se publican con `infra/docker-compose.dev.yml`.
- Desplegar otra instancia exige otra carpeta, otro `.env`, otro puerto en loopback, otro proyecto de Compose (y con él otro volumen) y otro bloque en el Caddyfile.
- Pendientes: confirmar la IP real (d), estrategia de beta (e) y respaldos (g). Están listados en `docs/STATUS.md` §5.
