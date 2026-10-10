import 'dart:ui';

import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/presentation/budget_calculations.dart';

void main() {
  // We need to initialize localization for tests
  late AppLocalizations l;
  setUpAll(() async {
    l = await AppLocalizations.delegate.load(const Locale('es'));
  });

  test('daily amount rounds recurring quotients and exact ties HALF_UP', () {
    expect(
      dailyAmount(Decimal.parse('1265.50'), 23).toStringAsFixed(2),
      '55.02',
    );
    expect(dailyAmount(Decimal.parse('2.01'), 2).toStringAsFixed(2), '1.01');
    expect(dailyAmount(Decimal.parse('-2.01'), 2).toStringAsFixed(2), '-1.01');
    expect(dailyAmount(Decimal.parse('2.0099'), 2).toStringAsFixed(2), '1.00');
  });

  for (final (remaining, days, expected) in [
    ('1265.50', 23, '55,02'),
    ('2.01', 2, '1,01'),
  ]) {
    test('budget and goal labels round $remaining / $days to $expected', () {
      final today = DateTime(2026, 10, 9);
      final due = today
          .add(Duration(days: days - 1))
          .toIso8601String()
          .split('T')
          .first;
      final budget = BudgetDto.fromJson({
        ...mockBudgets(l).first.toJson(),
        'amount': remaining,
        'end_on': due,
      });
      final goal = GoalDto.fromJson({
        ...mockGoals(l).first.toJson(),
        'target_amount': remaining,
        'progress_amount': '0.00',
        'due_on': due,
      });
      expect(
        budgetPerDayLabel(l, budget, Decimal.zero, today),
        'Puedes gastar $expected S/./día para $days días más',
      );
      expect(
        goalPerDayLabel(l, goal, today),
        '$expected S/./día para $days días',
      );
    });
  }

  test('budgetPerDayLabel calculates correctly', () {
    final budget = BudgetDto(
      id: '1',
      name: 'Test',
      amount: '100.00',
      period: BudgetPeriod.monthly,
      startOn: '2026-10-01',
      endOn: '2026-10-31',
      currency: 'PEN',
      scope: BudgetScope.all,
      categoryLimits: [],
      createdAt: '2026-10-01',
      updatedAt: '2026-10-01',
      color: null,
      deletedAt: null,
      remainingAmount: '50.00',
      spentAmount: '50.00',
      reportTotal: ReportTotalDto(
        byCurrency: [],
        reportCurrency: 'PEN',
        reportAmount: '-50',
        unconvertedCount: 0,
      ),
    );

    // 50 spent, 10 days left. 100-50=50 remaining. 50/10=5 per day.
    final label = budgetPerDayLabel(
      l,
      budget,
      Decimal.parse('50.00'),
      DateTime(2026, 10, 22),
    );
    // 10 days left because 31-22=9 + 1 = 10
    expect(label, 'Puedes gastar 5 S/./día para 10 días más');
  });
}
