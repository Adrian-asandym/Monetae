// Derived from Cashew widgets/selectAmount.dart (NumberPad, CalculatorButton).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: exact text editing,
// native focus/semantics and a fixed two-decimal keypad without a calculator.
// Modified 2026-10-11 (T-515 piece 4): four-column Cashew keypad, comma key,
// inactive calculator operators and theme tokens.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

typedef _T = TransactionFormTokens;

class DecimalNumberPad extends StatelessWidget {
  const DecimalNumberPad({
    super.key,
    required this.onKey,
    required this.onClear,
  });
  final ValueChanged<String> onKey;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    String label(String key) => switch (key) {
      '.' => l.decimalPoint,
      'backspace' => l.deleteDigit,
      'divide' => l.formDivide,
      'multiply' => l.formMultiply,
      'subtract' => l.formSubtract,
      'add' => l.formAdd,
      _ => key,
    };
    String symbol(String key) => switch (key) {
      '.' => ',',
      'divide' => '÷',
      'multiply' => '×',
      'subtract' => '-',
      'add' => '+',
      _ => key,
    };
    Widget button(String key) {
      final operator = const {
        'divide',
        'multiply',
        'subtract',
        'add',
      }.contains(key);
      return Semantics(
        label: label(key),
        button: true,
        enabled: !operator,
        child: InkWell(
          key: Key('amount-key-$key'),
          excludeFromSemantics: true,
          canRequestFocus: !operator,
          // TODO(T-515): calculator operators are design only.
          onTap: operator ? () {} : () => onKey(key),
          onLongPress: key == 'backspace' ? onClear : null,
          child: ExcludeSemantics(
            child: SizedBox(
              height: _T.keypadRowHeight,
              child: Center(
                child: key == 'backspace'
                    ? const Icon(
                        Icons.backspace_outlined,
                        size: _T.keypadBackspaceSize,
                      )
                    : Text(
                        symbol(key),
                        style: const TextStyle(fontSize: _T.keypadFontSize),
                      ),
              ),
            ),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(_T.keypadRadius),
      child: Material(
        color: form.keypad,
        child: Padding(
          padding: const EdgeInsets.all(_T.keypadPadding),
          child: Column(
            children: [
              for (final row in const [
                ['1', '2', '3', 'divide'],
                ['4', '5', '6', 'multiply'],
                ['7', '8', '9', 'subtract'],
                ['.', '0', 'backspace', 'add'],
              ])
                Row(
                  textDirection: TextDirection.ltr,
                  children: [
                    for (final key in row) Expanded(child: button(key)),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
