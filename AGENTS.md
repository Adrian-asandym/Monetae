# AGENTS.md — Contrato para todos los agentes de Monetae

> **PRIMERO: lee `docs/STATUS.md`** (estado actual, decisiones, plan y cómo retomar). Es lo primero que debe leer cualquier agente, antes que el resto de este archivo.

Este archivo lo leen **todos** los agentes (Claude, Codex, Command Code, Gemini/Antigravity). Si algo aquí contradice una instrucción puntual de una tarea, **gana este archivo**, salvo que Adrian diga lo contrario por escrito. La fuente de verdad funcional es `docs/SPEC.md`.

---

## 1. Qué es Monetae

App web **personal** de ingresos y gastos, inspirada en [Cashew](https://github.com/jameskokoska/Cashew) (Flutter, GPL-3.0), con su misma UI y gráficos, pero corrigiendo cinco problemas de flujo de Adrian:

| ID | Problema | Resumen de la solución |
|----|----------|------------------------|
| P1 | Un préstamo pagado desaparece de las transacciones | Los préstamos son un **libro mayor** (`loans` + `loan_movements`); nada se borra |
| P2 | El interés (p. ej. 5 %) no salda la deuda sin botón "liquidar" | Saldo y estado **calculados**; no existe botón "liquidar" |
| P3 | Préstamo pagado por otra cuenta acredita la cuenta original | Cada movimiento tiene su **propia cuenta** |
| P4 | Suscripciones no se pueden archivar | **Archivado reversible** (oculta de vista y total, conserva transacciones) |
| P5 | Respaldos en Google Drive fallan | Export/import propio y backups del servidor (sin Drive) |

Versiones: **V1** local (web, sin bot) → hito de despliegue en VPS Contabo → **V2** bot Telegram + categorización + cuentas familiares → **V3** asistente (Hermes + herramientas MCP) → **V4** app Android con sincronización. Detalle en `docs/SPEC.md`.

---

## 2. Idioma

- **Documentación y comunicación con Adrian: español.**
- **Código, identificadores, nombres de tablas/columnas, campos de API, mensajes de commit y ramas: inglés.**
- **UI:** i18n con `es` (principal) y `en`. Ningún texto visible hardcodeado en código.

---

## 3. Stack (decidido)

| Capa | Tecnología |
|------|------------|
| Lenguaje backend | **Python 3.12+** (NO Java) |
| Gestor de paquetes | `uv` |
| API | FastAPI, REST `/api/v1`, OpenAPI como contrato |
| Validación / modelos | **Pydantic v2 en modo estricto** |
| ORM | SQLAlchemy 2.0 tipado (estilo `Mapped[...]`), **síncrono** + psycopg 3 (ADR-007 puede cambiarlo) |
| Migraciones | Alembic |
| BD | PostgreSQL |
| Calidad | `ruff` (lint+format), `mypy --strict`, `pytest` |
| Dinero | `decimal.Decimal` y value object `Money` (nunca `float`) |
| UI | Flutter web, **UI propia** que reutiliza y desacopla widgets de Cashew (**ADR-001 aceptado, opción A**; no es un fork de la app completa) |
| Infra local | Docker Compose |
| ML (V2, reservado) | scikit-learn (TF-IDF + regresión logística) en `services/ml` |

No agregues dependencias nuevas sin justificarlo en la descripción de la tarea o en un ADR.

---

## 4. Estructura del repositorio

```
monetae/
├── AGENTS.md              # este archivo
├── CLAUDE.md              # instrucciones del coordinador (Claude)
├── img/                   # Usa estos íconos como representación de Monetae (en lugar de los íconos de Cashew)
├── docs/
│   ├── SPEC.md            # especificación funcional (fuente de verdad)
│   ├── ARCHITECTURE.md    # arquitectura (Fase 1)
│   ├── cashew-analysis.md # análisis del código de Cashew (Fase 0)
│   ├── decisions/         # ADRs: NNN-titulo.md
│   ├── tasks/             # T-XXX.md (Plan B sin orquestación)
│   └── api/openapi.json   # contrato exportado
├── reference/             # GIT-IGNORED
│   ├── cashew/            # SOLO LECTURA — copia de Cashew para estudio
│   └── backups/           # respaldos reales de Adrian. Fuente del importador: el SQLite (.sql); el .csv solo es rescate. SIEMPRE trabajar sobre una copia
├── apps/
│   └── web/               # UI Flutter propia (ADR-001-A); los widgets de Cashew (`reference/Cashew/budget/`) se copian desacoplados, con aviso GPL
├── services/
│   ├── api/               # FastAPI
│   │   └── src/monetae/
│   │       ├── domain/    # reglas puras y tipadas (sin I/O, sin FastAPI, sin SQLAlchemy)
│   │       ├── api/       # routers, schemas Pydantic, dependencias
│   │       ├── db/        # modelos SQLAlchemy, repositorios, migraciones
│   │       ├── importers/ # importador de Cashew
│   │       └── reports/   # consultas agregadas para gráficos
│   ├── ml/                # RESERVADO V2
│   └── bot/               # RESERVADO V2
├── infra/                 # docker-compose, Dockerfiles
└── scripts/
```

Regla de dependencias: `domain` **no importa** de `api`, `db` ni `importers`. `api` y `db` dependen de `domain`, nunca al revés.

---

## 5. Comandos

> Los marcados con (*) se crean en la fase indicada; antes de eso no existen.

**Backend (`services/api`)**
```bash
uv sync                          # instalar dependencias
uv run pytest                    # tests
uv run ruff check .              # lint
uv run ruff format .             # formato
uv run mypy                      # tipado estricto (config en pyproject.toml)
uv run alembic upgrade head      # migraciones (*Fase 2)
uv run uvicorn monetae.api.main:app --reload   # (*Fase 2)
```

**Stack local** (*Fase 2)
```bash
docker compose -f infra/docker-compose.yml up -d
```

**UI (`apps/web`)** (*Fase 5)
```bash
flutter pub get
flutter run -d chrome
flutter build web
dart analyze
flutter test
```

**Antes de reportar una tarea como terminada** debe pasar, en lo que hayas tocado: `ruff check`, `ruff format --check`, `mypy`, `pytest` (backend) o `dart analyze` + `flutter test` (UI).

---

## 6. Reglas de código (backend)

1. **Tipado fuerte obligatorio:** `mypy --strict` limpio. Prohibido `Any` implícito o explícito salvo en bordes justificados con comentario. Prohibido `# type: ignore` sin razón escrita.
2. **Pydantic v2 estricto** en todos los bordes (requests, responses, importador, config). Sin coerción silenciosa.
3. **Dinero:**
   - Siempre `Decimal`, nunca `float`.
   - `Money(amount, currency)` como value object; **prohibido sumar o comparar monedas distintas** (lanza error de dominio).
   - Redondeo `ROUND_HALF_UP` a 2 decimales; tipos de cambio con 6 decimales.
   - Moneda base: PEN. Secundaria: USD. Cada transacción guarda su moneda y el `fx_rate_to_base` vigente al registrarla.
4. **Identificadores:** PK `UUID`. Todas las tablas de negocio llevan `user_id`, `created_at`, `updated_at` y borrado lógico (`deleted_at`).
5. **Tiempo:** `timestamptz` en UTC en BD; zona de presentación `America/Lima`.
6. **API:** JSON en `snake_case`; errores como `application/problem+json`; paginación consistente; versionado `/api/v1`; todo endpoint con `response_model`.
7. **Dominio puro:** las reglas de préstamos, suscripciones y presupuestos viven en `domain/` como funciones/clases sin I/O, con tests unitarios exhaustivos.
8. **Saldos y estados se calculan**, no se almacenan como verdad (se puede cachear, pero la fuente es el libro mayor).
9. **Multiusuario desde el día 1:** toda consulta filtra por `user_id`. Debe existir un test con dos usuarios que verifique aislamiento.
10. Funciones pequeñas, nombres explícitos, sin lógica de negocio en routers.

### Reglas de negocio que NO se deben romper (resumen de SPEC §7–§8)

- El **capital** prestado/cobrado **no** cuenta como gasto ni ingreso; el **interés** sí (categoría de sistema "Intereses", base de caja por defecto).
- Un préstamo **nunca desaparece**: al saldarse cambia a estado `settled` y sigue visible/filtrable.
- Los préstamos **no tienen cuotas fijas**: pagos parciales variables o pago único.
- Cada pago puede salir/entrar por una **cuenta distinta** a la del desembolso original.
- **No hay botón "liquidar"**: `settled` ⇔ saldo pendiente = 0.
- Suscripción archivada: fuera de la vista y del total mensual, transacciones intactas, reactivable.

---

## 7. Reglas de código (UI Flutter)

- Mantener la apariencia y los gráficos de Cashew; cambiar solo lo necesario para P1–P5 y las funciones nuevas.
- La UI **no contiene reglas de negocio**: consume la API (`/api/v1`). Cliente generado o tipado desde `docs/api/openapi.json`.
- Respetar GPL-3.0: conservar avisos de licencia y atribución; **no usar el nombre "Cashew" ni su ícono** como marca de Monetae.
- `dart analyze` sin advertencias; textos vía i18n.

---

## 8. Tests

- Cobertura fuerte en `domain/` (préstamos, suscripciones, multimoneda, presupuestos).
- Los ejemplos A–E de `docs/SPEC.md` §7 y los criterios de §8 se convierten en tests literales.
- **Solo datos sintéticos** en fixtures. Nunca copies datos reales de Adrian a tests o commits.
- El importador de Cashew se prueba con un respaldo sintético que reproduce la estructura, no con el real.
- Un bug corregido = un test que lo reproduce.

---

## 9. Seguridad y privacidad

- Datos financieros reales de Adrian: **jamás** en git, logs, issues ni mensajes de commit. `reference/backups/` está en `.gitignore`.
- **Respaldos reales: siempre sobre una copia** (en una carpeta temporal fuera del repo), nunca sobre el original; SQLite abierto en solo lectura. Solo se inspeccionan nombres de tablas y columnas, jamás filas ni valores, salvo que Adrian lo pida expresamente.
- Secretos solo por variables de entorno / `.env` ignorado; mantener `.env.example` sin valores reales.
- Contraseñas con hash moderno (argon2/bcrypt); sesiones/tokens según ADR-002.
- No registrar en logs montos asociados a usuarios identificables más allá de lo estrictamente necesario.
- Entradas siempre validadas; consultas parametrizadas (nada de SQL por concatenación).

---

## 10. Git, worktrees y commits

- **Modelo de ramas** (para que los agentes no se pisen):
  - `main`: estable. Solo Adrian hace merge aquí (tras decision gate).
  - `master-dev`: rama de integración, la gestiona **Claude**. Los workers nunca hacen commit, merge ni push directo en ella.
  - **Una tarea = una rama = un worktree**, creada desde `master-dev` con el prefijo del agente: `codex/T-004-loan-ledger`, `agy/T-002-cashew-analysis`, `cmdc/T-010-loans-screen`, `claude/T-001-adr-ui`. Prefijos: `codex`, `agy` (Antigravity/Gemini), `cmdc` (Command Code), `claude`.
  - Un mismo agente con dos tareas en paralelo usa dos ramas/worktrees distintos; nunca comparten carpeta.
  - Git no permite la misma rama en dos worktrees: si tu rama ya está ocupada, no la fuerces, avisa.
  - Tareas en paralelo deben tener **archivos permitidos disjuntos**. Archivos de alto conflicto (`pyproject.toml`, `uv.lock`, `docs/api/openapi.json`, migraciones de Alembic) tienen un solo dueño a la vez; las migraciones se crean de una en una para no generar múltiples heads.
  - Antes de reportar `worker_done`, actualiza tu rama con `master-dev` (rebase o merge) y resuelve conflictos en TU rama.
- Tipos de cambio en el mensaje de commit: `feat`, `fix`, `docs`, `test`, `chore`.
- Commits pequeños, en inglés, estilo Conventional Commits (`feat(loans): compute outstanding balance from ledger`).
- **No hagas merge a `main`**: lo decide el coordinador con aprobación de Adrian (decision gate).
- **Prohibido:** `git push --force`, `git reset --hard` sobre trabajo ajeno, reescribir historial compartido, borrar ramas que no creaste.
- No toques archivos fuera del alcance de tu tarea. Si crees que hace falta, pregunta (ver §11).

---

## 11. Contrato del worker (orquestación Orca)

Si recibes una tarea de la orquestación de Orca:

1. Lee este archivo, `docs/SPEC.md` y la descripción de tu tarea completa **antes** de escribir código.
2. Trabaja **solo** dentro del alcance y criterios de aceptación de la tarea.
3. Si tienes una duda que **bloquea** el trabajo, usa `orca orchestration ask` (no adivines decisiones de diseño, no inventes reglas de negocio).
4. En trabajos largos envía heartbeat periódico.
5. Al terminar, ejecuta las verificaciones del §5 y corrige lo que falle.
6. Reporta con **`worker_done` exactamente una vez**, incluyendo `taskId` y `dispatchId`, y `--outcome succeeded` o `--outcome failed`. En el resumen incluye: qué cambiaste, archivos principales, comandos de verificación ejecutados y su resultado, y cualquier decisión pendiente.
7. Nunca uses `orchestration reset` ni el comando retirado `orchestration run`.
8. Si fallas o te bloqueas sin salida, reporta `failed` con la causa real; no maquilles un éxito.

**Plan B (sin orquestación):** Adrian pega manualmente el contenido de `docs/tasks/T-XXX.md` en tu panel. Aplica las mismas reglas y deja el resumen final en la propia respuesta.

---

## 12. Roles por agente (sugerido)

| Agente | Rol principal |
|--------|---------------|
| **Claude** | Coordinación, especificaciones, ADRs, revisión de diffs |
| **Codex** | Backend, dominio, importador, API, migraciones |
| **Command Code** | UI Flutter |
| **Gemini / Antigravity** | Análisis de Cashew (Fase 0), tests, QA, documentación |

El coordinador puede reasignar según disponibilidad y cuota.

---

## 13. Lo que NO debes hacer

- No uses Java ni otro lenguaje para el backend.
- No uses `float` para dinero.
- No metas datos reales ni respaldos en el repositorio.
- No modifiques `reference/cashew/` (solo lectura).
- No copies código de Cashew al backend; la UI derivada sí debe respetar GPL-3.0.
- No añadas un botón o flujo de "liquidar" préstamos.
- No borres préstamos ni transacciones físicamente (borrado lógico).
- No implementes funciones de V2/V3/V4 (bot, ML, Hermes, Android) en V1; solo deja los puntos de extensión que indica `docs/SPEC.md` §13.
- No tomes decisiones abiertas (ADR-002…007; el ADR-001 ya está aceptado) por tu cuenta: pregunta.
- No hagas merge a `main` ni push forzado.