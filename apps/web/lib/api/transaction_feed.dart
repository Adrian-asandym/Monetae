import '../data/api_dtos.dart';
import 'api_client.dart';

/// Joins display catalogs only; balances, amounts and states come from the API.
final class TransactionFeed {
  TransactionFeed(this.api);
  final ApiClient api;
  final accounts = <String, AccountDto>{};
  final categories = <String, CategoryDto>{};
  final tags = <String, TagDto>{};
  final transactions = <TransactionDto>[];
  String? nextCursor;

  Future<void> _catalog<T>(
    Future<(List<T>, String?)> Function(String?) fetch,
    Map<String, T> target,
    String Function(T) id,
  ) async {
    String? cursor;
    final seen = <String>{};
    do {
      final (items, next) = await fetch(cursor);
      for (final item in items) {
        target[id(item)] = item;
      }
      cursor = next;
      if (cursor != null && !seen.add(cursor)) {
        throw const ApiException(ApiErrorKind.unavailable);
      }
    } while (cursor != null);
  }

  Future<void> load() async {
    await Future.wait([
      _catalog(
        (cursor) async {
          final page = await api.accounts(cursor: cursor);
          return (page.items, page.nextCursor);
        },
        accounts,
        (item) => item.id,
      ),
      _catalog(
        (cursor) async {
          final page = await api.categories(cursor: cursor);
          return (page.items, page.nextCursor);
        },
        categories,
        (item) => item.id,
      ),
      _catalog(
        (cursor) async {
          final page = await api.tags(cursor: cursor);
          return (page.items, page.nextCursor);
        },
        tags,
        (item) => item.id,
      ),
    ]);
    await loadMore();
  }

  final _missing = <String>{};
  Future<void> _resolve<T>(
    String id,
    Map<String, T> target,
    Future<T> Function(String) fetch,
  ) async {
    if (target.containsKey(id) || _missing.contains(id)) return;
    try {
      target[id] = await fetch(id);
    } on ApiException catch (e) {
      // Soft-deleted catalogs may be unavailable while history stays visible.
      if (e.problem?.status != 404) rethrow;
      _missing.add(id);
    }
  }

  Future<void> loadMore() async {
    final page = await api.transactions(cursor: nextCursor);
    for (final item in page.items) {
      await _resolve(item.accountId, accounts, api.account);
      final categoryId = item.categoryId;
      if (categoryId != null) {
        await _resolve(categoryId, categories, api.category);
      }
      for (final id in item.tagIds) {
        await _resolve(id, tags, api.tag);
      }
    }
    final existing = transactions.map((item) => item.id).toSet();
    transactions.addAll(page.items.where((item) => existing.add(item.id)));
    nextCursor = page.nextCursor;
  }
}
