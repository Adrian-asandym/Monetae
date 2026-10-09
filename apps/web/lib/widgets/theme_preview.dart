import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

class ThemePreview extends StatelessWidget {
  const ThemePreview({super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        for (final (label, color) in [
          (l.themeBackground, colors.background),
          (l.themeCard, colors.card),
          (l.income, colors.income),
          (l.expense, colors.expense),
          (l.scheduled, colors.upcoming),
        ])
          Column(
            children: [
              Container(
                width: 64,
                height: 48,
                decoration: BoxDecoration(
                  color: color,
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outline,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              const SizedBox(height: 6),
              Text(label),
            ],
          ),
      ],
    );
  }
}
