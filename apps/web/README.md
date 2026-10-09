# Monetae · spike T-501

Pantalla Flutter Web de componentes con datos exclusivamente sintéticos. Permite
cambiar tema, acento, idioma (es/en), vista compacta y selección del gráfico, y
repetir la entrada animada. No conecta al backend ni persiste cambios.

Desde esta carpeta, con Flutter 3.47.6 / Dart 3.13.5:

```bash
export PATH="$HOME/flutter/bin:$PATH"
flutter pub get
flutter gen-l10n
dart analyze
flutter test
flutter build web --release
```

Para la revisión en Chrome, servir `build/web` con cualquier servidor estático;
por ejemplo, `python3 -m http.server 8080 --directory build/web`.

Los DTO de Account, Category y Transaction provienen de OpenAPI 0.3.0:

```bash
python3 tool/generate_dtos.py
dart format lib/data/api_dtos.dart
```

El generador conserva todos los campos, enums y nulabilidad de esas respuestas;
no es todavía un cliente HTTP. Verifica estructura y tipos sin coerción, pero no
replica las restricciones financieras/formato del servidor. Montos y tasas son
cadenas decimales exactas; los widgets reciben textos formateados y proporciones
para la geometría. El cliente HTTP y los reportes de la API son trabajo posterior.

Los ocho goldens tienen tamaño fijo, Roboto y MaterialIcons del SDK y cubren cada
componente en claro/oscuro; la animación se captura a los 250 ms. Las comparaciones
se realizan con `flutter test`, sin actualizar las referencias. Para un cambio
visual deliberado y revisado: `flutter test --update-goldens`.

Procedencia, modificaciones y atribución en NOTICE; licencia original íntegra en
LICENSE. El informe y las diferencias frente al original están en
`../../docs/cashew-analysis/05-ui-spike-results.md`.
