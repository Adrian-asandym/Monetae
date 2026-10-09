import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/presentation/currency_format.dart';

void main() {
  for (final locale in ['es', 'en']) {
    for (final (currency, symbol) in [
      ('PEN', 'S/'),
      ('USD', r'US$'),
      ('EUR', '€'),
    ]) {
      test(
        '$locale $currency uses approved placement and exact decimal strings',
        () {
          final prefix = '$symbol${locale == 'es' ? ' ' : ''}';
          expect(
            formatCurrency('1234.50', currency, locale),
            '${prefix}1,234.50',
          );
          expect(formatCurrency('48.50', currency, locale), '${prefix}48.50');
          expect(formatCurrency('-48.50', currency, locale), '-${prefix}48.50');
          expect(
            formatCurrency('-1234.50', currency, locale),
            '-${prefix}1,234.50',
          );
          expect(
            formatCurrency('-48.50', currency, locale, absolute: true),
            '${prefix}48.50',
          );
          expect(formatCurrency('0.00', currency, locale), '${prefix}0.00');
          expect(formatCurrency('0', currency, locale), '${prefix}0.00');
          expect(formatCurrency('12.5', currency, locale), '${prefix}12.50');
        },
      );
    }
    test('$locale retains decimal digits beyond floating point precision', () {
      final prefix = locale == 'es' ? 'S/ ' : 'S/';
      expect(
        formatCurrency('12345678901234567890.01', 'PEN', locale),
        '${prefix}12,345,678,901,234,567,890.01',
      );
    });
  }
  test('Spanish regional locale still uses the approved Peru format', () {
    expect(formatCurrency('1234.50', 'USD', 'es_PE'), r'US$ 1,234.50');
  });
}
