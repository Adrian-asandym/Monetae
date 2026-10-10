import 'dart:ui';
import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/presentation/budget_calculations.dart';

void main() {
  // We need to initialize localization for tests
  late AppLocalizations l;
  setUpAll(() async {
    l = await AppLocalizations.delegate.load(const Locale('es'));
  });

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
