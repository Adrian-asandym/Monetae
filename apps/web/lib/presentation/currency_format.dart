import 'package:intl/intl.dart';

/// Intl supplies symbols and the en_US pattern. Spanish uses Monetae's
/// approved Peru presentation: symbol, space, comma grouping and decimal point.
/// Contract decimal strings are formatted without floating-point parsing or rounding.
String currencySymbol(String currency, String locale) {
  final simple = NumberFormat.simpleCurrency(
    locale: locale,
    name: currency,
  ).currencySymbol;
  // Intl's simple symbols intentionally share '$' and '¥'. Always qualify these
  // families, so adding a second currency never changes existing labels.
  return switch (currency) {
    'PEN' => 'S/',
    'USD' => r'US$',
    'CAD' => r'CA$',
    'AUD' => r'A$',
    'NZD' => r'NZ$',
    'HKD' => r'HK$',
    'SGD' => r'S$',
    'MXN' => r'MX$',
    'ARS' => r'AR$',
    'CLP' => r'CL$',
    'COP' => r'CO$',
    'BSD' => r'BS$',
    'FJD' => r'FJ$',
    'GYD' => r'GY$',
    'KYD' => r'CI$',
    'LRD' => r'LR$',
    'SBD' => r'SI$',
    'SRD' => r'SR$',
    'BBD' => r'BB$',
    'BMD' => r'BM$',
    'BND' => r'BN$',
    'BZD' => r'BZ$',
    'JMD' => r'JM$',
    'NAD' => r'NA$',
    'TTD' => r'TT$',
    'XCD' => r'EC$',
    'CVE' => r'CV$',
    'SEK' => 'SEkr',
    'NOK' => 'NOkr',
    'DKK' => 'DKkr',
    'ISK' => 'ISkr',
    'GBP' => '£',
    'EGP' => 'EG£',
    'FKP' => 'FK£',
    'GIP' => 'GI£',
    'SHP' => 'SH£',
    'SSP' => 'SS£',
    'CHF' => 'CHFr',
    'JPY' => 'JP¥',
    'CNY' => 'CN¥',
    // For currencies without an Intl symbol, use the generic currency sign,
    // never expose an ISO code as a label.
    _ => simple == currency ? '¤' : simple,
  };
}

String formatCurrency(
  String amount,
  String currency,
  String locale, {
  bool absolute = false,
}) {
  final negative = amount.startsWith('-') && !absolute;
  final digits = amount.replaceFirst(RegExp(r'^[-+]'), '').split('.');
  final symbol = currencySymbol(currency, locale);
  // Intl's es/es_PE pattern uses a decimal comma and trailing symbol. The
  // product's Spanish format is explicitly Peruvian, including for EUR/USD.
  final spanish = locale.split(RegExp('[-_]')).first == 'es';
  final format = NumberFormat.currency(
    locale: 'en_US',
    name: currency,
    symbol: symbol,
    decimalDigits: 2,
  );
  final whole = digits.first.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => format.symbols.GROUP_SEP,
  );
  final fractionDigits = digits.length == 1 ? '00' : digits[1].padRight(2, '0');
  final fraction = '${format.symbols.DECIMAL_SEP}$fractionDigits';
  if (spanish) return '${negative ? '-' : ''}$symbol $whole$fraction';
  final prefix = negative ? format.negativePrefix : format.positivePrefix;
  final suffix = negative ? format.negativeSuffix : format.positiveSuffix;
  return '$prefix$whole$fraction$suffix';
}
