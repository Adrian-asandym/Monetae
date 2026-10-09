// Derived palette from Cashew budget/lib/colors.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: stable ID-based account fallback.
import 'package:flutter/material.dart';

import 'transaction_presenter.dart';

const accountPalette = [
  Color(0xFF59A849),
  Color(0xFFCA5A5A),
  Color(0xFF58A4C2),
  Color(0xFF6577E0),
  Color(0xFFCA995A),
  Color(0xFFFFD723),
];

Color accountColor(String id, String? color) {
  // Explicit hash, independent of platform/run and Dart's String.hashCode.
  var hash = 0;
  for (final unit in id.codeUnits) {
    hash = (hash * 31 + unit) % 65521;
  }
  return presentationColor(
    color,
    fallback: accountPalette[hash % accountPalette.length],
  );
}
