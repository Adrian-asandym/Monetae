---
name: cashew-inicio-ui
description: Guía de diseño para que la UI móvil de Monetae (Flutter web) sea fiel a Cashew — orden, estructura y estilo de los componentes de la pantalla de Inicio (saludo, cuentas, objetivos, presupuestos, gráfico de categorías, gráfico de línea, lista de transacciones, FAB y navegación inferior). Úsala siempre que se cree, modifique o revise UI de Monetae, o cuando se mencione Cashew, paridad visual, "diseño fiel" o rediseño de pantallas.
---

# Monetae → fidelidad visual con Cashew

Objetivo: que la UI móvil de Monetae se vea y se ordene como Cashew (el Cashew personalizado del usuario, desplegado en budget-track.web.app).

## Reglas

- Solo presentación: widgets, tema, tamaños, colores, formato de textos. No tocar lógica, modelos, base de datos ni flujos (préstamos/deudas, etc.).
- Ambas apps son Flutter web (CanvasKit), así que DevTools no sirve para leer estilos. Para valores exactos usa, en este orden:
  1. El código de Cashew: https://github.com/jameskokoska/Cashew (clónalo FUERA del repo de Monetae, solo lectura; localiza con Glob/Grep los widgets de inicio, tarjetas de cuenta/objetivo/presupuesto, gráficos, entrada de transacción y barra de navegación).
  2. Medición de píxeles sobre las capturas de `references/` (PIL/Python).
- Capturas en `references/`: viewport 400×642 dp mostrado a ~1.25× (1 dp ≈ 1.25 px). Izquierda = Monetae (estado actual), derecha = Cashew (objetivo). Orden: `01-inicio-top.png` … `06-inicio-fin.png`, de arriba hacia abajo en el scroll.
- Todas las medidas y colores de abajo son aproximaciones leídas de las capturas. Calíbralas antes de fijarlas y centraliza todo en un único archivo de tema/tokens (nada de valores sueltos por widget).
- Conserva los textos en español.

## Flujo de trabajo

1. Revisa las 6 capturas y esta guía.
2. Mapea cada componente de Monetae a su widget y a su equivalente en Cashew.
3. Entra en plan mode y presenta el plan antes de tocar código.
4. Cambia UN componente a la vez. Tras cada uno: levanta la app (localhost:8080), emula 400×642, compara con la captura y ajusta hasta que coincida.
5. Un commit por componente.
6. Al final lista lo que quedó distinto y por qué.

## Principios globales (lo que más separa a Monetae de Cashew)

- Fondo neutro casi negro SIN tinte azul (Monetae usa un navy). Tarjetas gris oscuro un poco más claras que el fondo. Aprox.: fondo ≈ #121212, tarjeta ≈ #1E1E1E, píldora de navegación seleccionada ≈ #3A3A3A (calibrar).
- Sin AppBar en Inicio. El contenido empieza arriba con el saludo y un menú ⋮ a la derecha. El botón de recargar y el logo pasan al menú ⋮.
- Sin tarjetas contenedoras ni títulos de sección ("Cuentas", "Objetivos", "Presupuestos", "Categorías", "Evolución acumulada", "Últimas transacciones"). Cada componente es su propia tarjeta directamente sobre el fondo.
- Márgenes laterales ≈ 13 dp y separación vertical entre tarjetas ≈ 13 dp. Radios grandes: tarjetas ≈ 18–24 dp, barras de progreso totalmente redondeadas.
- Nada de azul de acento. El acento es neutro/gris claro (FAB, píldora de navegación).
- Carruseles horizontales (cuentas, objetivos, presupuestos) con la siguiente tarjeta asomando unos ~24 dp a la derecha.
- Tipografía: fuerte jerarquía con negritas grandes en títulos y montos, texto secundario en blanco ~60 %. Usa la misma familia que el Cashew del usuario (revisa el tema/pubspec de Cashew).

## Orden de componentes en Inicio (de arriba abajo)

1. Saludo + nombre (sin AppBar, ⋮ arriba a la derecha)
2. Carrusel de cuentas
3. Carrusel de objetivos
4. Carrusel de presupuestos
5. Tarjeta del gráfico de categorías (con indicador de páginas)
6. Tarjeta del gráfico de línea (balance en el tiempo)
7. Lista de transacciones agrupadas por día, sobre el fondo
8. Botón píldora "Ver todas las transacciones"
9. FAB flotante + barra de navegación inferior

El orden actual de Monetae ya coincide; lo que cambia es la estructura y el estilo.

## Especificación por componente

### 1. Saludo
- Cashew: "Buenos días" (según la hora: días/tardes/noches) en negrita ≈ 20–22 dp; debajo el nombre del usuario muy grande en negrita ≈ 34–36 dp (ej. "Adrian Sandy"). Sin AppBar; ⋮ arriba a la derecha.
- Monetae hoy: AppBar "Inicio" con recargar + logo, y "¡Hola!" sin nombre.
- Cambiar: quitar AppBar, saludo por hora del día, usar el nombre del usuario guardado en ajustes, menú ⋮.

### 2. Cuentas
- Cashew: carrusel horizontal de tarjetas compactas (≈ 196×90 dp, radio ≈ 18 dp). Cada una: nombre en negrita (≈ 20 dp) a la izquierda; un punto de color de la cuenta (≈ 12 dp) arriba a la derecha; debajo, triángulo ▲/▼ pequeño + saldo en negrita coloreado (verde si positivo, rojo coral si negativo); debajo "393 transacciones" en blanco ~80 %. La cuenta seleccionada lleva borde de ≈ 2 dp del color de la cuenta (no relleno).
- Monetae hoy: lista vertical dentro de una tarjeta "Cuentas", con icono de billetera, saldo a la derecha y la cuenta por defecto con relleno verde.
- Cambiar: carrusel horizontal, punto de color en vez de icono de billetera, selección por borde en vez de relleno verde, quitar el texto "Cuenta por defecto". Corregir pluralización: "1 transacción" (hoy dice "1 transacciones").

### 3. Objetivos
- Cashew: tarjeta (≈ 146 dp de alto) en carrusel. Arriba: título en negrita ≈ 22 dp + subtítulo gris ≈ 14 dp ("4,05 S/./día para 74 días"); círculo gris ≈ 50 dp arriba a la derecha con el icono/emoji del objetivo. Medio: monto actual en negrita ≈ 26 dp (blanco) + "restante / 899 S/." pequeño y gris. Abajo: fecha inicio ("22 may") | barra de ≈ 20 dp con relleno claro y porcentaje centrado ("67%") | fecha fin ("22 dic"), todo en una sola fila.
- Monetae hoy: tarjeta muy alta (~300 dp) con título enorme, monto verde grande, "Completado", barra de ancho completo debajo, "160 %" con espacio.
- Cambiar: reducir tipografías y alto de la tarjeta, fechas a los lados de la barra, monto blanco, porcentaje sin espacio ("67%"), quitar la línea "Completado" y la etiqueta "Objetivo de ahorro / Hasta …" (el rango de fechas ya queda en los extremos de la barra).

### 4. Presupuestos
- Cashew: tarjeta con el color del presupuesto en la mitad superior y el mismo tono más oscuro (≈ 35 % de negro) en la inferior. Arriba: título en negrita ≈ 28 dp y "14 S/. restante de 25 S/." (monto en negrita); botón circular ≈ 44 dp arriba a la derecha (blanco ~20 %) con icono de historial. Abajo: "1 oct" | barra con relleno pastel del color y "44%" centrado | "31 oct"; marcador "Hoy" (burbuja pequeña con línea vertical) sobre la barra en la posición actual; debajo, centrado y en blanco ~50 %: "Puedes gastar 0,64 S/./día para 22 días más".
- Monetae hoy: estructura parecida pero con etiqueta "Mensual", "78 %" con espacio, línea "Gastado: S/ 465.85 / S/ 600.00", sin marcador "Hoy", sin botón de historial, sin texto de gasto diario.
- Cambiar: añadir botón de historial, marcador "Hoy", texto de gasto diario recomendado; quitar "Mensual" y "Gastado: …"; "44%" sin espacio; barra más gruesa.

### 5. Gráfico de categorías
- Cashew: tarjeta (≈ 280 dp de alto) sin título ni selector de mes. Arriba a la izquierda, leyenda de las 3 categorías principales (punto de color + nombre, blanco). Arriba a la derecha, triángulo ▼ (rojo = gasto) que cambia gasto/ingreso. Dona grande con anillo grueso, agujero central oscuro grande, colores saturados por categoría, e iconos de categoría en círculos con borde del color de la categoría sobre el anillo. Abajo, puntos de paginación (2 páginas, deslizable). Revisa el código de Cashew para el detalle exacto de los segmentos.
- Monetae hoy: tarjeta "Categorías" con selector de mes, pestañas Gasto/Ingreso, título del gráfico y lista de categorías con porcentaje debajo.
- Cambiar: reproducir el layout de Cashew en Inicio; NO eliminar funcionalidad: reubicar selector de mes, alternancia gasto/ingreso (vía el triángulo) y lista de categorías en la segunda página o en la pantalla de detalle.

### 6. Gráfico de línea
- Cashew: tarjeta sin título. Etiquetas del eje Y dentro del área, a la izquierda ("842 S/.", "632 S/.", "421 S/.", "211 S/."), cuadrícula punteada horizontal y vertical, área con degradado gris claro que se desvanece, línea suave de ≈ 2 px gris claro, etiquetas X ("10 sept", "18 sept", "25 sept", "3 oct", "10 oct"). Al tocar: línea vertical punteada, punto y burbuja con fecha + monto ("26 sept 385,57 S/.").
- Monetae hoy: título "Evolución acumulada", degradado azulado, etiquetas "S/ 3,200.00", rango 1–31 oct, sin cuadrícula ni tooltip.
- Cambiar: quitar título, degradado gris, cuadrícula punteada, formato de etiquetas Cashew, tooltip táctil.

### 7. Lista de transacciones
- Cashew: sin tarjeta contenedora ni título; se ve directamente sobre el fondo. Encabezado por día: a la izquierda fecha corta en gris ("jueves, 8 de octubre", sin año si es el actual); a la derecha el total neto del día en gris ("-12 S/.").
- Fila: círculo ≈ 48 dp con el color de la categoría y su icono; título en negrita; debajo una etiqueta pequeña con el nombre de la cuenta (chip redondeado con color de la cuenta); a la derecha, arriba la hora ("13:34", gris pequeña, con icono de nota si hay nota) y debajo el monto con ▼ rojo / ▲ verde ("5 S/."). Si la moneda es extranjera, debajo del monto va el original en gris ("1,36 $"). Las recurrentes/suscripciones llevan un icono gris de repetición. Las transferencias se muestran como un grupo de dos filas con flecha ("Interbank PEN Transferir → Lemon", -8 / +8). La fila seleccionada tiene un fondo más claro con esquinas redondeadas.
- Al final: botón píldora centrado "Ver todas las transacciones" (gris oscuro, texto gris claro, ≈ 44 dp de alto).
- Monetae hoy: tarjeta "Últimas transacciones"; encabezados con año completo, subtítulo con categoría, monto con la etiqueta "Gasto"/"Ingreso" debajo, sin hora, sin cuenta, sin total diario, sin botón final.
- Cambiar: todo lo anterior (chip de cuenta en lugar de categoría como subtítulo, hora, total diario, quitar la etiqueta "Gasto"/"Ingreso", botón final). Si falta el dato (p. ej. hora), añadirlo a la presentación sin alterar el modelo si ya existe en él; si no existe, avisar en vez de inventarlo.

### 8. FAB y navegación inferior
- FAB: cuadrado de esquinas redondeadas (radio ≈ 20 dp, ≈ 60 dp), gris claro neutro con "+" blanco (hoy es azul).
- Navegación: misma estructura de 4 destinos (Inicio, Transacciones, Presupuestos, Más) con píldora gris neutra detrás del icono+texto seleccionado. Iconos redondeados rellenos; el de Transacciones en Cashew parece billete/pagos (hoy es un recibo). Fondo de la barra igual al del fondo de la página.

## Formato de textos (por defecto, igual que Cashew)

- Montos: coma decimal y símbolo al final con espacio: "100,46 S/."; sin decimales cuando son cero ("899 S/.", "25 S/."); por día: "4,05 S/./día". Dólares: "1,36 $".
- Hoy Monetae usa "S/ 4,270.00" (símbolo delante, punto decimal): cambiar. Verifica el formato de miles en el código de Cashew.
- Porcentajes sin espacio: "44%".
- Fechas cortas: "22 may", "1 oct", "jueves, 8 de octubre" (sin año si es el año en curso).
- Pluralización correcta: "1 transacción", "6 transacciones".

## Verificación final

- Compara cada pantalla con su captura de referencia a 400×642.
- Comprueba: sin AppBar, sin azul, sin tarjetas contenedoras, sin títulos de sección, FAB gris, formato de montos, carruseles con tarjeta asomando.
- Reporta diferencias restantes con su motivo (p. ej. dato inexistente en el modelo).