import 'dart:math' as math;

import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import 'category_icon_source.dart';
import 'component_models.dart';
import 'currency_format.dart';
import 'transaction_presenter.dart';

/// Floats are exclusively chart coordinates/shares. Financial labels always
/// come from the untouched decimal strings. No conversion or total is computed.
List<CategorySlice> presentCategoryReport(
  List<CategoryReportRowDto> rows,
  Map<String, CategoryDto> categories,
  CategoryReportRowKind kind,
  AppLocalizations l,
) {
  final selected = rows.where((row) => row.kind == kind).toList();
  final scale = selected.fold<double>(
    0,
    (max, row) => math.max(max, double.parse(row.total.reportAmount).abs()),
  );
  final coordinates = [
    for (final row in selected)
      scale == 0 ? 0.0 : double.parse(row.total.reportAmount).abs() / scale,
  ];
  final extent = coordinates.fold<double>(0, (sum, value) => sum + value);
  return [
    for (var i = 0; i < selected.length; i++)
      CategorySlice(
        id: selected[i].categoryId ?? 'uncategorized',
        label: categories[selected[i].categoryId]?.name ?? l.uncategorized,
        weight: extent == 0 ? 0 : coordinates[i] / extent,
        percentLabel: l.percent(
          (NumberFormat.decimalPattern(l.localeName)..maximumFractionDigits = 1)
              .format(extent == 0 ? 0 : coordinates[i] / extent * 100),
        ),
        amountLabel: formatCurrency(
          selected[i].total.reportAmount,
          selected[i].total.reportCurrency,
          l.localeName,
          absolute: true,
        ),
        color: presentationColor(categories[selected[i].categoryId]?.color),
        icon: CategoryIconSource.resolve(
          categories[selected[i].categoryId]?.icon ?? 'wallet',
        ),
      ),
  ];
}

String reportAmount(ReportTotalDto total, AppLocalizations l) => formatCurrency(
  total.reportAmount,
  total.reportCurrency,
  l.localeName,
  absolute: true,
);

List<String> currencyBreakdown(ReportTotalDto total, AppLocalizations l) => [
  for (final value in total.byCurrency)
    formatCurrency(value.amount, value.currency, l.localeName, absolute: true),
];
