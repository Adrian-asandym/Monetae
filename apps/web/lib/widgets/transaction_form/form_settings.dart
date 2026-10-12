import 'package:flutter/foundation.dart';

/// Shared presentation preferences survive closing and reopening the form.
class TransactionFormSettings extends ChangeNotifier {
  // TODO(T-515): persist when browser-local preferences are available.
  static final shared = TransactionFormSettings();

  bool _showTransfer = true;
  bool _showAttachment = true;

  bool get showTransfer => _showTransfer;
  bool get showAttachment => _showAttachment;

  set showTransfer(bool value) {
    if (value == _showTransfer) return;
    _showTransfer = value;
    notifyListeners();
  }

  set showAttachment(bool value) {
    if (value == _showAttachment) return;
    _showAttachment = value;
    notifyListeners();
  }
}
