# T-501 — Resultados del spike de desacople

Fecha: 2026-10-09. Rama: `codex/T-501-ui-decoupling-spike`. Base: `master-dev`.

Se extrajeron **cuatro componentes representativos** en un Flutter Web nuevo:
tema, tarjeta de transacción, gráfico circular y entrada animada (con curva
retardada). Los tres obligatorios se renderizan con datos sintéticos, sin tipos
ni consultas de la base local original. **La opción A del ADR-001 es viable**;
recomiendo reservar **8–10 tareas de desacople**, frente a las 6–8 anteriores,
para terminar las variantes visuales e interacciones de los doce componentes.
No se supera el umbral de escalamiento de aproximadamente doce tareas.

## Qué se entrega y qué demuestra

`apps/web` contiene una pantalla responsive, con tema claro/oscuro, tres acentos,
i18n es/en mediante `flutter gen-l10n`, cuatro ejemplos de transacción (gasto,
ingreso, préstamo y programada en USD), gráfico seleccionable, paleta y repetición
de la animación. Usa el logo propio de `img/Monetae-Logo.jpg`, también en favicon y
manifiesto; la marca original no aparece en la interfaz.

`AccountDto`, `CategoryDto` y `TransactionDto` se generan desde **todos** los
campos de sus esquemas en `docs/api/openapi.json` 0.3.0. Conservan enums,
nulabilidad, ids y decimales como cadenas exactas, sin conversión a `double`.
El parser rechaza campos faltantes/desconocidos y tipos/enums incorrectos, sin
coerción. Es un generador acotado a estas respuestas planas: **no entrega un
cliente HTTP ni duplica la validación financiera/regex completa del servidor**.
Los montos, totales y porcentajes del mock están prefijados; no se calculan saldos,
intereses, conversiones ni estados financieros. Los `double` del gráfico son
proporciones geométricas, no importes monetarios.

La tarjeta recibe un modelo de vista con DTO, textos, iconos, tono y etiquetas;
el gráfico recibe una lista con pesos y etiquetas, selección por id y callback.
El tema recibe brillo, acento, tinte, contraste y fondo negro por parámetros. La
entrada animada recibe duración/habilitación y respeta movimiento reducido.

## Medición del trabajo realizado

Tiempo de esta sesión de agente: aproximadamente **35 minutos** incluyendo
lectura, arranque de Flutter, implementación, pruebas, build e informe. Los
minutos por componente son atribuciones aproximadas de los checkpoints de la
sesión, no tiempos de un desarrollador humano ni una promesa para futuras tareas;
las compilaciones y parte de la revisión se solapan.

| Componente | Lectura + adaptación + verificación aproximadas | Fuente leída | Destino: líneas totales | Líneas conservadas literalmente | Reescritas o nuevas |
|---|---:|---:|---:|---:|---:|
| Tema | 5 min | `colors.dart`: 677 | 111 | 4 | 98 |
| Tarjeta | 7 min | 6 archivos visuales: 1.942 | 197 | 21 | 168 |
| Gráfico circular | 7 min | `pieChart.dart`: 470 | 204 | 28 | 169 |
| Animación: curva | 1 min | `customDelayedCurve.dart`: 19 | 24 | 5 | 14 |
| Animación: FadeIn | 2 min | `fadeIn.dart`: 619; se adapta solo `FadeIn` | 60 | 13 | 35 |
| Transversal | ≈13 min | Contrato, proyecto, mocks, i18n, suite, build, informe | — | — | — |

**Método de conteo:** `tool/measure_reuse.py` cuenta líneas completas idénticas
tras quitar sangría, de al menos doce caracteres, excluyendo imports,
comentarios y anotaciones. Las restantes líneas no vacías ni comentarios se
clasifican como reescritas/nuevas. El total también incluye comentarios y blancos,
por lo que las dos columnas no suman el total físico. Es una aproximación
reproducible a la copia literal, que puede contar boilerplate común de Flutter y
subestimar una línea reformateada: no mide autoría ni reutilización del diseño.
Ningún archivo original se copió entero salvo LICENSE; se conservan algoritmos,
composición y constantes mediante adaptación. Se leyeron además los botones de
tipo y selección por arrastre para delimitar lo pendiente, sin copiarlos.

```bash
python3 apps/web/tool/measure_reuse.py \
  /home/artur/propio2/Monetae/reference/Cashew/budget
```

## Diferencias verificadas frente al original

### Tema (`budget/lib/colors.dart`)

Se conservan la mezcla pastel con `Color.alphaBlend`, las proporciones de tinte
fondo .91/.92 y tarjeta .92/.8, Material 3 y los colores originales de ingreso,
gasto, próximos y vencidos en ambos modos. El original **ya tenía un
ThemeExtension**, pero con mapa nullable indexado por texto; ahora son campos
`Color` obligatorios y `copyWith`/`lerp` tipados.

Se reemplazan 49 accesos a preferencias globales por parámetros. Se omiten
integraciones de color del sistema operativo, barras nativas Android/iOS,
helpers de hex, selector de colores y ramas de ahorro de batería ajenas al spike.
No se reproduce aquí la paleta especial de acentos grises. El texto secundario
usa opacidad .55 (o .7 con contraste), en lugar de .4/.25 de las variantes con
tinte del original, para mantener legibilidad; la selección de fuente queda en
Roboto de Flutter, sin copiar Avenir ni fuentes de Cashew. La identidad visual
no es una comparación píxel a píxel con una ejecución del original.

### Tarjeta (`budget/lib/widgets/transactionEntry/*`)

Se conserva la fila icono–título/categoría–monto, icono circular de 27 px en
contenedor de 47 px, texto de 16.5/14.5 px y monto de 19 px en negrita, flecha
rotatoria con `ElasticOutCurve(.5)` y duración 1.700 ms, nota/tooltip y etiquetas
pequeñas. El título vacío usa categoría o tipo ya suministrado, sin consultar una
tabla. Hay vista compacta y extendida, selección controlada y callbacks de tap y
long press; los widgets no escriben transacciones ni navegan a páginas internas.

Se reemplazan `Transaction`, `TransactionCategory`, `Budget`, `Objective`,
`AllWallets`, `Provider`, streams, estado global de selección y consultas por DTO
y entradas tipadas. Desaparecen `CountNumber` y cálculos de conversión en el
widget: recibe el importe principal y opcionalmente otro importe ya formateado.
El tono financiero lo suministra el modelo, incluyendo un tono neutro para el
capital de préstamos. Los ids y el historial se conservan en el DTO.

Los tags son textos precalculados; no se trasladan porcentajes de metas,
exclusiones de presupuestos, consultas de subcategorías ni lógica de préstamos
como objetivos. El original `transactionEntryTypeButton` mezcla navegación y
mutaciones (incluye invertir ingreso/monto); se presenta una etiqueta de tipo,
sin portar esas acciones. El nuevo contenedor usa radio 15 y espaciado fijo,
sin agrupación por vecinos, hitboxes ni selección por arrastre. Los iconos son
Material de Flutter en lugar de la caché y catálogo propios del original.

**Pendiente para una tarjeta de producción:** conectar callbacks a flujos de la
API, completar variantes de filas agrupadas/selección, etiquetas con color e
iconos, acciones de programadas, adjuntos y resolver exactamente las preferencias
que se quieran conservar. No hay botón de liquidar ni filtrado que haga desaparecer
movimientos de préstamo. El spike no implementa una pantalla de préstamos.

### Gráfico (`budget/lib/widgets/pieChart.dart`)

Se conservan `fl_chart` **0.68.0**, inicio −45°, separación y hueco geométrico 0,
los dos discos centrales 105/80 px (130/110 grande), radio pequeño 100/106 px,
radio grande 136/146 px, badges en .98 del radio, borde 2.5 px, ocultamiento de
badges <5 % salvo selección, tinte claro .3 / oscuro .1 y variación para vecinos
con mismo color. La selección conserva porcentaje desplazado ±34 px según la
mitad del círculo; transición de datos 1.300 ms con `ElasticOutCurve(.6)`.

Se reemplazan `CategoryWithTotal`, consultas de detalles/categorías y la
selección mediante `GlobalKey` por `CategorySlice` y `selectedId`/callback. Se
filtran pesos cero antes de asociar índices con ids y se ignoran índices negativos
/fuera de rango. Los porcentajes y textos se suministran; solo se calcula la
posición geométrica de la etiqueta. Vacío muestra un círculo y texto traducido.

Se omiten `PinWheelReveal` y el arranque escalonado que consultaba el número de
categorías y programaba decenas de futuros. Los badges aparecen inmediatamente
sin esa consulta; su icono usa Material (27 px normal/34 seleccionado), sin caché
ni emoji. El tamaño pequeño del lienzo es 220 en vez de 200 para dar margen a
badges; las proporciones de sectores y discos se conservan. La leyenda externa
permite teclado y muestra los mismos datos. No se ha portado aún el contenedor
`homePagePieChart` con sus filtros de periodo: corresponde a otra tarea.

### Animaciones (`customDelayedCurve.dart` + `fadeIn.dart`)

Se conserva la fórmula de retardo y `Curves.easeInOut`; constructor `const` y
assert para `0 ≤ delay < 1`. Se adapta **solo FadeIn** del archivo de 619 líneas:
opacidad lineal 0→1 y duración predeterminada 500 ms. El acceso a ahorro de batería
se reemplaza por `enabled` y movimiento reducido de `MediaQuery`; usa
`FadeTransition`, dispone el controlador y permite actualizar duración/habilitación.
El resto de animaciones de ese archivo permanece fuera del spike.

## Dependencias, licencia y privacidad

| Dependencia original | Sustitución / justificación |
|---|---|
| `fl_chart: ^0.68.0` | `fl_chart: 0.68.0`, misma versión exacta; mantiene geometría y eventos, sin cambiar de major. `equatable` llega transitivamente. |
| `easy_localization` / extensiones de texto | `flutter_localizations` del SDK + `intl: ^0.20.2` (SDK resuelve 0.20.3), necesarios para `flutter gen-l10n`; no se añade un framework de estado. |
| Preferencias globales, `Provider`, consultas y tipos locales | Parámetros, `ThemeExtension`, DTO generado y callbacks; no se añaden dependencias para sustituirlos. |
| Widgets propios de texto/iconos/navegación | Material de Flutter y Roboto; se documentan diferencias de fidelidad. |
| Animaciones auxiliares y timers de categorías | `AnimationController`/`FadeTransition`; no librería adicional. |

`flutter_lints` y `flutter_test` son los del proyecto generado. Se retiró
`cupertino_icons` del template porque la UI usa Material. El build informa que
el catálogo Cupertino no está incluido en el tree shaking; no se usan esos
iconos en `lib`, y los iconos Material sí están empaquetados y verificados.

LICENSE se copió íntegro del original, incluido su texto de autoría; NOTICE
atribuye a **James Kokoska** y registra fecha y rutas de las modificaciones. Cada
archivo derivado lleva origen y aviso de modificación. El coordinador autorizó
por `orca orchestration ask` leer **únicamente** README.md y LICENSE en la raíz de
Cashew para verificar atribución; el resto de lecturas de referencia se limitó a
`budget/`. No se abrió/listó `reference/backups/`, no se ejecutó Cashew y todos los
datos, fixtures e imágenes de pruebas son sintéticos. No hubo cambios de backend,
contrato, infraestructura ni especificación.

## Verificación y límites de la evidencia

Flutter **3.47.6**, Dart **3.13.5**, Linux/WSL:

- `flutter pub get`: correcto; lockfile versionado.
- `flutter gen-l10n`: correcto; ARB es/en y código generado.
- `dart analyze`: **No issues found!**, con strict casts/inference/raw types.
- `flutter test`: **12 tests passed**, sin `--update-goldens` en la verificación.
- **8 goldens**: tema, tarjetas (los cuatro estados), gráfico seleccionado y fade
  a 250 ms, cada uno en claro y oscuro. Roboto y MaterialIcons cargados desde el
  SDK para reproducibilidad y texto legible; referencias inspeccionadas.
- Interacciones adicionales: selección de gráfico y checkbox, tooltip compacto,
  pesos cero, vacío, progreso/disposal/movimiento reducido, tema/idioma/acento,
  anchura 390 px y escritorio. La suite reproduce el error de tinta de `ListTile`
  detectado y corregido sustituyendo el panel decorado por `Material`.
- `flutter build web --release`: correcto, `Built build/web`; salida local ignorada.
- `grep -rE 'drift|firebase|appStateSettings|package:budget/' apps/web/lib`: sin coincidencias.

Los goldens protegen **la adaptación**, no demuestran igualdad con capturas del
original. No se compiló ni ejecutó Cashew, conforme a la tarea. La revisión
visual final del build en Chrome corresponde al coordinador y a Adrian. El
README contiene los comandos para servirlo y regenerar DTOs y pruebas.

## Nuevo estimado para el desacople de los doce componentes

La mayor dificultad no es quitar un import: es decidir el límite de presentación
y cubrir variantes sin heredar reglas financieras. La tarjeta agrupa seis de los
archivos clasificados como «requiere desacoplar», por lo que multiplicar este
spike por cuatro o dividir solo líneas daría una proyección engañosa. Además,
`fadeIn.dart` incluye muchas animaciones que aquí no se portaron.

| Bloque de trabajo de desacople | Tareas de 1–2 h previstas |
|---|---:|
| Tema: completar tokens/preferencias y revisión de fidelidad | 1 |
| Familia transactionEntry: variantes visuales, selección y metadatos de presentación | 2–3 |
| Pie + homePagePieChart + homePageLineGraph + heatmap: entradas puras y goldens | 3–4 |
| Resto de animaciones pertinentes de fadeIn | 1 |
| Revisión conjunta de fidelidad, tamaños y actualización de goldens | 1 |
| **Total** | **8–10** |

Rango orientativo **12–18 h de implementación/revisión**, no extrapolación directa
de los minutos de generación asistida. Incertidumbre media: los gráficos de
líneas/heatmap no se desacoplaron en este spike y Adrian aún no ha validado
fidelidad. Este rango **no incluye** arquitectura HTTP/autenticación, ensamblado
de pantallas, los dos componentes clasificados como reescritura ni las funciones
de Fase 6; tampoco convierte el mock en producto terminado. Antes de comprometer
las siguientes tareas, revisar el build y acordar qué preferencias visuales se
conservan; no hace falta cambiar la estrategia A con la evidencia obtenida.

## T-502

Fecha: 2026-10-09. Rama: `codex/T-502-ui-brand-and-card`. Contrato **0.4.0**;
SPEC v0.4, RF-39/RF-46/RF-47, decisiones D10-A y D11-A. Solo se modifican
`apps/web/**` y esta sección; sin lectura/listado de respaldos ni datos reales.

### Marca y superficie azul

Se copiaron sin cambios ambos SVG de ícono y ambos JPG con nombre desde `img/`
a `assets/brand/`; los originales permanecen intactos. `BrandLogo` dibuja con
`flutter_svg` el ícono claro/oscuro según el tema interno; se retiraron las dos
copias antiguas `monetae-logo.jpg`. Los JPG con nombre quedan disponibles como
assets, mientras que la cabecera usa el ícono vectorial.

`web/index.html` incluye favicon PNG de respaldo y dos enlaces SVG con
`media="(prefers-color-scheme: light|dark)"`, además del apple-touch-icon PNG.
**Limitación del navegador:** favicon según el modo del sistema/navegador,
ícono dentro de la app según el tema de Flutter; cambiar el interruptor interno
no cambia `prefers-color-scheme`. El manifiesto usa PNG claros estables 192/512
y maskable 512, todos reales, generados reproduciblemente por
`tool/generate_brand_icons_test.dart` con `flutter_svg` y `Picture.toImage`.
También genera favicon 32 y Apple 180. No se instalaron rasterizadores del sistema;
el maskable usa fondo opaco y el dibujo cabe en el círculo seguro central.

Se conserva el tema de T-501: acento azul `#5F85C2`, `tinted = true`, fondo oscuro
mezclado .92 y superficie de tarjeta .8. Los goldens de marca/tarjetas oscuras y
las aserciones de tokens fijan este predeterminado, sin modificar la geometría ni
los tonos financieros originales. Los demás acentos siguen siendo configurables.

### Tarjeta configurable y diferencias frente a Cashew

Los DTO Account/Category/Transaction se regeneran desde 0.4.0 y se añaden
UserIcon y TransactionCardPreferences. El generador trata los enums MIME como
identificadores Dart válidos y toma los seis defaults directamente del contrato;
el parser rechaza claves desconocidas y booleanos nulos/no booleanos.
Las preferencias tienen `copyWith` y serialización `toJson` para T-503/T-505.

Por defecto, fecha/nota/etiquetas visibles, hora/cuenta/acciones ocultas.
`TransactionCardList` muestra **una cabecera por día** cuando `show_date` es true,
sin repetirla dentro de las tarjetas. Los modelos reciben claves, fechas y horas
ya formateadas; el mock representa America/Lima con fechas sintéticas. Se retiró
la cuenta de los subtítulos predeterminados del spike, que contradecía el default
`showAccountLabelTagInTransactionEntry = false` de Cashew; ahora tiene un detalle
propio. En el movimiento de préstamo el subtítulo muestra una persona sintética.
La nota oculta también desaparece del tooltip compacto. Para respetar RF-47,
`show_tags` manda también en la vista compacta: se elimina la omisión
incondicional de etiquetas del spike; los demás detalles mantienen sus controles.

Se mantienen círculo de 47 px, ícono de 27 px, tipografía, importes, flecha,
colores y composición del spike. Se añaden hora y nombre de cuenta pequeños, y
una fila adaptable de editar/duplicar/borrar cuando se habilita `show_actions`:
**solo callbacks**, sin mutaciones, navegación ni reglas financieras. Frente a
las acciones de Cashew, la demostración solo muestra un mensaje traducido. El
panel local de seis interruptores usa i18n es/en; no se ha adelantado la
persistencia, autenticación o cliente HTTP de T-503/T-505.

### SVG de categoría y diferencias frente a Cashew

`CategoryIconSource` acepta clave del catálogo base Material (Apache-2.0) o
`custom:<uuid>` resuelta contra bytes suministrados por el caller. Los bytes
se copian y quedan inmutables; una clave desconocida o un SVG pendiente puede
usar fallback Material. `CategoryIcon` utiliza `SvgPicture.memory`, compartido
por tarjeta, gráfico y leyenda, dentro de los mismos círculos y con las mismas
medidas del spike. Se mantiene la geometría circular de Cashew y sus badges;
los SVG preservan sus colores por defecto y aceptan tinte opcional mediante
`ColorFilter`, equivalente visual a `colorTintCategoryIcon = false` del original.
El catálogo base conserva los Material del spike, sin copiar el catálogo PNG de
Cashew cuya licencia no se ha verificado. El ícono de casa del mock es un SVG
sintético creado para esta tarea.

Dependencia directa nueva: **flutter_svg 2.3.0** (constraint `^2.3.0`), autorizada
por T-502 y necesaria tanto para marca como categorías; versiones transitivas
en `pubspec.lock`. No se añadieron otras dependencias directas. El renderizador
vectorial no crea un DOM ni ejecuta JavaScript. La prueba inserta `<script>` y
`onload` con instrucciones que lanzarían errores y comprueba píxeles RGBA
idénticos al SVG limpio, además del render correcto en tarjeta y gráfico en
ambos temas. El parser puede imprimir `unhandled element <script/>`; es una
advertencia de elemento ignorado, sin excepción de render. **Esto no sustituye
el saneado del servidor**, obligatorio con lista blanca y cabeceras en Fase 6;
no se implementa subida ni almacenamiento aquí.

### Verificación y pendientes

Flutter 3.47.6 / Dart 3.13.5:

- `python3 -I tool/generate_dtos.py` + `dart format lib/data/api_dtos.dart`: correcto.
- `flutter pub get`, `flutter gen-l10n`: correctos; lockfile y localizaciones versionados.
- `flutter test tool/generate_brand_icons_test.dart`: **1 prueba**, genera los cinco PNG.
- `dart analyze`: **No issues found!**.
- `flutter test`, sin `--update-goldens`: **29 pruebas verdes**.
- **20 goldens** claro/oscuro: los ocho del spike (tema sin cambios; tarjetas,
  pie y fade actualizados por las variantes deliberadas) y doce nuevos de marca,
  tarjeta default/todos/ninguno, SVG propio y SVG hostil. Capturas inspeccionadas;
  tinte opcional y tamaño real de SVG 27 px cubiertos.
- Interacciones: seis interruptores independientes, callbacks de las tres
  acciones, dos cabeceras por dos días sin ocultar movimientos, tooltip compacto,
  bytes inmutables/fallback, demo es/en/tema/acento y detalles completos a 390 px.
- `flutter build web --release`: correcto; salida `build/web` ignorada por git.
- PNG: cabeceras/dimensiones 32/180/192/512/512 comprobadas, fuentes copiadas
  idénticas y todas las rutas del manifiesto apuntan a archivos existentes.
- `grep -rE 'drift|firebase|appStateSettings|package:budget/' apps/web/lib`: vacío;
  ningún PNG de categoría copiado de Cashew; originales `img/` sin cambios.

Los goldens fijan esta adaptación; no equivalen a una ejecución o comparación
píxel a píxel de Cashew. Se mantienen las diferencias geométricas y de fuente
ya registradas en T-501. Quedan la revisión visual de Adrian, el cliente/persistencia
T-503/T-505 y la API de SVG saneados de Fase 6, conforme al alcance asignado.

## T-503

Fecha: 2026-10-09. Rama: `codex/T-503-ui-api-client-session`. Contrato **0.4.0**.

La entrada principal usa la API real con sesión del servidor. `GET /users/me`
decide acceso o transacciones y obtiene la cookie CSRF pre-login. El acceso
mantiene la paleta pastel, los campos redondeados y la marca propia por modo;
conserva el fondo azul de T-502 en oscuro. La demo sintética sigue disponible en
`/#/demo`, sin HTTP, y desde la barra de la app autenticada.

### Implementación y alcance

- `lib/api/api_client.dart`: transporte `package:http`, rutas relativas, lectura
  de `monetae_csrf` por escritura, DTOs tipados y errores Problem traducidos.
  `BrowserClient.withCredentials` entrega las cookies al navegador: Dart nunca
  lee ni guarda la cookie HttpOnly. El token CSRF se relee tras login/logout.
- `lib/session/session_controller.dart`: restauración, login/logout y guardado
  confirmado por el servidor. Una respuesta 401 vuelve al acceso; los 401
  tardíos de peticiones de una sesión anterior no borran un login posterior.
- `lib/api/transaction_feed.dart` y `transaction_presenter.dart`: catálogos
  paginados (incluidos archivados), transacciones por cursor y presentación
  diaria en America/Lima, incluso al cruzar medianoche UTC. Montos y tasas
  conservan exactamente sus cadenas; no hay sumas ni conversiones monetarias.
  Las referencias de catálogo borradas usan etiquetas de reserva conservando
  el historial. `custom:<uuid>` usa el respaldo Material de T-502.
- El panel RF-47 lee el perfil y envía el objeto `preferences` **entero** en
  PATCH. Conserva tema, acento y widgets ordenados; bloquea controles mientras
  guarda y mantiene el valor confirmado si falla. Se prueba el payload y la
  restauración en una nueva instancia de la app.
- `tool/generate_dtos.py` amplía la generación desde OpenAPI a perfil,
  preferencias, login por contraseña, sesión, páginas, etiquetas y Problem;
  conserva campos requeridos/opcionales, enums, nulabilidad y tipos estrictos.
- `infra/web/default.conf` y Compose: nginx oficial `1.28.0-alpine` sirve
  `build/web` del host en solo lectura. `/api/` va a `api:8000`, conservando
  **`Host $http_host` con puerto**, Origin y cabeceras `X-Forwarded-*`.
  Puertos API/web parametrizables y publicados solo en `127.0.0.1`; CORS sigue
  vacío y el valor predeterminado de cookies Secure no cambia. `.env.example`
  explica el ajuste temporal a `false` para HTTP local.

Las acciones de edición/duplicado/borrado se pueden mostrar según RF-47 pero
están deshabilitadas en la lista real; esos flujos pertenecen a tareas siguientes.
La demo conserva sus callbacks y mensajes de presentación. No se implementan
Google, subida de SVG ni reglas financieras en la UI. Solo se añaden las
dependencias autorizadas `http` y `web`, antes transitivas; sin otro paquete.

### Verificación

- `flutter pub get`: correcto; lockfile solo promueve `http` y `web` a directas.
- `dart analyze`: **sin incidencias**.
- `flutter test`: **47 pruebas** (29 previas + 18 nuevas), **22 goldens**;
  comparados sin actualizar referencias. Los únicos goldens nuevos son acceso
  claro/oscuro, revisados visualmente completos, sin recortar el formulario.
- `flutter build web --release`: correcto; incluye el dry-run Wasm. El compilador
  conserva el aviso previo del set de fuentes Cupertino procedente del gráfico;
  MaterialIcons se genera y las pruebas y goldens pasan.
- Búsqueda `drift|firebase|appStateSettings|package:budget/` en `apps/web/lib`:
  **limpio**. `git diff --check`: correcto; no se versiona `build/` ni `.env`.
- `bash apps/web/tool/e2e_session.sh`: servidores reales con proyecto
  `monetae-t503`, PostgreSQL **5444**, API **8001** y nginx **8081**, migraciones
  al día y usuario sintético `@example.test` creado por CLI.

Resultados de curl exclusivamente contra el puerto **web**:

| Comprobación | HTTP |
|---|---:|
| index.html | 200 |
| Perfil pre-login (obtiene cookie CSRF) | 401 |
| Login y cookies | 200 |
| Perfil autenticado | 200 |
| PATCH con `Origin: http://localhost:8081` y CSRF | 200 |
| PATCH sin CSRF | 403 |
| PATCH con Origin ajeno | 403 |
| Logout | 200 |
| Perfil después de logout | 401 |

Se verificó también que PATCH conserva tema, acento, orden de widgets y las seis
preferencias. La prueba ejecuta `down -v` del proyecto propio y elimina `.env`,
cookies y respuestas temporales incluso al fallar. Sin datos reales, sin acceder
a respaldos ni modificar servicios o contrato. README incluye comandos locales,
la ruta demo y la prueba reproducible. No quedan decisiones pendientes en T-503.

## T-504

Fecha: 2026-10-09. Rama: `codex/T-504-ui-income-expense-charts`.
Contrato **0.4.0**, datos exclusivamente sintéticos. No se accedió ni se listó
`reference/backups/`, ni se tocó la pila `monetae-review`.

### Componentes y diferencias frente a Cashew

| Componente de referencia | Adaptación y diferencia deliberada |
|---|---|
| `homePageAllSpendingSummary` + `transactionsAmountBox` | Dos cajas, gasto a la izquierda e ingreso a la derecha; radio 15, padding 15/17, títulos 18 e importes 21, mismos colores financieros por tema. Reciben un `CashFlowRow` mensual de la API. El desglose original por moneda sustituye el contador de transacciones, que el contrato no proporciona, solo cuando hay varias monedas o una original distinta de la de reporte; en moneda única igual a reporte se omite. Se omite la animación numérica para conservar las cadenas exactas. |
| `lineGraph` + `homePageLineGraph` | Trazo 3, extremos redondos, puntos ocultos salvo una fila única, cuadrícula discontinua `[2,8]`, relleno degradado alfa 100→1, transición 2000 ms `fastLinearToSlowEaseIn`, tooltip redondeado 8. Evolución **por periodo**, dos series ingreso/gasto; no se calcula el acumulado que usa Cashew por defecto. Se conservan los ceros del servidor en vez de eliminar entradas vacías. Eje vertical con cero y máximo, ambos etiquetas decimales exactas; no se inventan importes intermedios con floats. |
| `incomeExpenseTabSelector` / `slidingSelectorIncomeExpense` | Control gasto/ingreso de 45 px, radio 15, fondos de acento .1/.25 y flechas financieras de 24 px. Selección controlada y accesible por teclado; `InkWell` y `AnimatedContainer` sustituyen los controladores/globales y la opción «todos». Alimenta el circular por `CategoryReportRow.kind`; al cambiar se limpia la categoría seleccionada. |
| `homePagePieChart` + circular de T-501 | Mantiene los sectores, discos y badges de T-501; añade leyenda con íconos Material, porcentajes y barras de progreso redondeadas. Los pesos/porcentajes son solo geometría normalizada; importes y desgloses se muestran desde las cadenas de `ReportTotal`. No convierte ni suma dinero. El selector explícito sustituye el swipe/indicador de páginas del original móvil; en escritorio sigue mostrando un circular seleccionado, sin el doble panel del original. La leyenda mantiene los ListTile del spike con barras de 5 px, frente a la composición más completa de `categoryEntry`. |
| `barGraph` | No se usa en esta vista de inicio: el original recibe un presupuesto y sus rangos históricos. No se ha portado ni añadido un gráfico ajeno a esta composición; corresponde a T-507. |
| `homePageHeatmap` | Opcional, diferido. No condiciona esta entrega. |
| `transactionEntryTag` | Etiqueta de cuenta con radio 6, padding 4.5/1.05, texto 11.5 y fondo con alfa .25, usando `Account.color`. Color nulo/inválido: hash explícito del id, estable entre procesos y plataformas, sobre seis tonos de `colors.dart`. Una paleta finita puede repetir tonos; no se usa el hash variable de Dart. |

Las fuentes, los íconos del catálogo y las diferencias geométricas del circular
siguen lo registrado en T-501/T-502. Cada nuevo archivo derivado incluye origen,
autoría GPL-3.0 y modificaciones; `NOTICE` recoge la procedencia. Sin dependencias
nuevas y sin PNG de categorías de Cashew. Los goldens fijan la adaptación;
la aceptación visual frente al original corresponde a Adrian.

### Cliente, pantalla y símbolos

Los DTO de los seis esquemas de reportes se generan desde OpenAPI con el
script existente. `ApiClient.cashFlow` y `categoryReport` aceptan filtros,
periodo, límite y cursor; los null se omiten para respetar los defaults de T-506.
`ReportFeed` recorre todas las páginas y detecta cursores repetidos.

Inicio es ahora la pantalla tras restaurar la sesión. Usa el mes natural
seleccionado: petición diaria para la línea, mensual para **un único total**
y categories sin `period` para el circular del rango entero. Así no suma los
cubos diarios en Flutter. El servidor conserva sus reglas de zona horaria,
periodos inclusivos y orden; el mes inicial de presentación usa America/Lima,
como el resto de la UI V1. Hay navegación por meses y acceso a transacciones,
demo, recarga y cierre de sesión. `/#/demo/home` muestra la misma composición
con fixtures sintéticas y cambio de tema; `/#/demo` conserva el spike anterior.

404/501, incluso sin JSON Problem, muestran vacío i18n; otros errores tienen
reintento. Un 401 elimina las rutas de la sesión anterior y vuelve al acceso,
también desde la lista de transacciones abierta. La lista escucha las
preferencias confirmadas del perfil al vivir ahora en una ruta secundaria.

`unconverted_count > 0` en resumen, flujo o categorías muestra un aviso discreto
es/en. Los originales de `by_currency` se conservan visibles, incluso si una
categoría tiene total convertido cero y por ello no tiene sector.

Un único formateador usa símbolos de **intl** y agrupa las cadenas sin pasarlas
por double y sin redondearlas. Tras la revisión T-504b se restaura el formato
peruano aprobado para `es`: símbolo delante con espacio, miles con coma, decimal
con punto y dos decimales (`S/ 1,234.50`, `US$ 48.50`, `€ 48.50`). `intl` con
`es` o `es_PE` no produce ese formato, por lo que se fija explícitamente. Para
`en` se conserva el patrón `en_US`, sin espacio (`US$1,234.50`); un negativo
explícito lleva el signo antes del símbolo, y la tarjeta sigue usando flecha/color.
La familia de símbolos compartidos se califica siempre con
formas específicas (`US$`, `CA$`, `A$`, `JP¥`, `CN¥`, etc.), para que dos monedas
no se confundan ni cambie la etiqueta al añadir otra. El catálogo de símbolos
simples de intl no distingue esos casos: se complementa con calificadores
convencionales explícitos, también para coronas/libras/francos. Una moneda sin
símbolo reconocido usa `¤`, nunca el código ISO. Se eliminan los formateadores
ARB que permitían mostrar el código y se actualiza también el mock anterior.
No se añade ninguna etiqueta de tipo de moneda a tarjetas ni gráficas.

### Verificación y estimación pendiente

Flutter 3.47.6 / Dart 3.13.5. Verificación final: `flutter pub get`, `dart analyze`
sin incidencias, `flutter test` con **83 pruebas verdes**, **38 goldens**
comparados sin actualizar referencias, y `flutter build web --release` correcto.
El build conserva el aviso previo de fuente Cupertino procedente de fl_chart;
MaterialIcons está empaquetada, y el dry-run Wasm compila.

Los 14 goldens nuevos cubren resumen, líneas con/sin periodos vacíos,
selector+circular de ambos tipos, inicio demo completo y tres tarjetas
PEN/USD/EUR con cuentas de distinto color, en claro y oscuro. Las referencias
anteriores de tarjetas/circular se actualizan por la localización de importes y
la etiqueta coloreada; el tema y el acceso permanecen iguales. Capturas
inspeccionadas. Pruebas MockClient: parámetros de ambos endpoints, desgloses y
`ReportTotal` exactos, paginación, defaults omitidos, aviso sin tasa, vacío
404/501 en ambos endpoints, reintento 500, cambio de mes, cierre de sesión fallido y 401. También se
comprueban importes mayores que la precisión de double, fallback de colores,
selección ingreso/gasto y anchura de 390 px. Búsqueda de acoplamientos prohibidos
en `lib` y `git diff --check`: limpios; `build/` queda ignorado.

Estimación actualizada de lo que falta de Fase 5, separando desacople de
ensamblado funcional (rangos orientativos, sin comprometer tareas del coordinador):

| Trabajo pendiente | Tareas de 1–2 h |
|---|---:|
| Presupuestos y metas con progreso/historial de barras (T-507) | 2–3 |
| Resto de widgets de inicio, orden/preferencias y animaciones pertinentes | 2–3 |
| Formularios y navegación de transacciones/cuentas/categorías | 3–4 |
| Pantallas de préstamos y suscripciones sobre la API existente | 3–4 |
| Revisión de fidelidad con Adrian, responsive y recorrido completo | 2–3 |
| **Total restante de UI Fase 5** | **12–17** |

Rango aproximado **18–30 h** de implementación/revisión, incertidumbre media;
solo desacople visual pendiente **4–6 tareas / 6–10 h**. No incluye los endpoints
pendientes de Fase 6, API de SVG, heatmap opcional ni nuevas funciones de negocio.
T-506 se integra aparte; esta entrega ya soporta tanto sus respuestas 200 como
su ausencia temporal. No quedan decisiones de diseño bloqueantes en T-504.

### Seguimiento T-504b

La revisión del coordinador detectó dos regresiones: el patrón español de intl
había cambiado el formato peruano aprobado, y el resumen repetía el importe
en el desglose de una sola moneda igual a la de reporte. Se corrigen ambas
en el formateador compartido y en `IncomeExpenseSummary`, sin cambiar el cliente
ni hacer operaciones monetarias. La regla se aplica a tarjetas, resumen, ejes,
tooltips, leyendas y filas porque todos usan el mismo formateador.

Nueve pruebas unitarias nuevas cubren `es`/`en`, PEN/USD/EUR, miles, negativos,
valor absoluto, cero, dos decimales y cifras mayores que la precisión de double;
también cubren `es_PE`. El golden de resumen habitual verifica una sola línea
por importe; dos goldens nuevos muestran el caso multimoneda y el de una sola
moneda original distinta de reporte. Solo se regeneran los 28 goldens afectados
por los importes/composición; los ocho de tema, marca, circular aislado y acceso
quedan idénticos. Verificaciones: pub get, analyze limpio, 83 tests verdes sin
actualizar goldens, release web correcto y búsqueda de acoplamientos vacía.
Se mantiene la estimación anterior de Fase 5 y no quedan decisiones pendientes
en este seguimiento.
