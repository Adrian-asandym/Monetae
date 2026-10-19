// Adapted from Cashew widgets/selectColor.dart (horizontal SelectColor).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-18: controlled selection
// with existing Monetae colors, accessible labels and no external plugins.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';

/// Measurements from Cashew addWalletPage.dart and selectColor.dart.
abstract final class AccountFormTokens {
  static const nameSize = 30.0;
  static const amountSize = 32.0;
  static const colorSize = 55.0;
  static const colorGap = 5.0;
  static const colorRowHeight = 65.0;
  static const colorBorder = 2.0;
  static const rowRadius = 13.0;
  static const sectionGap = 15.0;
  static const rowVerticalPadding = 10.0;
  static const accountAddWidth = 130.0;
  static const accountMinHeight = 100.0;
}

class AccountColorPicker extends StatelessWidget {
  const AccountColorPicker({
    super.key,
    required this.selected,
    required this.onSelected,
  });
  final Color selected;
  final ValueChanged<Color>? onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Semantics(
      label: l.accountColor,
      child: SizedBox(
        height: AccountFormTokens.colorRowHeight,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: [
            for (var i = 0; i < accountPalette.length; i++)
              Padding(
                padding: const EdgeInsets.all(AccountFormTokens.colorGap),
                child: Semantics(
                  button: true,
                  selected: selected == accountPalette[i],
                  label: l.accountColorOption(i + 1),
                  child: InkResponse(
                    key: Key('account-color-$i'),
                    onTap: onSelected == null
                        ? null
                        : () => onSelected!(accountPalette[i]),
                    child: Container(
                      width: AccountFormTokens.colorSize,
                      height: AccountFormTokens.colorSize,
                      decoration: BoxDecoration(
                        color: accountPalette[i],
                        shape: BoxShape.circle,
                        border: selected == accountPalette[i]
                            ? Border.all(
                                width: AccountFormTokens.colorBorder,
                                color: Theme.of(context).colorScheme.onSurface,
                              )
                            : null,
                      ),
                      child: selected == accountPalette[i]
                          ? Icon(
                              Icons.check_rounded,
                              color:
                                  ThemeData.estimateBrightnessForColor(
                                        accountPalette[i],
                                      ) ==
                                      Brightness.dark
                                  ? Colors.white
                                  : Colors.black,
                            )
                          : null,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
