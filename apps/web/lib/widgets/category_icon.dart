import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../presentation/category_icon_source.dart';

/// A vector renderer, never an HTML/DOM image: scripts/events are not executed.
/// Server-side sanitization still belongs to the icons API (RF-46).
class CategoryIcon extends StatelessWidget {
  const CategoryIcon({
    super.key,
    required this.source,
    required this.color,
    this.size = 27,
    this.tintCustom = false,
  });

  final CategoryIconSource source;
  final Color color;
  final double size;
  final bool tintCustom;

  @override
  Widget build(BuildContext context) {
    final bytes = source.svgBytes;
    if (bytes == null) {
      return Icon(source.materialIcon, size: size, color: color);
    }
    return Center(
      widthFactor: 1,
      heightFactor: 1,
      child: SvgPicture.memory(
        bytes,
        width: size,
        height: size,
        colorFilter: tintCustom
            ? ColorFilter.mode(color, BlendMode.srcIn)
            : null,
        errorBuilder: (_, _, _) =>
            Icon(Icons.category_rounded, size: size, color: color),
      ),
    );
  }
}
