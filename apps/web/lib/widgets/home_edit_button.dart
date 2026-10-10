import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

class HomeEditButton extends StatelessWidget {
  const HomeEditButton({super.key, required this.onPressed});
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: HomeTokens.editWidth,
    height: HomeTokens.editHeight,
    child: TextButton(
      key: const Key('edit-home'),
      onPressed: onPressed,
      style: TextButton.styleFrom(
        backgroundColor: MonetaeColors.of(context).card,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        padding: const EdgeInsets.symmetric(horizontal: HomeTokens.editPadding),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(HomeTokens.editRadius),
        ),
        textStyle: Theme.of(context).textTheme.labelLarge!.copyWith(
          fontSize: HomeTokens.editFontSize,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.edit_rounded, size: HomeTokens.editIconSize),
          const SizedBox(width: HomeTokens.editGap),
          Text(AppLocalizations.of(context).editHome),
        ],
      ),
    ),
  );
}
