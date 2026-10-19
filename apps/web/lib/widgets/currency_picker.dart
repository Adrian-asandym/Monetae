// Adapted from Cashew pages/addWalletPage.dart, Copyright James Kokoska,
// GPL-3.0. Extracted from T-523 add_account_page.dart without visual changes.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';
import 'color_picker.dart';

// Explicit symbols in currency_format.dart, with the user's base currency first.
const accountCurrencies = [
  'PEN',
  'USD',
  'CAD',
  'AUD',
  'NZD',
  'HKD',
  'SGD',
  'MXN',
  'ARS',
  'CLP',
  'COP',
  'BSD',
  'FJD',
  'GYD',
  'KYD',
  'LRD',
  'SBD',
  'SRD',
  'BBD',
  'BMD',
  'BND',
  'BZD',
  'JMD',
  'NAD',
  'TTD',
  'XCD',
  'CVE',
  'SEK',
  'NOK',
  'DKK',
  'ISK',
  'GBP',
  'EGP',
  'FKP',
  'GIP',
  'SHP',
  'SSP',
  'CHF',
  'JPY',
  'CNY',
];

class CurrencyPicker extends StatelessWidget {
  const CurrencyPicker({
    super.key,
    required this.currencies,
    required this.selected,
    required this.onSelected,
    this.keyPrefix = 'account-currency',
  });
  final Iterable<String> currencies;
  final String selected;
  final ValueChanged<String> onSelected;
  final String keyPrefix;

  @override
  Widget build(BuildContext context) {
    final colors = TransactionFormColors.of(context);
    final l = AppLocalizations.of(context);
    return Column(
      children: [
        for (final currency in currencies)
          Padding(
            padding: const EdgeInsets.only(bottom: AccountFormTokens.colorGap),
            child: Material(
              color: currency == selected ? colors.chipSelected : colors.field,
              borderRadius: BorderRadius.circular(AccountFormTokens.rowRadius),
              child: ListTile(
                key: Key('$keyPrefix-$currency'),
                selected: currency == selected,
                textColor: Theme.of(context).colorScheme.onSurface,
                selectedColor: Theme.of(context).colorScheme.onSurface,
                title: Text(currency),
                trailing: Text(currencySymbol(currency, l.localeName)),
                onTap: () => onSelected(currency),
              ),
            ),
          ),
      ],
    );
  }
}
