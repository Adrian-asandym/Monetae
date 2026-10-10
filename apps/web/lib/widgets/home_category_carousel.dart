
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/home_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../theme/monetae_theme.dart';
import 'category_icon.dart';
import 'category_pie_chart.dart';

class HomeCategoryCarousel extends StatefulWidget {
  const HomeCategoryCarousel({
    super.key,
    required this.data,
    this.animate = true,
    required this.month,
    required this.onMoveMonth,
  });
  final HomeCategoryData data;
  final bool animate;
  final DateTime month;
  final ValueChanged<int> onMoveMonth;
  @override
  State<HomeCategoryCarousel> createState() => _HomeCategoryCarouselState();
}

class _HomeCategoryCarouselState extends State<HomeCategoryCarousel> {
  final _pages = PageController();
  int _page = 0;
  bool _isExpense = true;
  String? _selectedId;

  @override
  void didUpdateWidget(covariant HomeCategoryCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data) {
      _selectedId = null;
    }
  }

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = MonetaeColors.of(context);

    final kind = _isExpense ? CategoryReportRowKind.expense : CategoryReportRowKind.income;
    final slices = presentCategoryReport(
      widget.data.rows,
      widget.data.categories,
      kind,
      l,
    );
    final ranked = [...slices]..sort((a, b) => b.weight.compareTo(a.weight));

    return Material(
      color: colors.card,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: Container(
        height: 280,
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          children: [
            Expanded(
              child: PageView(
                key: const Key('category-pages'),
                controller: _pages,
                onPageChanged: (index) => setState(() => _page = index),
                children: [
                  // Page 1: Pie Chart + Top 3 Legend + Triangle Toggle
                  Stack(
                    children: [
                      Positioned(
                        top: 0,
                        left: 16,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: ranked.take(3).map((slice) {
                            return Padding(
                              key: Key('legend-${_isExpense ? 0 : 1}-${slice.id}'),
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                children: [
                                  Container(
                                    width: 10,
                                    height: 10,
                                    decoration: BoxDecoration(
                                      color: slice.color,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    slice.label,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                      Positioned(
                        top: 0,
                        right: 16,
                        child: InkWell(
                          key: const Key('expense-income-toggle'),
                          onTap: () => setState(() => _isExpense = !_isExpense),
                          child: Icon(
                            _isExpense ? Icons.arrow_drop_down : Icons.arrow_drop_up,
                            color: _isExpense ? colors.expense : colors.income,
                            size: 32,
                          ),
                        ),
                      ),
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.only(top: 40), // Push down below legend
                          child: CategoryPieChart(
                            slices: slices,
                            emptyLabel: l.emptyChart,
                            animate: widget.animate,
                            selectedId: _selectedId,
                            onSelected: (id) => setState(() => _selectedId = id),
                          ),
                        ),
                      ),
                    ],
                  ),
                  // Page 2: Month Selector + Category List
                  Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          IconButton(
                            tooltip: l.previousMonth,
                            onPressed: () => widget.onMoveMonth(-1),
                            icon: const Icon(Icons.chevron_left),
                          ),
                          Text(
                            DateFormat.yMMMM(l.localeName).format(widget.month),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          IconButton(
                            tooltip: l.nextMonth,
                            onPressed: () => widget.onMoveMonth(1),
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
                                leading: CategoryIcon(
                                  source: slice.icon,
                                  color: slice.color,
                                ),
                                title: Text(slice.label),
                                subtitle: Text(slice.percentLabel),
                                trailing: Text(slice.amountLabel),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var index = 0; index < 2; index++)
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _page == index
                          ? theme.colorScheme.primary
                          : theme.colorScheme.onSurface.withValues(alpha: 0.2),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
