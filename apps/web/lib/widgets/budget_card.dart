// Derived from Cashew budget/lib/widgets/budgetContainer.dart
// (BudgetContainer and BudgetTimeline), Copyright (C) 2023 James Kokoska, GPL-3.0.
// Modified for Monetae on 2026-10-09: typed server amounts/range, static tinted
// header, explicit callbacks, no local finance queries or per-day calculations.
import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/budget_calculations.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_progress.dart';
import '../presentation/transaction_presenter.dart';
import '../theme/monetae_theme.dart';
import 'budget_progress.dart';

class BudgetCard extends StatelessWidget {
  const BudgetCard({super.key, required this.budget, this.today, this.onTap});
  final BudgetDto budget;
  final DateTime? today;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final color = presentationColor(
      budget.color,
      fallback: theme.colorScheme.primary,
    );
    final progress = DecimalProgress.fromAmounts(
      budget.spentAmount,
      budget.amount,
    );
    final exceeded =
        budget.remainingAmount.startsWith('-') &&
        RegExp('[1-9]').hasMatch(budget.remainingAmount);
    String money(String value, {bool absolute = false}) => formatCurrency(
      value,
      budget.currency,
      l.localeName,
      absolute: absolute,
    );
    final dateFormat = DateFormat.MMMd(l.localeName);
    
    // Header is color, footer is color * darker
    return Material(
      color: pastel(
        color,
        theme.brightness,
        theme.brightness == Brightness.light ? .92 : .8,
      ),
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              color: pastel(
                color,
                theme.brightness,
                theme.brightness == Brightness.light ? .65 : .45,
              ),
              padding: const EdgeInsetsDirectional.fromSTEB(23, 13, 23, 13),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          budget.name,
                          style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text.rich(
                          TextSpan(
                            children: [
                              TextSpan(
                                text: money(
                                  budget.remainingAmount,
                                  absolute: exceeded,
                                ),
                              ),
                              TextSpan(
                                text: exceeded
                                    ? l.budgetOver('', money(budget.amount))
                                    : l.budgetLeft('', money(budget.amount)),
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.normal,
                                ),
                              ),
                            ],
                          ),
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.history, color: Colors.white),
                      onPressed: () {}, // Historial
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(15, 12, 15, 17),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        dateFormat.format(DateTime.parse(budget.startOn)),
                        style: const TextStyle(fontSize: 13),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: BudgetProgress(
                          darkTrackAmount: .45,
                          progress: progress,
                          color: color,
                          today: todayFraction(
                            budget.startOn,
                            budget.endOn,
                            today ?? DateTime.now(),
                          ),
                        ),
                      ),
                      if (budget.endOn != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          dateFormat.format(DateTime.parse(budget.endOn!)),
                          style: const TextStyle(fontSize: 13),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 12),
                  Builder(
                    builder: (context) {
                      final perDay = budgetPerDayLabel(
                        l,
                        budget,
                        Decimal.parse(budget.spentAmount),
                        today ?? DateTime.now(),
                      );
                      if (perDay == null) return const SizedBox.shrink();
                      return Text(
                        perDay,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.white.withValues(alpha: 0.5),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
