# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-10, ~22:45 (America/Lima)** — cierre de sesión («Continuaremos en otro momento») |
| **`origin`** | `origin/main` = `origin/master-dev` = **`8b8688e`** (hasta T-508, SPEC v0.5; G6). |
| **`main`** | `8b8688e`. |
| **`master-dev`** | **`d835d1b` (skill `cashew-form-transaccion`) + el commit de este cierre (`git log -1`)**, por delante de `main`: T-509, T-510, T-512, T-513, T-514 (UI), T-601, T-602, T-603 (API; migraciones `0009`–`0011`), SPEC v0.6, contrato 0.6.0, skill `cashew-inicio-ui`, `scripts/seed_review_data.py`. **Sin publicar.** |
| **Rama de tarea** | **`claude/T-515-form-transaccion` = `1f39158`** (worktree `../Monetae-claude-T-515-form-transaccion`): pieza 1 del formulario (`83a3e62`) + spec T-515 (`1f39158`). **Sin fusionar** en `master-dev` (la tarea sigue abierta). |
| **Gate abierto** | **G7 `gate_ecde8d19a53a`** (publicar en `main`): propuesto; Adrian eligió **B (esperar a su revisión visual)**. Su texto menciona T-509/T-510/T-601/T-602, pero al resolverlo se publicará **todo `master-dev`** tras repetir la auditoría. |
| **SPEC / ARCHITECTURE / contrato** | SPEC **v0.6** · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.6.0** (89 paths, 131 operaciones). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–4. **Fase 5:** T-501…T-510 (UI base, gráficas, cliente, formulario de transacción), T-512/T-513/T-514 (Inicio fiel a Cashew según la skill). **Adelantado de la Fase 6:** API de presupuestos (T-601), metas (T-602) y `display_name` (T-603). |
| 🔄 **En curso** | **T-515** formulario de transacción fiel a Cashew (skill `cashew-form-transaccion`, capturas 11–19): pieza 1 hecha y verificada; piezas 2–6 pendientes de delegar a Codex. Ningún worker vivo. |
| ⏳ **Pendiente** | **T-515 piezas 2–6** · **permiso SSH de Orca** (O1) · **Revisión visual de Inicio por Adrian** (R2) · **G7** · **F1** (formularios crear objetivo/presupuesto, detalle de categorías, reordenar Inicio) · **D12** (historial de presupuestos/metas = transacciones filtradas) · resto de la Fase 5 (pestañas Transacciones/Presupuestos/Más completas) · Fase 6 (íconos SVG API, adjuntos, notificaciones, Google, PIN/WebAuthn, proveedor de tipo de cambio) · Fase 7 · importación real (D9-A) · VPS → V2–V4. |

Backend: **58 de 89 rutas** aprox., 11 migraciones (cabeza **`0011`**), **1164 pruebas**. UI `apps/web`: **217 pruebas** (goldens claro/oscuro con DM Sans). Detalle en el Anexo A (sin actualizar para T-601–T-603).

## 3. Trabajo hecho en esta sesión (2026-10-10, noche — 2.ª sesión)

- **Reanudación:** STATUS coincidía con git y Orca. Docker no respondía (integración WSL); Adrian lo reactivó y liberó disco (borró los worktrees T-513/T-514 y cachés). Pila de revisión levantada y login verificado por nginx.
- **T-515 (formulario de transacción fiel a Cashew):** plan aprobado (plan mode). Adrian añadió la skill `.claude/skills/cashew-form-transaccion` (versionada en `d835d1b`) y las capturas `reference/cashew-inicio-ui/11–19.png` (coinciden con la tabla de la skill). La skill `cashew-ui` que citaba **no existe**: se usa `cashew-inicio-ui`.
  - **Pieza 1 (formulario base, capturas 12/13)** en `83a3e62`: pestañas Gasto/Ingreso/Transferir, cabecera de importe, caja de fecha «Hoy · HH : MM», 5 filas de chips, título/notas rellenos, adjunto, píldora «Más opciones», barra inferior; tokens `TransactionFormColors`/`TransactionFormTokens` medidos sobre las capturas. Verificada: `flutter analyze` limpio, **217 pruebas** verdes, goldens revisados, captura en `localhost:8080` a 400×642 (oscuro) fiel a 12/13. **La escribió el coordinador** antes de que Adrian recordara que el código se delega (ver §4).
  - **Spec de las piezas 2–6** en `docs/tasks/T-515-ui-transaction-form.md` (rama de la tarea).
- **Orca bloqueado:** `run-use`, `task-create`, `worker-list` fallan con «not available to the orca CLI on SSH host `ssh-1790983388010-x1ugta`» (`orca status` sí funciona). No se creó ninguna tarea ni se lanzó ningún worker. Un intento de lanzar `codex exec` directamente fue **rechazado por Adrian**.

## 3b. Trabajo de la sesión anterior (2026-10-10, día)

- **Reanudación:** STATUS coincidía con git y Orca; Docker volvió tras reactivarlo Adrian. **G6 publicado** (`8b8688e`) tras auditoría.
- **Integrado en `master-dev`** (cada tarea verificada por el coordinador: pruebas completas, goldens, sondas HTTP reales por nginx):
  - **T-509** Inicio + barra de 4 botones · **T-510** formulario de transacción (decimales exactos, idempotencia, tasas con 6 decimales).
  - **T-601** API de presupuestos (`0009`, ciclos anclados, gasto = clasificación de reportes) · **T-602** API de metas (`0010`, progreso con signo como Cashew, préstamos rechazados) · **T-603** `display_name` (`0011`; el coordinador corrigió la limpieza de su prueba de servidor, que rompía `test_ip_limit_and_purge`).
  - **T-512** Inicio fiel a Cashew con la skill (Antigravity Pro; dos entregas fallidas: goldens sin texto, afirmó pruebas verdes con 12 fallos; el coordinador versionó los goldens) · **T-513** 4 detalles (Codex) · **T-514** ajustes v2 de Adrian (tarjeta «añadir», circular de ingresos, eje Y de 4 etiquetas, píldora «Editar»).
- **Docs:** SPEC v0.6 + contrato 0.6.0 (`display_name`, RF-50); skill `cashew-inicio-ui` versionada y actualizada con v2; `docs/api/README.md` (claves de `home_widgets`, 0.6.0); specs T-509…T-514, T-601…T-603; `scripts/seed_review_data.py` (datos sintéticos por la API).
- **Workers:** Codex resolvió todas sus tareas; las preguntas atraparon dos errores de spec del coordinador (tasa con 6 decimales; caso «sin convertir»). **Antigravity suspendido** a pedido de Adrian (lento y poco fiable en T-512).

## 4. Decisiones tomadas por Adrian

| Fecha | Decisión |
|---|---|
| 2026-10-10 (noche, 2.ª) | **Cierre** («Continuaremos en otro momento») tras rechazar el lanzamiento de `codex exec`. |
| 2026-10-10 (noche, 2.ª) | Adrian recuerda: **el código lo escribe un agente (Codex de preferencia); el coordinador solo planifica y monitorea**, aunque la petición diga «implementa» (guardado en memoria). |
| 2026-10-10 (noche, 2.ª) | **Plan T-515 aprobado**: solo presentación; una pieza a la vez (base 12/13 → título 11 → categorías 15 → importe 16 → Más opciones 14 → modal de tipos 17–19), verificar cada una en `localhost:8080` a 400×642 y un commit por pieza; Suscripción, Repetitivo, Prestar, Deuda, Transferir, adjunto, calculadora, «Incluir importe» y «Excluir del presupuesto» quedan como diseño con TODO; selección de presupuesto/objetivo solo visual; Predeterminado/Próximamente = estado `posted`/`scheduled` (vía fecha). |
| 2026-10-10 (noche, 2.ª) | Reanudación: Adrian borró los worktrees T-513/T-514 y liberó disco; pidió levantar la pila para revisar el diseño. F1/D12/G7 siguen sin respuesta. |
| 2026-10-10 (noche) | **Cierre de sesión** («Continuamos en otro momento»). Pendientes: revisión visual (R2), G7, F1, D12. Adrian ya borró la mayoría de los worktrees integrados. |
| 2026-10-10 (noche) | Adrian pide **4 ajustes v2 de Inicio** (tarjeta «añadir» en carruseles, 2.ª página del circular = ingresos, eje Y con 4 etiquetas, ⋮ → botón «Editar») con capturas `reference/cashew-inicio-ui/v2-*.png`, y **actualizar la skill** al terminar. Lanzada **T-514** (Codex `gpt-6.1-sol` high). El coordinador actualizará la skill al integrar. |
| 2026-10-10 (noche) | Por la demora de Antigravity en T-512, Adrian pide **suspenderlo y pasar la UI a Codex** (esfuerzo según la tarea). T-513 (4 detalles de Inicio) lanzada con Codex `gpt-6.1-sol` high. La terminal de Antigravity no se puede liberar desde Orca (externa): Adrian la cierra. |
| 2026-10-10 (noche) | «**OK**» al plan de T-512 (9 componentes, valores calibrados del código de Cashew; corrección del coordinador: tarjeta de cuenta = `widgets/walletEntry.dart`). |
| 2026-10-10 (noche) | **S1:** capturas en `reference/cashew-inicio-ui/1.png…6.png` (ignoradas por git). **S2:** la skill manda sobre preferencias anteriores de UI. **S3-A:** `display_name` (contrato 0.6.0, SPEC v0.6, RF-50). **S4:** hacer en la UI los cálculos «X/día para N días» que muestra la skill (solo presentación). **S5-A:** DM Sans. **S6:** Antigravity Pro (Adrian da permiso y fija el modelo). D12 sigue sin confirmar. |
| 2026-10-10 (noche) | Adrian añade la skill **`.claude/skills/cashew-inicio-ui/SKILL.md`** (fidelidad de Inicio con Cashew; versionada en `11c82bf`) y pide seguirla: Antigravity (modelo Pro) si el esfuerzo es alto, Codex si no; avisar antes de usar Antigravity. La skill **sustituye** dos preferencias anteriores: fondo oscuro **neutro** (antes azul) y formato de montos **«100,46 S/.»** (antes «S/ 1,234.50»). |
| 2026-10-10 (tarde) | **G7-B:** no publicar aún; esperar a su revisión visual de Inicio (el gate `gate_ecde8d19a53a` queda abierto). **D12:** prefiere **no** crear un historial aparte: reutilizar la lista de transacciones **filtrada** por presupuesto o meta. El coordinador reformula D12 en §5 y pide confirmación. Pregunta si la UI ya está lo bastante cerca de producción para dar indicaciones sobre Inicio. |
| 2026-10-10 | Reanudación: STATUS contrastado con git y Orca (coincide); Docker volvió a estar accesible tras reactivarlo Adrian. «**OK para continuar**» al plan propuesto = **G6-A** (publicar) y **P1-A** (T-509 Inicio ∥ T-601 API presupuestos → T-602 API metas → T-510 formulario de transacción). |
| 2026-10-09 (noche) | **Cierre de sesión** («Continuaremos en otro momento»). Adrian **eliminó los worktrees de Codex** de la Fase 5. G6 queda como propuesta sin resolver. |
| 2026-10-09 (noche) | «**OK**» a **G5** (publicar T-504/T-506) y **T-507**. El diseño «sigue bien, como prueba». Adrian describe la **disposición de Cashew** que quiere (detalle en `docs/ui/home-layout.md`): barra inferior de 4 botones (Inicio, Transacciones, Presupuestos, Más) y, en Inicio, de arriba abajo: saludo, cuentas (nombre, saldo, nº de transacciones, color y **cuenta por defecto elegible desde Inicio**, resaltada con su color), objetivos, presupuestos (color y barra), circular de gastos con leyenda de las 3 categorías con más gasto y **deslizar a la izquierda** para ingresos, gráfico de líneas que **sube con ingresos y baja con gastos**, las **25 últimas transacciones** y un botón cuadrado «+» destacado para crear transacción. Esperará a que estén todas las integraciones para revisar posiciones y fidelidad. |
| 2026-10-09 (noche) | Revisión de T-503 en Chrome: «**OK, me parece bien (como prueba)**». OK a **G4** (publicar), **T-504** (gráficas) ∥ **T-506** (API de reportes) y luego **T-507** (presupuestos y metas). Ajustes pedidos: (1) la **etiqueta de la cuenta** (método de pago) se muestra con **su color** (distinto por cuenta); (2) **sin etiqueta de tipo de moneda**: la moneda se percibe por el **símbolo** del importe (S/, US$, €…), nunca por el código ISO. Van en T-504. |
| 2026-10-09 (noche) | «**OK, todo A**»: **G3-A** (publicar T-501 e imágenes), **D10-A** (íconos SVG propios en V1: contrato 0.4.0 ya, API en la Fase 6 con adjuntos, SVG saneado; catálogo base abierto, sin copiar los PNG de Cashew), **D11-A** (detalles de la tarjeta de transacción como preferencia en el servidor). Plan: SPEC v0.4 + contrato 0.4.0, luego T-502 (marca + tarjeta configurable) ∥ T-503 (cliente HTTP + sesión), después T-504+. |
| 2026-10-09 (noche) | **Revisión visual de T-501 por Adrian: le agrada.** Preferencias: **superficie azul en modo oscuro** (mantener); la UI debe ser **siempre fiel a Cashew** (colores, barras de progreso, íconos) en gráficas de ingresos/gastos, objetivos y presupuestos. Pide: (1) **subir SVG propios como íconos de categoría**; (2) **favicon e ícono de la app según el modo** con `img/icono-Monetae.svg` y `img/icono-Monetae-dark.svg` (añadió también `Monetae-Logo-dark.jpg` y `Monetae-Logo-Nombre-dark.jpg`, versionados en `f31f19c`); (3) **personalizar qué detalles muestra la tarjeta de transacción** (fecha/hora, botones de acción, notas…). (1) y (3) cambian SPEC y contrato: ver D10 y D11. |
| 2026-10-09 (tarde) | «**OK, todo A**»: **G2-A** (publicar T-405 en `main`), **D9-A** (la importación real definitiva espera a una base persistente y a las primeras pantallas de la Fase 5), y OK a arrancar la Fase 5 con `T-501`. **Adrian borró él mismo el worktree de T-405** y su rama; sus commits siguen en `master-dev`. |
| 2026-10-09 | «**OK, todo A**»: **G1-A** (aprobar merge a `main` y push de la Fase 4), **L1-A** (T-405: préstamos de largo plazo sin desembolso con desembolso sin dinero, principal = suma de pagos, ítem `principal_assumed`), **X1-A** (transferencias entre monedas distintas, después de V1), **X2** (borrar los 4 worktrees de la Fase 4: **los borró Adrian él mismo**, junto con sus ramas `codex/T-40x`; el coordinador comprobó que sus 4 commits están en `master-dev`). |
| 2026-10-08 (noche) | «**Acepto todas tus recomendaciones. OK, puedes continuar con el Paso 3**»: ADR-008 **J1-A, J2-C, J3-A**; autorizó un `--dry-run` sobre una **copia** del respaldo real **solo con conteos y saldos**; lanzó la Fase 4. |
| 2026-10-08 (noche) | **«Acepto todas tus recomendaciones. OK, puedes continuar con el Paso 3».** Queda **ADR-008 ACEPTADO** con **J1-A, J2-C, J3-A** (la letra de J2 se aclaró: la recomendada es la C). **Autoriza un `--dry-run` sobre una copia de su respaldo real al final de la Fase 4** (solo conteos y saldos, nunca filas). **Lanza la Fase 4.** |
| 2026-10-08 (noche) | **«Todo A»** a las recomendaciones: **D1-A** (publicar tras verificar), **D2-A** (cancelar todas las programadas sin publicar), **D3-A**, **D4-A**, **D4b-A**, **D5: J1-A y J3-A**, **D8-A** (tasa de importación: `--fx-rate`, o la de `app_settings` como provisional). **J2 queda por aclarar**: la recomendada es la **C** y «A» es otra opción (ver §5). Confirmó que **el push de las 17:36 fue suyo**. Ejecutó `wsl --shutdown` para restablecer Docker. |
| 2026-10-08 (tarde) | **«OK»** al plan de reanudación (Pasos 1 y 2) y al conjunto de recomendaciones D1–D6, interpretado por el coordinador como **«todo A»**: D1 publicar docs, D2 cancelar todas las programadas sin publicar al archivar, D3 contrato, D4 alcance acotado de la Fase 4, D4b `/imports` diferido, D5 ADR por redactar, D6 limpieza. *Si no era esa la intención, Adrian debe decirlo.* |
| 2026-10-08 (tarde) | **D6 ejecutada por Adrian:** eliminó los 10 worktrees restantes (y antes, 8); quedan solo `main` y `master-dev`. |
| 2026-10-08 (tarde) | Adrian abrió Docker Desktop; el coordinador comprobó que **sigue sin ser accesible** desde WSL (D0). |
| 2026-10-08 (mañana) | Continuar la Fase 3; aprobar el merge a `main` (gate `gate_621dc454eeee`); protocolo de sesión en `CLAUDE.md` §10. El push de `main` lo hizo alguien a las 17:36. |
| 2026-10-07 | ADR-001 **A** (UI propia en Flutter Web reutilizando widgets de Cashew), ADR-002 **A** (sesión en servidor + cookie), ADR-003 **A** (interés en base caja; pago primero a interés), ADR-004 **A** (tipo de cambio manual manda), ADR-006 **A** (PIN, luego WebAuthn), ADR-007 **A** (SQLAlchemy síncrono). |
| Fases 0–2 (oct 2026) | Importador **SQLite primero**, CSV solo como rescate, siempre sobre una copia; el respaldo real es Cashew **v48**. Etiquetas en V1. Nombres duplicados permitidos en categorías y personas (únicos solo en cuentas y etiquetas). Usuarios solo por CLI en V1. `PATCH /transactions/{id}` admite `account_id` (misma moneda) y `kind`. |
| Fases 0–2 (oct 2026) | Agentes: **Codex** (`gpt-6.1-sol` general / `gpt-6-astra` el más potente / `gpt-6-luna` ligero) para backend y, después, UI; **Antigravity** solo como relevo; **Command Code** de reserva. |

## 5. Decisiones pendientes

Cada una: contexto → opciones (la más recomendable primero) → impacto.

**O1 · Orca no acepta órdenes desde la terminal WSL** (bloquea delegar T-515).
- **A (recomendada): activar en Orca *Settings → SSH → host `ssh-1790983388010-x1ugta`* «Allow this host's orca CLI to control Orca»** y seguir el flujo normal (Run `run_c2cebe1745b9`, una tarea Codex por pieza en `path:/home/artur/propio2/Monetae-claude-T-515-form-transaccion`). *Razón:* supervisión, `ask` y `worker_done` como siempre.
- B: plan B de `CLAUDE.md` §3.4: el coordinador da a Adrian el texto de cada pieza para pegarlo en un panel de Codex y revisa por git.
- C: `codex exec` no interactivo desde el coordinador. *Contra:* Adrian lo rechazó la última vez; no usar sin su permiso explícito.

**T-515 · ¿Aviso para tipos solo de diseño?** Hoy, elegir Suscripción/Repetitivo/Prestar/Deuda guarda una transacción normal sin avisar. **A (recomendada):** nota pequeña bajo la fila («Aún no disponible: se guardará como transacción normal»). B: dejarlo así y reportarlo.

**R2 · Revisión visual de Inicio por Adrian** (lo primero al volver). Inicio ya incluye T-512/T-513/T-514. Relanzar la pila de revisión (§7) y abrir `http://localhost:8080` a 400×642 con `revision-g7@example.test` (nombre «Adrian Sandy»; contraseña dada en el chat, **no** versionada). Sus observaciones → una tarea Codex de ajuste.

**G7 · Publicar en `main`** (`gate_ecde8d19a53a`; Adrian eligió **B: esperar a su revisión**). Al resolverlo se publica **todo `master-dev`** tras repetir la auditoría de seguridad.
- **A (recomendada tras R2): aprobar merge y push** sin `--force`. *Razón:* hay mucho trabajo verificado solo en local (8 tareas, 3 migraciones).
- B: seguir esperando. *Contra:* sin copia remota de ese trabajo.

**F1 · Pantallas que faltan para conectar Inicio** (TODO en T-514): crear **objetivo**, crear **presupuesto**, **detalle de categorías** (lista + selector de mes) y **reordenar Inicio** (píldora «Editar», `preferences.home_widgets`).
- **A (recomendada): una tarea Codex por pantalla**, empezando por los formularios de objetivo y presupuesto (la API existe), fieles a `addObjectivePage.dart` / `addBudgetPage.dart` de Cashew.
- B: esperar a terminar la revisión visual de Inicio.

**D12 · Historial de presupuestos y metas (RF-30)** — Adrian prefiere **la misma lista de transacciones filtrada**, sin historial aparte. *Falta su confirmación de la forma:*
- **A (recomendada):** filtros `budget_id` (+ fecha del periodo) y `goal_id` en `GET /transactions`, y `GET /budgets/{id}?on=<fecha>` para el total de un periodo; pantalla del presupuesto con su barra y la lista debajo, flechas ◀ ▶ por periodo (como Cashew). Contrato 0.7.0 pequeño.
- B: usar **etiquetas** para marcar la pertenencia. *Contra:* duplica lo que ya calcula el servidor y obliga a etiquetar a mano.

**D7 · Para más adelante:** ADR-005 sincronización Android (antes de V4) · orden de categorías · OAuth de Google y proveedor de tipo de cambio (Fase 6) · proxy del VPS (`ARCHITECTURE.md` §10.10) · corregir el principal de un desembolso sin dinero sin crear efectivo · zona horaria de la UI distinta de Lima · radio de tarjetas 20 dp (Monetae) vs 15 dp (Cashew), pendiente de que Adrian elija.

*Resueltas el 2026-10-10:* G6-A, P1-A, S1–S6, plan de T-512, G7-B (esperar), paso de Antigravity a Codex (ver §4).

## 6. Siguiente paso concreto

0. **T-515 piezas 2–6 con Codex** (`gpt-6.1-sol`, high), **una pieza por lanzamiento** en el worktree `../Monetae-claude-T-515-form-transaccion` (rama `claude/T-515-form-transaccion`), spec `docs/tasks/T-515-ui-transaction-form.md`, tras resolver **O1**. Por cada pieza el coordinador: lee el diff, corre `dart analyze` + `flutter test`, revisa goldens, compila (`flutter build web --release`), copia `apps/web/build/web` al de `master-dev` (lo sirve nginx) y captura con Playwright a 400×642 en oscuro comparando con la captura 11–19. Al terminar la pieza 6: informe de TODO/diferencias a Adrian, actualizar la skill si hace falta y fusionar la rama en `master-dev`.
1. **Relanzar la pila de revisión** (§7) y que **Adrian revise Inicio (R2)**; responder **F1**, **D12** y, tras la revisión, **G7**.
2. **G7 = A:** auditoría (`git diff origin/main..master-dev`: rutas prohibidas, `.env`, `reference/`, secretos, correos, cifras reales), `gate-resolve gate_ecde8d19a53a`, `git merge --ff-only master-dev` en `../Monetae`, push sin `--force` (Anexo B), marcar `task_752b79134036` `completed`.
3. **Ajustes de R2:** una tarea Codex `gpt-6.1-sol` high en `apps/web`, rama `codex/T-515-…`, verificación `dart analyze` + `flutter test` (goldens con texto versionados) + build web + revisión de goldens por el coordinador.
4. **F1 = A:** T-516 formulario de objetivo y T-517 formulario de presupuesto (Codex high; `apps/web`; contra la API de T-601/T-602), después detalle de categorías y reordenar Inicio.
5. **D12 = A:** contrato 0.7.0 + T-604 API de filtros (Codex medium) y pantalla de presupuesto/meta (Codex high).

**Antes de lanzar:** `orca skills get orchestration --full`, `orca status --json`, `docker version`, `git worktree list`, disco ≥ 2,5 GB y puertos libres. Codex muestra «Update available» en cada lanzamiento: enviar *Esc* y reintentar con `--retry-of` (Anexo C). **Agentes:** Codex para todo; Antigravity solo como relevo por cuota (memoria y §4).

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 5: `run_c2cebe1745b9`.** Todas las tareas `completed` salvo: T-602 `task_752b79134036` **`blocked`** por el gate G7 (normal; marcar `completed` al resolverlo) y T-512b `task_e7ef47b4ca85` `failed` (sustituida por `task_c6324ab6cc3e`, completada). **Ningún worker vivo**; terminales de Codex liberadas. La terminal de Antigravity es externa (Orca no la libera): Adrian la cierra. Runs anteriores: `run_f5e95406186a` (F4), `run_63b520544a30` (F3), `run_70f5f187fe16` (F2), `run_2cddcd14320c` (F1), `run_bef8ecfc67a7` (F0). El CLI no cierra Runs; no usar `orchestration reset`.

**Worktrees:** `Monetae` → `main`, `Monetae-master-dev` → `master-dev`, **`Monetae-claude-T-515-form-transaccion` → `claude/T-515-form-transaccion`** (en uso: **no borrar**). Sin `.env` sueltos. **Orca:** ninguna tarea T-515 creada (O1).

**Contenedores:** **ninguno en marcha** (pila de revisión bajada al cerrar). **Ojo:** `Monetae-master-dev/apps/web/build/web` (artefacto ignorado que monta nginx) contiene ahora la compilación de **T-515 pieza 1**, no la de `master-dev`; recompilar desde `master-dev` si se quiere revisar solo Inicio. Se conserva el volumen `monetae-review_postgres_data` (BD en `0011`; usuarios sintéticos `adrian-review@example.test` y `revision-g7@example.test` «Adrian Sandy» con datos de octubre 2026; contraseñas solo en el chat). La pila de prueba que dejó Antigravity (`monetae-t512`) se bajó con su volumen. **Relanzar la pila de revisión** desde `Monetae-master-dev`:
```bash
export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"
(cd apps/web && flutter build web --release)          # build/web ya existe de la última integración; recompilar si hay cambios
cp .env.example .env && sed -i 's/^MONETAE_COOKIE_SECURE=true$/MONETAE_COOKIE_SECURE=false/' .env
COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml up -d --build db api web
COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
# bajar: COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml down && rm -f .env
```

**Paneles de Orca abiertos:** el del coordinador, `lupuna` (otro proyecto, no se toca) y, si siguen, los de Codex T-513/T-514 y Antigravity T-512 (inactivos: Adrian puede cerrarlos).

## 8. Limitaciones y riesgos conocidos

- **Docker Desktop depende de la integración con WSL** (distro `AlmaLinux-9`): si `/usr/bin/docker` apunta a un destino inexistente, reactivar *Settings → Resources → WSL integration* y `wsl --shutdown`.
- **Importación real:** el `apply` nunca se ha ejecutado (solo `--dry-run` sobre copias, cuadre exacto); espera a D9-A. El importador es **solo inserción**. Préstamos con principal supuesto (L1-A) aparecen `settled` hasta corregirlos con `adjustment` (el `PUT` del desembolso crea efectivo).
- **UI:** Inicio sigue la skill `cashew-inicio-ui`; sus botones «añadir» y «Editar» y el detalle de categorías son TODO (F1). Formato de montos de Cashew («1.234,50 S/.») fijado a mano en `currency_format.dart`. El favicon sigue el modo del **sistema/navegador**, no el tema de la app. Las transacciones en moneda extranjera muestran solo el original (el contrato no trae el convertido).
- **Agentes:** Antigravity resultó poco fiable (afirmó pruebas verdes con 12 fallos; ignora mensajes que no son respuestas a su `ask`). Verificar siempre por cuenta propia; preferir Codex.
- **Íconos de Cashew:** sus 277 PNG de categoría tienen licencia dudosa; **no** copiarlos (SPEC RF-46).
- **Presupuestos y metas en moneda distinta de la base:** toda conversión pasa por la base (PEN). Un presupuesto o meta en USD con gastos en USD muestra 0.00 hasta que exista una tasa PEN→USD en `exchange_rates` (proveedor en la Fase 6 o tasa manual).
- **Reportes:** sin proveedor de tipo de cambio (Fase 6), con moneda de reporte ≠ base todo cae en `unconverted_count` salvo tasas insertadas a mano en `exchange_rates`.
- **Sin auditoría de seguridad externa** (Fase 7). La BD admite un `income` negativo por SQL directo (`ARCHITECTURE.md` §10.12). Límite de login detrás de proxy (§10.10). `501 google_login_not_available` fuera del contrato (§10.11).
- **Zona horaria en la UI:** la presentación asume America/Lima (UTC−5 fijo) aunque `CurrentUser.timezone` admite cualquier zona IANA. Generalizarlo es una tarea aparte (decidido en T-513, 2026-10-10).
- **Disco:** ≈ 2,6 GB libres en `/` (20 GB) al cerrar el 2026-10-10 (noche, 2.ª). Playwright + Chromium para capturas ocupa ≈ 600 MB (se instaló en el scratchpad de la sesión y se borró al cerrar). Flutter + Docker lo consumen rápido: borrar artefactos (`build/`, `.dart_tool/`, `.venv/`) de worktrees ya fusionados.
- **Repositorio público:** todo push se audita antes; los datos reales solo viven en `reference/backups/` (ignorado).
- La cuota de Claude Pro es limitada: delegar generación de código; reservar al coordinador specs, revisión e integración.

## 9. Cómo retomar (comandos exactos)

```bash
# 0) Leer: este archivo, AGENTS.md, CLAUDE.md (§10), docs/SPEC.md v0.5, docs/ui/home-layout.md, ADRs y tareas. Luego:
cd /home/artur/propio2/Monetae-master-dev            # worktree de master-dev (main está en ../Monetae)
git status -sb && git log --oneline -5 && git worktree list
git -C ../Monetae log --oneline -1 && GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' ls-remote origin refs/heads/main refs/heads/master-dev

# 1) Herramientas (el Python del sistema es 3.9: NO usarlo para el proyecto)
export PATH="$HOME/.local/bin:$HOME/flutter/bin:$PATH"
uv --version && docker compose version && flutter --version | head -1
orca status --json | head -5 && orca orchestration run-use --id run_c2cebe1745b9
orca orchestration gate-list --json | grep -A3 gate_70e14ac5abc1     # G6 pendiente

# 2) Backend (≈ 8 min; BD propia)
cp .env.example .env && MONETAE_DB_PORT=5433 COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 1164 passed
uv run alembic upgrade head && uv run alembic check     # cabeza: 0011
cd ../.. && python3 -I scripts/check_openapi.py         # 89 paths, 131 operaciones
COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) UI
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release   # esperado: 217 pruebas
grep -rE "drift|firebase|appStateSettings|package:budget/" lib || echo limpio

# 4) Recorrido real web+API por nginx (sin navegador): apps/web/tool/e2e_session.sh (proyecto monetae-t503, puertos 5444/8001/8081)
```

## Anexo A · Qué incluye el backend (verificado sobre la cabeza de `master-dev`)

FastAPI síncrono (ADR-007) en `services/api`: **46 de 89 rutas = 73 de 131 operaciones**.

- **Acceso:**
  - login por correo y contraseña (argon2id);
  - sesiones opacas con cookie `HttpOnly` y CSRF con HMAC + `Origin`;
  - límite de intentos;
  - `users/me` con preferencias: tema, acento, widgets, `transaction_card` (RF-47) y `default_account_id` (RF-48).
  - Usuarios solo por CLI.
- **Catálogos:** cuentas (con saldo y `transaction_count` calculados), categorías (2 de sistema de interés), personas con alias y etiquetas.
- **Libro mayor:** transacciones, transferencias (también entre monedas), lotes y programadas.
- **Préstamos (T-301/T-302):** saldo y estado calculados; interés primero; exceso con `adjustment` o `income_expense`; revalidación del libro.
- **Suscripciones (T-303/T-304):** archivado reversible y totales por moneda.
- **Reportes (T-506/T-508):** `cash-flow` (con `cumulative_net`) y `categories`.
  - **Base caja:** el interés cuenta en la fecha del pago y el capital nunca.
  - **Multimoneda:** `fx_rate_to_base` + `exchange_rates` del día o anterior, con `unconverted_count`.
  - **Periodos:** zona horaria del usuario, semanas ISO.
- **Base de datos:**
  - Migraciones: `0001` identidad y catálogos, `0002` intentos, `0003` transacciones, `0004` transferencias, `0005` préstamos, `0006` suscripciones, `0007` importador, `0008` `exchange_rates` (tabla global).
  - FK compuestas con `user_id`.
- **Importador de Cashew** (`python -m monetae.cli import-cashew`): SQLite v48 en solo lectura sobre una copia; idempotente; `--dry-run`; cuadre atómico; préstamos ADR-008 + L1-A. Documentación en `docs/importers/`.
- **Calidad:** 1032 pruebas con PostgreSQL real; `ruff`, `mypy --strict` y `alembic check` limpios; cero `type: ignore`.
- **No implementado (operaciones del contrato):** usuarios 9 (PIN/WebAuthn), reportes 6, notificaciones 6, metas 6, presupuestos 6, reglas de categoría 5, reglas recurrentes 5, importaciones 4, adjuntos 4, íconos 4, Google OIDC 1, exportaciones 1 y sugerencia de tipo de cambio 1.

**UI `apps/web` (Flutter Web):**
- **Componentes de Cashew desacoplados:** tema, tarjeta, circular, líneas, resumen, selector, presupuestos y objetivos. Cada uno conserva su procedencia y el aviso GPL; `NOTICE` y `LICENSE` vienen de Cashew.
- **Datos:** DTO generados del contrato y cliente HTTP con CSRF.
- **Pantallas:** acceso, lista de transacciones e Inicio provisional.
- **Demos:** `/#/demo/home` y `/#/demo/budgets-goals`.
- **Textos y marca:** i18n es/en; marca por modo.
- **Despliegue:** servida por nginx (`infra/web/default.conf`) en el mismo origen que la API.

## Anexo B · GitHub

`origin` = `https://github.com/Adrian-asandym/Monetae.git` (público). Antes de cada push se verifica el historial (sin `.env`, claves, `reference/`, respaldos; únicos `.sqlite`/`.csv` versionados: los 3 fixtures sintéticos de `services/api/tests/fixtures/cashew_v48/`; sin correos reales). `origin/main` está en `1736d7a` (G5). Comando: `GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main master-dev` (sin `--force`; `gh` autenticado como `Adrian-asandym`).

## Anexo C · Lecciones operativas (no repetir errores)

- **Verificar, no confiar en el resumen del worker:** correr yo `ruff`, `mypy`, `pytest`, leer el servicio entero y hacer pruebas manuales. Así aparecieron: un bloqueo `FOR UPDATE` por petición (5,6 s → 0,03 s), duplicados de nombre mal aplicados, citas inventadas, errores de conteo y el `commit` posterior a la respuesta.
- **`TestClient` no es un servidor:** espera a que la app termine por completo y oculta errores de orden respuesta/commit. Probar además con `uvicorn` real y `httpx`.
- **Releer la spec contra el contrato y el código antes de lanzar:** en la Fase 3 corregí mi propia spec dos veces al lanzar. Las preguntas del worker (`ask`) fueron todas legítimas: responderlas con el contrato abierto.
- **Reglas de bloqueo:** las lecturas no toman bloqueos de fila; las escrituras usan bloqueos consultivos con orden fijo.
- **Orca:** `worker-start` puede devolver `outcome_unknown` aunque el worker trabaje; Antigravity pide «trust workspace» en cada worktree; Codex puede mostrar un menú «Update available» que solo Adrian puede saltar; `gate-create` no acepta `--run` y deja la tarea en `ready` (marcarla `completed` a mano); al abrir sesión hay que re-vincular el Run (`run-use --id`); solo **una** espera `check --wait` por Run (`waiter_exists` si queda una colgada), y menos de 10 min por llamada; no se pueden editar las especificaciones de una tarea ya creada (crear otra y marcar la vieja `failed/superseded`).
- **Shell:** nunca `pkill -f` ni `pgrep -f` con un texto que aparezca en el propio comando (mata el shell, código 144); parar servidores por puerto con `ss -ltnp`.
- **Modelos Codex** (`~/.codex/models_cache.json`): `gpt-6.1-sol` (general), `gpt-6-astra` (el más potente), `gpt-6-luna` (ligero; sirve para CRUD pero exige revisar las reglas).
- **Privacidad:** nunca leer filas de `reference/backups/`; trabajar sobre una copia; los fixtures son sintéticos.
- **La fixture sintética no basta:** en la Fase 4 ocultó tres supuestos falsos sobre los datos reales de Cashew (series de ocurrencias, emparejado unidireccional, préstamos sin desembolso). Antes de dar por buena una suposición sobre datos ajenos, leer el código de referencia (`reference/Cashew`) y correr un `--dry-run` real agregado. **No poner cifras del respaldo real en archivos versionados** (el repositorio es público).
- **Orca/Codex:** si `worker-start` falla en `agent_readiness` por el aviso «Update available», enviar *Esc* a la terminal (`orca terminal send --terminal <h> --text $'\x1b'`; nunca «Update now» ni «Skip until next version») y reintentar con `worker-start --task <id> --retry-of <dispatch> --worktree path:<dir> --terminal <h>`. Para un seguimiento en la misma terminal: `worker-start --spec ... --worktree path:<dir> --terminal <h>`.
- **Shell:** en `--body "..."` no usar acentos graves (el shell los ejecuta); usar comillas simples.
- **Bases de datos en paralelo:** nunca compartir proyecto/puerto de Compose entre workers; asignar `MONETAE_DB_PORT` y `COMPOSE_PROJECT_NAME` propios.
- **Orca, entregas:** `check --wait` vuelve a entregar la misma *Delivery* hasta confirmarla con `check --ack <delivery_id>`; tras responder (`reply --id <msg> --run <run>`) o procesar un `worker_done`, confirmar en la siguiente llamada.
- **`reference/` no existe en los worktrees** (está ignorado): dar a los workers la ruta absoluta `/home/artur/propio2/Monetae/reference/Cashew/budget/` y **prohibir** `reference/backups/` en cada spec de UI.
- **Revisar las capturas (goldens) yo mismo:** así apareció la regresión del formato de importes («170,00 S/»). `intl` no trae el formato peruano ni con `es_PE`.
- **Contrato por delante del backend:** al cambiar un esquema ya implementado, `test_contract_subset` falla a propósito hasta integrar la tarea del backend; decirlo en `STATUS` y en la spec.
- **Adrian deja a veces archivos sin commit en ambas carpetas** (p. ej. imágenes en `img/`): versionarlos en `master-dev` y, antes del ff de `main`, quitar las copias **idénticas** (comprobar hash) de la carpeta de `main`.
- **Disco:** borrar solo artefactos ignorados (`git check-ignore`) de worktrees fusionados; las carpetas las borra Adrian.
- **Pila de revisión:** proyecto Compose propio (`monetae-review`), usuario `@example.test`, datos de la **fixture sintética**, contraseña solo en el chat; para servidores locales por HTTP, `MONETAE_COOKIE_SECURE=false` solo en `.env`.
- **Capturas de Flutter Web sin navegador visible:** `uv venv` + `pip install playwright pillow` + `playwright install chromium` en el scratchpad; iniciar sesión **por la API antes** de cargar la app (health → cookie `monetae_csrf` → `POST /auth/login` con `Origin` y `X-CSRF-Token`), luego `goto /`; `color_scheme="dark"` para el tema; la ruta `#/transactions/new` no se abre por URL (abrir con «+»); en canvaskit usar `mouse.move` + `down` + `up` (un `click` simple a veces solo muestra el tooltip). Medir colores/alturas de las capturas de Adrian con Pillow (Cashew a 400 dp ≈ 500 px: escala 1,25).
- **Nunca `dart format lib` entero:** reformatea archivos ajenos a la tarea; formatear solo los tocados.
- **El código lo escribe Codex**, aunque la petición diga «implementa»; el coordinador planifica, especifica y verifica (memoria `delegate-code-to-codex`).
