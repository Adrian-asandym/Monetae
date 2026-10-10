import 'dart:math';

import 'package:flutter/foundation.dart';

import '../data/api_dtos.dart';
import '../presentation/decimal_input.dart';
import 'api_client.dart';
import 'home_controller.dart';

/// UUID v4 from OS randomness; no additional package or financial arithmetic.
String newIdempotencyKey() {
  final random = Random.secure();
  final bytes = List.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
      '${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

/// Form state only. Financial validation and persistence belong to the API.
final class NewTransactionController extends ChangeNotifier {
  NewTransactionController(this.api, this.user, {DateTime Function()? now})
    : now = now ?? DateTime.now {
    occurredAt = this.now().toUtc();
  }
  final ApiClient api;
  final CurrentUserDto user;
  final DateTime Function() now;
  List<AccountDto> accounts = [];
  List<CategoryDto> categories = [];
  AccountDto? account;
  String? categoryId;
  bool income = false;
  String amount = '';
  String rate = '';
  String title = '';
  String note = '';
  late DateTime occurredAt;
  bool loading = true;
  bool busy = false;
  ApiException? error;
  final fieldErrors = <String, String>{};
  final invalidFields = <String>{};
  String? _key;
  TransactionCreateDto? _attempt;
  bool _disposed = false;

  bool get needsRate =>
      account != null && account!.currency != user.baseCurrency;
  bool get scheduled => _attempt == null
      ? occurredAt.isAfter(now().toUtc())
      : _attempt!.status == TransactionCreateStatus.scheduled;
  // America/Lima has no DST. Use UTC arithmetic, independent of browser timezone.
  DateTime get limaTime =>
      occurredAt.toUtc().subtract(const Duration(hours: 5));
  List<CategoryDto> get visibleCategories => categories
      .where(
        (c) =>
            c.deletedAt == null &&
            c.kind == (income ? CategoryKind.income : CategoryKind.expense),
      )
      .toList();

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> load() async {
    loading = true;
    error = null;
    _notify();
    try {
      final result = await Future.wait([
        loadPages<AccountDto>((cursor) async {
          final page = await api.accounts(
            cursor: cursor,
            includeArchived: false,
          );
          return (page.items, page.nextCursor);
        }),
        loadPages<CategoryDto>((cursor) async {
          final page = await api.categories(cursor: cursor);
          return (page.items, page.nextCursor);
        }),
      ]);
      if (_disposed) return;
      accounts = result[0]
          .cast<AccountDto>()
          .where((a) => a.deletedAt == null && a.archivedAt == null)
          .toList();
      categories = result[1].cast<CategoryDto>();
      final preferred = user.preferences.defaultAccountId;
      account =
          accounts.where((a) => a.id == preferred).firstOrNull ??
          accounts.firstOrNull;
    } on ApiException catch (e) {
      if (!_disposed) error = e;
    } on Object {
      if (!_disposed) error = const ApiException(ApiErrorKind.unavailable);
    }
    loading = false;
    _notify();
  }

  /// Every user edit begins a new logical submission, including an edit reverted
  /// to its old value. A retry without edits keeps its exact body and UUID.
  void edit(VoidCallback change) {
    if (busy || _disposed) return;
    change();
    _key = null;
    _attempt = null;
    error = null;
    fieldErrors.clear();
    invalidFields.clear();
    _notify();
  }

  void selectIncome(bool value) => edit(() {
    income = value;
    categoryId = null;
  });

  void selectAccount(AccountDto value) => edit(() {
    account = value;
    rate = '';
  });

  void selectLimaTime(DateTime value) => edit(() {
    occurredAt = DateTime.utc(
      value.year,
      value.month,
      value.day,
      value.hour,
      value.minute,
    ).add(const Duration(hours: 5));
  });

  Future<bool> save() async {
    if (busy || loading || _disposed) return false;
    invalidFields.clear();
    if (!positiveDecimal(amount, 2)) invalidFields.add('amount');
    if (account == null) invalidFields.add('account_id');
    if (needsRate && !positiveDecimal(rate, 6)) {
      invalidFields.add('fx_rate_to_base');
    }
    if (invalidFields.isNotEmpty) {
      _notify();
      return false;
    }
    final selected = account!;
    _attempt ??= TransactionCreateDto(
      accountId: selected.id,
      categoryId: categoryId,
      kind: income
          ? TransactionCreateKind.income
          : TransactionCreateKind.expense,
      amount: '${income ? '' : '-'}${amountWireText(amount)}',
      currency: selected.currency,
      occurredAt: occurredAt.toUtc().toIso8601String(),
      status: scheduled
          ? TransactionCreateStatus.scheduled
          : TransactionCreateStatus.posted,
      title: title,
      note: note.isEmpty ? null : note,
      fxRateToBase: needsRate ? decimalWireText(rate, 6) : '1.000000',
      fxRateSource: TransactionCreateFxRateSource.manual,
    );
    _key ??= newIdempotencyKey();
    busy = true;
    error = null;
    fieldErrors.clear();
    _notify();
    var success = false;
    try {
      await api.createTransaction(_attempt!, idempotencyKey: _key!);
      success = true;
    } on ApiException catch (e) {
      if (!_disposed) {
        error = e;
        if (e.kind == ApiErrorKind.validation) {
          for (final field in e.problem?.errors ?? const <FieldErrorDto>[]) {
            fieldErrors[field.field.replaceFirst(RegExp(r'^body[.]'), '')] =
                field.message;
          }
        }
      }
    } on Object {
      if (!_disposed) error = const ApiException(ApiErrorKind.unavailable);
    }
    busy = false;
    _notify();
    return success;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
