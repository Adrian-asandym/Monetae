# Monetae · acceso y transacciones reales (T-503)

La ruta principal comprueba `GET /api/v1/users/me`, muestra el acceso por correo y
contraseña o carga las transacciones del usuario. La sesión se conserva en la
cookie HttpOnly del servidor; no se guarda en localStorage ni se lee desde Dart.
El cliente usa exclusivamente rutas relativas `/api/v1/...`, `BrowserClient`
con cookies del navegador y la cookie legible `monetae_csrf` para cada escritura.
El GET inicial obtiene también el CSRF pre-login. Login/logout rotan esa cookie:
se vuelve a leer en cada escritura, sin guardar una copia del token.

Un 401 en cualquier petición devuelve al acceso. Los errores Problem 403/409/422
se convierten en errores tipados y mensajes es/en; el texto interno del servidor
no se muestra. El tema, acento, idioma y tarjeta se leen del perfil. El panel
RF-47 guarda la tarjeta mediante PATCH **con las preferencias completas**:
conserva el tema, el acento y el orden de `home_widgets`. Mientras se guarda se
bloquean los controles; la respuesta del servidor confirma el cambio.

La lista carga páginas por cursor con «Cargar más» y agrupa por día de
America/Lima (UTC−05, independiente de la zona del navegador). Montos y tasas
siguen siendo cadenas; solo se formatean textos, sin sumar ni convertir dinero.
Los catálogos también se paginan y se incluyen cuentas/etiquetas archivadas.
Si una referencia eliminada ya no está disponible, el historial sigue visible
con una etiqueta de reserva. `custom:<uuid>` muestra el ícono de reserva del
catálogo hasta la biblioteca de SVG de Fase 6. Las acciones de las tarjetas se
pueden mostrar con RF-47, pero están deshabilitadas: los flujos de edición,
duplicado y borrado pertenecen a las pantallas siguientes.

## Ejecución local en el mismo origen

Desde la raíz del repositorio:

```bash
export PATH="$HOME/flutter/bin:$HOME/.local/bin:$PATH"
(cd apps/web && flutter pub get && flutter build web --release)
cp .env.example .env
# Para HTTP local, cambiar MONETAE_COOKIE_SECURE=true a false en .env.
docker compose -f infra/docker-compose.yml up -d --build db api web
# Usuario sintético de ejemplo; la contraseña se solicita, nunca como argumento.
docker compose -f infra/docker-compose.yml exec api python -m monetae.cli create-user --email sample@example.test
```

Abrir `http://localhost:8080`. nginx oficial `1.28.0-alpine` sirve la compilación
del host mediante montaje de solo lectura y reenvía `/api/` a `api:8000`.
`Host $http_host` conserva el puerto público para la comprobación de Origin;
se incluyen `X-Forwarded-Host/Proto/Port/For` y `X-Real-IP`. CORS continúa vacío.
Solo se publican puertos en `127.0.0.1`. Por ejemplo, otro worker puede usar
`COMPOSE_PROJECT_NAME=otro MONETAE_DB_PORT=5445 MONETAE_API_PORT=8002
MONETAE_WEB_PORT=8082 docker compose -f infra/docker-compose.yml up -d`.
Las cookies Secure siguen siendo el valor predeterminado; `false` es únicamente
para el entorno HTTP local. HTTPS y proxy de producción quedan para el hito VPS.

`http://localhost:8080/#/demo` conserva la demostración con datos sintéticos y
sus controles de tema/idioma/acento, sin iniciar el cliente HTTP. Desde la app
hay un acceso a esa demostración en la barra superior.

## Validación T-503

```bash
cd apps/web
python3 -I tool/generate_dtos.py
dart format lib/data/api_dtos.dart
flutter gen-l10n
dart analyze
flutter test
flutter build web --release
cd ../..
bash apps/web/tool/e2e_session.sh
```

La prueba E2E exige no tener `.env` previo, crea un entorno temporal con datos
sintéticos y usa exclusivamente el proyecto `monetae-t503` y puertos
5444/8001/8081. Compila primero como indica el bloque anterior. Levanta los tres
servicios, comprueba migraciones y crea el usuario por CLI; curl contra **web**
verifica index 200, bootstrap 401 con cookie, login 200, perfil 200, PATCH con
Origin/CSRF 200, sin CSRF 403, con otro Origin 403, logout 200 y perfil posterior
401. Al salir ejecuta `down -v` y elimina `.env`, las cookies y respuestas
temporales. No ejecutar mientras otro proceso use ese proyecto o esos puertos.

Las dependencias directas nuevas autorizadas son `http` (transporte y
MockClient) y `web` (lectura de la cookie CSRF). Ya eran transitivas; el lockfile
solo cambia su clasificación. Los DTO de perfil, sesión, páginas, etiquetas y
Problem se generan del contrato 0.4.0 junto con los DTO anteriores. Las **47 pruebas** (29 previas + 18 nuevas) y **22 goldens** incluyen sesión,
CSRF, errores tipados, paginación, preferencias y acceso claro/oscuro. La prueba
PATCH verifica conservación completa y restauración al montar una nueva sesión.

## Componentes T-501 y T-502

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
nulabilidad y valores predeterminados de las preferencias; el cliente HTTP está en `lib/api/`. Verifica estructura y tipos sin coerción, pero no replica las
restricciones financieras/formato del servidor. Montos y tasas son cadenas
exactas; los widgets reciben textos formateados y proporciones geométricas.
`TransactionCardPreferencesDto` incluye `copyWith` y `toJson` para que el cliente
pueda guardar el objeto `UserPreferences.transaction_card`.

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

Las **29 pruebas de componentes** incluyen **20 goldens**, con tamaño fijo, Roboto y MaterialIcons
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
