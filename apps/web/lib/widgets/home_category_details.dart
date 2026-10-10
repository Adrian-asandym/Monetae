// Preserved from the former second page of Home; intentionally unconnected.
// TODO(T-514): use in a category detail screen when that screen exists.
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
  });
  final List<CategorySlice> ranked;
  final DateTime month;
  final ValueChanged<int> onMoveMonth;

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
              for (final slice in ranked)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: CategoryIcon(source: slice.icon, color: slice.color),
                  title: Text(slice.label),
                  subtitle: Text(slice.percentLabel),
                  trailing: Text(slice.amountLabel),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
