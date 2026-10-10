// Derived from Cashew pages/homePage/homePagePieChart.dart and widgets/pieChart.dart.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: server reports,
// native PageView, top-three legend, explicit selection and reduced motion.
import 'dart:ui';

import 'package:flutter/material.dart';

import '../api/home_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../theme/monetae_theme.dart';
import 'category_icon.dart';
import 'category_pie_chart.dart';
import 'income_expense_selector.dart';

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
  final _selected = <String?>[null, null];
  @override
  void didUpdateWidget(covariant HomeCategoryCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data) {
      _selected[0] = null;
      _selected[1] = null;
    }
  }

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _selectPage(int index) {
    if (MediaQuery.disableAnimationsOf(context)) {
      _pages.jumpToPage(index);
    } else {
      _pages.animateToPage(
        index,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Column(
      children: [
        IncomeExpenseSelector(
          income: _page == 1,
          onChanged: (income) => _selectPage(income ? 1 : 0),
        ),
        const SizedBox(height: 16),
        if (widget.data.rows.any((row) => row.total.unconvertedCount > 0))
          Text(l.unconvertedNotice, key: const Key('home-unconverted-notice')),
        SizedBox(
          height: 475 * MediaQuery.textScalerOf(context).scale(1).clamp(1, 2),
          child: ScrollConfiguration(
            behavior: ScrollConfiguration.of(context).copyWith(
              dragDevices: {
                PointerDeviceKind.touch,
                PointerDeviceKind.mouse,
                PointerDeviceKind.trackpad,
              },
            ),
            child: PageView(
              key: const Key('category-pages'),
              controller: _pages,
              onPageChanged: (index) => setState(() => _page = index),
              children: [
                for (var index = 0; index < 2; index++)
                  Builder(
                    builder: (context) {
                      final kind = index == 0
                          ? CategoryReportRowKind.expense
                          : CategoryReportRowKind.income;
                      final slices = presentCategoryReport(
                        widget.data.rows,
                        widget.data.categories,
                        kind,
                        l,
                      );
                      final ranked = [...slices]
                        ..sort((a, b) => b.weight.compareTo(a.weight));
                      return SingleChildScrollView(
                        key: Key(index == 0 ? 'expense-page' : 'income-page'),
                        child: Column(
                          children: [
                            Text(
                              index == 0 ? l.expense : l.income,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 15),
                            CategoryPieChart(
                              slices: slices,
                              emptyLabel: l.emptyChart,
                              animate: widget.animate,
                              selectedId: _selected[index],
                              onSelected: (id) =>
                                  setState(() => _selected[index] = id),
                            ),
                            const SizedBox(height: 18),
                            for (final slice in ranked.take(3))
                              ListTile(
                                key: Key('legend-$index-${slice.id}'),
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                selected: _selected[index] == slice.id,
                                onTap: () => setState(
                                  () => _selected[index] =
                                      _selected[index] == slice.id
                                      ? null
                                      : slice.id,
                                ),
                                leading: CategoryIcon(
                                  source: slice.icon,
                                  color: slice.color,
                                ),
                                title: Text(slice.label),
                                subtitle: Text(slice.percentLabel),
                                trailing: Text(slice.amountLabel),
                              ),
                            for (final row in widget.data.rows.where(
                              (r) =>
                                  r.kind == kind &&
                                  (r.total.unconvertedCount > 0 ||
                                      r.total.byCurrency.any(
                                        (c) =>
                                            c.currency !=
                                            r.total.reportCurrency,
                                      )),
                            ))
                              Text(
                                '${widget.data.categories[row.categoryId]?.name ?? l.uncategorized}: ${currencyBreakdown(row.total, l).join(' · ')}',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: MonetaeColors.of(context).muted,
                                ),
                              ),
                          ],
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var index = 0; index < 2; index++)
              IconButton(
                key: Key('category-page-indicator-$index'),
                tooltip: index == 0 ? l.expense : l.income,
                onPressed: () => _selectPage(index),
                iconSize: 9,
                icon: Icon(
                  _page == index ? Icons.circle : Icons.circle_outlined,
                ),
              ),
          ],
        ),
      ],
    );
  }
}
