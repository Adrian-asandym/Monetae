// Adapted from Cashew widgets/lineGraph.dart (getMinPoint/getMaxPoint,
// interval and constant-range guard), Copyright James Kokoska, GPL-3.0.
import 'dart:math' as math;

/// Chart geometry only: no balances or monetary calculations are performed.
class CashFlowAxis {
  CashFlowAxis._(this.minimum, this.maximum);

  factory CashFlowAxis.fromValues(Iterable<double> values) {
    // Cashew includes zero when no separate amountBefore is supplied.
    var minimum = 0.0;
    var maximum = 0.0;
    for (final value in values) {
      minimum = math.min(minimum, value);
      maximum = math.max(maximum, value);
    }
    if (minimum == maximum) maximum += 1;
    return CashFlowAxis._(minimum, maximum);
  }

  final double minimum;
  final double maximum;
  double get interval => (maximum - minimum) / 4;
  // The lower bound is the baseline and has no label. Zero may be an interior
  // or upper tick for signed series (coordinator clarification for T-514).
  List<double> get ticks => [
    for (var i = 0; i < 4; i++) maximum - interval * i,
  ];
  double get zeroFraction => (0 - minimum) / (maximum - minimum);
  double fraction(double value) => (value - minimum) / (maximum - minimum);
}
