---
name: cashew-form-transaccion
description: Diseño del flujo y del formulario de agregar/editar transacción de Monetae (Flutter web) fiel a Cashew — hoja inicial de título, cabecera con pestañas e importe, filas de etiquetas (tipo, cuenta, presupuesto, objetivo, préstamo), título, notas y adjunto, "Más opciones", hojas de categoría e importe, modal de tipos de transacción, hoja "Seleccionar Cuenta", menú ⋮ del formulario, pantalla "Transferir saldo" y hoja "Tipo De Cambio". Úsala siempre que se cree o modifique el botón "+", el formulario de transacción, las hojas de categoría o importe, o cualquier pantalla de agregar/editar transacción. Complementa a cashew-inicio-ui.
---

# Formulario de transacción de Monetae → fiel a Cashew

Complementa la skill `cashew-inicio-ui` (la skill `cashew-ui` que se citaba no existe). Aplican igual sus reglas: solo presentación (no tocar modelos ni lógica de datos), reutilizar los tokens de tema (colores, radios, tipografía, formato de montos; no crear valores sueltos por widget), calibrar las medidas, un componente a la vez y un commit por pieza. Las medidas de abajo son aproximaciones leídas de las capturas (1 dp ≈ 1.25 px, viewport 400×642): calíbralas con el código de Cashew (https://github.com/jameskokoska/Cashew, clonado fuera del repo, solo lectura) o midiendo píxeles. **Regla (2026-10-12):** si una medida en dp de una pauta no cuadra con la captura, probablemente se midió en px (escala 1,25); manda el código de Cashew + la captura, y se anota la medida final y su fuente. El clon local de Cashew es **anterior** a las capturas 20–25: lo que no existe en el código sigue las capturas.

## Identificación de las capturas

Las capturas se identifican por el número con que las nombró el usuario (imagen 11 … imagen 19). NO las renombres. Búscalas con Glob por ese número. Verifica que cada una coincida con la tabla; si alguna no coincide, repórtalo en vez de adivinar. En ellas, el lado derecho es Cashew (objetivo) y el izquierdo, cuando aparece, es Monetae hoy.

| N.º | Contenido |
|---|---|
| 11 | Hoja inferior "Escribe Un Título", inicio del flujo, sobre el formulario atenuado |
| 12 | Formulario arriba: pestañas, importe, fecha, filas de etiquetas, Título y botón inferior "Selecciona una categoría" |
| 13 | Formulario desplazado: Título, panel de Notas con "Añadir un adjunto" y botón "Más opciones" |
| 14 | "Más opciones" desplegado: "Incluir importe" y "Excluir del presupuesto" |
| 15 | Hoja "Selecciona Una Categoría" (cuadrícula) |
| 16 | Hoja "Introduce El Importe": importe, etiquetas de cuenta, teclado y "Fijar importe" |
| 17 | Modal "Seleccionar El Tipo De Transacción", parte superior (Predeterminado, Próximamente, Suscripción, Repetitivo) |
| 18 | El mismo modal, parte media (Repetitivo, Prestar, Deuda) |
| 19 | El mismo modal, final (Prestar, Deuda y panel explicativo con ejemplo) |
| 20 | Cabecera con el nombre de la categoría bajo el monto y botón "Agregar transacción" |
| 21 | Hoja "Seleccionar Cuenta" abierta desde el ▼ de la fila de cuentas del formulario |
| 22 | La misma hoja apilada sobre "Introduce El Importe" |
| 23 | Menú ⋮ del formulario: hoja "Agregar Transacción" con 4 opciones |
| 24 | Pantalla "Transferir saldo" (tarjetas de origen y destino, tasa, fecha, "Transferir cantidad") |
| 25 | Diálogo ⓘ de "Transferir saldo" |

Las capturas 20–25 están en `reference/cashew-inicio-ui/` del worktree `master-dev` (ignoradas por git; los nombres y saldos que muestran son reales: no copiarlos). Las imágenes 17–19 son tres tramos de scroll del mismo modal. Si el orden numérico real difiere del de la tabla, guíate por el contenido.

## Estado actual de Monetae (lo que hay que reemplazar)

Pantalla única con AppBar "Añadir transacción" de color distinto, selector Gasto/Ingreso, campo "Importe" con teclado numérico en línea, cuadrícula "Categoría (opcional)", desplegable "Cuenta", campos con subrayado ("Título (opcional)", "Nota (opcional)"), botones de fecha y hora con la leyenda "Hora de Lima · UTC-5", chip "Publicada" y botón azul claro "Guardar transacción". Todo con tinte navy.

## Flujo (imágenes 11 → 15 → 16 → 12)

1. Al tocar el "+" (FAB) se abre el formulario (imagen 12) y encima, de inmediato, la hoja de título (imagen 11). El formulario queda atenuado detrás (scrim).
2. Hoja de título (imagen 11): el título es opcional. Se puede escribir un título y pulsar "Selecciona una categoría" (guarda el título y abre la hoja de categorías), pulsar ese botón sin escribir nada, o cerrar la hoja (tocar fuera o deslizar) y quedar en el formulario.
3. Hoja de categorías (imagen 15): al elegir una categoría, la hoja se cierra y se abre la hoja de importe (imagen 16). En la captura 16 se ve la categoría ya elegida detrás, lo que indica este orden; verifícalo en el código de Cashew.
4. Hoja de importe (imagen 16): "Fijar importe" la cierra y vuelve al formulario (imagen 12) con el icono de categoría y el importe en la cabecera.
5. En el formulario, tocar el importe reabre la hoja 16, tocar el icono de categoría o el botón inferior reabre la hoja 15, y el campo "Título" del formulario edita el mismo título.
6. El botón inferior dice "Selecciona una categoría" mientras no haya categoría elegida; después pasa a ser el botón de guardar: **"Agregar transacción"** en modo crear (como Cashew) y "Guardar transacción" en modo editar. Monetae hoy permite "Sin categoría": mantén esa opción como primera celda de la cuadrícula y cuenta como elección válida.
7. El mismo formulario sirve para editar: título de pantalla "Editar transacción" (en crear, "Agregar transacción").

## Título de pantalla y cabecera (imagen 12)

- AppBar sin color propio (mismo fondo de página): flecha atrás a la izquierda, título centrado en negrita ("Agregar transacción"), menú ⋮ a la derecha.
- Pestañas en tres partes iguales: "Gasto" (▼ rojo), "Ingreso" (▲ verde) y "Transferir" (icono ⇄). La seleccionada tiene fondo más claro, las demás más oscuro; alto ≈ 50 dp. "Transferir" se añade como diseño; si Monetae no tiene transferencias, queda visual con TODO y se reporta.
- Bloque de importe (≈ 136 dp de alto), fondo gris azulado oscuro (color de acento del tema atenuado): a la izquierda un cuadrado redondeado de ≈ 80 dp (oscuro y vacío sin categoría; con la categoría elegida muestra su icono sobre su color); a la derecha el importe en negrita ≈ 36 dp alineado a la derecha ("0 S/.", mismo formato de montos de cashew-ui). Tocarlo abre la hoja 16.
- **Nombre de la categoría bajo el monto (imagen 20):** alineado a la derecha, 18 dp, blanco ~70 %, hasta 2 líneas con "…" (`addTransactionPage.dart:1974–1977`; TAM = A, T-520); sin categoría no se muestra. El bloque del monto sube ≈ 10 dp.
- La pestaña "Transferir" abre la **pantalla aparte "Transferir saldo"** (imagen 24) y puede ocultarse desde el menú ⋮.

## Fecha (imagen 12)

Contenedor redondeado (≈ 46 dp, radio ≈ 14 dp, gris oscuro): a la izquierda icono de calendario sobre un cuadrado más oscuro, "Hoy" en negrita ≈ 24 dp (si la fecha es otra, muestra la fecha corta), y a la derecha la hora en cajas oscuras "21 : 16". Tocar la fecha o la hora abre sus selectores actuales. La leyenda "Hora de Lima · UTC-5" de Monetae se conserva como texto pequeño y gris bajo este contenedor (no existe en Cashew; es lo único añadido aquí).

## Filas de etiquetas (imágenes 12 y 13)

Cinco filas de chips con scroll horizontal, en este orden y con estas posiciones. Chip: alto ≈ 38 dp, radio ≈ 12 dp, borde de ≈ 1.5 dp del color de la entidad (cuenta/presupuesto/objetivo/préstamo) y texto ≈ 16–17 dp. El chip seleccionado va relleno en gris (#4A4A4A aprox., calibrar) con texto claro. Selección única en las 5 filas.

1. Tipo de transacción: icono ⓘ a la izquierda (abre el modal de las imágenes 17–19) + chips "Predeterminado" (seleccionado por defecto), "Próximamente", "Suscripción", "Repetitivo", "Prestar", "Deuda".
2. Método de pago: botón cuadrado con ▼ a la izquierda (abre la lista completa de cuentas) + un chip por cuenta con el color de la cuenta (Banco, Dólares, Efectivo… en Monetae).
3. Presupuesto: "Sin presupuesto" (por defecto) + un chip por presupuesto con su color. Al final, botón cuadrado "+" para crear uno.
4. Objetivo: "Sin objetivo" (por defecto) + un chip por objetivo. Al final, botón cuadrado "+" para crear uno (visible en la captura 13).
5. Préstamo: "Sin préstamo" (por defecto) + un chip por préstamo a alguien (nombre de la persona).

Los botones "+" abren los formularios de creación que ya existan en Monetae (los mismos de cashew-ui, ajuste 1 de Inicio). Si alguno no existe, no lo construyas: repórtalo. Verifica en el código de Cashew si la fila de presupuestos y la de préstamos también llevan "+".

Mapeo con el modelo actual: el estado "Publicada" de Monetae equivale a "Predeterminado" (y "Próximamente" a una transacción no publicada). Los datos que ya existen (préstamos/deudas, estado publicada) se conectan; "Suscripción", "Repetitivo" y cualquier otro que no exista en el modelo quedan solo como diseño con TODO y se reportan.

## Título, Notas y adjunto (imagen 13)

- Título: campo relleno gris oscuro, radio ≈ 14 dp, alto ≈ 44 dp, placeholder "Título" en gris a la izquierda y el icono "T" a la derecha. Sin subrayado.
- Notas: contenedor relleno de ≈ 90 dp de alto con el mismo radio y color. Placeholder "Notas" arriba a la izquierda y icono de nota abajo a la derecha. En la parte inferior del mismo contenedor, separado por una línea fina: icono de clip + "Añadir un adjunto" + "+" a la derecha. El adjunto es solo diseño por ahora (handler vacío con TODO).
- Debajo, centrado, botón píldora "Más opciones" (gris oscuro, texto gris, radio ≈ 12 dp) que despliega la sección de la imagen 14.

## Más opciones (imagen 14)

- Al desplegar, aparece una línea divisoria con el texto "Más opciones" centrado en gris.
- Tarjeta "Incluir importe": fondo gris, radio ≈ 16 dp, icono de check en círculo a la izquierda, texto en negrita y un interruptor a la derecha. Por defecto activado. Desactivado = la transacción se crea sin afectar el balance (y viceversa); conecta con el modelo solo si ya lo soporta, si no, solo diseño con TODO.
- Sección "Excluir del presupuesto" (texto gris ≈ 18 dp) con chips de los presupuestos (borde del color de cada presupuesto) y un botón cuadrado "+" al final. Selección múltiple: los seleccionados se muestran rellenos.

## Botón inferior (imágenes 11, 12, 13)

Barra pegada abajo con esquinas superiores redondeadas (≈ 28 dp), de ≈ 60 dp de alto, fondo gris azulado claro (≈ #8D99A5, calibrar) y texto oscuro centrado ≈ 19 dp. Texto "Selecciona una categoría" mientras falte la categoría; luego es el botón de guardar. Reemplaza al botón azul claro actual.

## Hoja de título (imagen 11)

Hoja inferior sobre scrim, esquinas superiores ≈ 28 dp, fondo gris oscuro (≈ #2B2B2B, calibrar), padding ≈ 16 dp. Título "Escribe Un Título" en negrita ≈ 26 dp con icono de calendario a la derecha (cambia la fecha; si complica, solo diseño). Debajo, el campo "Título" (igual que en el formulario) y el botón "Selecciona una categoría" a todo el ancho (mismo estilo que la barra inferior, aquí con las 4 esquinas redondeadas ≈ 20 dp).

Los encabezados de las hojas van en Title Case como en Cashew: "Escribe Un Título", "Selecciona Una Categoría", "Introduce El Importe", "Seleccionar El Tipo De Transacción".

## Hoja de categorías (imagen 15)

Misma hoja: título "Selecciona Una Categoría" en negrita ≈ 26 dp y ⋮ a la derecha. Cuadrícula de 4 columnas con scroll vertical. Cada celda: cuadrado redondeado ≈ 64 dp (radio ≈ 14 dp) con el color de la categoría como fondo sólido y su icono grande, y debajo el nombre ≈ 12–13 dp, centrado y truncado con "…". Monetae hoy usa celdas con fondo oscuro teñido: cámbialas por fondo sólido del color de cada categoría (mantén los iconos actuales de Monetae, en claro, si no hay ilustraciones). Espaciado ≈ 9 dp.

## Hoja de importe (imagen 16)

- Título "Introduce El Importe" en negrita a la izquierda.
- Importe en negrita ≈ 40 dp, alineado a la derecha ("40 S/.").
- Fila de cuentas entre el importe y el teclado: botón cuadrado ▼ + chips de cuenta (la cuenta activa seleccionada), igual que la fila 2 del formulario.
- Teclado dentro de un contenedor redondeado (≈ 24 dp, gris ≈ #3A3A3A) con 4 filas × 4 columnas: `1 2 3 ÷` / `4 5 6 ×` / `7 8 9 -` / `, 0 ⌫ +`. Teclas sin borde, número ≈ 32 dp, coma decimal. La columna de operadores ya forma parte del diseño; implementa la calculadora solo si es simple y, si no, deja los operadores solo visibles con TODO y repórtalo.
- Botón "Fijar importe" a todo el ancho (≈ 48 dp, radio ≈ 20 dp, gris azulado con texto oscuro).
- Elimina el campo "Importe" y el teclado en línea del formulario actual.

## Modal de tipos de transacción (imágenes 17, 18, 19)

Se abre con el ⓘ de la primera fila. Hoja a casi pantalla completa con título "Seleccionar El Tipo De Transacción" (negrita ≈ 26 dp, 2 líneas) y una pila de tarjetas con scroll. Cada tarjeta: radio ≈ 16 dp, fondo gris oscuro, borde fino gris, icono + nombre en negrita ≈ 22 dp y, en las que lo llevan, ⋮ a la derecha; después viñetas en blanco ≈ 15 dp. Al tocar una tarjeta se selecciona ese tipo y se cierra el modal. Textos (exactos, en español):

- Predeterminado: solo icono de check en círculo y título (tarjeta con fondo más claro cuando está seleccionada).
- Próximamente (icono de calendario): "Una transacción que no está pagada" / "No cuenta para su total a menos que sea marcado como 'Pagado' o 'Depositado'".
- Suscripción (calendario con flecha de repetición): "Transacción recurrente que se mostrará en la página de suscripciones" / "No cuenta para su total a menos que sea marcado como 'Pagado' o 'Depositado'" / "Próxima transacción generada cuando la actual está marcada como "Pagada" o "Depositada"".
- Repetitivo (icono de repetir): "Transacción recurrente" / "No cuenta para su total a menos que sea marcado como 'Pagado' o 'Depositado'" / "Próxima transacción generada cuando la actual está marcada como "Pagada" o "Depositada"".
- Prestar (icono de archivo con flecha arriba): "Transacción que prestaste" / "Flujo de caja negativo hasta que se marque como 'Recolectado'".
- Deuda (icono de archivo con flecha abajo): "Transacción prestada de alguien" / "Flujo de caja positivo hasta que se marque como 'Liquidado'".
- Al final, un panel más oscuro con borde, con texto centrado "Marque una transacción especial tocando el botón de acción en la entrada de la transacción", una fila de 5 botones circulares grises (calendario, calendario con flecha, repetir, archivo arriba, archivo abajo) y debajo una entrada de transacción de ejemplo (avatar gris con el icono de repetir resaltado en círculo rojo, título recortado, chip de cuenta, icono de nota, hora, "▼ 100 S/.").
- El chip "Predeterminado/Próximamente/…" de la fila 1 y este modal comparten el mismo estado.

## Hoja "Seleccionar Cuenta" (imágenes 21 y 22)

- Título "Seleccionar Cuenta" (negrita) con ⋮ a la derecha (solo diseño, TODO), esquinas superiores ≈ 28 dp, ≈ 65 % de la pantalla con scroll interno.
- Filas ≈ 48 dp a todo el ancho: radio vacío con borde del color de la cuenta + nombre (18 dp, hasta 3 líneas con elipsis; `radioItems.dart:107–111`) + saldo actual a la derecha con **símbolo y código ISO** ("120,50 S/. PEN", "35 $ USD", "0 S/. PEN": formato de montos de Cashew, sin decimales cero).
- Seleccionada: radio relleno y fila con fondo del color de la cuenta a ~30–35 %, radio 15 dp (`radioItems.dart:69`; web, TAM = A, T-520). El fondo tenue de la imagen 21 es hover/pressed, no un estado fijo.
- Padding de fila: inicio 16 dp y final 7 dp al mostrar saldo; contenido del título desplazado 12 dp hacia el inicio y separación antes del saldo 3 dp (`radioItems.dart:80–83,127`). `ListTile` denso, mínimo 48 dp; crece para nombres largos. Se conserva el escalado del saldo exacto para cuentas con importes largos.
- Se abre desde el ▼ del formulario y desde el ▼ de la hoja de importe (apilada encima); al elegir se cierra solo esta hoja y la selección es un único estado compartido. Es reutilizable (la usa "Transferir saldo" para origen y destino). Código: `apps/web/lib/widgets/transaction_form/account_selection_sheet.dart`.

## Menú ⋮ del formulario (imagen 23)

- Hoja "Agregar Transacción" ("Editar Transacción" al editar), título 23 dp negrita (`popupFramework.dart:117`). Filas sin separadores: icono gris claro a la izquierda, título negrita 16 dp y subtítulo 14 dp (`settingsContainers.dart:120,653,669`), interruptor (activados por defecto) o chevron. Textos exactos: "Pestaña de transferencia de saldo" / "En la página 'Agregar nueva transacción'" (⇄); "Botón Agregar archivos adjuntos" / "Mostrar debajo de la sección de notas" (clip); "Agregar títulos automáticamente" / "Cuando se crea una transacción" (nota con +); "Indicaciones iniciales de entrada" / "Al añadir una transacción por primera vez" (edición, chevron).
- Funcionales: la 1.ª muestra/oculta la pestaña Transferir (Gasto/Ingreso ocupan todo el ancho) y la 2.ª la fila de adjunto. Se guardan **en memoria** (`TransactionFormSettings`; TODO persistir).
- La 3.ª y la 4.ª son diseño. En Cashew, "Agregar títulos automáticamente" guarda/reordena asociaciones título-categoría al crear (`editAssociatedTitlesPage.dart:323`, `addTransactionPage.dart:459`); **no** controla la hoja de título. "Indicaciones iniciales de entrada" no existe en el clon local; equivalentes: `askForTransactionTitle` / `askForTransactionNoteWithTitle` (`editAssociatedTitlesPage.dart:351,382`).

## Pantalla "Transferir saldo" (imágenes 24 y 25)

- Pantalla aparte (ruta propia, sin pestañas) con flecha atrás al formulario, título centrado en negrita y ⓘ a la derecha.
- Diálogo ⓘ centrado (radio ≈ 28 dp, fondo gris muy oscuro): icono ⇄ grande, título "Transferir saldo", texto exacto de la imagen 25 y botones apilados "OK" y "Corrección De Saldo" (este último TODO: la lista de transacciones aún no filtra por categoría).
- Tarjeta de origen (borde ≈ 2 dp del color de la cuenta): "<cuenta> • <código>", "<saldo> − <monto>" y "= <resultado>" en vivo, botón ✕ (limpia el importe) y píldora roja "▼ <monto>" que abre la hoja de importe. Entre tarjetas: botón ↓ (intercambia cuentas y montos, invierte la tasa) y caja "× <tasa>". Tarjeta de destino igual con píldora verde "▲ <monto>" (editable). Tocar una tarjeta abre "Seleccionar Cuenta"; origen ≠ destino; origen por defecto = cuenta activa del formulario, destino = la primera distinta.
- Misma moneda: tasa 1, destino = origen; se ocultan "× …" y "Tipos de cambio".
- Abajo: divisoria, fila de fecha del formulario, línea discreta **"Llegada: igual que la salida"** (añadido de Monetae para transferencias diferidas: permite fecha/hora de llegada ≥ salida), título prellenado "Transferir saldo", píldora "Tipos de cambio" y barra "Transferir cantidad".
- **Qué se guarda (SPEC v0.7, RF-03):** `POST /api/v1/balance-corrections` crea a la vez **dos transacciones independientes** con la categoría de sistema "Corrección de saldo": gasto en origen e ingreso en destino (cada una en su moneda), enlazadas por `transfer_group_id`, con `to_occurred_at` para la llegada. No se guarda la tasa. No cuentan como ingreso ni gasto en reportes, presupuestos ni Inicio (sí en el saldo de cada cuenta). Cada pierna se edita/borra por separado (sin cambiar su tipo ni categoría).

## Hoja "Tipo De Cambio" (imagen 24)

- Solo con monedas distintas; la abren la caja "× tasa" y el botón "Tipos de cambio". Valor interno único: multiplicador origen → destino.
- Indicador "Sugerido · tu última compra (fecha)" / "Manual"; campo en **convención peruana cuando hay PEN** ("1 USD = [3,4294] PEN") y "1 [origen] = [x] [destino]" en otros pares; equivalente interno "× 0.2916" en gris; acepta coma y punto; vista previa "40 S/. → 11,66 $"; "Aplicar", "Usar sugerido" (solo si es Manual) y "Ver todos los tipos de cambio" (TODO: no hay lista de tasas hasta la Fase 6).
- Edición bidireccional exacta (sin `double`): tasa → destino; destino → tasa (sin redondear, pasa a Manual); origen → destino con la tasa vigente.
- Sugerencia (`GET /balance-corrections`, `implicit_rate`): 1) mismas dos cuentas; 2) mismo par de monedas y dirección; 3) dirección contraria invertida; 4) mercado (no existe aún: Fase 6); 5) vacío y obligatorio.

## Verificación

- Recorre el flujo completo en localhost:**8090** (pila de revisión; el 8080 es de Tomcat) a 400×642: "+" → hoja de título → categorías → importe → formulario → "Más opciones" → modal de tipos. Compara cada paso con su imagen (11 a 25), incluidos el menú ⋮, "Seleccionar Cuenta" y "Transferir saldo" con su hoja de tasa.
- Confirma: ya no hay AppBar de color, campo "Importe" ni teclado en línea, cuadrícula de categorías en el formulario, desplegable "Cuenta", campos con subrayado, chip "Publicada" suelto, azul de acento ni botón azul claro.
- Reporta lo que quedó solo como diseño (Suscripción, Repetitivo, Transferir, adjunto, calculadora, interruptor "Incluir importe", filtros de exclusión) y todo lo que no coincide con Cashew, con el motivo.
