// Derived from Cashew pages/homePage/{homePageWalletList,homePageWalletSwitcher}.dart
// and widgets/walletEntry.dart. Copyright James Kokoska, GPL-3.0.
// Modified 2026-10-10: API balances/counts, controlled default-account selection.
import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/currency_format.dart';
import '../theme/monetae_theme.dart';
import 'category_icon.dart';

class HomeAccounts extends StatelessWidget {
  const HomeAccounts({
    super.key,
    required this.accounts,
    required this.selectedId,
    required this.onSelected,
  });
  final List<AccountDto> accounts;
  final String? selectedId;
  final ValueChanged<String>? onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (accounts.isEmpty) return Text(l.emptyAccounts);
    return Column(
      children: [
        for (final account in accounts)
          Builder(
            builder: (context) {
              final color = accountColor(account.id, account.color);
              final selected = account.id == selectedId;
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Semantics(
                  selected: selected,
                  button: true,
                  child: Material(
                    key: Key('account-${account.id}'),
                    color: selected
                        ? pastel(color, Theme.of(context).brightness, .45)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(15),
                    child: ListTile(
                      selected: selected,
                      selectedColor: Theme.of(context).colorScheme.onSurface,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(15),
                      ),
                      onTap: onSelected == null
                          ? null
                          : () => onSelected!(account.id),
                      leading: CategoryIcon(
                        source: CategoryIconSource.resolve(account.icon),
                        color: color,
                      ),
                      title: Text(
                        account.name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        l.accountTransactionCount(account.transactionCount),
                      ),
                      trailing: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            formatCurrency(
                              account.balance,
                              account.currency,
                              l.localeName,
                            ),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          if (selected)
                            Text(
                              l.defaultAccount,
                              style: const TextStyle(fontSize: 10),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}
