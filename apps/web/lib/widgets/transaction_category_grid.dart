// Derived from Cashew widgets/selectCategory.dart (SelectCategory).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: typed API catalog,
// optional single selection and native grid; Material/SVG icons from T-502.
import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/transaction_presenter.dart';
import 'category_icon.dart';

class TransactionCategoryGrid extends StatelessWidget {
  const TransactionCategoryGrid({
    super.key,
    required this.categories,
    required this.selectedId,
    required this.onSelected,
  });
  final List<CategoryDto> categories;
  final String? selectedId;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return LayoutBuilder(
      builder: (context, constraints) => GridView.count(
        crossAxisCount: 4,
        // Keep room for the label below the icon on narrow viewports.
        childAspectRatio: constraints.maxWidth < 320
            ? constraints.maxWidth / 320
            : 1,
        mainAxisSpacing: 5,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        children: [
          _tile(context, null, l.uncategorized, Icons.category_outlined, null),
          for (final c in categories) _tile(context, c.id, c.name, null, c),
        ],
      ),
    );
  }

  Widget _tile(
    BuildContext context,
    String? id,
    String label,
    IconData? icon,
    CategoryDto? category,
  ) {
    final color = presentationColor(
      category?.color,
      fallback: Theme.of(context).colorScheme.primary,
    );
    final selected = selectedId == id;
    return Semantics(
      selected: selected,
      child: InkWell(
        key: Key('form-category-${id ?? 'none'}'),
        borderRadius: BorderRadius.circular(18),
        onTap: () => onSelected(id),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: color.withValues(alpha: .16),
                borderRadius: BorderRadius.circular(18),
                border: selected ? Border.all(color: color, width: 3) : null,
              ),
              child: Center(
                child: category == null
                    ? Icon(icon, color: color, size: 29)
                    : CategoryIcon(
                        source: CategoryIconSource.resolve(category.icon),
                        color: color,
                        size: 29,
                      ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}
