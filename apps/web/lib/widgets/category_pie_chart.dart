// Derived from Cashew budget/lib/widgets/pieChart.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: pure data input and controlled selection.
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../presentation/component_models.dart';
import '../theme/monetae_theme.dart';

class CategoryPieChart extends StatelessWidget {
  const CategoryPieChart({
    super.key,
    required this.slices,
    required this.emptyLabel,
    this.selectedId,
    this.onSelected,
    this.large = false,
    this.animate = true,
  });

  final List<CategorySlice> slices;
  final String emptyLabel;
  final String? selectedId;
  final ValueChanged<String?>? onSelected;
  final bool large;
  final bool animate;

  @override
  Widget build(BuildContext context) {
    final data = slices.where((slice) => slice.weight > 0).toList();
    final theme = Theme.of(context);
    final size = large ? 300.0 : 220.0;
    final radius = large ? 136.0 : 100.0;
    final motion = animate && !MediaQuery.disableAnimationsOf(context);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (data.isEmpty)
            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: theme.colorScheme.secondaryContainer.withValues(
                  alpha: .3,
                ),
              ),
            )
          else
            PieChart(
              PieChartData(
                startDegreeOffset: -45,
                sectionsSpace: 0,
                centerSpaceRadius: 0,
                borderData: FlBorderData(show: false),
                pieTouchData: PieTouchData(
                  enabled: onSelected != null,
                  touchCallback: (event, response) {
                    if (event is! FlTapDownEvent &&
                        event is! FlLongPressMoveUpdate) {
                      return;
                    }
                    final index = response?.touchedSection?.touchedSectionIndex;
                    if (index == null || index < 0 || index >= data.length) {
                      return;
                    }
                    final id = data[index].id;
                    onSelected?.call(
                      event is FlTapDownEvent && id == selectedId ? null : id,
                    );
                  },
                ),
                sections: [
                  for (var i = 0; i < data.length; i++)
                    _section(context, data, i, radius),
                ],
              ),
              swapAnimationDuration: motion
                  ? const Duration(milliseconds: 1300)
                  : Duration.zero,
              swapAnimationCurve: const ElasticOutCurve(.6),
            ),
          IgnorePointer(
            child: Container(
              width: large ? 130 : 105,
              height: large ? 130 : 105,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: theme.colorScheme.surface.withValues(alpha: .2),
              ),
            ),
          ),
          IgnorePointer(
            child: Container(
              width: large ? 110 : 80,
              height: large ? 110 : 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: theme.colorScheme.surface,
              ),
            ),
          ),
          if (data.isEmpty)
            Center(
              child: Text(
                emptyLabel,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ),
        ],
      ),
    );
  }

  PieChartSectionData _section(
    BuildContext context,
    List<CategorySlice> data,
    int i,
    double radius,
  ) {
    final slice = data[i];
    final selected = selectedId == slice.id;
    final sameNeighbor =
        (i > 0 && data[i - 1].color == slice.color) ||
        (i + 1 < data.length && data[i + 1].color == slice.color);
    final brightness = Theme.of(context).brightness;
    final variation = sameNeighbor
        ? (i % 3 == 0 ? .2 : (i % 3 == 1 ? .35 : 0))
        : 0.0;
    final color = pastel(
      slice.color,
      brightness,
      (brightness == Brightness.light ? .3 : .1) + variation,
    );
    final midpoint =
        data.take(i).fold<double>(0, (sum, item) => sum + item.weight) +
        slice.weight / 2;
    return PieChartSectionData(
      color: color,
      value: slice.weight,
      title: '',
      radius: radius + (selected ? (large ? 10 : 6) : 0),
      badgePositionPercentageOffset: .98,
      badgeWidget: slice.weight < .05 && !selected
          ? null
          : Semantics(
              label: '${slice.label}, ${slice.percentLabel}',
              button: onSelected != null,
              selected: selected,
              child: Tooltip(
                message: '${slice.label} · ${slice.percentLabel}',
                child: GestureDetector(
                  onTap: onSelected == null
                      ? null
                      : () => onSelected!(selected ? null : slice.id),
                  child: Stack(
                    alignment: Alignment.center,
                    clipBehavior: Clip.none,
                    children: [
                      if (selected)
                        Transform.translate(
                          offset: Offset(0, midpoint < .5 ? -34 : 34),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 5,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.surface,
                              borderRadius: BorderRadius.circular(5),
                              border: Border.all(color: color, width: 1.5),
                            ),
                            child: Text(
                              slice.percentLabel,
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                      Container(
                        width: selected ? 54 : 45,
                        height: selected ? 54 : 45,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Theme.of(context).colorScheme.surface,
                          border: Border.all(color: color, width: 2.5),
                        ),
                        child: Icon(
                          slice.icon,
                          size: selected ? 34 : 27,
                          color: slice.color,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
