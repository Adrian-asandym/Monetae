// Derived from Cashew budget/lib/pages/objectivesListPage.dart
// (ObjectiveContainer), Copyright (C) 2023 James Kokoska, GPL-3.0.
// Modified for Monetae on 2026-10-09: Goal DTO, exact progress/target labels,
// save/spend types, vector catalog icons and explicit presentation callbacks.
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/clock.dart';
import '../presentation/budget_calculations.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_progress.dart';
import '../presentation/transaction_presenter.dart';
import '../theme/monetae_theme.dart';
import 'budget_progress.dart';
import 'category_icon.dart';

class GoalCard extends StatelessWidget {
  const GoalCard({
    super.key,
    required this.goal,
    this.customIcons = const {},
    this.tintCustomIcon = false,
    this.onTap,
  });
  final GoalDto goal;
  final Map<String, Uint8List> customIcons;
  final bool tintCustomIcon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final theme = Theme.of(context);
    final color = presentationColor(
      goal.color,
      fallback: theme.colorScheme.primary,
    );
    final progress = DecimalProgress.fromAmounts(
      goal.progressAmount,
      goal.targetAmount,
    );
    String money(String value) =>
        formatCurrency(value, goal.currency, l.localeName);

    return Material(
      color: colors.card,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsetsDirectional.fromSTEB(20, 18, 20, 23),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          goal.name,
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Builder(
                          builder: (context) {
                            final perDay = goalPerDayLabel(
                              l,
                              goal,
                              PresentationClock.of(context),
                            );
                            if (perDay == null) return const SizedBox.shrink();
                            return Text(
                              perDay,
                              style: TextStyle(
                                fontSize: 14,
                                color: colors.muted,
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 5),
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: pastel(color, theme.brightness, .7),
                      shape: BoxShape.circle,
                    ),
                    child: CategoryIcon(
                      source: CategoryIconSource.resolve(
                        goal.icon,
                        customIcons: customIcons,
                      ),
                      color: color,
                      size: 30,
                      tintCustom: tintCustomIcon,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(text: money(goal.progressAmount)),
                    TextSpan(
                      text: l.goalAmounts('', money(goal.targetAmount)),
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.normal,
                        color: colors.muted,
                      ),
                    ),
                  ],
                ),
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Text(
                    DateFormat.MMMd(l.localeName)
                        .format(DateTime.parse(goal.createdAt)),
                    style: TextStyle(fontSize: 13, color: colors.muted),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: BudgetProgress(progress: progress, color: color),
                  ),
                  const SizedBox(width: 8),
                  if (goal.dueOn != null)
                    Text(
                      DateFormat.MMMd(l.localeName)
                          .format(DateTime.parse(goal.dueOn!)),
                      style: TextStyle(fontSize: 13, color: colors.muted),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
