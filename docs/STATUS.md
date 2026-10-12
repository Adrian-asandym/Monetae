# STATUS — Monetae (documento de traspaso)

> **Lo primero que debe leer cualquier agente.** Coordinador: Claude (Sonnet 5.5) · Dueño del producto: Adrian.
> Después de este archivo: `AGENTS.md` (contrato común), `CLAUDE.md` (rol del coordinador y **§10 Protocolo de sesión**) y `docs/SPEC.md` (qué se construye).
> Para reanudar: Adrian dice «Continuemos con el trabajo» y se aplica el Comando 2 de `CLAUDE.md` §10.

## 1. Fecha, hora y hashes

| | |
|---|---|
| **Última actualización** | **2026-10-12, noche (America/Lima)** — cierre de sesión («Continuaremos en otro momento»), tras terminar T-519 |
| **`origin`** | `origin/main` = `origin/master-dev` = **`8b8688e`** (hasta T-508, SPEC v0.5; G6). |
| **`main`** | `8b8688e`. |
| **`master-dev`** | **`0e1508e` + el commit de este cierre (`git log -1`)**: incluye T-515 (formulario piezas 1–9), T-518, T-604 (contrato **0.7.0**, migración **`0012`**), la corrección de DTO, **T-519** (pantalla «Transferir saldo» + hoja «Tipo De Cambio») y la skill `cashew-form-transaccion` actualizada. **Sin publicar.** |
| **Rama de tarea** | Ninguna abierta: `codex/T-519-transfer-balance` = `21bfc63` ya fusionada (`1b559c8`). |
| **Gate abierto** | **G7 `gate_ecde8d19a53a`** (publicar en `main`): sin resolver; al resolverlo se publica **todo `master-dev`** tras la auditoría. |
| **SPEC / ARCHITECTURE / contrato** | SPEC **v0.7** · `docs/ARCHITECTURE.md` v0.3 · `docs/api/openapi.json` **0.7.0** (90 paths, 133 operaciones). |

## 2. Fase actual

| Estado | Contenido |
|---|---|
| ✅ **Completo** | Fases 0–4. **Fase 5:** T-501…T-515 (formulario de transacción fiel a Cashew, piezas 1–9 incluidos los ajustes v2 1–3 de Adrian), T-518 (goldens sin fecha). **Adelantado de la Fase 6:** T-601/T-602/T-603 y **T-604** («Corrección de saldo»: categorías de sistema, `POST/GET /balance-corrections`, exclusión de totales, importador). |
| 🔄 **En curso** | Nada. Ningún worker vivo. |
| ⏳ **Pendiente** | **R4** revisión de T-519 por Adrian · **TAM** (medidas de ajustes 1–2) · R2/G7 · F1 · D12 · VPS1-C (cuando Adrian contrate el VPS) · resto de la Fase 5 · Fase 6 · Fase 7 · importación real (D9-A). |

Backend: **1190 pruebas**, migraciones hasta **`0012`**. UI `apps/web`: **343 pruebas** en `master-dev`, todas verdes.

## 3. Trabajo hecho en esta sesión (2026-10-12)

- **Reanudación:** STATUS coincidía con git. Pila de revisión levantada; **pasada al puerto 8090** (el 8080 es de Tomcat/Lupuna de Adrian).
- **Respuestas a Adrian:** el formulario guarda en la BD (`POST /transactions`); tipo de cambio solo manual (proveedor en la Fase 6); transferencias: API sí, UI no (resuelto con T-519). Plan VPS (VPS1-C).
- **Pautas v2 del formulario (capturas 20–25)** repartidas así:
  - **T-515 piezas 7–9** (Codex `gpt-6.1-sol` high, una por lanzamiento): `fdb955e` nombre de categoría bajo el monto + «Agregar transacción»; `3fa1af9` hoja «Seleccionar Cuenta» reutilizable (también apilada sobre la hoja de importe); `dbdc2eb` menú ⋮ (a y b funcionales, en memoria; c y d diseño). Investigación: (c) en Cashew guarda asociaciones título-categoría (no controla la hoja de título, `editAssociatedTitlesPage.dart:323`); (d) no existe en el clon local (versión anterior), equivalentes `askForTransactionTitle`/`askForTransactionNoteWithTitle`.
  - **T-604** (Codex high): migración `0012` (2 categorías de sistema «Corrección de saldo», CHECK de `transfer_group_id` ampliado), `POST/GET /balance-corrections` atómico e idempotente con `to_occurred_at` (llegada diferida), piernas editables por separado (PATCH conserva kind/categoría), exclusión en reportes/presupuestos/Inicio, metas como `transfer` (igual que Cashew `watchTotalTowardsObjective`), importador (categoría 0 de Cashew → correcciones). Verificado por el coordinador: ruff, mypy, **1190 pruebas**, `alembic` up/check/down/up, `check_openapi`.
  - **T-519** (Codex high; **pieza 11 terminada por el coordinador**: Codex se quedó sin continuar y Adrian autorizó la excepción): pieza 11 `21bfc63` hoja «Tipo De Cambio» (convención peruana «1 USD = x PEN», edición bidireccional exacta, sugerencia 1→2→3→5; el 4 «mercado» y «Ver todos los tipos de cambio» esperan a la Fase 6); verificada con 343 pruebas, golden y consulta real. Pieza 10 `1fb2c4b` pantalla «Transferir saldo» (tarjetas, ✕, ↓, ⓘ, línea «Llegada: igual que la salida», guardado exacto con idempotencia, ícono `swap_horiz`). Verificada: 321 pruebas, golden vs captura 24, **POST real** contra la pila (201; piernas borradas después). El clon de Cashew es **anterior** a las capturas 24–25: ✕ = limpiar importe, ↓ = intercambiar cuentas, «Corrección De Saldo» = TODO (la lista no filtra por categoría).
- **T-518** (Codex medium): reloj inyectable `PresentationClock`; 10 goldens ya no dependen del día.
- **Integrado en `master-dev`:** T-518, T-604, T-515 (M1), **T-519** (`1b559c8`). UI **343 pruebas verdes**. Pila del 8090 recompilada con `master-dev`.
- **Skill `cashew-form-transaccion` actualizada** (`0e1508e`) con los ajustes v2, la regla de medidas (px vs dp) y lo que quedó como diseño.
- **SPEC v0.7** (RF-03 y §9.4) por T1-B.
- **Incidente:** tras subir la API de revisión a `0012`, la UI mostraba «no se pudo conectar con el servidor»: los DTO (contrato 0.6.0) rechazaban `system_key` `balance_correction_*` y fallaba toda la lista de categorías. Corregido regenerando DTO con `apps/web/tool/generate_dtos.py` (`eeb622a`, 4 líneas). Ver lección en el Anexo C.

## 3b. Sesión anterior (2026-10-11)

- T-515 piezas 2–6 con Codex; prueba de punta a punta en la pila; hallazgo de los 10 goldens dependientes de la fecha (resuelto hoy con T-518).

## 3b. Sesión anterior (2026-10-10, noche — 2.ª sesión)

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
| 2026-10-12 (tarde) | **Cierre** («Continuaremos en otro momento») con la pieza 11 de T-519 cerrándose en su rama. Antes, Adrian autorizó: «**si te quedas sin cuota con Codex, completa su trabajo solo por esta vez**» (excepción puntual; la regla sigue siendo que el código lo escribe Codex). Reportó el error «no se pudo conectar con el servidor» en Inicio y al crear transacción (corregido, `eeb622a`). TAM sigue sin respuesta. |
| 2026-10-12 | «**OK todo A**» al plan T1-B: **Z1-A** (correcciones excluidas de ingresos/gastos, presupuestos e Inicio), **Z2-A** (el importador trae las «Correcciones de saldo» de Cashew como tales), **Z3**: por defecto ambas piernas con la misma fecha y hora, pero **la de llegada debe poder editarse** (transferencias diferidas). Por eso el par se enlaza con el `transfer_group_id` existente (pauta de Adrian: usar el campo de enlace si existe) en vez de emparejar por fecha. SPEC v0.7. T-604 lanzada. |
| 2026-10-12 | Pautas de diseño v2 del formulario (capturas 20–25; 5 ajustes) delegadas a Codex: piezas 7–9 de T-515 (`docs/tasks/T-515-ui-transaction-form.md`, sección «Ajustes v2»). **M1 = sí** (fusionar T-515 al terminar los ajustes). **T-518 = A** (lanzada, Codex `gpt-6.1-sol` medium, rama `codex/T-518-date-goldens`). **T1 = B**: transferencia «a lo Cashew» = dos transacciones independientes gasto/ingreso con la categoría **«Corrección de saldo»** (no `/transfers`). Como la categoría no existe, el coordinador presenta el plan para añadirla y **espera confirmación** antes de implementarla; no se cambian los totales hasta su OK. |
| 2026-10-12 | **VPS1-C**: contratará un VPS Contabo (6 vCPU, 12 GB RAM, 200 GB SSD o 100 GB NVMe) con **AlmaLinux 10**; primero para **desarrollo** (Orca por SSH, usuario sin root) y después también para **producción** en el mismo VPS (alternativas que evaluará: datos reales aislados solo para root, o PaaS tipo Supabase). Exposición con **Cloudflare Tunnel + Cloudflare Access** (Adrian gestiona sus subdominios en Cloudflare; el coordinador le dará los pasos). La pila de revisión local pasa al puerto **8090** (el 8080 queda para Tomcat/Lupuna). |
| 2026-10-12 | Reanudación: STATUS coincide con git; pila de revisión levantada (8080, luego 8090) y login verificado. Adrian preguntó por el guardado del formulario (sí, `POST /transactions`), tipo de cambio (solo manual; proveedor en la Fase 6) y transferencias (API sí; pestaña web «Transferir» solo diseño). Sus pautas de diseño de T-515 siguen pendientes. |
| 2026-10-11 (noche) | **Cierre** («Continuaremos en otro momento»). Adrian **terminará de verificar T-515** y dará su opinión del diseño y si hay que modificar algo más del formulario. Pide que **al reanudar se levante la interfaz en el 8080** para terminar de verificarla. M1 (fusionar) y T-518 (goldens por fecha) quedan sin respuesta. |
| 2026-10-11 | Reanudación: STATUS coincide con git; Adrian reactivó Docker y dio permiso SSH a Orca (O1 resuelto: `run-use`/`worker-list` funcionan). «**Apruebo todo A con el OK**»: **O1-A** (orquestación normal), **aviso A** (nota bajo la fila de tipos para los tipos solo de diseño, en la pieza 6) y el plan T-515 piezas 2–6 con Codex `gpt-6.1-sol` high, una por lanzamiento. |
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

**TAM · Medidas de los ajustes 1 y 2.** En la pieza 9 se vio que las medidas en dp de las pautas parecen px de la captura (escala 1,25): con 20/16 dp la hoja salía mucho más alta que en Cashew, y se calibró a 16/14 dp del código de Cashew. Los ajustes 1 (nombre de categoría, 20 dp, una línea) y 2 (hoja de cuentas, nombre 20 dp, radio de fila 12) usan los números literales; Cashew usa 18 dp (categoría hasta 2 líneas) y radio 15.
- **A (recomendada): igualarlos al código de Cashew** en una tarea pequeña de Codex (medium). *Razón:* misma regla para todo el formulario.
- B: dejarlos como están.

**R4 · Revisión de T-519 por Adrian** (pantalla «Transferir saldo» + hoja «Tipo De Cambio») en `localhost:8090` (ya publicada). La primera transferencia entre monedas pide la tasa a mano; desde la segunda aparece sugerida.

**R2 · Revisión visual de Inicio por Adrian** y **G7 · Publicar en `main`** (`gate_ecde8d19a53a`).
- **A (recomendada tras R2/R4): aprobar merge y push** sin `--force` tras la auditoría. *Razón:* hay mucho trabajo verificado solo en local (T-509…T-604, 4 migraciones).
- B: seguir esperando. *Contra:* sin copia remota.

**F1 · Pantallas que faltan para conectar Inicio:** crear objetivo, crear presupuesto, detalle de categorías, reordenar Inicio. **A (recomendada):** una tarea Codex por pantalla. B: esperar.

**F2 · Edición de transacciones existentes y filtro por categoría** (nuevo): la UI no abre transacciones guardadas para editarlas (la llegada diferida hoy solo se fija al crear) y la lista no filtra por categoría (botón «Corrección De Saldo» del diálogo ⓘ). **A (recomendada):** tarea Codex tras T-519. B: esperar a la pestaña Transacciones completa.

**D12 · Historial de presupuestos y metas** = lista de transacciones filtrada. **A (recomendada):** filtros `budget_id`/`goal_id` en `GET /transactions` (contrato 0.8.0). B: etiquetas.

**VPS1 · (decidido C)** pendiente de que Adrian contrate el VPS (6 vCPU, 12 GB; recomendado 100 GB NVMe; AlmaLinux 10). Plan en el punto VPS1 de la sesión 2026-10-12 (§4) y recomendación de **Docker rootless** para el usuario de desarrollo.

**D7 · Para más adelante:** ADR-005 · orden de categorías · OAuth Google y proveedor de tipo de cambio (Fase 6; habilita el paso 4 «mercado» de la sugerencia y «Ver todos los tipos de cambio») · proxy del VPS (`ARCHITECTURE.md` §10.10) · zona horaria de la UI · radio de tarjetas 20 vs 15 dp · persistir los ajustes del menú ⋮ (hoy en memoria).

## 6. Siguiente paso concreto

**Al reanudar:**
1. Comprobar que la pila del 8090 sigue en marcha (`docker ps`); si no, relanzarla (§7). Dar a Adrian usuario y contraseña para **R4** (T-519) y el resto del formulario.
2. Con sus respuestas:
   - **TAM = A:** tarea Codex `gpt-6.1-sol` medium en `apps/web` (rama `codex/T-520-form-measures` desde `master-dev`): nombre de categoría 18 dp hasta 2 líneas (Cashew `addTransactionPage.dart` ~1973), filas de «Seleccionar Cuenta» nombre 18 dp y radio 15 (`radioItems.dart`); goldens regenerados; verificar con `dart analyze`, `flutter test`, build y captura.
   - **F2 = A:** tarea Codex high: abrir una transacción guardada en el formulario en modo editar (incluida la llegada de una «Corrección de saldo», sin cambiar su tipo ni categoría) y filtro por categoría en la lista de transacciones (conecta el botón «Corrección De Saldo» del diálogo ⓘ). Revisar el contrato antes de escribir la spec.
   - Ajustes de R4, si Adrian pide cambios.
3. Luego **R2/G7** (publicar `master-dev` en `main` tras la auditoría) y **F1/D12**.
4. **Regla nueva:** todo cambio de contrato se integra junto con la regeneración de los DTO de la UI y una prueba de la UI contra la API real (Anexo C).

## 7. Estado del Run, de los worktrees y de los agentes abiertos

**Run de la Fase 5: `run_c2cebe1745b9`.** Completadas hoy: T-515 piezas 7–9 (`task_918cdbe06dbc`, `task_881bf03f5c44`, `task_2f7a58d49d4d`), T-518 `task_6e7d560172a3`, T-604 `task_1e5ea0e539ae`, T-519 piezas 10 `task_10487b71ff18` y 11 `task_0d6fceaff333` (el dispatch `ctx_b9b2114b4dbc` se detuvo con `worker-stop`; la terminó el coordinador). **Ningún worker vivo.** T-602 `task_752b79134036` sigue `blocked` por G7 (normal). El CLI no cierra Runs; no usar `orchestration reset`.

**Worktrees:** `Monetae` → `main`; `Monetae-master-dev` → `master-dev`. **Ya fusionados (Adrian puede borrarlos, con sus ramas):** `Monetae-claude-T-515-form-transaccion`, `Monetae-codex-T-518-date-goldens`, `Monetae-codex-T-604-balance-correction`, `Monetae-codex-T-519-transfer-balance`.

**Pila de revisión `monetae-review`: queda EN MARCHA** en `http://localhost:8090` (API `8000`, BD `5433`, migración **`0012`**), sirviendo la compilación de **`master-dev` `1b559c8`** (Inicio + formulario completo + «Transferir saldo» + «Tipo De Cambio»). Usuario `revision-g7@example.test` (contraseña solo en el chat). Si se apaga WSL/Docker, relanzar desde `Monetae-master-dev`:
```bash
export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"
cp .env.example .env && sed -i 's/^MONETAE_COOKIE_SECURE=true$/MONETAE_COOKIE_SECURE=false/' .env
MONETAE_WEB_PORT=8090 COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml up -d --build db api web   # el puerto va como variable: compose no lee el .env de la raíz
MONETAE_WEB_PORT=8090 COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
rm -f .env
# bajar: MONETAE_WEB_PORT=8090 COMPOSE_PROJECT_NAME=monetae-review docker compose -f infra/docker-compose.yml down
```
`apps/web/build/web` de `master-dev` (ignorado) es lo que monta nginx: recompilar ahí tras cada integración.

**Paneles de Orca abiertos:** coordinador y `lupuna` (otro proyecto, no tocar). Los de Codex (T-515 `term_dd064818…`, T-518 `term_a28d5186…`, T-604 `term_6956b6c7…`, T-519 `term_69891d59…`) están terminados: Adrian puede cerrarlos.

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
- **Disco:** ≈ 2,1 GB libres en `/` (20 GB) al cerrar el 2026-10-12 (se liberan al borrar los 4 worktrees ya fusionados). Playwright + Chromium para capturas ocupa ≈ 600 MB (se instaló en el scratchpad de la sesión y se borró al cerrar). Flutter + Docker lo consumen rápido: borrar artefactos (`build/`, `.dart_tool/`, `.venv/`) de worktrees ya fusionados.
- **Repositorio público:** todo push se audita antes; los datos reales solo viven en `reference/backups/` (ignorado).
- **Ajustes del menú ⋮** (pestaña Transferir, adjunto) solo en memoria: se pierden al recargar la página.
- **Clon de Cashew anterior** a las capturas 20–25: varios controles nuevos (menú ⋮ (d), ✕/↓/ⓘ de «Transferir saldo») siguen las capturas, no el código.
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
orca orchestration gate-list --json | grep -A3 gate_ecde8d19a53a     # G7 pendiente

# 2) Backend (≈ 8 min; BD propia)
cp .env.example .env && MONETAE_DB_PORT=5433 COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml up -d db
cd services/api
export MONETAE_TEST_DATABASE_URL=postgresql+psycopg://monetae:change-me@127.0.0.1:5433/postgres MONETAE_REQUIRE_DB=1
export MONETAE_DATABASE_URL=$MONETAE_TEST_DATABASE_URL
uv sync --frozen && uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -q                                        # esperado: 1190 passed (usar MONETAE_DB_PORT=5434 si la pila de revisión ocupa el 5433)
uv run alembic upgrade head && uv run alembic check     # cabeza: 0012
cd ../.. && python3 -I scripts/check_openapi.py         # 90 paths, 133 operaciones
COMPOSE_PROJECT_NAME=monetae-check docker compose -f infra/docker-compose.yml down -v && rm -f .env

# 3) UI
cd apps/web && flutter pub get && dart analyze && flutter test && flutter build web --release   # esperado: 301 pruebas (master-dev)
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
- **Codex en Orca:** si `worker-start` deja la terminal con `account/read failed … timed out`, la terminal queda en el shell (`agent_unconfigured`): `worker-stop --dispatch <id>` y `worker-start --task <id> --retry-of <id> --worktree path:<dir> --agent codex --model … --effort …` en terminal nueva. Para las piezas siguientes reutilizar la terminal con `worker-start --task <nueva> --worktree path:<dir> --terminal <h>` (sin «Update available»). Los latidos (`heartbeat`) llegan como mensajes: confirmarlos con `--ack`.
- **Goldens que dependen de `DateTime.now()`** se rompen solos al cambiar el día: antes de culpar a un worker, correr la misma suite en `master-dev` (T-518).
- **Contrato cambiado ⇒ regenerar DTO de la UI en la misma integración** (`python3 -I apps/web/tool/generate_dtos.py`, sin `dart format`) y probar la UI contra la **API real** antes de publicar en la pila: un `enum` nuevo (`system_key`) hizo fallar toda la lista de categorías y la UI lo mostró como «no se pudo conectar» (2026-10-12). Las pruebas con `ApiClient` falso no lo detectan.
- **Medidas de Adrian en dp:** suelen ser px de la captura (escala 1,25); manda el código de Cashew + la captura (pieza 9).
- **`rm -rf "$VAR"/*`** está bloqueado por seguridad: usar rutas literales.
