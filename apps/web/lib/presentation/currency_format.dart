import 'package:intl/intl.dart';

String currencySymbol(String currency, String locale) {
  final simple = NumberFormat.simpleCurrency(
    locale: locale,
    name: currency,
  ).currencySymbol;
  return switch (currency) {
    'PEN' => 'S/.', // Changed to S/. to match Cashew
    'USD' => r'$', // In Cashew, USD usually shows as $
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
  
  final spanish = locale.split(RegExp('[-_]')).first == 'es';
  
  // Cashew formatting rules for Spanish
  final groupSep = spanish ? '.' : ',';
  final decimalSep = spanish ? ',' : '.';
  
  final whole = digits.first.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => groupSep,
  );
  
  final fractionDigits = digits.length == 1 ? '00' : digits[1].padRight(2, '0');
  
  // Hide decimals if they are zero
  final hasDecimals = fractionDigits != '00';
  final fraction = hasDecimals ? '$decimalSep$fractionDigits' : '';
  
  if (spanish) return '${negative ? '-' : ''}$whole$fraction $symbol';
  
  return '${negative ? '-' : ''}$symbol$whole$fraction';
}
