// Derived from Cashew budget/lib/pages/homePage/homePageAllSpendingSummary.dart
// and widgets/transactionsAmountBox.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: server totals, no streams/count animation.
import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../theme/monetae_theme.dart';

class IncomeExpenseSummary extends StatelessWidget {
  const IncomeExpenseSummary({super.key, required this.row});
  final CashFlowRowDto row;
  @override
  Widget build(BuildContext context) {
    final colors = MonetaeColors.of(context);
    final l = AppLocalizations.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: _box(context, l.expense, row.expense, colors.expense)),
        const SizedBox(width: 10),
        Expanded(child: _box(context, l.income, row.income, colors.income)),
      ],
    );
  }

  Widget _box(
    BuildContext context,
    String label,
    ReportTotalDto total,
    Color color,
  ) {
    final l = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 17),
      decoration: BoxDecoration(
        color: MonetaeColors.of(context).card,
        borderRadius: BorderRadius.circular(15),
      ),
      child: Column(
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              reportAmount(total, l),
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            currencyBreakdown(total, l).join(' · '),
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              color: MonetaeColors.of(context).muted,
            ),
          ),
        ],
      ),
    );
  }
}
