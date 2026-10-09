import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../presentation/component_models.dart';
import 'transaction_card.dart';

/// Receives an already ordered list and caller-formatted dates (America/Lima).
/// showDate controls daily group headers, never a date inside each card.
class TransactionCardList extends StatelessWidget {
  const TransactionCardList({
    super.key,
    required this.models,
    this.preferences = const TransactionCardPreferencesDto(),
    this.compact = false,
    this.tintCategoryIcons = false,
    this.onEdit,
    this.onDuplicate,
    this.onDelete,
  });
  final List<TransactionCardModel> models;
  final TransactionCardPreferencesDto preferences;
  final bool compact;
  final bool tintCategoryIcons;
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
            child: Text(
              models[i].dateLabel,
              key: ValueKey('date-${models[i].dateKey}'),
              style: Theme.of(context).textTheme.labelLarge,
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
    ],
  );
}
