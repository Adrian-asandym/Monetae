import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/presentation/cash_flow_axis.dart';

void main() {
  test('positive range includes zero; four quarter marks exclude baseline', () {
    final axis = CashFlowAxis.fromValues([200, 1200, 400]);
    expect(axis.minimum, 0);
    expect(axis.maximum, 1200);
    expect(axis.interval, 300);
    expect(axis.ticks, [1200, 900, 600, 300]);
    expect(axis.zeroFraction, 0);
  });
  test(
    'signed range spans minimum to maximum with four equally spaced marks',
    () {
      final axis = CashFlowAxis.fromValues([-400, 1200, -200]);
      expect(axis.minimum, -400);
      expect(axis.maximum, 1200);
      expect(axis.ticks, [1200, 800, 400, 0]);
      expect(axis.zeroFraction, .25);
      for (var i = 1; i < 4; i++) {
        expect(axis.ticks[i - 1] - axis.ticks[i], axis.interval);
      }
    },
  );
  test('symmetric signed range retains zero as an interior mark', () {
    final axis = CashFlowAxis.fromValues([-200, 200]);
    expect(axis.ticks, [200, 100, 0, -100]);
    expect(axis.zeroFraction, .5);
  });
  test('negative-only range retains zero as the upper mark', () {
    final axis = CashFlowAxis.fromValues([-800, -400]);
    expect(axis.minimum, -800);
    expect(axis.maximum, 0);
    expect(axis.ticks, [0, -200, -400, -600]);
    expect(axis.zeroFraction, 1);
  });
  test('zero and missing geometry use Cashew nonzero constant-range guard', () {
    for (final values in [
      <double>[],
      [0.0],
      [0.0, 0.0],
    ]) {
      final axis = CashFlowAxis.fromValues(values);
      expect(axis.minimum, 0);
      expect(axis.maximum, 1);
      expect(axis.ticks, hasLength(4));
      expect(axis.interval, .25);
      expect(axis.ticks.every((v) => v.isFinite), true);
    }
  });
}
