# T-404 — Importador de Cashew: transferencias con emparejado unidireccional y motivos

> **ESTADO: ACEPTADA e integrada en `master-dev` el 2026-10-08** (merge `e9394fb`; Run `run_f5e95406186a`). Los seguimientos T-402b/T-403b/T-401b y los hallazgos del `--dry-run` real quedan en `docs/importers/cashew*.md` y `docs/STATUS.md`.
> Agente: **Codex**, modelo `gpt-6.1-sol` esfuerzo `medium` (corrección acotada en el emparejado; el cuidado está en no emparejar mal).
> Depende de: T-401, T-402 y T-403 integradas en `master-dev`. No corre en paralelo con otra tarea.

## Contexto (hallazgo)

El importador (T-401) solo convierte en transferencia un par de filas cuando **ambas** se apuntan entre sí con `paired_transaction_fk` (reciprocidad). La fixture sintética y `docs/importers/cashew.md` lo daban por cierto. **Con un respaldo real no es así**: Cashew guarda el emparejado en **un solo sentido** (una pata apunta a la otra; la otra no apunta de vuelta). Resultado en el `--dry-run` real: ninguna transferencia se emparejó y todas se importaron como ingresos y gastos ordinarios (el saldo cuadra, pero las estadísticas contarían cada transferencia como un gasto más un ingreso). Además, parte de los pares es entre monedas distintas. No se incluyen cifras del respaldo real en este repositorio público.

## Objetivo

1. Aceptar el emparejado **unidireccional** (y el recíproco, que ya funciona) sin emparejar nunca por parecido.
2. Registrar **por qué** una fila queda sin emparejar con un código de motivo, para poder explicarlo y medirlo sin mostrar filas.

## Reglas (decididas)

1. **Par:** `(a, b)` con `a.paired_pk == b.pk`. Se acepta si `b.paired_pk` es `NULL` **o** apunta de vuelta a `a` (recíproco). Un par se cuenta una sola vez.
2. **Condiciones** (las de hoy, menos la reciprocidad): ambas filas ordinarias (`type` nulo o 0, sin `objective_loan_fk`, no omitidas), `paid = 1` las dos, cuentas distintas, **misma moneda**, importes opuestos (suma 0,00).
3. **Sin ambigüedad:** si otra fila distinta de `a` también apunta a `b`, o `b.paired_pk` apunta a una tercera fila, **ningún par se forma** con `b` y las filas implicadas quedan ordinarias con motivo `ambiguous_counterpart`.
4. **Entre monedas distintas:** sigue **sin** emparejarse (importar como ordinarias), motivo `currency_mismatch`. Queda anotado en `docs/importers/cashew.md` como mejora futura; no inventes una tasa.
5. **Motivo en cada `unpaired_transfer`:** añade `reason` al payload con uno de `counterpart_missing`, `counterpart_not_ordinary` (préstamo, recurrente, omitida o `type` ≠ 0), `same_wallet`, `currency_mismatch`, `amount_mismatch`, `unpaid`, `ambiguous_counterpart`. Un solo código por fila (el primero que aplique en ese orden).
6. **Idempotencia y solo inserción:** igual que hoy (identidad `cashew:sqlite:<pk>` por pata; si solo existe una pata ya importada, no se repara: `partially_imported`).
7. **El reporte agrega** los motivos: en `steps` o `counts` (a tu criterio, documentado) un conteo por `reason` de los `unpaired_transfer`, para que el resumen pueda mostrarse **sin payloads**.

## Archivos permitidos

```
services/api/src/monetae/importers/cashew/mapping.py        # emparejado y motivos
services/api/src/monetae/importers/cashew/runner.py         # SOLO si hace falta para el conteo por motivo
services/api/src/monetae/importers/cashew/report.py         # SOLO el campo del conteo por motivo
services/api/tests/importers/test_transfers_pairing.py      # nuevo
services/api/tests/importers/test_reader_mapping.py         # SOLO las aserciones de emparejado que cambien
services/api/tests/importers/test_runner.py                 # SOLO las aserciones de transferencias que cambien
docs/importers/cashew.md                                    # regla de emparejado y motivos
```

No tocar `domain/`, `services/`, `db/`, migraciones, `loans.py`, `subscriptions.py`, `cli.py`, `openapi.json` ni los fixtures. Sin dependencias nuevas.

## Pruebas obligatorias (PostgreSQL real; copias temporales de la fixture, nunca el original)

- Fixture H (recíproca) sigue dando una transferencia de dos patas.
- **Unidireccional:** poner a `NULL` el `paired_transaction_fk` de una de las dos patas de H ⇒ sigue siendo **una** transferencia de dos patas; saldos `unexplained = 0.00`.
- **Ambigua:** una tercera fila que también apunte a la misma pata ⇒ nada se empareja, motivo `ambiguous_counterpart`, el dinero se importa.
- **Un motivo por caso:** contraparte inexistente, contraparte préstamo/recurrente, misma cuenta, monedas distintas (H con una cuenta USD), importes distintos, `paid = 0`.
- **Idempotencia** (segunda importación: 0 creados, 0 modificados) y `--dry-run` con transferencias unidireccionales.
- **Aislamiento entre dos usuarios.**
- Ninguna salida estándar contiene títulos ni notas.

## Criterios de aceptación (con salidas en `worker_done`)

```bash
# BD PROPIA de esta tarea (no hay otro worker, pero respeta el proyecto y el puerto):
export MONETAE_DB_PORT=5438 COMPOSE_PROJECT_NAME=monetae-t404
cp .env.example .env && docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5438/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q
uv run alembic upgrade head && uv run alembic check
cd ../.. && docker compose -f infra/docker-compose.yml down -v && rm -f .env
grep -rn "type: ignore" services/api/src || true
git diff --stat master-dev...HEAD         # solo archivos permitidos
```

## Reglas

Commits pequeños en inglés (`fix(importer):`, `test(importer):`). Actualiza tu rama con `master-dev` antes de reportar. Sin `Any` ni `# type: ignore` sin razón escrita. **No inventes reglas de negocio**: ante un caso que esta spec no cubra, `orca orchestration ask`. Una fila anómala nunca aborta la importación. Reporta `worker_done` una sola vez.
