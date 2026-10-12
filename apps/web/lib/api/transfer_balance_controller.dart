import 'package:flutter/foundation.dart';

import '../data/api_dtos.dart';
import '../data/balance_correction_dtos.dart';
import '../presentation/decimal_input.dart';
import '../presentation/exact_decimal.dart';
import 'api_client.dart';
import 'new_transaction_controller.dart';

/// Form state and exact previews. Persistence and ledger rules belong to API.
final class TransferBalanceController extends ChangeNotifier {
  TransferBalanceController(
    this.api,
    this.user, {
    required this.accounts,
    required AccountDto? initialAccount,
    required this.occurredAt,
    DateTime Function()? now,
  }) : now = now ?? DateTime.now {
    from =
        accounts.where((a) => a.id == initialAccount?.id).firstOrNull ??
        accounts.firstOrNull;
    to = accounts.where((a) => a.id != from?.id).firstOrNull;
    _resetPair();
  }
  final ApiClient api;
  final CurrentUserDto user;
  final List<AccountDto> accounts;
  final DateTime Function() now;
  AccountDto? from, to;
  String fromAmount = '', toAmount = '', rate = '', title = '';
  String fromManualRate = '', toManualRate = '';
  DateTime occurredAt;
  DateTime? arrivalAt;
  bool busy = false, _disposed = false;
  ApiException? error;
  final invalidFields = <String>{};
  final fieldErrors = <String, String>{};
  String? _key;
  BalanceCorrectionCreateDto? _attempt;
  ExactDecimal? _multiplier;

  bool get sameCurrency => from != null && from?.currency == to?.currency;
  bool get neitherBase =>
      from != null &&
      to != null &&
      from!.currency != user.baseCurrency &&
      to!.currency != user.baseCurrency;
  DateTime get limaTime =>
      occurredAt.toUtc().subtract(const Duration(hours: 5));
  DateTime get arrivalTime =>
      (arrivalAt ?? occurredAt).toUtc().subtract(const Duration(hours: 5));
  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void edit(VoidCallback change) {
    if (busy || _disposed) return;
    change();
    _key = null;
    _attempt = null;
    error = null;
    invalidFields.clear();
    fieldErrors.clear();
    _notify();
  }

  void _resetPair() {
    rate = sameCurrency ? '1' : '';
    _multiplier = sameCurrency ? ExactDecimal.parse('1') : null;
    toAmount = sameCurrency ? fromAmount : '';
    fromManualRate = '';
    toManualRate = '';
  }

  void selectAccount(AccountDto account, {required bool outgoing}) {
    if (account.id == (outgoing ? to : from)?.id) return;
    edit(() {
      if (outgoing) {
        from = account;
      } else {
        to = account;
      }
      _resetPair();
    });
  }

  void setFromAmount(String value) => edit(() {
    fromAmount = value;
    toAmount = sameCurrency
        ? value
        : _multiplier == null || value.isEmpty
        ? ''
        : (ExactDecimal.parse(value) * _multiplier!).fixed(2);
  });
  void setToAmount(String value) => edit(() {
    toAmount = value;
    if (sameCurrency) {
      fromAmount = value;
    } else if (positiveDecimal(fromAmount, 2) && positiveDecimal(value, 2)) {
      _multiplier = ExactDecimal.parse(value) / ExactDecimal.parse(fromAmount);
      rate = _multiplier!.fixed(6);
    } else {
      rate = '';
      _multiplier = null;
    }
  });
  void setRate(String value) => edit(() {
    rate = value;
    _multiplier = positiveDecimal(value, 6) ? ExactDecimal.parse(value) : null;
    toAmount = _multiplier == null || fromAmount.isEmpty
        ? ''
        : (ExactDecimal.parse(fromAmount) * _multiplier!).fixed(2);
  });
  // Captures 24–25 + coordinator clarification: local Cashew reference is older.
  void swapAccounts() => edit(() {
    final oldFrom = from;
    from = to;
    to = oldFrom;
    final oldAmount = fromAmount;
    fromAmount = toAmount;
    toAmount = oldAmount;
    final oldManual = fromManualRate;
    fromManualRate = toManualRate;
    toManualRate = oldManual;
    if (_multiplier != null) {
      _multiplier = ExactDecimal.parse('1') / _multiplier!;
      rate = sameCurrency ? '1' : _multiplier!.fixed(6);
    }
  });
  void setDeparture(DateTime utc) => edit(() {
    occurredAt = utc.toUtc();
  });
  void setArrival(DateTime? utc) => edit(() {
    arrivalAt = utc?.toUtc();
  });

  String resultingBalance({required bool outgoing}) {
    final account = outgoing ? from : to;
    if (account == null) return '0.00';
    final amount = outgoing ? fromAmount : toAmount;
    final balance = ExactDecimal.parse(account.balance);
    final delta = ExactDecimal.parse(amount.isEmpty ? '0' : amount);
    return (outgoing ? balance - delta : balance + delta).fixed(2);
  }

  Future<bool> save({required String defaultTitle}) async {
    if (busy || _disposed) return false;
    invalidFields.clear();
    if (from == null) invalidFields.add('from_account_id');
    if (to == null || from?.id == to?.id) invalidFields.add('to_account_id');
    if (!positiveDecimal(fromAmount, 2)) invalidFields.add('from_amount');
    if (!positiveDecimal(toAmount, 2)) invalidFields.add('to_amount');
    if (!sameCurrency && _multiplier == null) invalidFields.add('rate');
    if ((arrivalAt ?? occurredAt).isBefore(occurredAt)) {
      invalidFields.add('to_occurred_at');
    }
    if (neitherBase) {
      if (!positiveDecimal(fromManualRate, 6)) {
        invalidFields.add('from_fx_rate_to_base');
      }
      if (!positiveDecimal(toManualRate, 6)) {
        invalidFields.add('to_fx_rate_to_base');
      }
    }
    if (invalidFields.isNotEmpty) {
      _notify();
      return false;
    }
    final fromValue = ExactDecimal.parse(fromAmount);
    final toValue = ExactDecimal.parse(toAmount);
    final fromRate = from!.currency == user.baseCurrency
        ? '1.000000'
        : to!.currency == user.baseCurrency
        ? (toValue / fromValue).fixed(6)
        : decimalWireText(fromManualRate, 6);
    final toRate = to!.currency == user.baseCurrency
        ? '1.000000'
        : from!.currency == user.baseCurrency
        ? (fromValue / toValue).fixed(6)
        : decimalWireText(toManualRate, 6);
    if (!positiveDecimal(fromRate, 6)) {
      invalidFields.add('from_fx_rate_to_base');
    }
    if (!positiveDecimal(toRate, 6)) invalidFields.add('to_fx_rate_to_base');
    if (invalidFields.isNotEmpty) {
      _notify();
      return false;
    }
    _attempt ??= BalanceCorrectionCreateDto(
      fromAccountId: from!.id,
      toAccountId: to!.id,
      fromAmount: amountWireText(fromAmount),
      toAmount: amountWireText(toAmount),
      fromFxRateToBase: fromRate,
      toFxRateToBase: toRate,
      occurredAt: occurredAt.toUtc().toIso8601String(),
      toOccurredAt: (arrivalAt ?? occurredAt).toUtc().toIso8601String(),
      title: title.trim().isEmpty ? defaultTitle : title,
    );
    _key ??= newIdempotencyKey();
    busy = true;
    error = null;
    fieldErrors.clear();
    _notify();
    var saved = false;
    try {
      await api.createBalanceCorrection(_attempt!, idempotencyKey: _key!);
      saved = true;
    } on ApiException catch (e) {
      if (!_disposed) {
        error = e;
        for (final field in e.problem?.errors ?? const <FieldErrorDto>[]) {
          fieldErrors[field.field.replaceFirst(RegExp(r'^body[.]'), '')] =
              field.message;
        }
      }
    } on Object {
      if (!_disposed) error = const ApiException(ApiErrorKind.unavailable);
    }
    busy = false;
    _notify();
    return saved;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
