import '../presentation/currency_format.dart';

import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_localizations.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/component_models.dart';
import 'api_dtos.dart';

// Synthetic IDs, dates and amounts. No persistence or financial calculations.
const mockCustomIconId = '00000000-0000-4000-8000-000000000050';
// Original synthetic house illustration; no imported category artwork.
const mockHouseSvg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<path d="M3 15L16 4l13 11v14H3Z" fill="#BA7DBD"/>'
    '<path d="M12 18h8v11h-8Z" fill="#FFD05B"/></svg>';
Uint8List get mockHouseBytes => Uint8List.fromList(utf8.encode(mockHouseSvg));

const _time = '2026-10-09T15:00:00Z';
const mockAccountId = '00000000-0000-4000-8000-000000000001';
const _categoryId = '00000000-0000-4000-8000-000000000010';

Map<String, Object?> get _metadata => {
  'created_at': _time,
  'updated_at': _time,
  'deleted_at': null,
};

Map<String, Object?> mockTransactionJson({
  String id = '00000000-0000-4000-8000-000000000100',
  String occurredAt = _time,
  String title = '',
  String? note,
  String kind = 'expense',
  String status = 'posted',
  String amount = '-48.50',
  String currency = 'PEN',
  String accountId = mockAccountId,
}) => {
  ..._metadata,
  'id': id,
  'account_id': accountId,
  'category_id': _categoryId,
  'kind': kind,
  'amount': amount,
  'currency': currency,
  'occurred_at': occurredAt,
  'status': status,
  'title': title,
  'note': note,
  'fx_rate_to_base': '1.000000',
  'fx_rate_source': 'manual',
  'tag_ids': <String>[],
  'transfer_group_id': null,
  'recurring_rule_id': null,
  'loan_id': kind == 'loan' ? '00000000-0000-4000-8000-000000000900' : null,
  'source': 'web',
  'categorization_source': 'manual',
  'is_initial_data': false,
  'reactivation_suggestions': <String>[],
};

AccountDto mockAccount(AppLocalizations l, {bool usd = false}) =>
    AccountDto.fromJson({
      ..._metadata,
      'id': usd ? '00000000-0000-4000-8000-000000000002' : mockAccountId,
      'name': usd ? l.dollarAccount : l.sampleAccount,
      'type': 'cash',
      'currency': usd ? 'USD' : 'PEN',
      'initial_balance': '0.00',
      'balance': '0.00',
      'transaction_count': 4,
      'color': usd ? '#BA7DBD' : '#5F85C2',
      'icon': 'wallet',
      'sort_order': 0,
      'archived_at': null,
    });

CategoryDto mockCategory(
  AppLocalizations l, {
  bool income = false,
  bool custom = false,
}) => CategoryDto.fromJson({
  ..._metadata,
  'id': _categoryId,
  'name': custom ? l.homeCategory : (income ? l.workCategory : l.foodCategory),
  'kind': income ? 'income' : 'expense',
  'parent_id': null,
  'icon': custom
      ? 'custom:$mockCustomIconId'
      : (income ? 'work' : 'restaurant'),
  'color': custom ? '#BA7DBD' : (income ? '#59A849' : '#CA995A'),
  'is_system': false,
  'system_key': null,
});

List<TransactionCardModel> mockCards(
  AppLocalizations l, {
  Uint8List? customSvgBytes,
}) {
  final account = mockAccount(l);
  final usdAccount = mockAccount(l, usd: true);
  final food = mockCategory(l);
  final work = mockCategory(l, income: true);
  final home = mockCategory(l, custom: true);
  // Presentation only: this synthetic timestamp is 10:00 in America/Lima.
  final localDate = DateTime.parse(_time).subtract(const Duration(hours: 5));
  final dateLabel = DateFormat.yMMMMEEEEd(l.localeName).format(localDate);
  final timeLabel = DateFormat.Hm(l.localeName).format(localDate);
  return [
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(title: l.sampleLunch, note: l.sampleNote),
      ),
      category: food,
      account: account,
      amountLabel: formatCurrency('48.50', 'PEN', l.localeName),
      subtitle: food.name,
      dateKey: '2026-10-09',
      dateLabel: dateLabel,
      timeLabel: timeLabel,
      icon: const CategoryIconSource.base('restaurant'),
      categoryColor: const Color(0xFFCA995A),
      tone: AmountTone.expense,
      typeLabel: l.expense,
      tags: [l.sampleTag],
    ),
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(
          id: '00000000-0000-4000-8000-000000000101',
          title: l.sampleWork,
          kind: 'income',
          amount: '250.00',
        ),
      ),
      category: work,
      account: account,
      amountLabel: formatCurrency('250.00', 'PEN', l.localeName),
      subtitle: work.name,
      dateKey: '2026-10-09',
      dateLabel: dateLabel,
      timeLabel: timeLabel,
      icon: const CategoryIconSource.base('work'),
      categoryColor: const Color(0xFF59A849),
      tone: AmountTone.income,
      typeLabel: l.income,
    ),
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(
          id: '00000000-0000-4000-8000-000000000102',
          title: l.sampleLoan,
          kind: 'loan',
          amount: '80.00',
        ),
      ),
      category: null,
      account: account,
      amountLabel: formatCurrency('80.00', 'PEN', l.localeName),
      subtitle: l.sampleLoanParty,
      dateKey: '2026-10-09',
      dateLabel: dateLabel,
      timeLabel: timeLabel,
      icon: const CategoryIconSource.base('loan'),
      categoryColor: const Color(0xFF6577E0),
      tone: AmountTone.neutral,
      typeLabel: l.loanMovement,
    ),
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(
          id: '00000000-0000-4000-8000-000000000103',
          occurredAt: '2026-10-10T15:00:00Z',
          title: l.sampleUpcoming,
          kind: 'expense',
          status: 'scheduled',
          amount: '-12.00',
          currency: 'USD',
          accountId: usdAccount.id,
        ),
      ),
      category: home,
      account: usdAccount,
      amountLabel: formatCurrency('12.00', 'USD', l.localeName),
      subtitle: home.name,
      dateKey: '2026-10-10',
      dateLabel: DateFormat.yMMMMEEEEd(l.localeName)
          .format(localDate.add(const Duration(days: 1))),
      timeLabel: timeLabel,
      icon: CategoryIconSource.resolve(
        home.icon,
        customIcons: {mockCustomIconId: customSvgBytes ?? mockHouseBytes},
      ),
      categoryColor: const Color(0xFFBA7DBD),
      tone: AmountTone.upcoming,
      typeLabel: l.scheduled,
    ),
  ];
}

List<CategorySlice> mockSlices(
  AppLocalizations l, {
  Uint8List? customSvgBytes,
}) => [
  CategorySlice(
    id: 'food',
    label: l.foodCategory,
    weight: .5,
    percentLabel: l.percent('50'),
    amountLabel: formatCurrency('150.00', 'PEN', l.localeName),
    color: const Color(0xFFCA995A),
    icon: const CategoryIconSource.base('restaurant'),
  ),
  CategorySlice(
    id: 'transport',
    label: l.transportCategory,
    weight: .3,
    percentLabel: l.percent('30'),
    amountLabel: formatCurrency('90.00', 'PEN', l.localeName),
    color: const Color(0xFF5F85C2),
    icon: const CategoryIconSource.base('transport'),
  ),
  CategorySlice(
    id: 'home',
    label: l.homeCategory,
    weight: .2,
    percentLabel: l.percent('20'),
    amountLabel: formatCurrency('60.00', 'PEN', l.localeName),
    color: const Color(0xFFBA7DBD),
    icon: CategoryIconSource.resolve(
      'custom:$mockCustomIconId',
      customIcons: {mockCustomIconId: customSvgBytes ?? mockHouseBytes},
    ),
  ),
];
