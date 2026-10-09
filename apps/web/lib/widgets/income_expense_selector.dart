// Derived from Cashew budget/lib/widgets/{incomeExpenseTabSelector,
// slidingSelectorIncomeExpense}.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: controlled selection and SDK localization.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

class IncomeExpenseSelector extends StatelessWidget {
  const IncomeExpenseSelector({
    super.key,
    required this.income,
    required this.onChanged,
  });
  final bool income;
  final ValueChanged<bool> onChanged;
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(15),
      child: Material(
        color: Theme.of(context).colorScheme.primary.withValues(alpha: .1),
        child: Row(
          children: [
            for (final isIncome in [false, true])
              Expanded(
                child: Semantics(
                  selected: income == isIncome,
                  child: InkWell(
                    key: Key(isIncome ? 'select-income' : 'select-expense'),
                    onTap: () => onChanged(isIncome),
                    child: AnimatedContainer(
                      duration: MediaQuery.disableAnimationsOf(context)
                          ? Duration.zero
                          : const Duration(milliseconds: 200),
                      height: 45,
                      color: income == isIncome
                          ? Theme.of(context).colorScheme.primary
                                .withValues(alpha: .25)
                          : Colors.transparent,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          RotatedBox(
                            quarterTurns: isIncome ? 2 : 0,
                            child: Icon(
                              Icons.arrow_drop_down_rounded,
                              size: 24,
                              color: isIncome ? colors.income : colors.expense,
                            ),
                          ),
                          Text(
                            isIncome ? l.income : l.expense,
                            style: TextStyle(
                              fontSize: 14,
                              color: income == isIncome ? null : colors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
