import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../l10n/app_localizations.dart';

class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, this.size = 52});
  final double size;

  @override
  Widget build(BuildContext context) => SvgPicture.asset(
    Theme.of(context).brightness == Brightness.dark
        ? 'assets/brand/icono-Monetae-dark.svg'
        : 'assets/brand/icono-Monetae.svg',
    width: size,
    height: size,
    semanticsLabel: AppLocalizations.of(context).appTitle,
  );
}
