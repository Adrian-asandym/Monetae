import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/transaction_feed.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import 'category_icon_source.dart';
import 'component_models.dart';

Color presentationColor(
  String? value, {
  Color fallback = const Color(0xFF5F85C2),
}) {
  if (value == null || !RegExp(r'^#[0-9a-fA-F]{6}$').hasMatch(value)) {
    return fallback;
  }
  return Color(0xFF000000 | int.parse(value.substring(1), radix: 16));
}

List<TransactionCardModel> presentTransactions(
  TransactionFeed feed,
  AppLocalizations l,
) => [for (final item in feed.transactions) _present(item, feed, l)];

TransactionCardModel _present(
  TransactionDto item,
  TransactionFeed feed,
  AppLocalizations l,
) {
  // America/Lima uses UTC-05 without DST. Use UTC calendar fields, independent
  // of the browser/device timezone, including around midnight.
  final date = DateTime.parse(item.occurredAt)
      .toUtc()
      .subtract(const Duration(hours: 5));
  final category = feed.categories[item.categoryId];
  final label = switch (item.kind) {
    TransactionKind.income => l.income,
    TransactionKind.expense => l.expense,
    TransactionKind.loan => l.loanMovement,
    TransactionKind.transfer => l.transfer,
  };
  // String formatting only: preserve decimal digits; no floating-point parsing.
  final digits = item.amount.startsWith('-')
      ? item.amount.substring(1)
      : item.amount;
  final amount = switch (item.currency) {
    'PEN' => l.penAmount(digits),
    'USD' => l.usdAmount(digits),
    _ => l.currencyAmount(item.currency, digits),
  };
  return TransactionCardModel(
    transaction: item,
    category: category,
    account: feed.accounts[item.accountId],
    amountLabel: amount,
    subtitle: category?.name ?? label,
    dateKey: DateFormat('yyyy-MM-dd').format(date),
    dateLabel: DateFormat.yMMMMEEEEd(l.localeName).format(date),
    timeLabel: DateFormat.Hm(l.localeName).format(date),
    icon: CategoryIconSource.resolve(category?.icon ?? item.kind.name),
    categoryColor: presentationColor(category?.color),
    tone: item.status == TransactionStatus.scheduled
        ? AmountTone.upcoming
        : switch (item.kind) {
            TransactionKind.income => AmountTone.income,
            TransactionKind.expense => AmountTone.expense,
            _ => AmountTone.neutral,
          },
    typeLabel: item.status == TransactionStatus.scheduled ? l.scheduled : label,
    tags: [
      for (final id in item.tagIds) feed.tags[id]?.name ?? l.unavailableTag,
    ],
  );
}
