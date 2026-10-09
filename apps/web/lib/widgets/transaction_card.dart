// Derived from Cashew budget/lib/widgets/transactionEntry/{transactionEntry,
// transactionEntryAmount,incomeAmountArrow,transactionEntryNote,
// transactionEntryTag,transactionLabel}.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: immutable view model and action callbacks.
import 'package:flutter/material.dart';

import '../presentation/component_models.dart';
import '../presentation/account_color.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import 'category_icon.dart';
import '../theme/monetae_theme.dart';

class TransactionCard extends StatelessWidget {
  const TransactionCard({
    super.key,
    required this.model,
    this.onTap,
    this.preferences = const TransactionCardPreferencesDto(),
    this.onEdit,
    this.onDuplicate,
    this.onDelete,
    this.tintCategoryIcon = false,
    this.onSelectionChanged,
    this.selected = false,
    this.compact = false,
  });

  final TransactionCardModel model;
  final TransactionCardPreferencesDto preferences;
  final VoidCallback? onEdit;
  final VoidCallback? onDuplicate;
  final VoidCallback? onDelete;
  final bool tintCategoryIcon;
  final VoidCallback? onTap;
  final ValueChanged<bool>? onSelectionChanged;
  final bool selected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final amountColor = switch (model.tone) {
      AmountTone.income => colors.income,
      AmountTone.expense => colors.expense,
      AmountTone.neutral => colors.muted,
      AmountTone.upcoming => colors.upcoming,
    };
    final note = model.transaction.note;
    final title = model.transaction.title.trim().isEmpty
        ? (model.category?.name ?? model.typeLabel)
        : model.transaction.title;
    return Material(
      color: selected ? theme.colorScheme.secondaryContainer : colors.card,
      borderRadius: BorderRadius.circular(15),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        onLongPress: onSelectionChanged == null
            ? null
            : () => onSelectionChanged!(!selected),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (onSelectionChanged != null)
                Checkbox(
                  value: selected,
                  onChanged: (value) {
                    if (value != null) onSelectionChanged!(value);
                  },
                ),
              Container(
                width: 47,
                height: 47,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: pastel(model.categoryColor, theme.brightness, .55),
                ),
                child: CategoryIcon(
                  source: model.icon,
                  color: model.categoryColor,
                  tintCustom: tintCategoryIcon,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 16.5),
                    ),
                    Text(
                      model.subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 14.5, color: colors.muted),
                    ),
                    if (preferences.showTime)
                      Text(
                        model.timeLabel,
                        key: const Key('transaction-time'),
                        style: TextStyle(fontSize: 12, color: colors.muted),
                      ),
                    if (preferences.showAccount)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Container(
                          key: const Key('transaction-account-tag'),
                          decoration: BoxDecoration(
                            color: accountColor(
                              model.transaction.accountId,
                              model.account?.color,
                            ).withValues(alpha: .25),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 4.5,
                            vertical: 1.05,
                          ),
                          child: Text(
                            model.account?.name ?? l.unavailableAccount,
                            key: const Key('transaction-account'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11.5,
                              color: theme.colorScheme.onSurface.withValues(
                                alpha: .7,
                              ),
                            ),
                          ),
                        ),
                      ),
                    if (preferences.showActions)
                      Wrap(
                        spacing: 2,
                        children: [
                          IconButton(
                            tooltip: l.editTransaction,
                            onPressed: onEdit,
                            icon: const Icon(Icons.edit_outlined),
                            iconSize: 18,
                          ),
                          IconButton(
                            tooltip: l.duplicateTransaction,
                            onPressed: onDuplicate,
                            icon: const Icon(Icons.copy_outlined),
                            iconSize: 18,
                          ),
                          IconButton(
                            tooltip: l.deleteTransaction,
                            onPressed: onDelete,
                            icon: const Icon(Icons.delete_outline),
                            iconSize: 18,
                          ),
                        ],
                      ),
                    if (preferences.showNote &&
                        !compact &&
                        note != null &&
                        note.trim().isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 5),
                        child: Row(
                          children: [
                            Icon(
                              Icons.sticky_note_2_outlined,
                              size: 16,
                              color: colors.muted,
                            ),
                            const SizedBox(width: 5),
                            Expanded(
                              child: Text(
                                note,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 12,
                                  color: colors.muted,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    if (preferences.showTags && model.tags.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Wrap(
                          spacing: 4,
                          runSpacing: 4,
                          children: [
                            for (final tag in model.tags)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: theme.colorScheme.secondaryContainer,
                                  borderRadius: BorderRadius.circular(5),
                                ),
                                child: Text(
                                  tag,
                                  style: const TextStyle(fontSize: 10),
                                ),
                              ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 7),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (model.tone == AmountTone.income ||
                          model.tone == AmountTone.expense)
                        AnimatedRotation(
                          duration: const Duration(milliseconds: 1700),
                          curve: const ElasticOutCurve(.5),
                          turns: model.tone == AmountTone.income ? .5 : 0,
                          child: Icon(
                            Icons.arrow_drop_down_rounded,
                            size: 24,
                            color: amountColor,
                          ),
                        ),
                      Text(
                        model.amountLabel,
                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                          color: amountColor,
                        ),
                      ),
                    ],
                  ),
                  if (model.secondaryAmountLabel != null)
                    Text(
                      model.secondaryAmountLabel!,
                      style: TextStyle(fontSize: 12, color: amountColor),
                    ),
                  Text(
                    model.typeLabel,
                    style: TextStyle(fontSize: 10, color: colors.muted),
                  ),
                  if (preferences.showNote &&
                      compact &&
                      note != null &&
                      note.trim().isNotEmpty)
                    Tooltip(
                      message: note,
                      triggerMode: TooltipTriggerMode.tap,
                      child: Icon(
                        Icons.sticky_note_2_outlined,
                        size: 22,
                        color: colors.muted,
                      ),
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
