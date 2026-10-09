/// Presentation geometry only: the quotient of two contract decimal strings.
/// Align decimal scales as BigInts, divide at six decimal places, then convert
/// only the bounded dimensionless result to double. No money enters a float,
/// and no balance, remaining amount, exchange rate or financial total is derived.
final class DecimalProgress {
  const DecimalProgress._(this.fraction, this.percent, this.reachedTarget);

  factory DecimalProgress.fromAmounts(String current, String target) {
    final a = _decimal(current);
    final b = _decimal(target);
    final numerator = a.$1 * BigInt.from(10).pow(b.$2);
    final denominator = b.$1 * BigInt.from(10).pow(a.$2);
    if (numerator <= BigInt.zero || denominator <= BigInt.zero) {
      return const DecimalProgress._(0, '0', false);
    }
    final reached = numerator >= denominator;
    final units = numerator * BigInt.from(1000000) ~/ denominator;
    // Cashew rounds the percentage; it may exceed 100 while the bar is capped.
    final percent =
        (numerator * BigInt.from(100) + denominator ~/ BigInt.two) ~/
        denominator;
    return DecimalProgress._(
      reached ? 1 : units.toDouble() / 1000000,
      percent.toString(),
      reached,
    );
  }

  final double fraction;
  final String percent;
  final bool reachedTarget;
}

(BigInt, int) _decimal(String value) {
  if (!RegExp(r'^-?\d+(\.\d+)?$').hasMatch(value)) {
    throw const FormatException('Expected a contract decimal string');
  }
  final parts = value.split('.');
  return (BigInt.parse(parts.join()), parts.length == 1 ? 0 : parts[1].length);
}

/// Calendar-day geometry for the supplied range. Caller supplies today's date
/// in the presentation timezone; recurring budget periods are never inferred.
double? todayFraction(String startOn, String? endOn, DateTime? today) {
  if (endOn == null || today == null) return null;
  final start = DateTime.parse(startOn);
  final end = DateTime.parse(endOn);
  final day = DateTime.utc(today.year, today.month, today.day);
  final first = DateTime.utc(start.year, start.month, start.day);
  final last = DateTime.utc(end.year, end.month, end.day);
  if (day.isBefore(first) || day.isAfter(last) || last.isBefore(first)) {
    return null;
  }
  final days = last.difference(first).inDays;
  return days == 0 ? 0 : day.difference(first).inDays / days;
}
