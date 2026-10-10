import 'package:flutter/material.dart';
import '../presentation/component_models.dart';
import '../presentation/account_color.dart';
import '../theme/monetae_theme.dart';
import '../l10n/app_localizations.dart';
import 'category_icon.dart';

class HomeTransactionRow extends StatelessWidget {
  const HomeTransactionRow({
    super.key,
    required this.model,
    this.tintCategoryIcon = false,
  });

  final TransactionCardModel model;
  final bool tintCategoryIcon;

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
    final title = model.transaction.title.trim().isEmpty
        ? (model.category?.name ?? model.typeLabel)
        : model.transaction.title;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 44,
            height: 44,
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
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 2),
                Container(
                  decoration: BoxDecoration(
                    color: accountColor(
                      model.transaction.accountId,
                      model.account?.color,
                    ).withValues(alpha: .25),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 4.5, vertical: 1),
                  child: Text(
                    model.account?.name ?? l.unavailableAccount,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11,
                      color: theme.colorScheme.onSurface.withValues(alpha: .7),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                model.timeLabel,
                style: TextStyle(fontSize: 12, color: colors.muted),
              ),
              const SizedBox(height: 2),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (model.tone == AmountTone.income || model.tone == AmountTone.expense)
                    AnimatedRotation(
                      duration: const Duration(milliseconds: 1700),
                      curve: const ElasticOutCurve(.5),
                      turns: model.tone == AmountTone.income ? .5 : 0,
                      child: Icon(
                        Icons.arrow_drop_down_rounded,
                        size: 20,
                        color: amountColor,
                      ),
                    ),
                  Text(
                    model.amountLabel,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: amountColor,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
