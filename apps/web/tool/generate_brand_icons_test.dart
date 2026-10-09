// Run from apps/web: flutter test tool/generate_brand_icons_test.dart
// Reproducible Flutter/vector rendering; no system rasterizer is required.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('generate PNG web icons from the light brand SVG', () async {
    final svg = await File('assets/brand/icono-Monetae.svg').readAsString();
    final picture = await vg.loadPicture(SvgStringLoader(svg), null);
    try {
      for (final (name, size, maskable) in [
        ('favicon.png', 32, false),
        ('apple-touch-icon.png', 180, false),
        ('Icon-192.png', 192, false),
        ('Icon-512.png', 512, false),
        ('Icon-maskable-512.png', 512, true),
      ]) {
        final recorder = ui.PictureRecorder();
        final canvas = Canvas(recorder);
        canvas.drawColor(const Color(0xFFE9EEF7), BlendMode.src);
        // Maskable artwork fits within the central safe-zone circle.
        final fraction = maskable ? .56 : .9;
        final inset = size * (1 - fraction) / 2;
        canvas.translate(inset, inset);
        canvas.scale(
          size * fraction / picture.size.width,
          size * fraction / picture.size.height,
        );
        canvas.drawPicture(picture.picture);
        final rasterPicture = recorder.endRecording();
        final raster = await rasterPicture.toImage(size, size);
        try {
          final png = await raster.toByteData(format: ui.ImageByteFormat.png);
          if (png == null) throw StateError('PNG encoding failed');
          await File('web/icons/$name').writeAsBytes(png.buffer.asUint8List());
        } finally {
          raster.dispose();
          rasterPicture.dispose();
        }
      }
    } finally {
      picture.picture.dispose();
    }
  });
}
