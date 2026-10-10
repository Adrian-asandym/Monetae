import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../presentation/component_models.dart';
import 'transaction_card.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';
import '../l10n/app_localizations.dart';

/// Receives an already ordered list and caller-formatted dates (America/Lima).
/// showDate controls daily group headers, never a date inside each card.
class TransactionCardList extends StatelessWidget {
  const TransactionCardList({
    super.key,
    required this.models,
    this.preferences = const TransactionCardPreferencesDto(),
    this.compact = false,
    this.tintCategoryIcons = false,
    this.dailyFlow,
    this.onEdit,
    this.onDuplicate,
    this.onDelete,
  });
  final List<TransactionCardModel> models;
  final TransactionCardPreferencesDto preferences;
  final bool compact;
  final bool tintCategoryIcons;
  final List<CashFlowRowDto>? dailyFlow;
  final ValueChanged<TransactionCardModel>? onEdit;
  final ValueChanged<TransactionCardModel>? onDuplicate;
  final ValueChanged<TransactionCardModel>? onDelete;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      for (var i = 0; i < models.length; i++) ...[
        if (preferences.showDate &&
            (i == 0 || models[i].dateKey != models[i - 1].dateKey))
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    models[i].dateLabel,
                    key: ValueKey('date-${models[i].dateKey}'),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (dailyFlow != null)
                  Builder(
                    builder: (context) {
                      final net = dailyFlow!.firstWhere(
                        (r) => r.startOn.startsWith(models[i].dateKey),
                        orElse: () => const CashFlowRowDto(
                          startOn: '',
                          endOn: '',
                          income: ReportTotalDto(byCurrency: [], reportCurrency: 'PEN', reportAmount: '0.00', unconvertedCount: 0),
                          expense: ReportTotalDto(byCurrency: [], reportCurrency: 'PEN', reportAmount: '0.00', unconvertedCount: 0),
                          net: ReportTotalDto(byCurrency: [], reportCurrency: 'PEN', reportAmount: '0.00', unconvertedCount: 0),
                          cumulativeNet: ReportTotalDto(byCurrency: [], reportCurrency: 'PEN', reportAmount: '0.00', unconvertedCount: 0),
                        ),
                      );
                      if (net.startOn.isEmpty) return const SizedBox.shrink();
                      return Text(
                        formatCurrency(
                          net.net.reportAmount,
                          net.net.reportCurrency,
                          AppLocalizations.of(context).localeName,
                        ),
                        style: TextStyle(
                          color: net.net.reportAmount.startsWith('-')
                              ? MonetaeColors.of(context).expense
                              : MonetaeColors.of(context).income,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: TransactionCard(
            model: models[i],
            preferences: preferences,
            compact: compact,
            tintCategoryIcon: tintCategoryIcons,
            onEdit: onEdit == null ? null : () => onEdit!(models[i]),
            onDuplicate: onDuplicate == null
                ? null
                : () => onDuplicate!(models[i]),
            onDelete: onDelete == null ? null : () => onDelete!(models[i]),
          ),
        ),
      ],
      if (models.isNotEmpty)
      Padding(
        padding: const EdgeInsets.only(top: 16),
        child: Center(
          child: TextButton(
            onPressed: () => Navigator.of(context).pushNamed('/transactions'),
            style: TextButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
              shape: const StadiumBorder(),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
            child: Text(
              AppLocalizations.of(context).transactions,
              style: TextStyle(color: Theme.of(context).colorScheme.onSurface),
            ),
          ),
        ),
      ),
    ],
  );
}
