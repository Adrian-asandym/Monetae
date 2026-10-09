import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';

/// Supplemental server totals only; never combines currencies or derives money.
/// Omit the duplicate amount when all originals use the card currency.
class BudgetGoalReportTotal extends StatelessWidget {
  const BudgetGoalReportTotal({
    super.key,
    required this.total,
    required this.currency,
  });
  final ReportTotalDto total;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final foreign = total.byCurrency.any((value) => value.currency != currency);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (foreign || total.reportCurrency != currency)
          Text(
            l.convertedTotal(
              formatCurrency(
                total.reportAmount,
                total.reportCurrency,
                l.localeName,
              ),
            ),
            style: const TextStyle(fontSize: 12),
          ),
        if (foreign)
          Text(
            total.byCurrency
                .map(
                  (value) => formatCurrency(
                    value.amount,
                    value.currency,
                    l.localeName,
                  ),
                )
                .join(' · '),
            style: TextStyle(
              fontSize: 12,
              color: MonetaeColors.of(context).muted,
            ),
          ),
        if (total.unconvertedCount > 0)
          Text(
            l.unconvertedNotice,
            style: TextStyle(
              fontSize: 12,
              color: MonetaeColors.of(context).muted,
            ),
          ),
      ],
    );
  }
}
