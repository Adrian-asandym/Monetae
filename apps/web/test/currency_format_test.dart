import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/presentation/currency_format.dart';

void main() {
  for (final locale in ['es', 'en']) {
    for (final (currency, symbol) in [
      ('PEN', 'S/.'),
      ('USD', r'$'),
      ('EUR', '€'),
    ]) {
      test(
        '$locale $currency uses Cashew-style formatting',
        () {
          if (locale == 'es') {
            expect(formatCurrency('1234.50', currency, locale), '1.234,50 $symbol');
            expect(formatCurrency('48.50', currency, locale), '48,50 $symbol');
            expect(formatCurrency('-48.50', currency, locale), '-48,50 $symbol');
            expect(formatCurrency('-1234.50', currency, locale), '-1.234,50 $symbol');
            expect(formatCurrency('-48.50', currency, locale, absolute: true), '48,50 $symbol');
            expect(formatCurrency('0.00', currency, locale), '0 $symbol');
            expect(formatCurrency('0', currency, locale), '0 $symbol');
            expect(formatCurrency('12.5', currency, locale), '12,50 $symbol');
          } else {
            expect(formatCurrency('1234.50', currency, locale), '$symbol${'1,234.50'}');
            expect(formatCurrency('48.50', currency, locale), '$symbol${'48.50'}');
            expect(formatCurrency('-48.50', currency, locale), '-$symbol${'48.50'}');
            expect(formatCurrency('-1234.50', currency, locale), '-$symbol${'1,234.50'}');
            expect(formatCurrency('-48.50', currency, locale, absolute: true), '$symbol${'48.50'}');
            expect(formatCurrency('0.00', currency, locale), '$symbol${'0'}');
            expect(formatCurrency('0', currency, locale), '$symbol${'0'}');
            expect(formatCurrency('12.5', currency, locale), '$symbol${'12.50'}');
          }
        },
      );
    }
    test('$locale retains decimal digits beyond floating point precision', () {
      if (locale == 'es') {
        expect(
          formatCurrency('12345678901234567890.01', 'PEN', locale),
          '12.345.678.901.234.567.890,01 S/.',
        );
      } else {
        expect(
          formatCurrency('12345678901234567890.01', 'PEN', locale),
          'S/.12,345,678,901,234,567,890.01',
        );
      }
    });
  }
  test('Spanish regional locale works too', () {
    expect(formatCurrency('1234.50', 'USD', 'es_PE'), r'1.234,50 $');
  });
}
