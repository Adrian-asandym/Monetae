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
  2. Medición de píxeles sobre las capturas de `reference/cashew-inicio-ui/` (PIL/Python).
- Capturas en **`reference/cashew-inicio-ui/`** (carpeta ignorada por git: **contienen datos reales, nunca copiarlas al repositorio**): viewport 400×642 dp mostrado a ~1.25× (1 dp ≈ 1.25 px). Izquierda = Monetae (estado en su fecha), derecha = Cashew (objetivo). v1: `1.png` … `6.png` (de arriba abajo en el scroll); v2 (2026-10-10): `v2-01-top.png` (tarjeta «añadir»), `v2-02-pie-ingresos.png`, `v2-03-linea.png`, `v2-04-editar.png`.
- El código de Cashew está en `reference/Cashew/budget/lib/` (solo lectura); **nunca** leer `reference/backups/`.
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
- Sin AppBar en Inicio. El contenido empieza arriba con el saludo y, a la derecha, la **píldora «Editar»** (no hay menú ⋮, ni logo, ni botón de recargar visibles; la recarga sigue existiendo en código, propuesta futura: *pull-to-refresh*).
- Sin tarjetas contenedoras ni títulos de sección ("Cuentas", "Objetivos", "Presupuestos", "Categorías", "Evolución acumulada", "Últimas transacciones"). Cada componente es su propia tarjeta directamente sobre el fondo.
- Márgenes laterales ≈ 13 dp y separación vertical entre tarjetas ≈ 13 dp. Radios grandes: tarjetas ≈ 18–24 dp, barras de progreso totalmente redondeadas.
- Nada de azul de acento. El acento es neutro/gris claro (FAB, píldora de navegación).
- Carruseles horizontales (cuentas, objetivos, presupuestos) con la siguiente tarjeta asomando unos ~24 dp a la derecha. Los de **objetivos y presupuestos terminan con una tarjeta «añadir»** (ver §3 y §4).
- Tipografía: fuerte jerarquía con negritas grandes en títulos y montos, texto secundario en blanco ~60 %. Usa la misma familia que el Cashew del usuario (revisa el tema/pubspec de Cashew).

## Orden de componentes en Inicio (de arriba abajo)

1. Saludo + nombre (sin AppBar, píldora «Editar» arriba a la derecha)
2. Carrusel de cuentas
3. Carrusel de objetivos (+ tarjeta «añadir» al final)
4. Carrusel de presupuestos (+ tarjeta «añadir» al final)
5. Tarjeta del gráfico de categorías: página 1 gastos, página 2 ingresos (con indicador de páginas)
6. Tarjeta del gráfico de línea (balance en el tiempo, eje Y con 4 etiquetas)
7. Lista de transacciones agrupadas por día, sobre el fondo
8. Botón píldora "Ver todas las transacciones"
9. FAB flotante + barra de navegación inferior

El orden actual de Monetae ya coincide; lo que cambia es la estructura y el estilo.

## Especificación por componente

### 1. Saludo y botón «Editar» (v2, 2026-10-10)
- Cashew (`pages/homePage/homePageUsername.dart`): con nombre, dos líneas: saludo según la hora («Buenos días/tardes/noches») en negrita **20 dp** y el nombre en negrita **33 dp**; sin nombre, una sola línea «Inicio» en negrita 33 dp. Sin AppBar.
- **Arriba a la derecha: píldora «Editar»** (no menú ⋮): ≈ **114×45 dp**, radio **14 dp**, fondo gris oscuro (token de tarjeta), icono de lápiz **22 dp** + texto «Editar» **14 dp**, separación 8 dp. Servirá para **reordenar los componentes de Inicio** (`preferences.home_widgets`); hoy el handler está vacío con TODO.
- Quitados del encabezado: «Actualizar» y el logo grande. La recarga (`HomeController.load`) se conserva sin UI; propuesta: *pull-to-refresh* con `RefreshIndicator`.
- El nombre sale de `CurrentUser.display_name` (RF-50).

### 2. Cuentas
- Cashew: carrusel horizontal de tarjetas compactas (≈ 196×90 dp, radio ≈ 18 dp). Cada una: nombre en negrita (≈ 20 dp) a la izquierda; un punto de color de la cuenta (≈ 12 dp) arriba a la derecha; debajo, triángulo ▲/▼ pequeño + saldo en negrita coloreado (verde si positivo, rojo coral si negativo); debajo "393 transacciones" en blanco ~80 %. La cuenta seleccionada lleva borde de ≈ 2 dp del color de la cuenta (no relleno).
- Monetae hoy: lista vertical dentro de una tarjeta "Cuentas", con icono de billetera, saldo a la derecha y la cuenta por defecto con relleno verde.
- Cambiar: carrusel horizontal, punto de color en vez de icono de billetera, selección por borde en vez de relleno verde, quitar el texto "Cuenta por defecto". Corregir pluralización: "1 transacción" (hoy dice "1 transacciones").

### 3. Objetivos
- Cashew: tarjeta (≈ 146 dp de alto) en carrusel. Arriba: título en negrita ≈ 22 dp + subtítulo gris ≈ 14 dp ("4,05 S/./día para 74 días"); círculo gris ≈ 50 dp arriba a la derecha con el icono/emoji del objetivo. Medio: monto actual en negrita ≈ 26 dp (blanco) + "restante / 899 S/." pequeño y gris. Abajo: fecha inicio ("22 may") | barra de ≈ 20 dp con relleno claro y porcentaje centrado ("67%") | fecha fin ("22 dic"), todo en una sola fila.
- Monetae hoy: tarjeta muy alta (~300 dp) con título enorme, monto verde grande, "Completado", barra de ancho completo debajo, "160 %" con espacio.
- Cambiar: reducir tipografías y alto de la tarjeta, fechas a los lados de la barra, monto blanco, porcentaje sin espacio ("67%"), quitar la línea "Completado" y la etiqueta "Objetivo de ahorro / Hasta …" (el rango de fechas ya queda en los extremos de la barra).
- **Tarjeta «añadir» (v2):** al final del carrusel, como `pages/addButton.dart` de Cashew: mismo alto, ancho y radio que las tarjetas del carrusel, **fondo transparente**, **borde 1,5 dp gris ~35 %**, icono de lista con «+» centrado (~22–28 dp) y etiqueta gris **«Objetivo»** debajo (14 dp, separación 2 dp). Si no hay objetivos, es lo único del carrusel. Abre el formulario de creación de objetivo (**aún no existe en Monetae**: hoy TODO).

### 4. Presupuestos
- Cashew: tarjeta con el color del presupuesto en la mitad superior y el mismo tono más oscuro (≈ 35 % de negro) en la inferior. Arriba: título en negrita ≈ 28 dp y "14 S/. restante de 25 S/." (monto en negrita); botón circular ≈ 44 dp arriba a la derecha (blanco ~20 %) con icono de historial. Abajo: "1 oct" | barra con relleno pastel del color y "44%" centrado | "31 oct"; marcador "Hoy" (burbuja pequeña con línea vertical) sobre la barra en la posición actual; debajo, centrado y en blanco ~50 %: "Puedes gastar 0,64 S/./día para 22 días más".
- Monetae hoy: estructura parecida pero con etiqueta "Mensual", "78 %" con espacio, línea "Gastado: S/ 465.85 / S/ 600.00", sin marcador "Hoy", sin botón de historial, sin texto de gasto diario.
- Cambiar: añadir botón de historial, marcador "Hoy", texto de gasto diario recomendado; quitar "Mensual" y "Gastado: …"; "44%" sin espacio; barra más gruesa.
- «X/día»: `(total − importe) / días restantes` (hoy incluido, zona America/Lima), redondeo medio-arriba a 2 decimales con `Decimal` (55,02, no 55,03).
- **Tarjeta «añadir» (v2):** igual que en §3 pero con la etiqueta **«Presupuesto»**; abre el formulario de creación de presupuesto (**aún no existe**: hoy TODO).

### 5. Gráfico de categorías (v2, 2026-10-10)
- Cashew (`homePagePieChart.dart`, `widgets/pieChart.dart`): tarjeta (≈ 280 dp de alto) sin título ni selector de mes, **dos páginas deslizables**:
  - **Página 1 = gastos** (triángulo ▼ rojo arriba a la derecha).
  - **Página 2 = ingresos** (triángulo ▲ verde). **No es una lista de categorías.**
- Mismo layout en ambas páginas: leyenda de las 3 categorías principales arriba a la izquierda (punto de color + nombre, puede ocupar 2 líneas); **dona grande a la derecha** con anillo grueso, agujero central oscuro e iconos de categoría en círculos con borde de su color sobre el anillo; puntos de paginación abajo (el activo, más claro). Tocar el triángulo también cambia de página.
- **Un solo widget parametrizado por tipo** (gasto/ingreso). Sin datos en el periodo: anillo vacío sin romper el layout.
- La lista de categorías con porcentajes y el selector de mes **no van en Inicio**: irán a una **pantalla de detalle** que se abre al tocar la tarjeta (**aún no existe**; su código queda sin conectar).

### 6. Gráfico de línea
- Cashew: tarjeta sin título. Etiquetas del eje Y dentro del área, a la izquierda ("842 S/.", "632 S/.", "421 S/.", "211 S/."), cuadrícula punteada horizontal y vertical, área con degradado gris claro que se desvanece, línea suave de ≈ 2 px gris claro, etiquetas X ("10 sept", "18 sept", "25 sept", "3 oct", "10 oct"). Al tocar: línea vertical punteada, punto y burbuja con fecha + monto ("26 sept 385,57 S/.").
- Monetae hoy: título "Evolución acumulada", degradado azulado, etiquetas "S/ 3,200.00", rango 1–31 oct, sin cuadrícula ni tooltip.
- Cambiar: quitar título, degradado gris, cuadrícula punteada, formato de etiquetas Cashew, tooltip táctil.
- **Eje Y (v2), como `widgets/lineGraph.dart` de Cashew:** siempre **4 etiquetas equiespaciadas** desde el máximo hacia abajo con intervalo `(máx − mín) / 4`: máx, máx−i, máx−2i, máx−3i. El extremo inferior (mín) es la línea base **sin etiqueta**. Cada etiqueta alineada con su línea punteada, dentro de la tarjeta a la izquierda, gris ~50 %, enteros con formato «842 S/.».
  - Serie positiva: mín = 0 → el 0 no se etiqueta.
  - Serie que cruza 0: el eje va de mín a máx, el 0 puede aparecer como etiqueta interior y se dibuja **línea de referencia en 0** (áreas positiva/negativa cortadas en 0).
  - Serie solo negativa: máx = 0 arriba, etiquetado.
- **Contenedor:** el gráfico va dentro de una **tarjeta** con el fondo de tarjeta (se distingue del fondo de Inicio); área ≈ 175 dp, márgenes 18/12/7 dp.

### 7. Lista de transacciones
- Cashew: sin tarjeta contenedora ni título; se ve directamente sobre el fondo. Encabezado por día: a la izquierda fecha corta en gris ("jueves, 8 de octubre", sin año si es el actual); a la derecha el total neto del día en gris ("-12 S/.").
- Fila: círculo ≈ 48 dp con el color de la categoría y su icono; título en negrita; debajo una etiqueta pequeña con el nombre de la cuenta (chip redondeado con color de la cuenta); a la derecha, arriba la hora ("13:34", gris pequeña, con icono de nota si hay nota) y debajo el monto con ▼ rojo / ▲ verde ("5 S/."). Si la moneda es extranjera, debajo del monto va el original en gris ("1,36 $"). Las recurrentes/suscripciones llevan un icono gris de repetición. Las transferencias se muestran como un grupo de dos filas con flecha ("Banco Transferir → Efectivo", −monto / +monto). La fila seleccionada tiene un fondo más claro con esquinas redondeadas.
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
- Comprueba: sin AppBar, sin azul, sin tarjetas contenedoras de sección, sin títulos de sección, píldora «Editar» (no ⋮), tarjetas «añadir» al final de objetivos y presupuestos, circular con página 2 = ingresos, eje Y con 4 etiquetas, gráfico de línea en su tarjeta, FAB gris, formato de montos, carruseles con tarjeta asomando.
- Reporta diferencias restantes con su motivo (p. ej. dato inexistente en el modelo).