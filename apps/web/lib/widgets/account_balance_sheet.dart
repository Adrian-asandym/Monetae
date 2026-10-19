// Adapted from Monetae's transaction amount sheet and Cashew SelectAmount.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-18: zero/negative balances,
// currency precision and exact text editing; shared sheet and keypad widgets.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/app_localizations.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_input.dart';
import '../presentation/exact_decimal.dart';
import '../theme/monetae_theme.dart';
import 'decimal_number_pad.dart';
import 'transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;

class AccountBalanceSheet extends StatefulWidget {
  const AccountBalanceSheet({
    super.key,
    required this.initialBalance,
    required this.currency,
    required this.decimals,
    this.positiveOnly = false,
    this.amountLabel,
  });
  final String initialBalance;
  final String currency;
  final int decimals;
  final bool positiveOnly;
  final String? amountLabel;
  @override
  State<AccountBalanceSheet> createState() => _AccountBalanceSheetState();
}

class _AccountBalanceSheetState extends State<AccountBalanceSheet> {
  late final _amount = TextEditingController(
    text: widget.initialBalance.replaceFirst('-', ''),
  );
  late bool _negative = widget.initialBalance.startsWith('-');
  bool get _valid =>
      RegExp('^[0-9]{1,16}(\\.[0-9]{0,${widget.decimals}})?\$')
          .hasMatch(_amount.text) &&
      (!widget.positiveOnly ||
          ExactDecimal.parse(_amount.text).numerator > BigInt.zero);
  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  void _key(String key) {
    final old = _amount.value;
    final text = key == 'backspace'
        ? (old.text.isEmpty ? '' : old.text.substring(0, old.text.length - 1))
        : (old.text == '0' && key != '.' ? key : old.text + key);
    final next = DecimalTextFormatter(widget.decimals).formatEditUpdate(
      old,
      TextEditingValue(
        text: text,
        selection: TextSelection.collapsed(offset: text.length),
      ),
    );
    if (next.text.split('.').first.length <= 16) {
      setState(() => _amount.value = next);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerRight,
          child: Text(
            formatTypedAmount(
              '${_negative ? '-' : ''}${_amount.text}',
              widget.currency,
              l.localeName,
            ),
            key: const Key('account-amount-preview'),
            style: const TextStyle(
              fontSize: _T.amountSheetFontSize,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        TextField(
          key: const Key('account-amount-input'),
          controller: _amount,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            DecimalTextFormatter(widget.decimals),
            LengthLimitingTextInputFormatter(19),
          ],
          decoration: InputDecoration(
            labelText:
                widget.amountLabel ??
                (widget.positiveOnly
                    ? l.goalTargetAmount
                    : l.accountStartingAt),
            errorText: _valid
                ? null
                : widget.positiveOnly
                ? l.goalAmountRequired
                : l.accountBalanceInvalid,
          ),
          onChanged: (_) => setState(() {}),
          onSubmitted: (_) {
            if (_valid) _done();
          },
        ),
        if (!widget.positiveOnly)
          SwitchListTile.adaptive(
            key: const Key('account-negative-balance'),
            contentPadding: EdgeInsets.zero,
            title: Text(l.accountNegativeBalance),
            value: _negative,
            onChanged: (value) => setState(() => _negative = value),
          ),
        const SizedBox(height: _T.amountSheetGap),
        DecimalNumberPad(
          onKey: _key,
          onClear: () => setState(() => _amount.text = '0'),
        ),
        const SizedBox(height: _T.amountSheetActionGap),
        FormSheetButton(
          key: const Key('account-amount-done'),
          height: _T.amountSheetButtonHeight,
          label: l.formSetAmount,
          onPressed: _valid ? _done : null,
        ),
      ],
    );
  }

  void _done() => Navigator.of(context).pop(
    ExactDecimal.parse('${_negative ? '-' : ''}${_amount.text}')
        .fixed(widget.decimals),
  );
}
