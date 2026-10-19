import 'package:intl/intl.dart';

import 'api_client.dart';
import 'home_controller.dart';
import 'report_query.dart';

/// Loads only the category report and its display catalog for one calendar month.
final class CategoryDetailController {
  CategoryDetailController(
    this.api, {
    required DateTime month,
    this.reportCurrency,
  }) : month = DateTime(month.year, month.month) {
    categories = HomeBlock(() async {
      // Capture the range before awaiting pagination: a new selection must not
      // change the remaining pages of an already running request.
      final selectedQuery = query;
      final rows = await loadPages((cursor) async {
        final page = await api.categoryReport(
          query: selectedQuery,
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      });
      final catalog = await loadPages((cursor) async {
        final page = await api.categories(cursor: cursor);
        return (page.items, page.nextCursor);
      });
      return HomeCategoryData(rows, {
        for (final item in catalog) item.id: item,
      });
    });
  }

  final ApiClient api;
  final String? reportCurrency;
  DateTime month;
  late final HomeBlock<HomeCategoryData> categories;

  ReportQuery get query => ReportQuery(
    dateFrom: DateFormat('yyyy-MM-dd').format(month),
    dateTo: DateFormat('yyyy-MM-dd')
        .format(DateTime(month.year, month.month + 1, 0)),
    reportCurrency: reportCurrency,
  );

  Future<void> moveMonth(int delta) {
    month = DateTime(month.year, month.month + delta);
    return categories.load();
  }

  void dispose() => categories.dispose();
}
