# Monetae · componentes T-501 y T-502

Pantalla Flutter Web de componentes con datos exclusivamente sintéticos. Permite
cambiar tema, acento, idioma (es/en), vista compacta, detalles de la tarjeta y
selección del gráfico, teñir los SVG propios y repetir la entrada animada. No
conecta al backend ni persiste cambios: HTTP/sesión llegan con T-503, las
preferencias del servidor con T-505 y la biblioteca de SVG con la Fase 6.

Desde esta carpeta, con Flutter 3.47.6 / Dart 3.13.5:

```bash
export PATH="$HOME/flutter/bin:$PATH"
flutter pub get
flutter gen-l10n
python3 -I tool/generate_dtos.py
dart format lib/data/api_dtos.dart
flutter test tool/generate_brand_icons_test.dart
dart analyze
flutter test
flutter build web --release
```

Para la revisión en Chrome, servir `build/web` con un servidor estático;
por ejemplo, `python3 -I -m http.server 8080 --bind 127.0.0.1 --directory build/web`.

Los DTO de Account, Category, Transaction, UserIcon y TransactionCardPreferences
provienen de OpenAPI **0.4.0**. El generador conserva todos los campos, enums,
nulabilidad y valores predeterminados de las preferencias; no es todavía un
cliente HTTP. Verifica estructura y tipos sin coerción, pero no replica las
restricciones financieras/formato del servidor. Montos y tasas son cadenas
exactas; los widgets reciben textos formateados y proporciones geométricas.
`TransactionCardPreferencesDto` incluye `copyWith` y `toJson` para que el cliente
posterior pueda guardar el objeto `UserPreferences.transaction_card`.

`show_date` controla cabeceras de grupo por día en `TransactionCardList`; los
modelos llegan ordenados, con claves, fechas y horas ya formateadas por el caller.
El mock usa días y horas sintéticos de America/Lima. Las acciones son callbacks;
en la demostración solo muestran un mensaje traducido. La vista compacta presenta la nota como tooltip; `show_note = false` también
lo oculta. `show_tags` manda en ambas variantes; hora, cuenta y acciones
conservan su control propio.

`BrandLogo` dibuja el SVG propio según el **tema interno de la app**. El favicon
usa el **modo del sistema/navegador**, mediante dos enlaces SVG con `media` y
respaldo PNG: el tema interno de Flutter no cambia esa preferencia del navegador.
El manifiesto y el ícono de Apple usan PNG del SVG **claro**, de forma estable.
Las cuatro fuentes se copian sin cambios desde `img/` a `assets/brand/`.

`tool/generate_brand_icons_test.dart` genera PNG 32/180/192/512 y maskable 512
mediante `flutter_svg` + `Picture.toImage`, usando el motor de Flutter, sin
rasterizadores del sistema. El maskable deja el dibujo dentro de la zona segura
central (cuadrado del 56 % del lienzo, dentro del círculo del 80 %). Para regenerar,
ejecutar el `flutter test` dedicado del bloque anterior y revisar los archivos.

`CategoryIconSource.resolve` interpreta claves Material o `custom:<uuid>` y
recibe un mapa de bytes del caller; los bytes se copian y quedan inmutables.
Íconos pendientes/desconocidos usan un fallback Material. El mismo `CategoryIcon`
rasteriza vectores en tarjetas, badges y leyenda, con tinte propio opcional.
`flutter_svg: ^2.3.0` es la nueva dependencia directa autorizada: necesaria para
las marcas SVG y RF-46, evitando HTML/DOM y rasterizadores externos. Sus paquetes
transitivos se registran en el lockfile. El catálogo Material es Apache-2.0 y la
ilustración del mock es original; no se copiaron PNG de categorías de Cashew.

Las **29 pruebas** incluyen **20 goldens**, con tamaño fijo, Roboto y MaterialIcons
del SDK: marca, tarjetas por defecto/todos/ninguno, SVG propio y SVG con script,
además de tema, tarjetas originales, gráfico y fade del spike, en claro/oscuro.
La prueba hostil añade `<script>` y `onload` que lanzarían errores si se ejecutaran:
el renderizador ignora esos elementos/atributos, no falla y produce exactamente
los mismos píxeles que el SVG limpio. Puede emitir `unhandled element <script/>`.
Esto verifica el renderizador; el saneado con lista blanca en el servidor sigue
siendo obligatorio en Fase 6.

Las comparaciones se realizan con `flutter test`, sin actualizar referencias.
Para un cambio visual deliberado y revisado: `flutter test --update-goldens`.

Procedencia y modificaciones en NOTICE; licencia original íntegra en LICENSE.
Informe y diferencias frente a Cashew:
`../../docs/cashew-analysis/05-ui-spike-results.md`, sección «T-502».
