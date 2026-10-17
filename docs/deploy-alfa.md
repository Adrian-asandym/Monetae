# Despliegue de Monetae alfa en el VPS (runbook)

> **Repositorio público.** Solo marcadores: `<DOMINIO_ALFA>` (el valor real está en `.env.alfa.example`), `<DOMINIO_RAIZ>`, `<RUTA_PRODUCCION>`, `<USUARIO_ADMIN>` (con sudo), `<USUARIO_DEV>` (Docker rootless, agentes), `<IP_VPS>`. Nunca escribir aquí valores reales ni del `.env`.
> Decisiones y su porqué: `docs/decisions/009-alfa-deployment-vps.md`. Detalle de proxy e IP: `docs/ARCHITECTURE.md` §10.10.

## Estado (2026-10-16)

- **Alfa desplegada y funcionando** en `https://<DOMINIO_ALFA>`. Login verificado de extremo a extremo desde el navegador.
- Cadena: navegador → Cloudflare (proxy activo, «nube naranja») → Caddy en el host (80/443, TLS de Let's Encrypt) → `127.0.0.1:8090` → nginx del contenedor `web` (80 interno) → `api` (FastAPI/Uvicorn) → `db` (PostgreSQL 16).
- Solo `web` publica puerto en el host, y solo en loopback (`127.0.0.1:8090`). `db` y `api` no publican nada.
- Los tres servicios están `healthy` con `restart: unless-stopped`.
- Código desplegado: `main` (incluye T-701).
- Modo SSL/TLS de Cloudflare: **Full (strict)** (fijado por Adrian el 2026-10-16; ajuste de toda la zona `<DOMINIO_RAIZ>`).
- **Por confirmar:** la IP real del cliente (ver la nota del paso 9).

## Entorno

- **AlmaLinux 10**, SELinux en `enforcing`, **firewalld**. No es Ubuntu: no usar `apt` ni `ufw`.
- **Caddy** instalado con `dnf` desde el repositorio COPR oficial (`@caddy/caddy`), con `sudo` desde un usuario normal (no desde root). El servicio corre con su propio usuario `caddy`.
- **Producción:** Docker del sistema, controlado por `<USUARIO_ADMIN>`, en `<RUTA_PRODUCCION>`.
- **Desarrollo:** Docker rootless de `<USUARIO_DEV>`, sin acceso a producción. El 8090 es de alfa; la pila de revisión de desarrollo usa el **8091**.

## Despliegue inicial

### 1. Carpeta y clon

Crear `<RUTA_PRODUCCION>` y clonar el repositorio público por HTTPS, rama `main`:

```bash
sudo mkdir -p <RUTA_PRODUCCION>
sudo git clone --branch main <URL_HTTPS_DEL_REPO> <RUTA_PRODUCCION>   # la URL: git remote get-url origin
cd <RUTA_PRODUCCION>
```

Quién es el dueño de la carpeta en producción: **por confirmar** (no está documentado).

### 2. `.env` de producción

Copiar la plantilla. `.env.alfa.example` **no se edita ni lleva secretos**. El `.env` real queda fuera de git (`.gitignore`) y con permisos `600`:

```bash
sudo cp .env.alfa.example .env && sudo chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # MONETAE_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # POSTGRES_PASSWORD
```

- Reemplazar cada `REEMPLAZAR…` del `.env`.
- Generar **valores nuevos y aleatorios** para `MONETAE_SECRET_KEY` y `POSTGRES_PASSWORD`; no reutilizar valores del entorno de desarrollo.
- Usar `token_urlsafe`: solo produce `A–Z a–z 0–9 - _`, así que no rompe `MONETAE_DATABASE_URL`.
- La misma contraseña de `POSTGRES_PASSWORD` va dentro de `MONETAE_DATABASE_URL`.
- `MONETAE_ENVIRONMENT=prod` exige un secreto real (no `fake-…`, de 32 caracteres o más) y `MONETAE_COOKIE_SECURE=true`; si no, la API no arranca.
- `MONETAE_CORS_ORIGINS` lleva el origen público exacto: ya viene así en la plantilla.
- `MONETAE_WEB_PORT` es opcional: el compose usa 8090 por defecto.
- **`POSTGRES_PASSWORD` solo se aplica al crear el volumen por primera vez.** Cambiarla después en el `.env` no cambia la contraseña de la BD.

### 3. Web Flutter compilada

`apps/web/build/web` no está en git y nginx la monta desde el host. Root no tiene Flutter, así que se compila como `<USUARIO_DEV>`, **desde un clon limpio de `main`**:

```bash
# Como <USUARIO_DEV>
git clone --branch main <URL_HTTPS_DEL_REPO> <CLON_LIMPIO>
cd <CLON_LIMPIO>/apps/web && flutter build web --release
tar -C build/web -czf /tmp/monetae-web.tar.gz . && chmod a+r /tmp/monetae-web.tar.gz
```

Luego, como `<USUARIO_ADMIN>`, instalarla en producción:

```bash
cd <RUTA_PRODUCCION>
sudo mkdir -p apps/web/build/web
# Tras el primer arranque de Docker la carpeta puede quedar como propiedad de root:
# si se extrae sin sudo, cambiarle antes el dueño (sudo chown -R "$USER": apps/web/build/web).
sudo tar -xzf /tmp/monetae-web.tar.gz -C apps/web/build/web
sudo chmod -R a+rX apps/web/build/web
sudo rm -f /tmp/monetae-web.tar.gz   # es de otro usuario: /tmp tiene sticky bit, hace falta sudo
```

Sin la web compilada, o sin permiso de lectura, nginx responde **403** (`directory index of "/usr/share/nginx/html/" is forbidden`).

### 4. Arranque

```bash
sudo docker compose --env-file <RUTA_PRODUCCION>/.env -f infra/docker-compose.yml up -d --build
```

- Hace falta `sudo` si el usuario no está en el grupo `docker`.
- Un alias **no funciona detrás de `sudo`**: el `sudo` debe ir **dentro** del alias, por ejemplo `alias dcp='sudo docker compose --env-file <RUTA_PRODUCCION>/.env -f <RUTA_PRODUCCION>/infra/docker-compose.yml'`.
- La API ejecuta `alembic upgrade head` al arrancar.
- `--env-file` sirve para interpolar el compose (p. ej. `MONETAE_WEB_PORT`). Los contenedores leen el `.env` raíz por `env_file: ../.env`.

### 5. Verificación local

```bash
sudo docker compose --env-file <RUTA_PRODUCCION>/.env -f infra/docker-compose.yml ps   # db, api y web: healthy
curl -I http://127.0.0.1:8090          # 200
ss -tlnp | grep 8090                   # 127.0.0.1:8090, NUNCA 0.0.0.0:8090
```

### 6. Usuario de la app

Es una **cuenta de Monetae**, no un usuario de Linux. Los usuarios se crean solo por CLI en V1. La contraseña se pide por la terminal, nunca como argumento:

```bash
sudo docker compose --env-file <RUTA_PRODUCCION>/.env -f infra/docker-compose.yml exec api \
  python -m monetae.cli create-user --email <CORREO_DE_LA_CUENTA>
```

### 7. Firewall

Abrir solo `http` y `https`. **El 8090 nunca se abre**:

```bash
sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
```

### 8. DNS en Cloudflare

Registro **A** de `<DOMINIO_ALFA>` hacia `<IP_VPS>`.
- **Recomendado:** empezar en «DNS only» (nube gris), para que Caddy obtenga su certificado sin intermediarios.
- Pasar a «Proxied» (nube naranja) cuando ya cargue con HTTPS válido.
- El subdominio debe ser de **un solo nivel** (ADR-009 a).

### 9. Caddyfile

Bloque global con `trusted_proxies` = rangos de Cloudflare, y el sitio con `reverse_proxy` al 8090. Los rangos se **descargan al configurar** (`https://www.cloudflare.com/ips-v4` y `…/ips-v6`): no se copian en el repositorio porque cambian.

Configuración aplicada en el despliegue (según lo informado):

```caddyfile
{
	servers {
		trusted_proxies static <RANGOS_DE_CLOUDFLARE>
	}
}

<DOMINIO_ALFA> {
	reverse_proxy 127.0.0.1:8090
}
```

> **Nota (comprobada el 2026-10-16 con Caddy v2.11.7 en una prueba local):** con solo `trusted_proxies`, Caddy **conserva** el `X-Forwarded-For` de Cloudflare y **añade al final la IP del borde de Cloudflare** (`…, <ip-cliente>, <ip-cloudflare>`). nginx (T-701) toma la primera IP pública desde la derecha, es decir, **la de Cloudflare**, y el límite de intentos de login quedaría compartido.
> **Corrección recomendada (pendiente de aplicar y confirmar en producción):** que Caddy tome la IP de `CF-Connecting-IP` (Cloudflare la fija siempre; solo se acepta de sus rangos) y mande únicamente esa:
>
> ```caddyfile
> {
> 	servers {
> 		trusted_proxies static <RANGOS_DE_CLOUDFLARE>
> 		client_ip_headers CF-Connecting-IP
> 	}
> }
>
> <DOMINIO_ALFA> {
> 	reverse_proxy 127.0.0.1:8090 {
> 		header_up X-Forwarded-For {client_ip}
> 	}
> }
> ```
>
> En la misma prueba, con esta versión el backend recibió solo la IP del cliente. Para confirmarlo en producción: iniciar sesión y mirar la última fila de `login_attempts.ip`.

Validar y recargar:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy conserva `Host` y manda `X-Forwarded-Proto: https`: nginx lo reenvía a la API, y eso es lo que hace pasar la comprobación de Origin del CSRF.

### 10. Prueba final

- **Login desde el navegador** en `https://<DOMINIO_ALFA>`: valida a la vez las cookies `Secure`, el CSRF y las cabeceras en toda la cadena.
- `curl -I https://<DOMINIO_ALFA>` debe mostrar `server: cloudflare`.
- En Cloudflare, el modo SSL/TLS debe estar en **Full (strict)** (nunca «Flexible»).

## Cómo desplegar una actualización

```bash
cd <RUTA_PRODUCCION>
sudo git pull --ff-only origin main
# Solo si cambió el frontend (apps/web): recompilar como <USUARIO_DEV> desde un clon limpio de main
# y reinstalar apps/web/build/web (paso 3).
sudo docker compose --env-file <RUTA_PRODUCCION>/.env -f infra/docker-compose.yml up -d --build
```

- Las migraciones se aplican solas al arrancar la API.
- Después, repetir la verificación del paso 5 y un login.
- **Antes de actualizar con datos reales, sacar un respaldo:** la política de respaldos está **pendiente** (ADR-009 g).

## Problemas conocidos y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| **403 de CSRF** al iniciar sesión | `X-Forwarded-Proto` mal propagado: nginx informaba `http` y la API comparaba el Origin `https://…` contra `http://…`. | **Corregido en T-701** (`infra/web/default.conf` reenvía el esquema de Caddy; Uvicorn confía en la red de Compose). Si vuelve a pasar, revisar que Caddy no reescriba `X-Forwarded-Proto` y que `MONETAE_CORS_ORIGINS` tenga el origen exacto. |
| **403 de nginx** (`directory index … is forbidden`) | Falta `apps/web/build/web` o no tiene permisos de lectura. | Paso 3: instalar la web y `chmod -R a+rX`. |
| **502 en Caddy** | En AlmaLinux suele ser SELinux, que impide a Caddy conectar con el puerto. | **Si ocurre:** `sudo setsebool -P httpd_can_network_connect 1`. No consta que hiciera falta en este despliegue. |
| **Bucle de redirecciones** | Cloudflare en modo SSL «Flexible». | Usar **Full (strict)** (ADR-009 c). |
| **No se puede borrar un archivo en `/tmp`** | Es de otro usuario y `/tmp` tiene sticky bit. | Borrarlo con `sudo`. |
| La API no arranca: `Permission denied: 'pyproject.toml'` | Clon hecho con umask 077 e imagen anterior a T-701. | Corregido en T-701 (`services/api/Dockerfile`); reconstruir con `--build`. |
| La API no arranca en `prod` | Secreto `fake-…` o de menos de 32 caracteres, o `MONETAE_COOKIE_SECURE=false`. | Paso 2. |

## Cambios de código e infraestructura que lo hicieron posible (T-701)

| Archivo | Cambio |
|---|---|
| `infra/docker-compose.yml` | Solo `web` publica, en `127.0.0.1:${MONETAE_WEB_PORT:-8090}:80`. `db` y `api` sin puertos. `restart: unless-stopped`; healthchecks de `api` (`/api/v1/health`) y `web`; `:z` en los montajes del host (SELinux). `FORWARDED_ALLOW_IPS` fija en rangos privados. |
| `infra/docker-compose.dev.yml` (nuevo) | Solo para desarrollo y pruebas: publica la BD (`127.0.0.1:5433`) y la API (`127.0.0.1:8000`). No se usa en alfa. |
| `infra/web/default.conf` | Solo HTTP, `server_name _`, sin redirección a https. Toma la IP real de `X-Forwarded-For` solo desde pares de loopback o privados (`real_ip_recursive`); reenvía `X-Forwarded-Proto` de Caddy (o su propio esquema si falta), `$proxy_add_x_forwarded_for` y un `X-Forwarded-Port` coherente con el esquema. |
| `services/api/Dockerfile` | `chmod a+r`/`a+rX` del código copiado: la imagen arranca aunque el clon tenga umask 077. |
| `.env.example` | `MONETAE_WEB_PORT=8090`; comentarios sobre CORS/Origin y sobre el override de desarrollo. |
| `.env.alfa.example` (nuevo) | Plantilla de alfa sin secretos (`REEMPLAZAR…`), `prod`, cookies `Secure` y el origen público. |

**Por qué `FORWARDED_ALLOW_IPS` va fija en rangos privados y nunca en `"*"`:**
- Uvicorn solo usa `X-Forwarded-Proto`/`-For` si el par que conecta está en esa lista. Los rangos privados cubren a nginx en la red interna de Compose, y la API no publica puertos, así que nadie más llega a ella.
- Con `"*"`, Uvicorn toma la entrada **más a la izquierda** de `X-Forwarded-For`, que es la que controla el cliente: cualquiera podría falsear su IP y saltarse el límite de intentos de login.
- Con una lista, Uvicorn toma la primera IP no confiable desde la derecha.
