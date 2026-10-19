import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/currency_format.dart';
import 'budget_goal_lists.dart';
import 'color_picker.dart';

class HomeAccounts extends StatelessWidget {
  const HomeAccounts({
    super.key,
    required this.accounts,
    required this.selectedId,
    required this.onSelected,
    this.onCreate,
  });
  final List<AccountDto> accounts;
  final String? selectedId;
  final ValueChanged<String>? onSelected;
  final VoidCallback? onCreate;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 13.0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        clipBehavior: Clip.none,
        child: IntrinsicHeight(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final account in accounts)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: _WalletEntry(
                    account: account,
                    selected: account.id == selectedId,
                    onSelected: onSelected,
                  ),
                ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: SizedBox(
                  width: AccountFormTokens.accountAddWidth,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      minHeight: AccountFormTokens.accountMinHeight,
                    ),
                    child: HomeAddCard(
                      key: const Key('add-account-card'),
                      label: l.addAccountLabel,
                      onTap: onCreate,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WalletEntry extends StatelessWidget {
  const _WalletEntry({
    required this.account,
    required this.selected,
    required this.onSelected,
  });
  final AccountDto account;
  final bool selected;
  final ValueChanged<String>? onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final color = accountColor(account.id, account.color);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final double amount = double.tryParse(account.balance) ?? 0.0;
    Color amountColor = Theme.of(context).colorScheme.onSurface;
    if (amount > 0) {
      amountColor = isDark ? const Color(0xFF62CA77) : const Color(0xFF59A849);
    } else if (amount < 0) {
      amountColor = isDark ? const Color(0xFFDA7272) : const Color(0xFFCA5A5A);
    }

    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        key: Key('account-${account.id}'),
        color: Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(15),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onSelected == null ? null : () => onSelected!(account.id),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 450),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(15),
              border: Border.all(
                width: 2,
                color: selected
                    ? color.withValues(alpha: 0.7)
                    : Colors.transparent,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Positioned(
                    right: -11,
                    top: -5,
                    child: Container(
                      width: 20,
                      height: 20,
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.7),
                        borderRadius: BorderRadius.circular(100),
                      ),
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(right: 17),
                        child: Text(
                          account.name,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (amount != 0)
                            Icon(
                              amount > 0
                                  ? Icons.arrow_drop_up_rounded
                                  : Icons.arrow_drop_down_rounded,
                              color: amountColor,
                              size: 24,
                            ),
                          Text(
                            formatCurrency(
                              amount.toStringAsFixed(
                                2,
                              ), // We format with 2 decimals
                              account.currency,
                              l.localeName,
                            ),
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              color: amountColor,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        l.accountTransactionCount(account.transactionCount),
                        style: TextStyle(
                          fontSize: 14,
                          color: Theme.of(context).colorScheme.onSurface
                              .withValues(alpha: 0.65),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
