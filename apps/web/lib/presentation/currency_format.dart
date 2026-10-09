import 'package:intl/intl.dart';

/// Intl supplies locale patterns, separators and symbols. Decimal strings are
/// grouped without parsing to floating point, rounding or changing their digits.
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
  final format = NumberFormat.currency(
    locale: locale,
    name: currency,
    symbol: currencySymbol(currency, locale),
  );
  final whole = digits.first.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => format.symbols.GROUP_SEP,
  );
  final fraction = digits.length == 1
      ? ''
      : '${format.symbols.DECIMAL_SEP}${digits[1]}';
  final prefix = negative ? format.negativePrefix : format.positivePrefix;
  final suffix = negative ? format.negativeSuffix : format.positiveSuffix;
  return '$prefix$whole$fraction$suffix';
}
