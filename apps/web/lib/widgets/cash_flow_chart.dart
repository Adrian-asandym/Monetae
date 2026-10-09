// Derived from Cashew budget/lib/widgets/lineGraph.dart and
// pages/homePage/homePageLineGraph.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: period coordinates and exact wire tooltips;
// no cumulative money calculations or global settings.
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/report_presenter.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';

class CashFlowChart extends StatelessWidget {
  const CashFlowChart({
    super.key,
    required this.rows,
    this.income,
    this.animate = true,
  });
  final List<CashFlowRowDto> rows;
  final bool? income;
  final bool animate;
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    if (rows.isEmpty) {
      return SizedBox(height: 220, child: Center(child: Text(l.emptyChart)));
    }
    final types = [if (income != true) false, if (income != false) true];
    ReportTotalDto total(CashFlowRowDto row, bool isIncome) =>
        isIncome ? row.income : row.expense;
    final scale = rows.fold<double>(
      0,
      (max, row) => math.max(
        max,
        types.fold<double>(
          0,
          (max, kind) =>
              math.max(max, double.parse(total(row, kind).reportAmount).abs()),
        ),
      ),
    );
    final maximum = [
      for (final row in rows)
        for (final kind in types) total(row, kind),
    ].firstWhere((value) => double.parse(value.reportAmount).abs() == scale);
    final muted = colors.muted.withValues(alpha: .5);
    final intervalX = math.max(1.0, ((rows.length - 1) / 4).ceilToDouble());
    return Semantics(
      label: l.cashFlow,
      child: SizedBox(
        height: 240,
        child: Padding(
          padding: const EdgeInsets.only(top: 8, right: 25),
          child: LineChart(
            LineChartData(
              minX: 0,
              maxX: math.max(1, rows.length - 1).toDouble(),
              minY: 0,
              maxY: 1.1,
              borderData: FlBorderData(show: false),
              gridData: FlGridData(
                verticalInterval: intervalX,
                horizontalInterval: .25,
                getDrawingVerticalLine: (_) => FlLine(
                  color: colors.muted.withValues(alpha: .12),
                  strokeWidth: 2,
                  dashArray: [2, 8],
                ),
                getDrawingHorizontalLine: (_) => FlLine(
                  color: colors.muted.withValues(alpha: .12),
                  strokeWidth: 2,
                  dashArray: [2, 8],
                ),
              ),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                rightTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    interval: 1,
                    reservedSize: 80,
                    getTitlesWidget: (value, meta) {
                      if (value != 0 && value != 1) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            value == 0
                                ? formatCurrency(
                                    '0.00',
                                    maximum.reportCurrency,
                                    l.localeName,
                                  )
                                : reportAmount(maximum, l),
                            style: TextStyle(fontSize: 12, color: muted),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    interval: intervalX,
                    reservedSize: 30,
                    getTitlesWidget: (value, meta) {
                      final index = value.toInt();
                      if (index >= rows.length || value != index) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          DateFormat.MMMd(l.localeName)
                              .format(DateTime.parse(rows[index].startOn)),
                          style: TextStyle(fontSize: 13, color: muted),
                        ),
                      );
                    },
                  ),
                ),
              ),
              lineTouchData: LineTouchData(
                touchSpotThreshold: 1000,
                touchTooltipData: LineTouchTooltipData(
                  tooltipRoundedRadius: 8,
                  fitInsideHorizontally: true,
                  fitInsideVertically: true,
                  getTooltipColor: (_) => colors.card,
                  getTooltipItems: (spots) => [
                    for (final spot in spots)
                      LineTooltipItem(
                        '${DateFormat.MMMd(l.localeName).format(DateTime.parse(rows[spot.x.toInt()].startOn))}\n${types[spot.barIndex] ? l.income : l.expense}: ${reportAmount(total(rows[spot.x.toInt()], types[spot.barIndex]), l)}',
                        TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: types[spot.barIndex]
                              ? colors.income
                              : colors.expense,
                        ),
                      ),
                  ],
                ),
              ),
              lineBarsData: [
                for (final kind in types)
                  LineChartBarData(
                    spots: [
                      for (var i = 0; i < rows.length; i++)
                        FlSpot(
                          i.toDouble(),
                          scale == 0
                              ? 0
                              : double.parse(total(rows[i], kind).reportAmount)
                                        .abs() /
                                    scale,
                        ),
                    ],
                    color: pastel(
                      kind ? colors.income : colors.expense,
                      Brightness.light,
                      .3,
                    ),
                    barWidth: 3,
                    isStrokeCapRound: true,
                    isCurved: false,
                    dotData: FlDotData(show: rows.length == 1),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          (kind ? colors.income : colors.expense).withAlpha(
                            100,
                          ),
                          (kind ? colors.income : colors.expense).withAlpha(1),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            duration: animate && !MediaQuery.disableAnimationsOf(context)
                ? const Duration(milliseconds: 2000)
                : Duration.zero,
            curve: Curves.fastLinearToSlowEaseIn,
          ),
        ),
      ),
    );
  }
}
