// Derived from Cashew budget/lib/widgets/budgetContainer.dart
// (BudgetProgress, AnimatedProgress, TodayIndicator) and progressBar.dart.
// Copyright (C) 2023 James Kokoska, GPL-3.0.
// Modified for Monetae on 2026-10-09: bounded geometry, explicit inputs,
// reduced-motion support and no shared/pending transaction layers.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../presentation/decimal_progress.dart';
import '../theme/monetae_theme.dart';

class BudgetProgress extends StatelessWidget {
  const BudgetProgress({
    super.key,
    required this.progress,
    required this.color,
    this.today,
  });

  final DecimalProgress progress;
  final Color color;
  final double? today;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final brightness = Theme.of(context).brightness;
    final label = l.percent(progress.percent);
    final reduced = MediaQuery.disableAnimationsOf(context);
    return Semantics(
      label: l.progress,
      value: label,
      child: ExcludeSemantics(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth;
            final marker = today == null
                ? null
                : (width - 3) * today!.clamp(0, 1);
            return SizedBox(
              height: marker == null ? 19.2 : 40,
              child: Stack(
                children: [
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: 19.2,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(50),
                      child: ColoredBox(
                        color: pastel(color, brightness, .8),
                        child: TweenAnimationBuilder<double>(
                          tween: Tween(begin: 0, end: progress.fraction),
                          duration: reduced
                              ? Duration.zero
                              : const Duration(milliseconds: 1500),
                          curve: Curves.easeInOutCubic,
                          builder: (context, value, _) => Stack(
                            children: [
                              Align(
                                alignment: AlignmentDirectional.centerStart,
                                child: FractionallySizedBox(
                                  widthFactor: value,
                                  heightFactor: 1,
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: pastel(
                                        color,
                                        Brightness.light,
                                        .6,
                                      ),
                                      borderRadius: BorderRadius.circular(50),
                                    ),
                                    child: value > .4
                                        ? Center(
                                            child: _percentText(
                                              label,
                                              pastel(
                                                color,
                                                Brightness.dark,
                                                .6,
                                              ),
                                            ),
                                          )
                                        : null,
                                  ),
                                ),
                              ),
                              if (value <= .4)
                                Center(
                                  child: _percentText(
                                    label,
                                    Theme.of(context).colorScheme.onSurface,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  if (marker != null) ...[
                    Positioned(
                      left: (marker - 19).clamp(
                        0,
                        (width - 40).clamp(0, width),
                      ),
                      top: 0,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 5,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1F1F1F),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          l.today,
                          style: const TextStyle(
                            fontSize: 9,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      key: const Key('today-marker'),
                      left: marker,
                      bottom: 0,
                      width: 3,
                      height: 22,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.onSurface
                              .withValues(alpha: .4),
                          borderRadius: const BorderRadius.vertical(
                            bottom: Radius.circular(5),
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _percentText(String label, Color color) => Text(
    label,
    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: color),
  );
}
