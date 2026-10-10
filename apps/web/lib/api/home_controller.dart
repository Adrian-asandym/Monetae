import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import 'api_client.dart';
import 'report_query.dart';
import 'transaction_feed.dart';

/// Independent request state; a late response cannot replace a newer refresh.
final class HomeBlock<T> extends ChangeNotifier {
  HomeBlock(this.fetch);
  final Future<T> Function() fetch;
  T? data;
  ApiException? error;
  bool loading = true;
  bool _disposed = false;
  int _revision = 0;

  Future<void> load() async {
    if (_disposed) return;
    final revision = ++_revision;
    loading = true;
    error = null;
    notifyListeners();
    try {
      final value = await fetch();
      if (!_disposed && revision == _revision) data = value;
    } on ApiException catch (e) {
      if (!_disposed && revision == _revision) error = e;
    } on Object {
      if (!_disposed && revision == _revision) {
        error = const ApiException(ApiErrorKind.unavailable);
      }
    }
    if (!_disposed && revision == _revision) {
      loading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}

Future<List<T>> loadPages<T>(
  Future<(List<T>, String?)> Function(String?) fetch, {
  bool unavailableIsEmpty = false,
}) async {
  final items = <T>[];
  final seen = <String>{};
  String? cursor;
  try {
    do {
      final (page, next) = await fetch(cursor);
      items.addAll(page);
      cursor = next;
      if (cursor != null && !seen.add(cursor)) {
        throw const ApiException(ApiErrorKind.unavailable);
      }
    } while (cursor != null);
  } on ApiException catch (e) {
    if (!unavailableIsEmpty || (e.statusCode != 404 && e.statusCode != 501)) {
      rethrow;
    }
    return const [];
  }
  return List.unmodifiable(items);
}

Future<List<BudgetDto>> loadBudgets(ApiClient api) => loadPages((cursor) async {
  final page = await api.budgets(cursor: cursor);
  return (page.items, page.nextCursor);
}, unavailableIsEmpty: true);

final class HomeCategoryData {
  const HomeCategoryData(this.rows, this.categories);
  final List<CategoryReportRowDto> rows;
  final Map<String, CategoryDto> categories;
}

final class HomeController {
  HomeController(this.api, {required this.month, this.reportCurrency}) {
    accounts = HomeBlock(() async {
      final all = await loadPages((cursor) async {
        final page = await api.accounts(cursor: cursor, includeArchived: false);
        return (page.items, page.nextCursor);
      });
      return all
          .where((a) => a.archivedAt == null && a.deletedAt == null)
          .toList();
    });
    goals = HomeBlock(
      () => loadPages((cursor) async {
        final page = await api.goals(cursor: cursor);
        return (page.items, page.nextCursor);
      }, unavailableIsEmpty: true),
    );
    budgets = HomeBlock(() => loadBudgets(api));
    categories = HomeBlock(() async {
      final rows = await loadPages((cursor) async {
        final page = await api.categoryReport(query: query, cursor: cursor);
        return (page.items, page.nextCursor);
      });
      final catalogs = await loadPages((cursor) async {
        final page = await api.categories(cursor: cursor);
        return (page.items, page.nextCursor);
      });
      return HomeCategoryData(rows, {
        for (final item in catalogs) item.id: item,
      });
    });
    dailyFlow = HomeBlock(
      () => loadPages((cursor) async {
        final page = await api.cashFlow(
          query: ReportQuery(
            period: ReportPeriod.daily,
            reportCurrency: reportCurrency,
            dateFrom: month.toIso8601String(),
            dateTo: DateTime(month.year, month.month + 1).toIso8601String(),
          ),
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      }),
    );
    flow = HomeBlock(
      () => loadPages((cursor) async {
        final page = await api.cashFlow(
          query: ReportQuery(
            dateFrom: query.dateFrom,
            dateTo: query.dateTo,
            reportCurrency: reportCurrency,
            period: ReportPeriod.daily,
          ),
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      }),
    );
    transactions = HomeBlock(() async {
      final feed = TransactionFeed(api);
      // One page only, in server order; the full feed belongs to Transactions.
      await feed.load(limit: 25);
      return feed;
    });
  }

  final ApiClient api;
  final String? reportCurrency;
  DateTime month;
  late final HomeBlock<List<AccountDto>> accounts;
  late final HomeBlock<List<GoalDto>> goals;
  late final HomeBlock<List<BudgetDto>> budgets;
  late final HomeBlock<HomeCategoryData> categories;
  late final HomeBlock<List<CashFlowRowDto>> flow;
  late final HomeBlock<List<CashFlowRowDto>> dailyFlow;
  late final HomeBlock<TransactionFeed> transactions;

  ReportQuery get query => ReportQuery(
    dateFrom: DateFormat('yyyy-MM-dd').format(month),
    dateTo: DateFormat('yyyy-MM-dd')
        .format(DateTime(month.year, month.month + 1, 0)),
    reportCurrency: reportCurrency,
  );

  List<ChangeNotifier> get blocks => [
    accounts,
    goals,
    budgets,
    categories,
    flow,
    transactions,
  ];
  Future<void> load() => Future.wait([
    accounts.load(),
    goals.load(),
    budgets.load(),
    categories.load(),
    flow.load(),
    dailyFlow.load(),
    transactions.load(),
  ]);
  Future<void> moveMonth(int delta) async {
    month = DateTime(month.year, month.month + delta);
    await Future.wait([categories.load(), flow.load(), dailyFlow.load()]);
  }

  void dispose() {
    for (final block in blocks) {
      block.dispose();
    }
  }
}
