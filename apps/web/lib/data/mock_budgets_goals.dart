import '../l10n/app_localizations.dart';
import 'api_dtos.dart';
import 'mock_data.dart';

// Synthetic contract responses. All financial amounts (including remaining and
// converted totals) are literal fixture values, never computed by the UI.
final syntheticBudgetToday = DateTime.utc(2026, 10, 9);
const _metadata = <String, Object?>{
  'created_at': '2026-10-01T15:00:00Z',
  'updated_at': '2026-10-09T15:00:00Z',
  'deleted_at': null,
};

ReportTotalDto _total(String amount, String currency, String converted) =>
    ReportTotalDto(
      byCurrency: [CurrencyTotalDto(currency: currency, amount: amount)],
      reportCurrency: 'PEN',
      reportAmount: converted,
      unconvertedCount: 0,
    );

List<BudgetDto> mockBudgets(AppLocalizations l) => [
  BudgetDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000701',
    'name': l.sampleFoodBudget,
    'period': 'monthly',
    'start_on': '2026-10-01',
    'end_on': '2026-10-31',
    'amount': '2500.00',
    'currency': 'PEN',
    'scope': 'all',
    'category_limits': <Object?>[],
    'spent_amount': '1234.50',
    'remaining_amount': '1265.50',
    'report_total': _total('1234.50', 'PEN', '1234.50').toJson(),
    'color': '#59A849',
  }),
  BudgetDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000702',
    'name': l.sampleTravelBudget,
    'period': 'custom',
    'start_on': '2026-10-05',
    'end_on': '2026-10-15',
    'amount': '500.00',
    'currency': 'USD',
    'scope': 'selected',
    'category_limits': [
      {
        'category_id': '00000000-0000-4000-8000-000000000010',
        'limit_amount': '500.00',
      },
    ],
    'spent_amount': '480.00',
    'remaining_amount': '20.00',
    'report_total': _total('480.00', 'USD', '1824.00').toJson(),
    'color': '#CA995A',
  }),
  BudgetDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000703',
    'name': l.sampleHomeBudget,
    'period': 'weekly',
    'start_on': '2026-10-05',
    'end_on': '2026-10-11',
    'amount': '1200.00',
    'currency': 'PEN',
    'scope': 'all',
    'category_limits': <Object?>[],
    'spent_amount': '1440.00',
    'remaining_amount': '-240.00',
    'report_total': _total('1440.00', 'PEN', '1440.00').toJson(),
    'color': '#CA5A5A',
  }),
];

List<GoalDto> mockGoals(AppLocalizations l) => [
  GoalDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000711',
    'name': l.sampleSavingsGoal,
    'kind': 'save',
    'target_amount': '2469.00',
    'currency': 'PEN',
    'due_on': '2027-01-31',
    'progress_amount': '1234.50',
    'report_total': _total('1234.50', 'PEN', '1234.50').toJson(),
    'color': '#6577E0',
    'icon': 'wallet',
  }),
  GoalDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000712',
    'name': l.sampleSpendingGoal,
    'kind': 'spend',
    'target_amount': '1800.00',
    'currency': 'USD',
    'due_on': null,
    'progress_amount': '1800.00',
    'report_total': _total('1800.00', 'USD', '6840.00').toJson(),
    'color': '#59A849',
    'icon': 'work',
  }),
  GoalDto.fromJson({
    ..._metadata,
    'id': '00000000-0000-4000-8000-000000000713',
    'name': l.sampleHolidayGoal,
    'kind': 'spend',
    'target_amount': '200.00',
    'currency': 'USD',
    'due_on': '2026-12-31',
    'progress_amount': '80.00',
    'report_total': _total('80.00', 'USD', '304.00').toJson(),
    'color': null,
    'icon': 'custom:$mockCustomIconId',
  }),
];
