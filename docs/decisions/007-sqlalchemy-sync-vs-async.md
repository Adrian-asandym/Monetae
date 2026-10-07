# ADR-007 — SQLAlchemy síncrono o asíncrono

- **Estado:** ACEPTADO — opción A (decidido por Adrian el 2026-10-07)
- **Fecha:** 2026-10-07 · **Autor:** Claude
- **Relacionado:** AGENTS.md §3 (síncrono + psycopg 3 como valor por defecto), SPEC §12 (rendimiento)

## Contexto

FastAPI admite endpoints `def` (se ejecutan en un grupo de hilos) y `async def`. SQLAlchemy 2.0 ofrece sesiones síncronas y asíncronas. Hay que elegir antes de escribir repositorios, pruebas y migraciones, porque cambiarlo después toca todo el acceso a datos.

El volumen esperado es pequeño: un usuario en V1 y unas pocas cuentas familiares en V2; "decenas de miles de transacciones" con respuesta menor a 1 s (SPEC §12). El cuello de botella son las **consultas agregadas en PostgreSQL** (índices por `user_id, occurred_at`), no la concurrencia de conexiones.

## Opciones

### A (recomendada) — Síncrono con psycopg 3
- Endpoints `def`, sesión `Session`, repositorios síncronos; Alembic y las pruebas con `pytest` sin bucles de eventos.
- **Pros:** código más simple y legible; sin trampas de la carga perezosa en asíncrono (`MissingGreenlet`); pruebas más sencillas; encaja con `mypy --strict`; el dominio puro no cambia en ningún caso.
- **Contras:** cada petición ocupa un hilo mientras espera a la BD (el grupo por defecto da margen de sobra para esta escala).

### B — Asíncrono (`AsyncSession` + driver asíncrono)
- **Pros:** más peticiones simultáneas por proceso; estilo uniforme si V2 incorpora mucha E/S externa.
- **Contras:** más complejidad accidental (carga perezosa, sesiones y transacciones asíncronas, pruebas asíncronas) sin ganancia medible a esta escala; los servicios de V2 (bot, ML) son procesos separados y no obligan a que la API lo sea.

## Recomendación

**Opción A.** Para evitar un callejón sin salida: el acceso a datos va detrás de repositorios y el dominio no conoce SQLAlchemy (AGENTS.md §4), de modo que pasar a asíncrono sería acotado si algún día se mide una necesidad real.

## Consecuencias si se acepta A

- Reglas para los workers: endpoints de la API con `def`; prohibido bloquear dentro de `async def`; ajustar el tamaño del *pool* de conexiones.
- Sin dependencias asíncronas (`asyncpg`, `pytest-asyncio`) en V1.

## Decisión de Adrian

**Opción A — SQLAlchemy síncrono con psycopg 3** (2026-10-07).
