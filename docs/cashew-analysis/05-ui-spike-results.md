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
