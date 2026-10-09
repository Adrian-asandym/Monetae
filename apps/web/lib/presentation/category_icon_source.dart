import 'dart:typed_data';

import 'package:flutter/material.dart';

/// Material icons are supplied by Flutter (Apache-2.0); no third-party PNGs.
const baseCategoryIcons = <String, IconData>{
  'restaurant': Icons.restaurant_rounded,
  'work': Icons.work_rounded,
  'transport': Icons.directions_bus_rounded,
  'home': Icons.home_rounded,
  'wallet': Icons.account_balance_wallet_rounded,
  'loan': Icons.handshake_outlined,
  'calendar': Icons.calendar_month_outlined,
};

@immutable
class CategoryIconSource {
  const CategoryIconSource.base(this.key) : svgBytes = null;

  CategoryIconSource.custom(String id, Uint8List bytes)
    : key = 'custom:$id',
      svgBytes = Uint8List.fromList(bytes).asUnmodifiableView();

  /// Resolve Category.icon with bytes already fetched by the caller.
  /// Missing/deleted icons fall back to a base icon until bytes are available.
  factory CategoryIconSource.resolve(
    String? key, {
    Map<String, Uint8List> customIcons = const {},
  }) {
    if (key != null && key.startsWith('custom:')) {
      final id = key.substring(7);
      final bytes = customIcons[id];
      if (bytes != null) return CategoryIconSource.custom(id, bytes);
    }
    return CategoryIconSource.base(key ?? 'wallet');
  }

  final String key;
  final Uint8List? svgBytes;
  IconData get materialIcon => baseCategoryIcons[key] ?? Icons.category_rounded;
}
