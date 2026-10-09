// Derived from Cashew budget/lib/struct/customDelayedCurve.dart, GPL-3.0.
// Modified for Monetae on 2026-10-09: const constructor and bounded delay.
import 'package:flutter/animation.dart';

class CustomDelayedCurve extends Curve {
  const CustomDelayedCurve({
    this.delayPercentage = .25,
    this.innerCurve = Curves.easeInOut,
  }) : assert(delayPercentage >= 0 && delayPercentage < 1);

  final double delayPercentage;
  final Curve innerCurve;

  @override
  double transformInternal(double t) {
    if (t < delayPercentage) {
      return 0.0;
    } else {
      return innerCurve.transform(
        (t - delayPercentage) / (1 - delayPercentage),
      );
    }
  }
}
