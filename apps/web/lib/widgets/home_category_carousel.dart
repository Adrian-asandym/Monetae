// Presentation adapted from Cashew pages/homePage/homePagePieChart.dart.
// Copyright James Kokoska, GPL-3.0. Independent expense/income API pages.
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../api/home_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../theme/monetae_theme.dart';
import 'category_pie_chart.dart';

class HomeCategoryCarousel extends StatefulWidget {
  const HomeCategoryCarousel({
    super.key,
    required this.data,
    this.animate = true,
  });
  final HomeCategoryData data;
  final bool animate;
  @override
  State<HomeCategoryCarousel> createState() => _HomeCategoryCarouselState();
}

class _HomeCategoryCarouselState extends State<HomeCategoryCarousel> {
  final _pages = PageController();
  int _page = 0;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _switchTo(int index) => _pages.animateToPage(
    index,
    duration: const Duration(milliseconds: HomeTokens.pageSwitchMilliseconds),
    curve: Curves.easeInOut,
  );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: MonetaeColors.of(context).card,
      borderRadius: BorderRadius.circular(HomeTokens.cardRadius),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: HomeTokens.categoryCardHeight,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: HomeTokens.categoryPadding,
          ),
          child: Column(
            children: [
              Expanded(
                child: PageView(
                  key: const Key('category-pages'),
                  controller: _pages,
                  onPageChanged: (index) => setState(() => _page = index),
                  children: [
                    for (final (index, kind) in [
                      (0, CategoryReportRowKind.expense),
                      (1, CategoryReportRowKind.income),
                    ])
                      HomeCategoryPiePage(
                        data: widget.data,
                        kind: kind,
                        animate: widget.animate,
                        onSwitch: () => _switchTo(1 - index),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: HomeTokens.pageDotGap),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  for (var index = 0; index < 2; index++)
                    Container(
                      key: Key('category-dot-$index'),
                      margin: const EdgeInsets.symmetric(
                        horizontal: HomeTokens.pageDotSpacing,
                      ),
                      width: HomeTokens.pageDotSize,
                      height: HomeTokens.pageDotSize,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: _page == index
                              ? HomeTokens.activeDotOpacity
                              : HomeTokens.inactiveDotOpacity,
                        ),
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

/// The same layout and selection behavior for both kinds, including empty data.
class HomeCategoryPiePage extends StatefulWidget {
  const HomeCategoryPiePage({
    super.key,
    required this.data,
    required this.kind,
    required this.onSwitch,
    this.animate = true,
  });
  final HomeCategoryData data;
  final CategoryReportRowKind kind;
  final VoidCallback onSwitch;
  final bool animate;
  @override
  State<HomeCategoryPiePage> createState() => _HomeCategoryPiePageState();
}

class _HomeCategoryPiePageState extends State<HomeCategoryPiePage> {
  String? _selectedId;
  @override
  void didUpdateWidget(covariant HomeCategoryPiePage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data || oldWidget.kind != widget.kind) {
      _selectedId = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final expense = widget.kind == CategoryReportRowKind.expense;
    final slices = presentCategoryReport(
      widget.data.rows,
      widget.data.categories,
      widget.kind,
      l,
    );
    final ranked = [...slices]..sort((a, b) => b.weight.compareTo(a.weight));
    return LayoutBuilder(
      builder: (context, constraints) {
        final pieSize = math.min(
          HomeTokens.categoryPieSize,
          constraints.maxWidth * HomeTokens.categoryPieFraction,
        );
        return Stack(
          children: [
            Positioned(
              top: HomeTokens.categoryPieTop,
              right: HomeTokens.categoryPadding,
              width: pieSize,
              height: pieSize,
              child: FittedBox(
                child: CategoryPieChart(
                  slices: slices,
                  emptyLabel: l.emptyChart,
                  animate: widget.animate,
                  selectedId: _selectedId,
                  onSelected: (id) => setState(() => _selectedId = id),
                ),
              ),
            ),
            Positioned(
              top: 0,
              left: HomeTokens.categoryPadding,
              width: constraints.maxWidth * HomeTokens.categoryLegendFraction,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final slice in ranked.take(3))
                    Padding(
                      key: Key('legend-${expense ? 0 : 1}-${slice.id}'),
                      padding: const EdgeInsets.only(
                        bottom: HomeTokens.legendGap,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(
                              top: HomeTokens.legendDotTop,
                            ),
                            child: Container(
                              width: HomeTokens.legendDotSize,
                              height: HomeTokens.legendDotSize,
                              decoration: BoxDecoration(
                                color: slice.color,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ),
                          const SizedBox(width: HomeTokens.legendDotGap),
                          Expanded(
                            child: Text(
                              slice.label,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: HomeTokens.legendFontSize,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            Positioned(
              top: 0,
              right: HomeTokens.categoryPadding,
              child: Tooltip(
                message: expense ? l.income : l.expense,
                child: InkWell(
                  key: Key('category-toggle-${widget.kind.name}'),
                  onTap: widget.onSwitch,
                  child: Icon(
                    expense ? Icons.arrow_drop_down : Icons.arrow_drop_up,
                    color: expense ? colors.expense : colors.income,
                    size: HomeTokens.categoryTriangleSize,
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
