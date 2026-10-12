/// Exact rational arithmetic for transfer previews. Only wire amounts and rates
/// are rounded (half up); intermediate ratios never use floating point.
final class ExactDecimal {
  ExactDecimal(this.numerator, this.denominator)
    : assert(denominator > BigInt.zero);
  factory ExactDecimal.parse(String text) {
    final parts = text.split('.');
    final decimals = parts.length == 1 ? '' : parts[1];
    return ExactDecimal(
      BigInt.parse('${parts[0]}$decimals'),
      BigInt.from(10).pow(decimals.length),
    );
  }
  final BigInt numerator;
  final BigInt denominator;
  ExactDecimal operator +(ExactDecimal other) => ExactDecimal(
    numerator * other.denominator + other.numerator * denominator,
    denominator * other.denominator,
  );
  ExactDecimal operator -(ExactDecimal other) => ExactDecimal(
    numerator * other.denominator - other.numerator * denominator,
    denominator * other.denominator,
  );
  ExactDecimal operator *(ExactDecimal other) => ExactDecimal(
    numerator * other.numerator,
    denominator * other.denominator,
  );
  ExactDecimal operator /(ExactDecimal other) => ExactDecimal(
    numerator * other.denominator,
    denominator * other.numerator,
  );
  String fixed(int decimals) {
    final scaled = numerator.abs() * BigInt.from(10).pow(decimals);
    var rounded = scaled ~/ denominator;
    if (scaled.remainder(denominator) * BigInt.two >= denominator) {
      rounded += BigInt.one;
    }
    final digits = rounded.toString().padLeft(decimals + 1, '0');
    final sign = numerator.isNegative && rounded != BigInt.zero ? '-' : '';
    if (decimals == 0) return '$sign$digits';
    final split = digits.length - decimals;
    return '$sign${digits.substring(0, split)}.${digits.substring(split)}';
  }
}
