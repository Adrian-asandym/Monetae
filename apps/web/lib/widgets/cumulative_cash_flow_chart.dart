// Derived from Cashew widgets/lineGraph.dart and pages/homePage/homePageLineGraph.dart.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: signed coordinates from
// cumulative_net only, exact server labels; no client-side financial aggregation.
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';

class CumulativeCashFlowChart extends StatelessWidget {
  const CumulativeCashFlowChart({
    super.key,
    required this.rows,
    this.animate = true,
  });
  final List<CashFlowRowDto> rows;
  final bool animate;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (rows.isEmpty) {
      return SizedBox(height: 240, child: Center(child: Text(l.emptyChart)));
    }
    // double values are chart geometry only; tooltips use the original strings.
    final values = [
      for (final row in rows) double.parse(row.cumulativeNet.reportAmount),
    ];
    final scale = values.fold<double>(
      0,
      (maximum, value) => math.max(maximum, value.abs()),
    );
    final coordinates = [
      for (final value in values) scale == 0 ? 0.0 : value / scale,
    ];
    final low = coordinates.reduce(math.min);
    final high = coordinates.reduce(math.max);
    final color = Theme.of(context).colorScheme.onSurface;
    final muted = MonetaeColors.of(context).muted;
    final intervalX = math.max(1.0, ((rows.length - 1) / 4).ceilToDouble());
    String amount(int index) => formatCurrency(
      rows[index].cumulativeNet.reportAmount,
      rows[index].cumulativeNet.reportCurrency,
      l.localeName,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (rows.any((row) => row.cumulativeNet.unconvertedCount > 0))
          Text(l.unconvertedNotice),
        SizedBox(
          height: 250,
          child: Padding(
            padding: const EdgeInsets.only(top: 10, right: 20),
            child: LineChart(
              LineChartData(
                minX: 0,
                maxX: math.max(1, rows.length - 1).toDouble(),
                minY: math.min(0, low) - .1,
                maxY: math.max(0, high) + .1,
                borderData: FlBorderData(show: false),
                gridData: FlGridData(
                  horizontalInterval: .5,
                  verticalInterval: intervalX,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: muted.withValues(alpha: .12),
                    strokeWidth: 2,
                    dashArray: [2, 8],
                  ),
                  getDrawingVerticalLine: (_) => FlLine(
                    color: muted.withValues(alpha: .12),
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
                      reservedSize: 85,
                      interval: 1,
                      getTitlesWidget: (value, meta) {
                        if (value != 0 && value.abs() != 1) {
                          return const SizedBox.shrink();
                        }
                        final extreme = coordinates.indexOf(value);
                        if (value != 0 && extreme < 0) {
                          return const SizedBox.shrink();
                        }
                        return FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            value == 0
                                ? formatCurrency(
                                    '0.00',
                                    rows.first.cumulativeNet.reportCurrency,
                                    l.localeName,
                                  )
                                : amount(extreme),
                            style: TextStyle(fontSize: 12, color: muted),
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
                        if (index < 0 ||
                            index >= rows.length ||
                            value != index) {
                          return const SizedBox.shrink();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            DateFormat.MMMd(l.localeName)
                                .format(DateTime.parse(rows[index].startOn)),
                            style: TextStyle(fontSize: 12, color: muted),
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
                    getTooltipColor: (_) => color.withValues(alpha: 0.7),
                    getTooltipItems: (spots) => [
                      for (final spot in spots)
                        LineTooltipItem(
                          '${DateFormat.MMMd(l.localeName).format(DateTime.parse(rows[spot.x.toInt()].startOn))}\n${amount(spot.x.toInt())}',
                          const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                    ],
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: [
                      for (var i = 0; i < coordinates.length; i++)
                        FlSpot(i.toDouble(), coordinates[i]),
                    ],
                    color: pastel(color, Brightness.light, .3),
                    barWidth: 3,
                    isStrokeCapRound: true,
                    dotData: FlDotData(show: rows.length == 1),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [color.withAlpha(100), color.withAlpha(1)],
                      ),
                    ),
                  ),
                ],
              ),
              duration: animate && !MediaQuery.disableAnimationsOf(context)
                  ? const Duration(milliseconds: 1500)
                  : Duration.zero,
              curve: Curves.fastLinearToSlowEaseIn,
            ),
          ),
        ),
      ],
    );
  }
}
