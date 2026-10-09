import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../presentation/component_models.dart';
import 'api_dtos.dart';

// Synthetic IDs, dates and amounts. No persistence or financial calculations.
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
  'occurred_at': _time,
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
      'color': '#5F85C2',
      'icon': 'wallet',
      'sort_order': 0,
      'archived_at': null,
    });

CategoryDto mockCategory(AppLocalizations l, {bool income = false}) =>
    CategoryDto.fromJson({
      ..._metadata,
      'id': _categoryId,
      'name': income ? l.workCategory : l.foodCategory,
      'kind': income ? 'income' : 'expense',
      'parent_id': null,
      'icon': income ? 'work' : 'restaurant',
      'color': income ? '#59A849' : '#CA995A',
      'is_system': false,
      'system_key': null,
    });

List<TransactionCardModel> mockCards(AppLocalizations l) {
  final account = mockAccount(l);
  final usdAccount = mockAccount(l, usd: true);
  final food = mockCategory(l);
  final work = mockCategory(l, income: true);
  return [
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(title: l.sampleLunch, note: l.sampleNote),
      ),
      category: food,
      account: account,
      amountLabel: l.penAmount('48.50'),
      subtitle: l.cardSubtitle(food.name, account.name),
      icon: Icons.restaurant_rounded,
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
      amountLabel: l.penAmount('250.00'),
      subtitle: l.cardSubtitle(work.name, account.name),
      icon: Icons.work_rounded,
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
      amountLabel: l.penAmount('80.00'),
      subtitle: account.name,
      icon: Icons.handshake_outlined,
      categoryColor: const Color(0xFF6577E0),
      tone: AmountTone.neutral,
      typeLabel: l.loanMovement,
    ),
    TransactionCardModel(
      transaction: TransactionDto.fromJson(
        mockTransactionJson(
          id: '00000000-0000-4000-8000-000000000103',
          title: l.sampleUpcoming,
          kind: 'expense',
          status: 'scheduled',
          amount: '-12.00',
          currency: 'USD',
          accountId: usdAccount.id,
        ),
      ),
      category: food,
      account: usdAccount,
      amountLabel: l.usdAmount('12.00'),
      subtitle: usdAccount.name,
      icon: Icons.calendar_month_outlined,
      categoryColor: const Color(0xFF58A4C2),
      tone: AmountTone.upcoming,
      typeLabel: l.scheduled,
    ),
  ];
}

List<CategorySlice> mockSlices(AppLocalizations l) => [
  CategorySlice(
    id: 'food',
    label: l.foodCategory,
    weight: .5,
    percentLabel: l.percent('50'),
    amountLabel: l.penAmount('150.00'),
    color: const Color(0xFFCA995A),
    icon: Icons.restaurant_rounded,
  ),
  CategorySlice(
    id: 'transport',
    label: l.transportCategory,
    weight: .3,
    percentLabel: l.percent('30'),
    amountLabel: l.penAmount('90.00'),
    color: const Color(0xFF5F85C2),
    icon: Icons.directions_bus_rounded,
  ),
  CategorySlice(
    id: 'home',
    label: l.homeCategory,
    weight: .2,
    percentLabel: l.percent('20'),
    amountLabel: l.penAmount('60.00'),
    color: const Color(0xFFBA7DBD),
    icon: Icons.home_rounded,
  ),
];
