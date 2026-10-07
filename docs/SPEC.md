# SPEC.md — Monetae

> Versión 0.2 · 2026-10-07 · Autor: Adrian (revisión: Claude). Historial de cambios en §18.
> Documento fuente de verdad del producto. Los agentes lo leen junto con `AGENTS.md`.
> Los cambios de alcance se registran como ADR en `docs/decisions/`, no se improvisan en código.

---

## 1. Resumen

**Monetae** es una aplicación web personal de gestión de ingresos y gastos, inspirada en **Cashew** (Flutter, GPL-3.0). Mantiene su interfaz, sus gráficos y su estilo, pero corrige los flujos que hoy rompen el uso diario: préstamos y deudas, cobros con otro medio de pago, intereses y suscripciones que ya no se usan.

El backend es propio (**Python**), con base de datos en servidor, para que más adelante un asistente por Telegram y una app Android trabajen contra los mismos datos.

### Objetivos
1. Reproducir la experiencia de Cashew en web (misma IU) sobre un backend propio.
2. Resolver los problemas de la sección 2.
3. Importar el historial actual desde un backup de Cashew sin perder información.
4. Dejar el diseño preparado (sin implementarlo) para el bot de Telegram (V2), consultas con IA (V3) y app Android (V4).

### No objetivos de V1
Bot de Telegram, clasificador de categorías, Hermes/RAG, app móvil, cuentas de familiares, despliegue en el VPS (es un hito posterior, ver sección 3).

---

## 2. Problemas a resolver (motivo del proyecto)

| ID | Problema en Cashew | Resultado esperado en Monetae |
|----|--------------------|-------------------------------|
| P1 | Al marcar un préstamo como pagado, deja de aparecer en transacciones: parece que nunca existió. | Todo movimiento queda en el historial para siempre. "Saldado" es un estado calculado, no un borrado. |
| P2 | Si el prestamista cobra intereses (p. ej. 5 % o un monto fijo específico ej. S/1) y se registra como transacción normal, la deuda sigue apareciendo pendiente salvo que se use el botón de liquidar. | No existe botón "liquidar". El saldo se calcula solo a partir de los movimientos del préstamo, incluidos los intereses. |
| P3 | Si el préstamo salió de un medio de pago y se cobra por otro, no se refleja: el dinero cobrado vuelve al medio de pago original y el préstamo parece inexistente. | Cada movimiento afecta a la cuenta que realmente se usó. El préstamo registra desembolso y cobros, cada uno con su cuenta. |
| P4 | Una suscripción cancelada (p. ej. Netflix) sigue ocupando espacio en la sección de suscripciones. | Las suscripciones se pueden **archivar** de forma reversible: salen de la vista principal y del total, pero el historial de pagos se conserva. |
| P5 | Copias de seguridad en Google Drive con fallos desde hace meses. | Los respaldos no dependen de Drive (ver 5.11). |

### Contexto técnico de Cashew (a confirmar en la Fase 0)
- Flutter + Drift (SQLite) + Firebase; licencia GPL-3.0; el autor no acepta contribuciones externas.
- Según su README, un préstamo de largo plazo se modela como una **meta (objective)** cuyo total se calcula con transacciones de polaridad contraria. Hipótesis: de ahí nacen P1 a P3. La Fase 0 debe confirmarlo.
- Cashew guarda los datos en el dispositivo y sincroniza vía Firebase; Monetae usará un servidor propio como fuente de verdad.

---

## 3. Versiones

| Versión | Contenido | Dónde corre |
|---------|-----------|-------------|
| **V1** | Todo lo de la sección 5. Un solo usuario (Adrian) con login real. Sin bot. | **Local** (Docker Compose en WSL2) |
| **Hito de despliegue** | Subir V1 al VPS (Contabo Cloud VPS 4: 4 vCPU, 8 GB RAM, 100 GB SSD), HTTPS, respaldos automáticos. | VPS |
| **V2** | Clasificador de categorías entrenado con el historial propio + LLM pequeño por API solo para casos dudosos; bot de Telegram para registrar transacciones; cuentas para familiares (datos aislados por usuario). | VPS |
| **V3** | Asistente Hermes con ChatGPT Plus (más proveedor de respaldo) que consulta datos mediante herramientas (MCP) sobre la API: "¿cuánto me debe Juan?", "¿en qué gasté más este trimestre?". | VPS |
| **V4** | App Android que sincroniza con el servidor. | Móvil |

V2 y V3 **no se implementan en V1**, pero V1 deja listos los datos y endpoints listados en la sección 13.

---

## 4. Usuarios y supuestos

- V1: un único usuario. V2: cuentas independientes para cada familiar (cada uno gestiona *sus* finanzas; no hay datos compartidos).
- Por eso, **todas las tablas llevan `user_id` desde V1** y existe un test de aislamiento con dos usuarios (sección 12).
- Idioma de la interfaz: español (principal) e inglés (secundario) mediante i18n.
- Zona horaria por defecto: `America/Lima`. Moneda base por defecto: `PEN`. Moneda secundaria de uso frecuente: `USD`.
- Es web responsive y se podrá instalar como PWA; no hay app móvil en V1.

---

## 5. Requisitos funcionales de V1

### 5.1 Cuentas (medios de pago) y monedas
- **RF-01** CRUD de cuentas: nombre, tipo (efectivo, banco, billetera digital, tarjeta, otro), **moneda propia** (código ISO 4217), saldo inicial, color/ícono, orden, archivada (sí/no).
- **RF-02** Saldo actual de cada cuenta calculado desde saldo inicial + transacciones. Nunca se guarda un saldo "pegado" editable.
- **RF-03** Transferencia entre cuentas, también entre monedas distintas: se registran ambos montos y se muestra el tipo de cambio implícito.
- **RF-04** Vista de inicio con cuenta/moneda seleccionable y conversión a la moneda de reporte (ver sección 9).

### 5.2 Categorías
- **RF-05** Categorías de ingreso y de gasto, con subcategorías (un nivel), ícono y color. Incluir una categoría de sistema **"Intereses"** (ingreso y gasto) usada por los préstamos.
- **RF-06** Títulos frecuentes → categoría sugerida (equivalente a los "custom titles" de Cashew). Se guarda en una tabla de reglas editable (base para V2, ver sección 13).

### 5.3 Transacciones
- **RF-07** Tipos: ingreso, gasto, transferencia, y los movimientos de préstamo de la sección 5.4.
- **RF-08** Campos: fecha y hora, cuenta, monto, moneda (la de la cuenta), categoría/subcategoría, título, nota/descripción, etiquetas, adjuntos opcionales.
- **RF-09** Transacciones **recurrentes** y **próximas** (programadas, se marcan como pagadas cuando ocurren).
- **RF-10** Búsqueda y filtros: texto, rango de fechas, categoría, cuenta, moneda, etiquetas, persona/préstamo, tipo.
- **RF-11** Selección múltiple para editar o borrar en lote.
- **RF-12** Borrado lógico (`deleted_at`) y deshacer. Las transacciones **nunca** desaparecen por un cambio de estado de otra entidad (P1).

#### Etiquetas (v0.2)
- **RF-43** CRUD de **etiquetas** (`tags`): nombre, color, ícono/emoji, orden y archivada (reversible, igual que las cuentas). El nombre es único por usuario entre las no archivadas.
- **RF-44** **Asignación** de una o varias etiquetas a una transacción (relación N:M `transaction_tags`), desde el formulario de la transacción y en lote mediante la selección múltiple (RF-11). Quitar una etiqueta es borrado lógico del vínculo; archivar una etiqueta no la quita de las transacciones.
- **RF-45** **Filtro básico** por etiquetas dentro de RF-10: una o varias etiquetas, con criterio *cualquiera de ellas* (OR). Sin reglas avanzadas (AND, exclusión) en V1. Las etiquetas **no** afectan a saldos, presupuestos ni a la lógica de préstamos.

### 5.4 Préstamos y deudas (núcleo del proyecto)
Un **préstamo** conecta a una **persona** con una secuencia de movimientos. Ver reglas detalladas y ejemplos en la sección 7.

- **RF-13** Dos direcciones: *presté* (me deben) y *me prestaron* (debo).
- **RF-14** Un préstamo tiene: persona, dirección, moneda del préstamo, monto inicial, fecha, vencimiento opcional, nota.
- **RF-15** Tipos de movimiento: `disbursement` (desembolso inicial), `interest` (interés), `payment` (pago/cobro, parcial o total), `adjustment` (ajuste) y `write_off` (condonación).
- **RF-16** Cada movimiento con efecto de dinero genera su transacción real en **la cuenta elegida para ese movimiento**. Desembolso y cobros pueden usar cuentas y monedas distintas (P3).
- **RF-17** Los pagos pueden ser de cualquier monto y en cualquier cantidad (sin cuotas fijas). Un pago único que cubre todo es un caso más.
- **RF-18** Interés: se registra como movimiento. Debe existir una ayuda "calcular X % sobre el saldo" que propone el monto, editable antes de guardar.
- **RF-19** **Saldo pendiente calculado**, nunca editable ni con botón de liquidar. Estado derivado: `open` (saldo ≠ 0) o `settled` (saldo = 0).
- **RF-20** Vista de detalle: línea de tiempo con todos los movimientos (fecha, cuenta, monto original y monto aplicado al préstamo), saldo acumulado y total pagado.
- **RF-21** Listado de préstamos por persona con saldo total por moneda. Los saldados se muestran en una sección propia, no desaparecen.
- **RF-22** Aviso (no bloqueo) si un pago excede el saldo: se ofrece registrar el exceso como ajuste o como ingreso/gasto.
- **RF-23** Las personas tienen nombre y **alias** (para búsqueda exacta y futuro asistente).

### 5.5 Suscripciones y archivo (P4)
Ver reglas en la sección 8.
- **RF-24** CRUD de suscripciones: título, monto, moneda, cuenta, categoría, periodicidad, próxima fecha de cobro, recordatorio opcional.
- **RF-25** Estados: `active` y `archived`. **Archivar** es reversible; no borra nada.
- **RF-26** Las suscripciones archivadas no aparecen en el listado principal, ni en el total de compromisos mensuales/anuales, ni en el gráfico de suscripciones.
- **RF-27** Sección plegada **"Archivadas"** con el total pagado a lo largo del tiempo, fecha de archivo y botón de reactivar.

### 5.6 Presupuestos
- **RF-28** Presupuestos con periodo mensual, semanal, diario o personalizado (por ejemplo, un viaje).
- **RF-29** Presupuesto general y límites por categoría; posibilidad de asignar solo ciertas transacciones al presupuesto.
- **RF-30** Historial de presupuestos pasados y comparación entre periodos.

### 5.7 Metas
- **RF-31** Metas de gasto y de ahorro con monto objetivo; se asignan transacciones a una meta y se muestra el progreso.
- **RF-32** Las metas **no** se usan para modelar préstamos (a diferencia de Cashew).

### 5.8 Notificaciones
- **RF-33** Centro de notificaciones dentro de la app y notificaciones push web (PWA) para: pagos próximos, renovación de suscripciones, vencimiento de préstamos, umbrales de presupuesto (p. ej. 80 % y 100 %).
- **RF-34** Preferencias por tipo de aviso y anticipación. Las horas respetan la zona horaria del usuario.

### 5.9 Acceso y seguridad
- **RF-35** Login con **Google** (OpenID Connect) y alternativa con correo y contraseña (para no depender de Google en desarrollo local).
- **RF-36** Bloqueo de la app con PIN y/o WebAuthn (huella o rostro del dispositivo) como equivalente web del bloqueo biométrico. Decisión final en ADR-006.
- **RF-37** Sesiones con expiración y cierre de sesión en todos los dispositivos.

### 5.10 Inicio y gráficos
- **RF-38** Pantalla de inicio personalizable con widgets al estilo Cashew: saldo por cuenta/moneda, gasto por categoría, evolución en el tiempo, progreso de presupuestos, próximos pagos, préstamos pendientes, suscripciones activas.
- **RF-39** Tema claro/oscuro y color de acento configurable.

### 5.11 Importación, exportación y respaldos
- **RF-40** **Importador de backup de Cashew** (sección 11).
- **RF-41** Exportación completa en JSON y por tabla en CSV.
- **RF-42** Respaldos que **no dependen de Google Drive**: en V1, script de `pg_dump` con rotación local y botón de exportar; en el VPS, `pg_dump` programado más el snapshot de Contabo. Respaldo en Drive queda como opcional futuro.

---

## 6. Modelo de datos propuesto (no vinculante)

Claude lo finaliza en la Fase 1 (`docs/ARCHITECTURE.md` + `schema` en migraciones Alembic). Convenciones: ver `AGENTS.md`.

Comunes a todas las tablas: `id` (UUID), `user_id`, `created_at`, `updated_at`, `deleted_at` (borrado lógico donde aplique).

| Tabla | Campos clave |
|-------|--------------|
| `users` | email, google_sub (nullable), password_hash (nullable), timezone, base_currency, locale |
| `accounts` | name, type, currency, initial_balance, color, icon, sort_order, archived_at |
| `categories` | parent_id, kind (income/expense), name, icon, color, is_system |
| `people` | name, aliases (lista), note |
| `tags` | name, color, icon, emoji, sort_order, archived_at |
| `transaction_tags` | transaction_id, tag_id (vínculo N:M; únicos mientras no estén borrados lógicamente) |
| `transactions` | account_id, category_id (nullable), kind, amount, currency, occurred_at, title, note, fx_rate_to_base, fx_rate_source, transfer_group_id (nullable), source (`web`/`import`/`telegram`/`api`), raw_input (nullable), categorization_source (`manual`/`rule`/`model`/`llm`) |
| `loans` | person_id, direction (`lent`/`borrowed`), currency, principal, opened_on, due_on (nullable), note |
| `loan_movements` | loan_id, transaction_id (nullable, p. ej. interés devengado sin dinero), kind, amount_in_loan_currency, fx_rate_applied, occurred_at |
| `subscriptions` | title, amount, currency, account_id, category_id, period, next_due_on, status, archived_at, archive_reason |
| `recurring_rules` | plantilla de transacción, periodicidad, próxima fecha |
| `budgets`, `budget_categories`, `budget_transactions` | periodo, monto, límites por categoría, transacciones incluidas |
| `goals`, `goal_transactions` | kind (gasto/ahorro), objetivo, transacciones asignadas |
| `category_rules` | pattern, category_id, source, hits (base de V2) |
| `notifications`, `notification_prefs` | tipo, payload, leída, canal |
| `exchange_rates` | from, to, rate, as_of, source |

Notas:
- `user_id` + `updated_at` + UUID + borrado lógico permiten sincronizar con una app Android en V4 sin rediseñar.
- `amount` siempre `Decimal`/`NUMERIC`, nunca flotante.

---

## 7. Reglas de negocio de préstamos

1. **Saldo del préstamo** (en la moneda del préstamo) = monto inicial + intereses registrados + ajustes − pagos aplicados − condonaciones. Se calcula, no se almacena como dato editable.
2. **Estado**: `settled` si el saldo es exactamente 0; en cualquier otro caso `open`. Un préstamo saldado puede reabrirse registrando un nuevo movimiento.
3. **Efecto en cuentas**: solo los movimientos que mueven dinero crean transacción, y la crean en la cuenta indicada en ese movimiento.
4. **Efecto en estadísticas**:
   - El **capital** (desembolso y la parte de capital de los pagos) **no** cuenta como gasto ni como ingreso en categorías, presupuestos ni gráficos de gasto. Sí cambia el saldo de la cuenta.
   - La parte de **interés** sí cuenta: gasto en la categoría "Intereses" si debo, ingreso en "Intereses" si presté.
   - *Valor por defecto (ADR-003):* el interés se reconoce cuando se paga o cobra (base caja), porque así lo piensa el usuario. Los pagos se asignan primero a interés y luego a capital, editable.
5. **Multi-moneda**: el movimiento guarda el monto en la moneda de la cuenta usada y el monto equivalente aplicado al préstamo, con el tipo de cambio utilizado (editable, ver sección 9).
6. **Orden**: el historial siempre es inmutable en la UI salvo edición explícita de un movimiento, que recalcula saldos. Eliminar un movimiento es borrado lógico.

### Ejemplos que deben convertirse en tests

**Ejemplo A — me prestaron con interés del 5 %**
Juan me presta S/ 200 y entran a la cuenta "Efectivo". Registro interés 5 % = S/ 10, saldo S/ 210. Pago S/ 100 desde "BCP": saldo S/ 110. Pago S/ 110 desde "Efectivo": saldo S/ 0 → `settled`.
Esperado: Efectivo +200 −110; BCP −100; en gastos solo aparece S/ 10 de interés; los tres movimientos siguen visibles en el historial.

**Ejemplo B — presté desde un medio y cobré por otros**
Presto S/ 500 desde "Yape". Me pagan S/ 300 en "Efectivo" y S/ 200 en "BCP".
Esperado: Yape −500, Efectivo +300, BCP +200, saldo 0 → `settled`; las tres transacciones aparecen en la lista de transacciones (P1, P3).

**Ejemplo C — préstamo en dólares cobrado en soles** (cifras ilustrativas)
Presto US$ 100 desde una cuenta USD. Me pagan S/ 380 en una cuenta PEN acordando 3,80.
Esperado: la cuenta PEN sube S/ 380; el préstamo baja US$ 100; el tipo de cambio 3,80 queda guardado en el movimiento.

**Ejemplo D — pago mayor al saldo**
Saldo US$ 50 y recibo US$ 60. Esperado: aviso con opciones para registrar el exceso (ajuste o ingreso); nunca un saldo negativo silencioso.

**Ejemplo E — pagos pequeños y variables**
Préstamo de S/ 1000 con pagos de S/ 50, S/ 120, S/ 30 y S/ 800 en fechas distintas. Esperado: saldo correcto tras cada pago y `settled` solo al llegar a 0.

---

## 8. Reglas de suscripciones y archivo

1. **Archivar**: pasa la suscripción a `archived`, guarda `archived_at` y un motivo opcional, y **cancela los cobros futuros programados**. No toca transacciones pasadas.
2. **Visibilidad**: una suscripción archivada no aparece en el listado principal, ni en los totales mensual/anual de suscripciones, ni en el gráfico de suscripciones, que muestra solo compromisos vigentes.
3. **Sección "Archivadas"**: plegada, con total pagado histórico, última fecha de pago y fecha de archivo.
4. **Reactivar**: botón manual, o sugerencia automática cuando se registra una transacción con el mismo título (el usuario confirma; no se reactiva solo).
5. **Permanencia**: quedar archivada para siempre es válido; no se exige borrar.
6. **Historial**: los pagos pasados siguen en transacciones y en los gráficos de gasto por categoría de los meses en que ocurrieron.

Criterios de aceptación:
- Dado Netflix activa con 3 pagos previos, cuando la archivo, entonces desaparece del listado principal y del total, las 3 transacciones siguen visibles y no hay cobros futuros programados.
- Dado Netflix archivada, cuando registro un pago "Netflix", entonces el sistema sugiere reactivarla y, si acepto, vuelve al listado con su historial.

---

## 9. Reglas multi-moneda (PEN y USD)

1. Cada cuenta tiene **una** moneda; cada transacción hereda la de su cuenta.
2. Cada transacción guarda el **tipo de cambio de su momento** hacia la moneda base (`fx_rate_to_base`) y su origen (`manual` o `auto`). **No se recalcula el pasado** con el cambio de hoy.
3. El tipo de cambio es **manual por defecto** (lo que realmente se pagó o recibió en casa de cambio), con sugerencia automática de una fuente a decidir en ADR-004.
4. Transferencias entre monedas: dos transacciones enlazadas por `transfer_group_id`, con ambos montos reales y la tasa implícita.
5. Reportes: desglose **por moneda** más un total en la **moneda de reporte** (la base por defecto, seleccionable), calculado con las tasas guardadas.
6. Importes en `Decimal` con 2 decimales de persistencia; tasas con 6 decimales. Operar con monedas distintas sin conversión explícita debe lanzar error.
7. Detección de moneda para el futuro bot (V2): `S/` o "soles" → PEN; `$`, "dólares" o "USD" → USD; sin marca → PEN por defecto.

---

## 10. Reportes y API necesarios (V1)

La web los usa para gráficos, y V2/V3 los reutilizan como herramientas. Se construyen **una sola vez**.

- Gasto e ingreso por categoría y periodo (con desglose por moneda y total en moneda de reporte).
- Flujo de caja por periodo y evolución del saldo por cuenta.
- Saldo de préstamos por persona (por moneda) y detalle de movimientos.
- Total de suscripciones activas (mensual/anual) y total pagado de archivadas.
- Avance de presupuestos y metas.
- Búsqueda de personas por nombre o alias.

La API es REST bajo `/api/v1`, con OpenAPI generado y versionado en `docs/api/openapi.json`.

---

## 11. Importador de backup de Cashew

- **RF-40a** Lee el backup de Cashew y carga cuentas, categorías, transacciones, presupuestos, metas, suscripciones, préstamos y etiquetas. **Fuente primaria: el archivo SQLite (`.sql`/`.sqlite`)**, que es la base completa de Cashew; el formato está documentado en `docs/cashew-analysis/03-backup-format.md`. El **CSV es solo un modo de rescate** (ver RF-40h).
- **RF-40b** Idempotente: reimportar el mismo archivo no duplica datos.
- **RF-40c** Modo `--dry-run` y reporte final: conteos por entidad, saldo de cada cuenta antes y después, y lista de elementos que no se pudieron mapear. Los saldos deben coincidir con los de Cashew.
- **RF-40d** Los préstamos modelados en Cashew como metas con transacciones de polaridad contraria se convierten a `loans` + `loan_movements` con una heurística documentada en un ADR. Los casos ambiguos se listan para revisión manual, no se adivinan.
- **RF-40e** Se conservan monedas, fechas y el historial completo. Los primeros meses (agosto a octubre de 2025) se marcan como "datos iniciales" para poder excluirlos de futuros entrenamientos del clasificador (V2) sin borrarlos.
- **RF-40f** El backup real **nunca** se commitea: vive en `reference/backups/` (ignorado por git). Los tests usan fixtures sintéticos.
- **RF-40g** **Siempre sobre una copia.** El importador (y cualquier agente o script) trabaja sobre una **copia** del respaldo y nunca sobre el original: abre el SQLite en modo solo lectura (`mode=ro`) y no escribe en él. El original queda intacto.
- **RF-40h** **CSV solo como rescate.** El CSV de Cashew excluye las transacciones con `paid = false` (entre ellas los préstamos de pago único ya saldados), no incluye identificadores, presupuestos, reglas ni etiquetas. Si se importa un CSV, el reporte lo advierte, la idempotencia se basa en un hash determinista de los campos (no en ids) y los préstamos se listan para revisión manual.
- **RF-40i** **Tolerancia al esquema real.** El respaldo de Adrian es esquema Drift **v48** (versión posterior al código público de Cashew, que está en v46). El importador lee `PRAGMA user_version`, descubre tablas y columnas con `PRAGMA table_info`, ignora las desconocidas y avisa en el reporte; no asume una versión fija.
- **RF-40j** **Etiquetas.** Se importan las tablas `tags` y `transaction_to_tag_links` de Cashew a `tags` y `transaction_tags`, conservando nombre, color, ícono y estado de archivada; las etiquetas con transacciones asociadas nunca se descartan.

---

## 12. Requisitos no funcionales

- **Tipado estricto**: Python con `mypy --strict`, Pydantic v2 en los bordes, `Decimal` para dinero; Dart con análisis estático sin advertencias.
- **Aislamiento de datos**: test automático con dos usuarios que demuestre que ninguno puede leer ni modificar datos del otro.
- **Seguridad**: contraseñas con argon2, secretos solo por variables de entorno, CORS restringido, límite de intentos de login, ningún endpoint sin autenticar salvo login y salud.
- **Privacidad**: sin telemetría; nada de datos reales a servicios externos. En V2, al LLM solo se envía el texto del mensaje y la lista de categorías, nunca la base completa.
- **Rendimiento**: con decenas de miles de transacciones, las pantallas principales responden en menos de 1 s en local (índices por `user_id, occurred_at`).
- **Portabilidad**: todo corre con `docker compose up` en WSL2 (AlmaLinux 9) y en el VPS.
- **Calidad**: la lógica de dominio de préstamos, monedas y suscripciones tiene tests unitarios exhaustivos (incluidos los ejemplos de la sección 7).
- **i18n**: textos de interfaz en archivos de traducción; español por defecto.

---

## 13. Preparación para V2 y V3 (solo datos y endpoints, sin implementación)

- Tabla `category_rules` y columnas `source`, `raw_input` y `categorization_source` en transacciones.
- Tabla `people` con alias.
- Endpoints de reportes de la sección 10 (futuras herramientas MCP).
- Marca de "datos iniciales" en transacciones importadas de los primeros meses.
- Usuarios múltiples soportados por el esquema.
- Nada del bot, del clasificador ni de Hermes se configura en V1.

---

## 14. Criterios de aceptación de V1

- [ ] `docker compose up` levanta API, base de datos y web en local con un solo comando documentado.
- [ ] Los ejemplos A a E de la sección 7 pasan como tests automáticos y también manualmente en la UI.
- [ ] Un préstamo saldado sigue visible en transacciones y en su historial (P1).
- [ ] No existe botón "liquidar"; el interés se refleja en el saldo (P2).
- [ ] Un cobro en otra cuenta o moneda actualiza la cuenta correcta (P3).
- [ ] Archivar y reactivar una suscripción cumple la sección 8 (P4).
- [ ] El importador procesa una **copia** del backup real de Adrian (SQLite) en modo `--dry-run` con saldos idénticos a Cashew, e importa sus etiquetas.
- [ ] Etiquetas: se crean, se asignan a transacciones (también en lote) y se filtran por una o varias.
- [ ] Presupuestos, metas, notificaciones web, login con Google, bloqueo con PIN/WebAuthn y exportación funcionan.
- [ ] `mypy --strict`, `ruff` y todos los tests pasan; test de aislamiento entre usuarios incluido.
- [ ] La interfaz es reconocible respecto a Cashew en inicio, transacciones, presupuestos y suscripciones.
- [ ] `docs/` está actualizado (arquitectura, ADRs, OpenAPI).

---

## 15. Decisiones abiertas (ADR) para la Fase 1

| ADR | Tema | Valor por defecto propuesto |
|-----|------|-----------------------------|
| 001 | Estrategia de interfaz: fork de Cashew (Flutter) con capa de datos sobre la API, o reescritura | **ACEPTADO (2026-10-07): opción A**, UI propia en Flutter Web reutilizando y desacoplando widgets de Cashew. Ver `docs/decisions/001-ui-strategy.md` |
| 002 | Autenticación y sesiones | Google OIDC + correo/contraseña; sesiones con cookie `HttpOnly` o JWT corto con refresh |
| 003 | Reconocimiento contable del interés | Base caja, pagos asignados primero a interés |
| 004 | Fuente del tipo de cambio automático | Manual por defecto; fuente automática a elegir |
| 005 | Modelo de sincronización para Android | UUID + `updated_at` + borrado lógico |
| 006 | Bloqueo biométrico en web | PIN y WebAuthn |
| 007 | SQLAlchemy síncrono o asíncrono | Síncrono con psycopg 3 |

Si la Fase 0 muestra que el fork de Flutter es demasiado invasivo, Claude **pregunta a Adrian antes** de cambiar la estrategia.

---

## 16. Fuera de alcance de V1

Bot de Telegram, clasificador de categorías, asistente Hermes, RAG, app Android, cuentas compartidas entre usuarios, respaldo en Google Drive, banca abierta o importación automática desde bancos.

---

## 17. Glosario

- **ADR**: registro de decisión de arquitectura.
- **Desembolso**: entrega inicial del dinero de un préstamo.
- **Saldo pendiente**: lo que falta por pagar o cobrar de un préstamo, calculado.
- **Archivar**: ocultar de forma reversible sin borrar historial.
- **Moneda base / de reporte**: moneda en la que se suman totales de varias monedas.

---

## 18. Historial de cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 0.1 | 2026-10-05 | Versión inicial. |
| 0.2 | 2026-10-07 | **Etiquetas** (RF-43 a RF-45, tablas `tags` y `transaction_tags`, criterio de aceptación). **Importador** (§11): SQLite como fuente primaria y CSV solo de rescate (RF-40a, RF-40h), trabajo siempre sobre una copia (RF-40g), tolerancia al esquema v48 (RF-40i) e importación de etiquetas (RF-40j). ADR-001 marcado como aceptado (§15). Aprobado por Adrian. |
