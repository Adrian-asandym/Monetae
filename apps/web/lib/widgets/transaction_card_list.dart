import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../presentation/component_models.dart';
import 'transaction_card.dart';
import 'home_transaction_row.dart';
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
    this.isHome = false,
    this.onViewTransactions,
    this.onTap,
    this.onEdit,
    this.onDuplicate,
    this.onDelete,
  });
  final List<TransactionCardModel> models;
  final TransactionCardPreferencesDto preferences;
  final bool compact;
  final bool tintCategoryIcons;
  final List<CashFlowRowDto>? dailyFlow;
  final bool isHome;
  final VoidCallback? onViewTransactions;
  final ValueChanged<TransactionCardModel>? onTap;
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
                      fontWeight: isHome ? FontWeight.normal : FontWeight.bold,
                      color: isHome ? MonetaeColors.of(context).muted : null,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (dailyFlow != null)
                  for (final row in dailyFlow!)
                    if (row.startOn == models[i].dateKey)
                      Text(
                        formatCurrency(
                          row.net.reportAmount,
                          row.net.reportCurrency,
                          AppLocalizations.of(context).localeName,
                        ),
                        key: ValueKey('day-net-${models[i].dateKey}'),
                        style: Theme.of(context).textTheme.labelLarge
                            ?.copyWith(color: MonetaeColors.of(context).muted),
                      ),
              ],
            ),
          ),
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: isHome
              ? InkWell(
                  onTap: onTap == null ? null : () => onTap!(models[i]),
                  child: HomeTransactionRow(
                    model: models[i],
                    tintCategoryIcon: tintCategoryIcons,
                  ),
                )
              : TransactionCard(
                  model: models[i],
                  onTap: onTap == null ? null : () => onTap!(models[i]),
                  preferences: preferences,
                  compact: compact,
                  tintCategoryIcon: tintCategoryIcons,
                  onEdit: onEdit == null ? null : () => onEdit!(models[i]),
                  onDuplicate: onDuplicate == null
                      ? null
                      : () => onDuplicate!(models[i]),
                  onDelete: onDelete == null
                      ? null
                      : () => onDelete!(models[i]),
                ),
        ),
      ],
      if (models.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 16),
          child: Center(
            child: TextButton(
              onPressed:
                  onViewTransactions ??
                  () => Navigator.of(context).pushNamed('/transactions'),
              style: TextButton.styleFrom(
                minimumSize: isHome ? const Size(0, 44) : null,
                backgroundColor: isHome
                    ? MonetaeColors.of(context).card
                    : Theme.of(context).colorScheme.surfaceContainerHighest,
                shape: const StadiumBorder(),
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 12,
                ),
              ),
              child: Text(
                isHome
                    ? AppLocalizations.of(context).viewAllTransactions
                    : AppLocalizations.of(context).transactions,
                style: TextStyle(
                  color: isHome
                      ? MonetaeColors.of(context).muted
                      : Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ),
          ),
        ),
    ],
  );
}
