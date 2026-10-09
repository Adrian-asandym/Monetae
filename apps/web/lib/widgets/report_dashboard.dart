// Derived composition from Cashew budget/lib/pages/homePage/{
// homePageAllSpendingSummary,homePageLineGraph,homePagePieChart}.dart,
// James Kokoska, GPL-3.0. Modified 2026-10-09: typed API input and callbacks.
import 'package:flutter/material.dart';

import '../api/report_feed.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../theme/monetae_theme.dart';
import 'cash_flow_chart.dart';
import 'category_icon.dart';
import 'category_pie_chart.dart';
import 'income_expense_selector.dart';
import 'income_expense_summary.dart';

class ReportDashboard extends StatefulWidget {
  const ReportDashboard({super.key, required this.feed, this.animate = true});
  final ReportFeed feed;
  final bool animate;
  @override
  State<ReportDashboard> createState() => _ReportDashboardState();
}

class _ReportDashboardState extends State<ReportDashboard> {
  bool _income = false;
  String? _selected;
  @override
  void didUpdateWidget(covariant ReportDashboard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.feed != widget.feed) _selected = null;
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final feed = widget.feed;
    final summary = feed.summary;
    final totals = [
      for (final row in feed.flow) ...[row.income, row.expense],
      for (final row in feed.rows) row.total,
      if (summary != null) ...[summary.income, summary.expense],
    ];
    final slices = presentCategoryReport(
      feed.rows,
      feed.categories,
      _income ? CategoryReportRowKind.income : CategoryReportRowKind.expense,
      l,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (feed.unavailable || (feed.flow.isEmpty && feed.rows.isEmpty))
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(l.emptyReports, key: const Key('empty-reports')),
          ),
        if (totals.any((total) => total.unconvertedCount > 0))
          Padding(
            padding: const EdgeInsets.only(bottom: 13),
            child: Text(
              l.unconvertedNotice,
              key: const Key('unconverted-notice'),
              style: TextStyle(
                fontSize: 12,
                color: MonetaeColors.of(context).muted,
              ),
            ),
          ),
        if (summary != null) ...[
          IncomeExpenseSummary(row: summary),
          const SizedBox(height: 13),
        ],
        _panel(
          context,
          l.cashFlow,
          Column(
            children: [
              Wrap(
                spacing: 16,
                children: [
                  _legend(
                    context,
                    l.expense,
                    MonetaeColors.of(context).expense,
                  ),
                  _legend(context, l.income, MonetaeColors.of(context).income),
                ],
              ),
              CashFlowChart(rows: feed.flow, animate: widget.animate),
            ],
          ),
        ),
        const SizedBox(height: 13),
        _panel(
          context,
          l.categoryDistribution,
          Column(
            children: [
              IncomeExpenseSelector(
                income: _income,
                onChanged: (value) => setState(() {
                  _income = value;
                  _selected = null;
                }),
              ),
              const SizedBox(height: 24),
              CategoryPieChart(
                slices: slices,
                emptyLabel: l.emptyChart,
                animate: widget.animate,
                selectedId: _selected,
                onSelected: (id) => setState(() => _selected = id),
              ),
              const SizedBox(height: 24),
              for (final slice in slices)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  selected: slice.id == _selected,
                  onTap: () => setState(
                    () => _selected = _selected == slice.id ? null : slice.id,
                  ),
                  leading: CategoryIcon(source: slice.icon, color: slice.color),
                  title: Text(slice.label),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(slice.percentLabel),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: slice.weight,
                          minHeight: 5,
                          color: slice.color,
                          backgroundColor: slice.color.withValues(alpha: .15),
                        ),
                      ),
                    ],
                  ),
                  trailing: Text(slice.amountLabel),
                ),
              // Preserve originals even when conversion is unavailable/zero and the
              // category therefore has no visible slice in the converted chart.
              for (final row in feed.rows.where(
                (row) =>
                    row.kind ==
                    (_income
                        ? CategoryReportRowKind.income
                        : CategoryReportRowKind.expense),
              ))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '${feed.categories[row.categoryId]?.name ?? l.uncategorized}: ${currencyBreakdown(row.total, l).join(' · ')}',
                    style: TextStyle(
                      fontSize: 12,
                      color: MonetaeColors.of(context).muted,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _legend(BuildContext context, String label, Color color) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
      const SizedBox(width: 6),
      Text(label, style: TextStyle(color: color, fontSize: 12)),
    ],
  );
  Widget _panel(BuildContext context, String title, Widget child) => Material(
    color: MonetaeColors.of(context).card,
    borderRadius: BorderRadius.circular(15),
    child: Padding(
      padding: const EdgeInsets.all(15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 13),
          child,
        ],
      ),
    ),
  );
}
