# T-102 — Contrato OpenAPI inicial (`docs/api/openapi.json`)

> Agente: **Codex** (modelo medio-alto: es diseño de contrato, con muchas reglas que cruzar).
> Depende de T-101 (`docs/ARCHITECTURE.md`). Es *contract-first*: el backend de la Fase 2 se implementa contra este archivo y luego lo regenera desde FastAPI.

## Objetivo

Escribir el contrato OpenAPI 3.1 de la API `/api/v1` de V1 como un único `docs/api/openapi.json`, coherente con el esquema de datos y las reglas de negocio, de modo que la UI (Fase 5) pueda generarse y probarse contra un mock sin esperar al backend.

## Leer primero

`AGENTS.md` (§6 API y dinero, §7), `docs/SPEC.md` v0.3 (§5, §7 ejemplos A–E, §8, §9, §10), `docs/ARCHITECTURE.md` (§4 convenciones, §5 esquema, §7 API) y las ADR 002, 003, 004, 006.

## Alcance

Recursos (ver `ARCHITECTURE.md` §7): `auth` (login, logout, logout-all, Google OIDC, sesiones), `users/me` (preferencias, PIN/bloqueo), `accounts`, `categories`, `people`, `tags`, `transactions` (CRUD, filtros RF-10, etiquetas, lote, borrado lógico y deshacer), `transfers`, `loans` (CRUD, `movements`, `balance`, `summary` por persona y moneda), `subscriptions` (CRUD, `archive`, `reactivate`, totales), `recurring-rules`, `budgets`, `goals`, `exchange-rates` (sugerencia), `notifications`, `reports/*` (SPEC §10), `imports` (dry-run y apply), `exports`, `health`.
Para recursos de la Fase 6 (`budgets`, `goals`, `notifications`, PIN/WebAuthn) basta un contrato **inicial** claro: lista de operaciones y esquemas principales.

## Reglas obligatorias del contrato

1. Dinero y tipos de cambio como **cadenas decimales** (`"200.00"`, `"3.800000"`) con `pattern`; nunca `number`. Moneda `^[A-Z]{3}$`. Identificadores `uuid`. Nombres en `snake_case` y en inglés.
2. Errores como `application/problem+json` (esquema `Problem` reutilizable) en 400, 401, 403, 404, 409, 422 donde aplique.
3. Paginación única: `limit` (1–200, por defecto 50) y `cursor`; respuesta `{items, next_cursor}`.
4. Seguridad: esquema de cookie de sesión; todo endpoint exige sesión salvo `POST /auth/login`, `GET /auth/google/callback` y `GET /health`. Peticiones que modifican datos documentan CSRF.
5. `Idempotency-Key` en la creación de transacciones y movimientos de préstamo.
6. **Préstamos:** no existe operación "liquidar". `settled`/`open` es solo un campo de lectura derivado. Cada movimiento con dinero indica su **propia** cuenta. Pagos incluyen `interest_part` y `principal_part` (propuestos por el servidor, editables antes de guardar; ADR-003). Un pago que excede el saldo responde 409/422 con un `Problem` que ofrece las salidas de RF-22 (ajuste o ingreso/gasto).
7. **Suscripciones:** `archive` (con motivo opcional) y `reactivate`; los archivados no aparecen por defecto en el listado ni en los totales.
8. **Aislamiento:** ningún recurso expone `user_id` ajeno; el contrato no incluye `user_id` en peticiones.
9. Cada operación con `operationId` único (`snake_case`), `tags` por recurso, `summary` y `description` útiles, y esquemas reutilizables en `components` (sin duplicar).
10. Ejemplos (`examples`) en préstamos que reproduzcan los **Ejemplos A–E de SPEC §7** (peticiones de movimientos y respuesta de `balance`).

## Archivos permitidos

- `docs/api/openapi.json` (nuevo)
- `docs/api/README.md` (cómo leer, validar y regenerar el contrato; convenciones)
- `scripts/check_openapi.py` (comprobaciones propias, solo biblioteca estándar)

No tocar `docs/ARCHITECTURE.md`, `docs/SPEC.md`, `AGENTS.md`, `scripts/generate_cashew_fixture.py`, `scripts/verify_cashew_fixture.py` ni nada fuera de lo anterior. Si el esquema de datos parece inconsistente o incompleto para el contrato, **no lo corrijas**: pregunta con `orca orchestration ask` o anótalo en `docs/api/README.md` bajo "Observaciones para el coordinador".

## Criterios de aceptación

1. `npx --yes @redocly/cli@latest lint docs/api/openapi.json` termina sin errores (herramienta efímera de npm; **no se añade dependencia al repo**). Si hay `uvx` disponible puede usarse además `uvx openapi-spec-validator`. Un aviso (warning) aceptable debe justificarse en el README.
2. `python3 -I scripts/check_openapi.py` termina con código 0 (**el `python3` del entorno es la 3.9**: escribe el script con solo biblioteca estándar y compatible con 3.9+, p. ej. `from __future__ import annotations`, sin `match`) y comprueba al menos: todos los `$ref` resuelven; no hay `type: number` en campos de dinero ni tasas; todas las operaciones tienen `operationId` único y respuesta de error `Problem`; toda operación tiene seguridad salvo la lista permitida; ningún path contiene "settle"/"liquidar"; los listados usan la paginación común; no hay `user_id` en cuerpos de petición.
3. Los 5 ejemplos A–E están presentes y, usando `ARCHITECTURE.md` §5.5, sus saldos de ejemplo son aritméticamente correctos (el script los recalcula).
4. `git diff --stat master-dev...HEAD` muestra solo archivos permitidos.
5. En `worker_done`: salida de ambos comandos, número de paths/operaciones/esquemas y lista de observaciones para el coordinador.

## Verificación

```bash
npx --yes @redocly/cli@latest lint docs/api/openapi.json
python3 -I scripts/check_openapi.py
git diff --stat master-dev...HEAD
```
