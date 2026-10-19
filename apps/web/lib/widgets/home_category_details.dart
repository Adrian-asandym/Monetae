// Category ranking and month picker shared with the category detail screen.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_localizations.dart';
import '../presentation/component_models.dart';
import 'category_icon.dart';

class HomeCategoryDetails extends StatelessWidget {
  const HomeCategoryDetails({
    super.key,
    required this.ranked,
    required this.month,
    required this.onMoveMonth,
    this.summary,
    this.onCategorySelected,
    this.originalAmounts = const {},
  });
  final List<CategorySlice> ranked;
  final DateTime month;
  final ValueChanged<int> onMoveMonth;
  final Widget? summary;
  final ValueChanged<String>? onCategorySelected;
  final Map<String, String> originalAmounts;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              tooltip: l.previousMonth,
              onPressed: () => onMoveMonth(-1),
              icon: const Icon(Icons.chevron_left),
            ),
            Text(
              DateFormat.yMMMM(l.localeName).format(month),
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            IconButton(
              tooltip: l.nextMonth,
              onPressed: () => onMoveMonth(1),
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              ?summary,
              for (final slice in ranked)
                ListTile(
                  key: Key('category-detail-${slice.id}'),
                  // TODO(F1): filtering uncategorized transactions needs an API contract extension.
                  onTap:
                      slice.id == 'uncategorized' || onCategorySelected == null
                      ? null
                      : () => onCategorySelected!(slice.id),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: CategoryIcon(source: slice.icon, color: slice.color),
                  title: Text(slice.label),
                  subtitle: Text(
                    [
                      slice.percentLabel,
                      if (originalAmounts[slice.id] case final String original)
                        original,
                    ].join(' · '),
                  ),
                  trailing: Text(slice.amountLabel),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
