// Adapted from Cashew pages/addWalletPage.dart (name, colors, starting balance,
// currency picker and fixed save action), Copyright James Kokoska, GPL-3.0.
// Modified 2026-10-18: typed API, i18n, exact decimals and currency precision.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../data/account_create_dto.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/currency_format.dart';
import '../presentation/exact_decimal.dart';
import '../theme/monetae_theme.dart';
import '../widgets/color_picker.dart';
import '../widgets/currency_picker.dart';
import '../widgets/account_balance_sheet.dart';
import '../widgets/transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;
typedef _A = AccountFormTokens;

class AddAccountPage extends StatefulWidget {
  const AddAccountPage({
    super.key,
    required this.api,
    required this.baseCurrency,
  });
  final ApiClient api;
  final String baseCurrency;
  @override
  State<AddAccountPage> createState() => _AddAccountPageState();
}

class _AddAccountPageState extends State<AddAccountPage> {
  final _name = TextEditingController();
  late String _currency = widget.baseCurrency;
  Color _color = accountPalette.first;
  String _balance = '0';
  bool _busy = false;
  ApiException? _error;
  int get _decimals => NumberFormat.currency(name: _currency).decimalDigits!;
  bool get _validName => _name.text.trim().isNotEmpty;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_busy || !_validName) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.createAccount(
        AccountCreateDto(
          name: _name.text.trim(),
          currency: _currency,
          initialBalance: ExactDecimal.parse(_balance).fixed(2),
          color:
              '#${_color.toARGB32().toRadixString(16).substring(2).toUpperCase()}',
        ),
      );
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editBalance() async {
    FocusScope.of(context).unfocus();
    final chosen = await showFormSheet<String>(
      context,
      key: const Key('account-amount-sheet'),
      title: AppLocalizations.of(context).formEnterAmount,
      bottomPadding: _T.sheetPadding,
      builder: (_) => AccountBalanceSheet(
        initialBalance: _balance,
        currency: _currency,
        decimals: _decimals,
      ),
    );
    if (mounted && chosen != null) setState(() => _balance = chosen);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final currencies = {widget.baseCurrency, ...accountCurrencies};
    final error = _error;
    return PopScope(
      canPop: !_busy,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.addAccount),
          backgroundColor: Theme.of(context).scaffoldBackgroundColor,
          surfaceTintColor: Colors.transparent,
          leading: BackButton(
            onPressed: _busy ? null : () => Navigator.of(context).pop(),
          ),
        ),
        body: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: _T.maxWidth),
            child: AbsorbPointer(
              key: const Key('account-fields'),
              absorbing: _busy,
              child: ListView(
                padding: const EdgeInsets.all(_T.sidePadding),
                children: [
                  TextField(
                    key: const Key('account-name'),
                    controller: _name,
                    maxLength: 120,
                    textCapitalization: TextCapitalization.sentences,
                    style: const TextStyle(
                      fontSize: _A.nameSize,
                      fontWeight: FontWeight.bold,
                    ),
                    decoration: InputDecoration(
                      hintText: l.accountName,
                      counterText: '',
                      border: InputBorder.none,
                      errorText: _name.text.isNotEmpty && !_validName
                          ? l.accountNameRequired
                          : null,
                    ),
                    onChanged: (_) => setState(() => _error = null),
                  ),
                  const SizedBox(height: _A.sectionGap),
                  AccountColorPicker(
                    selected: _color,
                    onSelected: (color) => setState(() => _color = color),
                  ),
                  const SizedBox(height: _A.sectionGap),
                  InkWell(
                    key: const Key('account-initial-balance'),
                    borderRadius: BorderRadius.circular(_A.rowRadius),
                    onTap: _editBalance,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: _A.rowVerticalPadding,
                      ),
                      child: Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            '${l.accountStartingAt} ',
                            style: const TextStyle(
                              fontSize: _T.actionFontSize,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            formatCurrency(_balance, _currency, l.localeName),
                            key: const Key('account-balance-value'),
                            style: const TextStyle(
                              fontSize: _A.amountSize,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: _A.sectionGap),
                  Text(
                    l.accountCurrency,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: _A.sectionGap),
                  CurrencyPicker(
                    currencies: currencies,
                    selected: _currency,
                    onSelected: (currency) => setState(() {
                      _currency = currency;
                      _balance = ExactDecimal.parse(_balance).fixed(_decimals);
                    }),
                  ),
                ],
              ),
            ),
          ),
        ),
        bottomNavigationBar: SafeArea(
          minimum: const EdgeInsets.all(_T.sidePadding),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: _A.sectionGap),
                  child: Text(
                    error.kind == ApiErrorKind.conflict
                        ? l.accountDuplicateName
                        : error.message(l),
                    key: const Key('account-save-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              FormSheetButton(
                key: const Key('account-save'),
                height: _T.actionHeight,
                label: _busy ? l.savingTransaction : l.addAccount,
                onPressed: !_validName || _busy ? null : _save,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
