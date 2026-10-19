// Derived from Cashew pages/editWalletsPage.dart (selectWalletPopup),
// widgets/radioItems.dart and widgets/openBottomSheet.dart.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-12 (T-515 piece 8):
// reusable typed account selection with API balances and Monetae theme tokens.
import 'package:flutter/material.dart';

import '../../data/api_dtos.dart';
import '../../l10n/app_localizations.dart';
import '../../presentation/account_color.dart';
import '../../presentation/currency_format.dart';
import '../../theme/monetae_theme.dart';
import 'form_sheet.dart';

typedef _T = TransactionFormTokens;

/// Returns the chosen account, closing only this route when sheets are stacked.
Future<AccountDto?> showAccountSelectionSheet(
  BuildContext context, {
  required List<AccountDto> accounts,
  required String? selectedId,
}) {
  final l = AppLocalizations.of(context);
  return showFormSheet<AccountDto>(
    context,
    key: const Key('account-sheet'),
    title: l.formAccountSheetTitle,
    expand: true,
    heightFraction: _T.accountSheetHeightFraction,
    trailing: IconButton(
      key: const Key('account-sheet-menu'),
      tooltip: l.formMenu,
      padding: EdgeInsets.zero,
      style: IconButton.styleFrom(
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      constraints: const BoxConstraints.tightFor(
        width: _T.sheetTitleSize,
        height: _T.sheetTitleSize,
      ),
      icon: const Icon(Icons.more_vert_rounded, size: _T.sheetTitleSize),
      // TODO(T-515): account management menu is presentation only.
      onPressed: () {},
    ),
    builder: (sheet) => AccountSelectionList(
      accounts: accounts,
      selectedId: selectedId,
      onSelected: (account) => Navigator.of(sheet).pop(account),
    ),
  );
}

/// Presentation only: account balances are exact strings supplied by the API.
class AccountSelectionList extends StatelessWidget {
  const AccountSelectionList({
    super.key,
    required this.accounts,
    required this.selectedId,
    required this.onSelected,
  });

  final List<AccountDto> accounts;
  final String? selectedId;
  final ValueChanged<AccountDto> onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    if (accounts.isEmpty) return Center(child: Text(l.emptyAccounts));
    return ListView.builder(
      key: const Key('account-sheet-list'),
      padding: const EdgeInsets.only(bottom: _T.sheetPadding),
      itemCount: accounts.length,
      itemBuilder: (context, index) {
        final account = accounts[index];
        final selected = account.id == selectedId;
        final color = accountColor(account.id, account.color);
        final balance =
            '${formatCurrency(account.balance, account.currency, l.localeName)} ${account.currency}';
        return Semantics(
          checked: selected,
          inMutuallyExclusiveGroup: true,
          child: Material(
            key: Key('account-sheet-row-${account.id}'),
            color: selected
                ? color.withValues(alpha: _T.accountSelectionOpacity)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(_T.accountRowRadius),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              key: Key('form-account-option-${account.id}'),
              onTap: () => onSelected(account),
              overlayColor: WidgetStateProperty.resolveWith(
                (states) =>
                    states.contains(WidgetState.hovered) ||
                        states.contains(WidgetState.pressed)
                    ? form.typeText.withValues(alpha: _T.accountHoverOpacity)
                    : Colors.transparent,
              ),
              child: ListTile(
                dense: true,
                minTileHeight: _T.accountRowHeight,
                contentPadding: const EdgeInsetsDirectional.only(
                  start: _T.accountRowPadding,
                  end: _T.accountRowEndPadding,
                ),
                leading: SizedBox.square(
                  dimension: _T.accountRadioTapSize,
                  child: Center(
                    child: Container(
                      key: Key('account-sheet-radio-${account.id}'),
                      width: _T.accountRadioSize,
                      height: _T.accountRadioSize,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: color,
                          width: _T.accountRadioBorder,
                        ),
                      ),
                      child: selected
                          ? Center(
                              child: Container(
                                width: _T.accountRadioFillSize,
                                height: _T.accountRadioFillSize,
                                decoration: BoxDecoration(
                                  color: color,
                                  shape: BoxShape.circle,
                                ),
                              ),
                            )
                          : null,
                    ),
                  ),
                ),
                title: Transform.translate(
                  offset: Offset(
                    Directionality.of(context) == TextDirection.rtl
                        ? _T.accountRowTitleOffset
                        : -_T.accountRowTitleOffset,
                    0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          account.name,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: _T.accountNameSize,
                            fontWeight: FontWeight.normal,
                            color: form.typeText,
                          ),
                        ),
                      ),
                      const SizedBox(width: _T.accountBalanceGap),
                      Flexible(
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: AlignmentDirectional.centerEnd,
                          child: Text(
                            balance,
                            key: Key('account-sheet-balance-${account.id}'),
                            maxLines: 3,
                            textAlign: TextAlign.end,
                            style: TextStyle(
                              fontSize: _T.accountBalanceSize,
                              fontWeight: FontWeight.normal,
                              color: form.typeText,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
