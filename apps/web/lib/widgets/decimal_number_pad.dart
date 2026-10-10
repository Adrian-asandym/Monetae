// Derived from Cashew widgets/selectAmount.dart (NumberPad, CalculatorButton).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: exact text editing,
// native focus/semantics and a fixed two-decimal keypad without a calculator.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

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
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: Material(
        color: Theme.of(context).colorScheme.secondaryContainer
            .withValues(alpha: .5),
        child: Column(
          children: [
            for (final row in const [
              ['1', '2', '3'],
              ['4', '5', '6'],
              ['7', '8', '9'],
              ['.', '0', 'backspace'],
            ])
              Row(
                textDirection: TextDirection.ltr,
                children: [
                  for (final key in row)
                    Expanded(
                      child: InkWell(
                        key: Key('amount-key-$key'),
                        onTap: () => onKey(key),
                        onLongPress: key == 'backspace' ? onClear : null,
                        child: SizedBox(
                          height: 48,
                          child: Center(
                            child: key == 'backspace'
                                ? Icon(
                                    Icons.backspace_outlined,
                                    semanticLabel: l.deleteDigit,
                                  )
                                : Semantics(
                                    label: key == '.' ? l.decimalPoint : key,
                                    child: Text(
                                      key,
                                      style: const TextStyle(fontSize: 23),
                                    ),
                                  ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
