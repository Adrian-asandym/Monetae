# T-515 · Formulario de transacción fiel a Cashew (piezas 2–6)

> Lee primero `docs/STATUS.md`, `AGENTS.md` y la skill **`.claude/skills/cashew-form-transaccion/SKILL.md`** (manda sobre esta spec en el aspecto visual). La pieza 1 ya está hecha por el coordinador (`83a3e62`): úsala como base y estilo.

- **Agente:** Codex `gpt-6.1-sol`, esfuerzo high.
- **Rama/worktree:** `claude/T-515-form-transaccion` en `/home/artur/propio2/Monetae-claude-T-515-form-transaccion` (continúa sobre la pieza 1; **no** crees otra rama).
- **Una pieza por lanzamiento**, en este orden: 2 → 3 → 4 → 5 → 6. **Un commit por pieza** (`feat(web): … (T-515 piece N)`), sin push, y detente: el coordinador verifica en `localhost:8080` antes de lanzar la siguiente.

## Contexto
- Capturas de referencia (solo lectura, ignoradas por git): `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/11.png … 19.png` (lado derecho = Cashew a 400×642 con escala 1,25 px/dp).
- Código de Cashew (solo lectura, GPL-3.0; cita el origen en la cabecera del archivo como ya hace el repo): `/home/artur/propio2/Monetae/reference/Cashew/budget/lib/` — `pages/addTransactionPage.dart` (`SelectTitle`, flujo líneas ~930–1030), `widgets/selectAmount.dart`, `widgets/selectCategory.dart`, `widgets/openBottomSheet.dart`, `widgets/selectChips.dart`.
- **Prohibido** leer o tocar `reference/backups/`.
- Pieza 1 (ya hecha): `apps/web/lib/pages/new_transaction_page.dart`, `apps/web/lib/widgets/transaction_form/form_controls.dart` (pestañas, cabecera, fecha, chips, campos, barra), `form_sheet.dart` (`showFormSheet`, `FormSheetButton`), tokens `TransactionFormColors` / `TransactionFormTokens` en `apps/web/lib/theme/monetae_theme.dart` (colores medidos en las capturas), `formatTypedAmount` en `presentation/currency_format.dart`.

## Reglas
- **Solo presentación.** No cambies `NewTransactionController` (validación, idempotencia, tasa de 6 decimales, `posted/scheduled`), DTOs, `ApiClient`, el contrato ni el backend.
- Todo color/medida nuevo va a `TransactionFormColors` / `TransactionFormTokens`; nada suelto en widgets. Textos nuevos en `lib/l10n/app_es.arb` y `app_en.arb` (`flutter gen-l10n`); encabezados de hoja en **Title Case** como en Cashew.
- Lo que no existe en el modelo queda **visible con `// TODO(T-515): …`** y handler vacío: Suscripción, Repetitivo, Prestar, Deuda, Transferir, adjunto, operadores de calculadora, «Incluir importe», «Excluir del presupuesto».
- Formatea **solo los archivos que tocas** (`dart format <archivos>`), nunca `dart format lib` entero.
- Archivos permitidos: `apps/web/lib/pages/new_transaction_page.dart`, `apps/web/lib/widgets/transaction_form/**`, `apps/web/lib/widgets/decimal_number_pad.dart`, `apps/web/lib/widgets/transaction_category_grid.dart`, `apps/web/lib/theme/monetae_theme.dart`, `apps/web/lib/l10n/*`, `apps/web/test/new_transaction_test.dart`, `apps/web/test/goldens/new_transaction_*.png`. Cualquier otro: pregunta (`ask`).

## Piezas

### 2 · Hoja de título (captura 11)
- Al abrir el formulario desde «+», tras el primer frame (y cuando `loading` termina) se abre la hoja «Escribe Un Título» sobre el formulario atenuado. Solo en modo crear (`editing == false`).
- Contenido: título 26 dp negrita + icono calendario a la derecha (abre `_pickDate`); campo «Título» (mismo `FormFilledField`) con autofocus; botón «Selecciona una categoría» a todo ancho (`FormSheetButton`, 4 esquinas redondeadas).
- El botón guarda el título y **encadena** la hoja de categorías; Enter en el campo hace lo mismo. Cerrar la hoja (tocar fuera / deslizar) deja el formulario con el título escrito.
- El campo «Título» del formulario debe mostrar el mismo texto: pásalo a un `TextEditingController` sincronizado.
- Claves de prueba: `title-sheet`, `title-sheet-field`, `title-sheet-next`.

### 3 · Hoja de categorías (captura 15)
- Sustituye la hoja provisional de `_openCategorySheet`: título «Selecciona Una Categoría» + ⋮ a la derecha (TODO, sin acción). Cuadrícula de 4 columnas con scroll vertical (hoja alta, `expand`).
- Celda: cuadrado ≈ 64 dp, radio ≈ 14 dp, **fondo sólido del color de la categoría**, icono claro grande (usa `CategoryIcon` con color blanco); debajo nombre 12–13 dp centrado y truncado con «…». Primera celda «Sin categoría» (fondo neutro). Espaciado ≈ 9 dp. Selección: borde claro de 3 dp.
- Al elegir: cierra la hoja y **abre la hoja de importe** (orden de Cashew). Conserva claves `form-category-<id>` / `form-category-none`. Puedes adaptar `TransactionCategoryGrid` (solo lo usa el formulario).

### 4 · Hoja de importe (captura 16)
- Sustituye la hoja provisional de `_openAmountSheet`: título «Introduce El Importe»; importe 40 dp negrita alineado a la derecha (`formatTypedAmount`, se actualiza en vivo); fila de cuentas (▼ + chips, igual que la fila 2 del formulario, misma `_selectAccount`); teclado 4×4 en contenedor redondeado (`TransactionFormTokens.keypad*`, color `keypad`): `1 2 3 ÷` / `4 5 6 ×` / `7 8 9 -` / `, 0 ⌫ +`, teclas sin borde, números ≈ 30 dp. La coma escribe el separador decimal (`'.'` interno). Operadores visibles e **inactivos** (TODO calculadora).
- «Fijar importe» (`FormSheetButton`, clave `amount-sheet-done`) cierra y vuelve al formulario.
- Teclado físico: dígitos, `.`/`,`, Backspace y Enter (= Fijar).
- Mantén las claves `amount-key-<0-9>`, `amount-key-.`, `amount-key-backspace` (pulsación larga = borrar todo).

### 5 · Más opciones (captura 14)
- La píldora despliega (y la oculta): divisor con «Más opciones» centrado en gris; tarjeta «Incluir importe» (fondo `card`, radio 16, icono check en círculo, texto negrita, `Switch` activado por defecto, TODO sin efecto en el modelo); sección «Excluir del presupuesto» (texto gris ≈ 18 dp) con chips de presupuestos (borde de su color, **selección múltiple**, estado local) y botón «+» (TODO F1).
- Claves: `form-more-options`, `form-include-amount`, `form-exclude-budget-<id>`.

### 6 · Modal de tipos (capturas 17–19)
- El ⓘ de la fila 1 (`form-type-info`) abre una hoja casi a pantalla completa «Seleccionar El Tipo De Transacción» con tarjetas (radio 16, fondo gris oscuro, borde fino, icono + nombre negrita ≈ 22 dp, ⋮ en las que lo llevan, viñetas ≈ 15 dp) con los **textos exactos** de la skill, y al final el panel explicativo con los 5 botones circulares y la entrada de ejemplo.
- Tocar una tarjeta llama a la misma `_selectType` de los chips y cierra la hoja; la tarjeta seleccionada va con fondo más claro (estado compartido con la fila 1).
- Claves: `type-sheet`, `type-card-<FormTransactionType.name>`.
- **Aviso (decisión de Adrian, 2026-10-11):** si el tipo elegido es Suscripción, Repetitivo, Prestar o Deuda, muestra bajo la fila 1 una nota pequeña gris (≈ 12 dp): «Aún no disponible: se guardará como transacción normal» (clave `form-type-notice`; texto en ARB es/en).

## Criterios de aceptación (por pieza)
1. La pieza coincide con su captura (posiciones, tamaños, colores, textos) a 400×642 en oscuro; claro coherente.
2. `cd apps/web && dart analyze` sin avisos y `flutter test` **todo verde** (pega el resumen final).
3. Pruebas nuevas en `test/new_transaction_test.dart` para el comportamiento de la pieza (encadenado de hojas, teclado, despliegue, selección de tipo). Las pruebas existentes de lógica (idempotencia, reintentos, 401, tasa, errores 422) siguen pasando.
4. Goldens `new_transaction_*` regenerados **con texto visible** y versionados si cambia el formulario.
5. `flutter build web --release` compila.
6. Sin cambios fuera de los archivos permitidos; sin datos reales; sin dependencias nuevas.
7. En tu respuesta final: archivos tocados, TODO añadidos y cualquier diferencia con Cashew y su motivo.

---

## Ajustes v2 de Adrian (capturas 20–25) — piezas 7–9

> Pedido por Adrian el 2026-10-12. Capturas (solo lectura, ignoradas por git): `/home/artur/propio2/Monetae-master-dev/reference/cashew-inicio-ui/20.png … 25.png` (izquierda = Monetae hoy, derecha = Cashew, objetivo). Identifícalas por su número. Mismas **Reglas**, **Contexto** y **Criterios de aceptación** de arriba; **una pieza por lanzamiento** y un commit por pieza. Los saldos y nombres de cuenta que ves en las capturas son de Adrian: **no los copies** a código, pruebas ni goldens (usa los datos sintéticos de las pruebas).
> Las piezas 10 (pantalla «Transferir saldo», capturas 24–25) y 11 (tipo de cambio con sugerencia) se especificarán aparte: dependen de una decisión de Adrian sobre el modelo de transferencia.

### 7 · Nombre de la categoría bajo el monto (captura 20)
- En la cabecera, **debajo del monto**, el nombre de la categoría elegida: alineado a la derecha como el monto, ≈ 20 dp, blanco ~70 %, una línea con «…» si es largo. Sin categoría no se muestra nada (ni reserva hueco visible).
- Sube el bloque del monto ≈ 10 dp para dejar sitio al nombre, como en Cashew.
- En modo crear, el botón inferior dice **«Agregar transacción»** (en: «Add transaction»), no «Guardar transacción». Si existe modo editar, conserva su texto actual.
- Commit: `feat(web): category name under amount and add button label (T-515 piece 7)`.

### 8 · Hoja «Seleccionar Cuenta» (capturas 21 y 22)
- Sustituye la hoja «Todas las cuentas» por la de Cashew: título **«Seleccionar Cuenta»** (negrita ≈ 26 dp) con ⋮ a la derecha (solo diseño: handler vacío + `TODO(T-515)`), esquinas superiores ≈ 28 dp, hoja alta (≈ 65 % de la pantalla) con scroll interno.
- Filas ≈ 48 dp, ancho completo, padding horizontal ≈ 16 dp: radio (círculo vacío, borde ≈ 2 dp del color de la cuenta) + nombre en blanco ≈ 20 dp + **saldo actual** a la derecha en blanco ≈ 18 dp con el formato «120,50 S/. PEN», «35,00 $ USD», «0 S/. PEN» (formato de montos de la skill + espacio + código ISO; aquí sí va el código, por pedido expreso de Adrian).
- Cuenta seleccionada: radio relleno por dentro y fila con fondo del color de la cuenta a ~30–35 % de opacidad, radio ≈ 12 dp. En la captura 21 la fila con fondo tenue es un estado hover/pressed: no es un estado permanente (sí puede usarse como efecto de hover/pulsación).
- Quita los puntos de color rellenos, el nombre coloreado de la seleccionada y el símbolo suelto a la derecha de la hoja actual.
- Se abre desde **dos sitios**: el botón ▼ de la fila de cuentas del formulario (21) y el ▼ de la hoja «Introduce El Importe» (22). En el segundo caso se **apila** sobre la hoja del importe (que queda atenuada detrás). Al elegir una cuenta se cierra **solo** esta hoja y la selección se actualiza en ambos lugares (un único estado compartido: la cuenta del controlador).
- Haz la hoja reutilizable (widget/función propia en `widgets/transaction_form/`): la pieza 10 la usará para origen y destino.
- Commit: `feat(web): Cashew account selection sheet (T-515 piece 8)`.

### 9 · Menú ⋮ del formulario (captura 23)
- El ⋮ de la esquina superior derecha abre una hoja inferior con título **«Agregar Transacción»** («Editar Transacción» en modo editar, si existe), negrita ≈ 26 dp. Lista sin separadores; filas con padding vertical ≈ 12 dp y horizontal ≈ 16 dp: icono a la izquierda (≈ 28 dp, gris claro), título en negrita ≈ 20 dp (hasta 2 líneas), subtítulo regular ≈ 16 dp (blanco ~80 %) y a la derecha un interruptor (todos activados por defecto) o un chevron ›. Textos exactos (es; traduce en en):
  a. «Pestaña de transferencia de saldo» / «En la página 'Agregar nueva transacción'» (icono ⇄, interruptor)
  b. «Botón Agregar archivos adjuntos» / «Mostrar debajo de la sección de notas» (icono de clip, interruptor)
  c. «Agregar títulos automáticamente» / «Cuando se crea una transacción» (icono de nota con +, interruptor)
  d. «Indicaciones iniciales de entrada» / «Al añadir una transacción por primera vez» (icono de edición, chevron)
- Persistencia: si Monetae ya tiene un mecanismo de ajustes locales del navegador, úsalo; si no, estado en memoria compartido (una clase pequeña de ajustes del formulario) + `TODO(T-515): persist`. **Sin dependencias nuevas** y sin tocar el contrato ni `users/me`.
- Funcionales solo **(a)** (muestra u oculta la pestaña Transferir; con ella oculta, las pestañas Gasto/Ingreso ocupan todo el ancho) y **(b)** (muestra u oculta la fila de adjunto bajo Notas). (c) y (d) quedan como diseño con `TODO`.
- **Investigación (sin implementar):** en el código de Cashew, ¿qué controla exactamente (c)? Hipótesis de Adrian: si aparece la hoja inicial de título (captura 11). ¿Y qué abre (d)? Responde con archivo y línea en tu `worker_done`.
- Commit: `feat(web): add transaction options menu (T-515 piece 9)`.
