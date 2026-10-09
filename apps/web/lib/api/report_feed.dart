import '../data/api_dtos.dart';
import 'api_client.dart';
import 'report_query.dart';

/// One selected calendar month. The monthly row supplies summary totals without
/// client-side money sums; daily rows include server-provided zero periods.
final class ReportFeed {
  const ReportFeed({
    required this.flow,
    required this.summary,
    required this.rows,
    required this.categories,
    this.unavailable = false,
  });
  final List<CashFlowRowDto> flow;
  final CashFlowRowDto? summary;
  final List<CategoryReportRowDto> rows;
  final Map<String, CategoryDto> categories;
  final bool unavailable;

  static Future<List<T>> _pages<T>(
    Future<(List<T>, String?)> Function(String?) fetch,
  ) async {
    final items = <T>[];
    final seen = <String>{};
    String? cursor;
    do {
      final (page, next) = await fetch(cursor);
      items.addAll(page);
      cursor = next;
      if (cursor != null && !seen.add(cursor)) {
        throw const ApiException(ApiErrorKind.unavailable);
      }
    } while (cursor != null);
    return List.unmodifiable(items);
  }

  static Future<ReportFeed> load(
    ApiClient api, {
    required String dateFrom,
    required String dateTo,
    String? reportCurrency,
  }) async {
    ReportQuery query(ReportPeriod? period) => ReportQuery(
      dateFrom: dateFrom,
      dateTo: dateTo,
      reportCurrency: reportCurrency,
      period: period,
    );
    try {
      final flow = await _pages((cursor) async {
        final page = await api.cashFlow(
          query: query(ReportPeriod.daily),
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      });
      final summary = await _pages((cursor) async {
        final page = await api.cashFlow(
          query: query(ReportPeriod.monthly),
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      });
      final rows = await _pages((cursor) async {
        final page = await api.categoryReport(
          query: query(null),
          cursor: cursor,
        );
        return (page.items, page.nextCursor);
      });
      final catalogs = await _pages((cursor) async {
        final page = await api.categories(cursor: cursor);
        return (page.items, page.nextCursor);
      });
      return ReportFeed(
        flow: flow,
        summary: summary.singleOrNull,
        rows: rows,
        categories: {for (final category in catalogs) category.id: category},
      );
    } on ApiException catch (e) {
      if (e.statusCode != 404 && e.statusCode != 501) rethrow;
      return const ReportFeed(
        flow: [],
        summary: null,
        rows: [],
        categories: {},
        unavailable: true,
      );
    }
  }
}
