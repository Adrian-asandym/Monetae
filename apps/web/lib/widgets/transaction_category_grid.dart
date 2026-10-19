// Derived from Cashew widgets/selectCategory.dart (SelectCategory).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: typed API catalog,
// optional single selection and native grid; Material/SVG icons from T-502.
// Modified 2026-10-11 (T-515 piece 3): scrolling four-column sheet grid with
// solid category colors, light icons and labels below each rounded square.
import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/transaction_presenter.dart';
import '../theme/monetae_theme.dart';
import 'category_icon.dart';

typedef _T = TransactionFormTokens;

class TransactionCategoryGrid extends StatelessWidget {
  const TransactionCategoryGrid({
    super.key,
    required this.categories,
    required this.selectedId,
    required this.onSelected,
    this.uncategorizedSelected = false,
    this.showUncategorized = true,
  });
  final List<CategoryDto> categories;
  final String? selectedId;
  final ValueChanged<String?> onSelected;
  final bool uncategorizedSelected;
  final bool showUncategorized;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return GridView.builder(
      key: const Key('category-sheet-grid'),
      padding: const EdgeInsets.fromLTRB(
        _T.categoryGridInset,
        0,
        _T.categoryGridInset,
        _T.sheetPadding,
      ),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: _T.categoryGridColumns,
        mainAxisExtent: _T.categoryGridTileHeight,
        mainAxisSpacing: _T.categoryGridGap,
        crossAxisSpacing: _T.categoryGridGap,
      ),
      itemCount: categories.length + (showUncategorized ? 1 : 0),
      itemBuilder: (context, index) {
        final category = showUncategorized && index == 0
            ? null
            : categories[index - (showUncategorized ? 1 : 0)];
        return _tile(context, category?.name ?? l.uncategorized, category);
      },
    );
  }

  Widget _tile(BuildContext context, String label, CategoryDto? category) {
    final form = TransactionFormColors.of(context);
    final id = category?.id;
    final color = presentationColor(
      category?.color,
      fallback: form.neutralCategory,
    );
    final selected = id == null ? uncategorizedSelected : selectedId == id;
    return Semantics(
      selected: selected,
      button: true,
      label: label,
      child: InkWell(
        key: Key('form-category-${id ?? 'none'}'),
        borderRadius: BorderRadius.circular(_T.categoryGridRadius),
        onTap: () => onSelected(id),
        child: Column(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final size = constraints.maxWidth < _T.categoryGridSquare
                    ? constraints.maxWidth
                    : _T.categoryGridSquare;
                return Container(
                  width: size,
                  height: size,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(_T.categoryGridRadius),
                    border: selected
                        ? Border.all(
                            color: form.onCategory,
                            width: _T.categoryGridBorderWidth,
                          )
                        : null,
                  ),
                  child: Center(
                    child: category == null
                        ? Icon(
                            Icons.category_outlined,
                            color: form.onCategory,
                            size: _T.categoryGridIconSize,
                          )
                        : CategoryIcon(
                            source: CategoryIconSource.resolve(category.icon),
                            color: form.onCategory,
                            tintCustom: true,
                            size: _T.categoryGridIconSize,
                          ),
                  ),
                );
              },
            ),
            const SizedBox(height: _T.categoryGridLabelGap),
            Text(
              label,
              maxLines: 1,
              textAlign: TextAlign.center,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: _T.categoryGridLabelSize,
                height: _T.categoryGridLabelHeight,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
