import '../api/report_feed.dart';
import '../l10n/app_localizations.dart';
import 'api_dtos.dart';
import 'mock_data.dart';

ReportTotalDto syntheticTotal(String amount, {int unconverted = 0}) =>
    ReportTotalDto(
      byCurrency: [CurrencyTotalDto(currency: 'PEN', amount: amount)],
      reportCurrency: 'PEN',
      reportAmount: amount,
      unconvertedCount: unconverted,
    );

CashFlowRowDto syntheticFlow(
  String day,
  String income,
  String expense,
  String net,
  String cumulative,
) => CashFlowRowDto(
  startOn: day,
  endOn: day,
  income: syntheticTotal(income),
  expense: syntheticTotal(expense),
  net: syntheticTotal(net),
  cumulativeNet: syntheticTotal(cumulative),
);

ReportFeed mockReports(AppLocalizations l, {bool emptyPeriods = true}) {
  final food = mockCategory(l);
  final work = CategoryDto.fromJson({
    ...mockCategory(l, income: true).toJson(),
    'id': '00000000-0000-4000-8000-000000000011',
  });
  final home = CategoryDto.fromJson({
    ...mockCategory(l, custom: true).toJson(),
    'id': '00000000-0000-4000-8000-000000000012',
    'icon': 'home',
  });
  return ReportFeed(
    flow: [
      syntheticFlow('2026-10-01', '250.00', '48.50', '201.50', '201.50'),
      syntheticFlow('2026-10-02', '80.00', '31.50', '48.50', '250.00'),
      syntheticFlow('2026-10-03', '120.00', '60.00', '60.00', '310.00'),
      if (emptyPeriods)
        syntheticFlow('2026-10-04', '0.00', '0.00', '0.00', '310.00'),
      syntheticFlow('2026-10-05', '50.00', '10.00', '40.00', '350.00'),
      if (emptyPeriods)
        syntheticFlow('2026-10-06', '0.00', '0.00', '0.00', '350.00'),
      syntheticFlow('2026-10-07', '0.00', '20.00', '-20.00', '330.00'),
    ],
    summary: CashFlowRowDto(
      startOn: '2026-10-01',
      endOn: '2026-10-31',
      income: syntheticTotal('500.00'),
      expense: syntheticTotal('170.00'),
      net: syntheticTotal('330.00'),
      cumulativeNet: syntheticTotal('330.00'),
    ),
    rows: [
      CategoryReportRowDto(
        categoryId: food.id,
        kind: CategoryReportRowKind.expense,
        startOn: '2026-10-01',
        endOn: '2026-10-31',
        total: syntheticTotal('110.00'),
      ),
      CategoryReportRowDto(
        categoryId: home.id,
        kind: CategoryReportRowKind.expense,
        startOn: '2026-10-01',
        endOn: '2026-10-31',
        total: syntheticTotal('60.00'),
      ),
      CategoryReportRowDto(
        categoryId: work.id,
        kind: CategoryReportRowKind.income,
        startOn: '2026-10-01',
        endOn: '2026-10-31',
        total: syntheticTotal('500.00'),
      ),
    ],
    categories: {food.id: food, home.id: home, work.id: work},
  );
}
