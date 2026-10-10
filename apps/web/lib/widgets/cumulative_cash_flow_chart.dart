// Derived from Cashew widgets/lineGraph.dart (James Kokoska), GPL-3.0.
// Modified 2026-10-10: server cumulative_net, signed axes and Monetae card.
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/cash_flow_axis.dart';
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
    final colors = MonetaeColors.of(context);
    final color = Theme.of(context).colorScheme.onSurface;
    // These doubles are only coordinates. Tooltips retain exact API strings.
    final values = [
      for (final row in rows) double.parse(row.cumulativeNet.reportAmount),
    ];
    final axis = CashFlowAxis.fromValues(values);
    final scale = math.max(axis.minimum.abs(), axis.maximum.abs());
    final coordinates = [for (final value in values) value / scale];
    final intervalX = math.max(1.0, ((rows.length - 1) / 4).ceilToDouble());
    String amount(int index) => formatCurrency(
      rows[index].cumulativeNet.reportAmount,
      rows[index].cumulativeNet.reportCurrency,
      l.localeName,
    );
    final gridColor = color.withValues(alpha: HomeTokens.lineGridOpacity);

    return Material(
      key: const Key('cash-flow-card'),
      color: colors.card,
      borderRadius: BorderRadius.circular(HomeTokens.cardRadius),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          HomeTokens.lineLeftPadding,
          HomeTokens.lineTopPadding,
          HomeTokens.lineRightPadding,
          HomeTokens.lineBottomPadding,
        ),
        child: rows.isEmpty
            ? SizedBox(
                height: HomeTokens.linePlotHeight,
                child: Center(child: Text(l.emptyChart)),
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (rows.any((row) => row.cumulativeNet.unconvertedCount > 0))
                    Text(l.unconvertedNotice),
                  SizedBox(
                    height: HomeTokens.lineChartHeight,
                    child: Stack(
                      children: [
                        Positioned.fill(
                          left: HomeTokens.lineAxisWidth,
                          top: HomeTokens.lineLabelHeight / 2,
                          child: LineChart(
                            LineChartData(
                              minX: 0,
                              maxX: math.max(1, rows.length - 1).toDouble(),
                              // Cashew's tiny endpoint extension keeps zero visible.
                              minY: axis.minimum == 0
                                  ? -HomeTokens.lineZeroEpsilon
                                  : axis.minimum / scale,
                              maxY: axis.maximum == 0
                                  ? HomeTokens.lineZeroEpsilon
                                  : axis.maximum / scale,
                              borderData: FlBorderData(show: false),
                              gridData: FlGridData(
                                drawHorizontalLine: false,
                                verticalInterval: intervalX,
                                getDrawingVerticalLine: (_) => FlLine(
                                  color: gridColor,
                                  strokeWidth: HomeTokens.lineGridWidth,
                                  dashArray: HomeTokens.lineGridDashes,
                                ),
                              ),
                              extraLinesData: ExtraLinesData(
                                horizontalLines: [
                                  for (final tick in axis.ticks)
                                    HorizontalLine(
                                      y: tick / scale,
                                      color: gridColor,
                                      strokeWidth: HomeTokens.lineGridWidth,
                                      dashArray: HomeTokens.lineGridDashes,
                                    ),
                                  HorizontalLine(
                                    y: 0,
                                    color: color.withValues(
                                      alpha: HomeTokens.lineZeroOpacity,
                                    ),
                                    strokeWidth: HomeTokens.lineZeroWidth,
                                  ),
                                ],
                              ),
                              titlesData: FlTitlesData(
                                topTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                rightTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                leftTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                bottomTitles: AxisTitles(
                                  sideTitles: SideTitles(
                                    showTitles: true,
                                    interval: intervalX,
                                    reservedSize:
                                        HomeTokens.lineBottomTitleHeight,
                                    getTitlesWidget: (value, meta) {
                                      final index = value.toInt();
                                      if (index < 0 ||
                                          index >= rows.length ||
                                          value != index) {
                                        return const SizedBox.shrink();
                                      }
                                      return SideTitleWidget(
                                        axisSide: meta.axisSide,
                                        space: HomeTokens.lineDateGap,
                                        fitInside:
                                            SideTitleFitInsideData.fromTitleMeta(
                                              meta,
                                            ),
                                        child: Text(
                                          DateFormat.MMMd(l.localeName).format(
                                            DateTime.parse(rows[index].startOn),
                                          ),
                                          style: TextStyle(
                                            fontSize: HomeTokens.lineFontSize,
                                            color: colors.muted,
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ),
                              lineTouchData: LineTouchData(
                                touchSpotThreshold: 1000,
                                touchTooltipData: LineTouchTooltipData(
                                  tooltipRoundedRadius:
                                      HomeTokens.lineTooltipRadius,
                                  fitInsideHorizontally: true,
                                  fitInsideVertically: true,
                                  getTooltipColor: (_) =>
                                      color.withValues(alpha: .7),
                                  getTooltipItems: (spots) => [
                                    for (final spot in spots)
                                      LineTooltipItem(
                                        '${DateFormat.MMMd(l.localeName).format(DateTime.parse(rows[spot.x.toInt()].startOn))}\n${amount(spot.x.toInt())}',
                                        const TextStyle(
                                          color: Colors.white,
                                          fontSize: HomeTokens.lineFontSize,
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
                                  barWidth: HomeTokens.lineStrokeWidth,
                                  isStrokeCapRound: true,
                                  dotData: FlDotData(show: rows.length == 1),
                                  aboveBarData: BarAreaData(
                                    show: axis.minimum < 0,
                                    applyCutOffY: true,
                                    cutOffY: 0,
                                    gradient: LinearGradient(
                                      begin: Alignment.bottomCenter,
                                      end: Alignment(
                                        0,
                                        axis.maximum > 0
                                            ? -axis.minimum.abs() /
                                                  (axis.maximum.abs() +
                                                      axis.minimum.abs())
                                            : -1,
                                      ),
                                      colors: [
                                        color.withAlpha(100),
                                        color.withAlpha(1),
                                      ],
                                    ),
                                  ),
                                  belowBarData: BarAreaData(
                                    show: axis.maximum > 0,
                                    applyCutOffY: true,
                                    cutOffY: 0,
                                    gradient: LinearGradient(
                                      begin: Alignment.topCenter,
                                      end: Alignment.bottomCenter,
                                      colors: [
                                        color.withAlpha(100),
                                        color.withAlpha(1),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            duration:
                                animate &&
                                    !MediaQuery.disableAnimationsOf(context)
                                ? const Duration(
                                    milliseconds:
                                        HomeTokens.lineAnimationMilliseconds,
                                  )
                                : Duration.zero,
                            curve: Curves.fastLinearToSlowEaseIn,
                          ),
                        ),
                        // Exact tick positions rather than fl_chart's zero-anchored
                        // intervals, which do not align to min + k * interval when signed.
                        for (var i = 0; i < axis.ticks.length; i++)
                          Positioned(
                            left: 0,
                            top:
                                (1 - axis.fraction(axis.ticks[i])) *
                                HomeTokens.linePlotHeight,
                            width:
                                HomeTokens.lineAxisWidth -
                                HomeTokens.lineAxisGap,
                            height: HomeTokens.lineLabelHeight,
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Text(
                                  formatCurrency(
                                    axis.ticks[i].round().toString(),
                                    rows.first.cumulativeNet.reportCurrency,
                                    l.localeName,
                                  ),
                                  key: Key('cash-flow-y-$i'),
                                  style: TextStyle(
                                    fontSize: HomeTokens.lineFontSize,
                                    color: color.withValues(
                                      alpha: HomeTokens.lineLabelOpacity,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
