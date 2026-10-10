import 'package:flutter/services.dart';

/// A decimal editing buffer, never parsed as a floating-point number.
class DecimalTextFormatter extends TextInputFormatter {
  const DecimalTextFormatter(this.decimals);
  final int decimals;

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final text = newValue.text.replaceAll(',', '.');
    if (!RegExp('^([0-9]+)?(\\.[0-9]{0,$decimals})?\$').hasMatch(text)) {
      return oldValue;
    }
    return newValue.copyWith(
      text: text.startsWith('.') ? '0$text' : text,
      selection: text.startsWith('.')
          ? TextSelection.collapsed(offset: newValue.selection.end + 1)
          : newValue.selection,
    );
  }
}

bool positiveDecimal(String text, int decimals) =>
    RegExp('^[0-9]+(\\.[0-9]{0,$decimals})?\$').hasMatch(text) &&
    RegExp('[1-9]').hasMatch(text);

String amountWireText(String text) => decimalWireText(text, 2);

String decimalWireText(String text, int decimals) {
  final parts = text.split('.');
  final whole = parts.first.replaceFirst(RegExp(r'^0+(?=[0-9])'), '');
  return '$whole.${(parts.length == 1 ? '' : parts[1]).padRight(decimals, '0')}';
}
