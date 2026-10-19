import 'package:flutter/material.dart';

import '../api/category_detail_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../session/session_controller.dart';
import '../theme/monetae_theme.dart';
import '../widgets/home_category_carousel.dart';
import '../widgets/home_category_details.dart';
import 'transactions_page.dart';

class CategoryDetailPage extends StatefulWidget {
  const CategoryDetailPage({
    super.key,
    required this.session,
    required this.month,
    this.initialKind = CategoryReportRowKind.expense,
    this.animate = true,
  });

  final SessionController session;
  final DateTime month;
  final CategoryReportRowKind initialKind;
  final bool animate;

  @override
  State<CategoryDetailPage> createState() => _CategoryDetailPageState();
}

class _CategoryDetailPageState extends State<CategoryDetailPage> {
  late final CategoryDetailController _controller;
  late CategoryReportRowKind _kind;
  late int _transactionRevision;

  @override
  void initState() {
    super.initState();
    _kind = widget.initialKind;
    _transactionRevision = widget.session.transactionRevision;
    _controller = CategoryDetailController(
      widget.session.api,
      month: widget.month,
      reportCurrency: widget.session.user?.reportCurrency,
    );
    widget.session.addListener(_sessionChanged);
    _controller.categories.load();
  }

  void _sessionChanged() {
    if (_transactionRevision != widget.session.transactionRevision) {
      _transactionRevision = widget.session.transactionRevision;
      _controller.categories.load();
    }
  }

  @override
  void dispose() {
    widget.session.removeListener(_sessionChanged);
    _controller.dispose();
    super.dispose();
  }

  void _openCategory(String id) {
    final month = _controller.month;
    // TODO(timezone): generalize the UI's America/Lima convention to IANA zones.
    // Lima has no DST. Transactions use [start, next month); reports use local
    // calendar dates and let the server apply the profile timezone.
    String boundary(int monthNumber) => DateTime.utc(
      month.year,
      monthNumber,
      1,
      5,
    ).toIso8601String().replaceFirst('.000Z', 'Z');
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionsPage(
          session: widget.session,
          categoryIds: [id],
          dateFrom: boundary(month.month),
          dateTo: boundary(month.month + 1),
          onDemo: () => Navigator.of(context).pushNamed('/demo/home'),
          onHome: () =>
              Navigator.of(context).popUntil((route) => route.isFirst),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.categoryDetailTitle)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: ListenableBuilder(
            listenable: _controller.categories,
            builder: (context, _) {
              final block = _controller.categories;
              final data = block.loading || block.error != null
                  ? null
                  : block.data;
              final ranked = presentCategoryReport(
                data?.rows ?? [],
                data?.categories ?? {},
                _kind,
                l,
              )..sort((a, b) => b.weight.compareTo(a.weight));
              return HomeCategoryDetails(
                month: _controller.month,
                ranked: ranked,
                onMoveMonth: _controller.moveMonth,
                onCategorySelected: _openCategory,
                originalAmounts: {
                  for (final row in data?.rows ?? <CategoryReportRowDto>[])
                    if (row.kind == _kind && row.total.unconvertedCount > 0)
                      row.categoryId ?? 'uncategorized': currencyBreakdown(
                        row.total,
                        l,
                      ).join(' · '),
                },
                summary: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (block.loading)
                      const Center(child: CircularProgressIndicator())
                    else if (block.error != null) ...[
                      Text(block.error!.message(l)),
                      TextButton(onPressed: block.load, child: Text(l.retry)),
                    ] else if (data != null) ...[
                      Material(
                        color: MonetaeColors.of(context).card,
                        borderRadius: BorderRadius.circular(
                          HomeTokens.cardRadius,
                        ),
                        child: SizedBox(
                          height: HomeTokens.categoryCardHeight,
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              vertical: HomeTokens.categoryPadding,
                            ),
                            child: HomeCategoryPiePage(
                              key: ValueKey((_controller.month, _kind)),
                              data: data,
                              kind: _kind,
                              animate: widget.animate,
                              onSwitch: () => setState(() {
                                _kind = _kind == CategoryReportRowKind.expense
                                    ? CategoryReportRowKind.income
                                    : CategoryReportRowKind.expense;
                              }),
                            ),
                          ),
                        ),
                      ),
                      if (data.rows.any(
                        (row) =>
                            row.kind == _kind && row.total.unconvertedCount > 0,
                      ))
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: HomeTokens.categoryPadding,
                          ),
                          child: Text(
                            l.unconvertedNotice,
                            key: const Key('unconverted-notice'),
                          ),
                        ),
                      if (ranked.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: HomeTokens.categoryPadding,
                          ),
                          child: Text(l.emptyReports),
                        ),
                    ],
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
