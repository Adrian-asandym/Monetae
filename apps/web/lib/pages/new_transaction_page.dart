// Derived from Cashew pages/addTransactionPage.dart (form, SelectTitle,
// TransactionNotesTextInput) and widgets/util/showDatePicker.dart (date selection).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: API form with exact
// decimals, manual exchange rate, UTC/Lima dates and server error handling.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/new_transaction_controller.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_input.dart';
import '../session/session_controller.dart';
import '../theme/monetae_theme.dart';
import '../widgets/decimal_number_pad.dart';
import '../widgets/income_expense_selector.dart';
import '../widgets/transaction_category_grid.dart';

class NewTransactionPage extends StatefulWidget {
  const NewTransactionPage({super.key, required this.session, this.controller});
  final SessionController session;
  final NewTransactionController? controller;
  @override
  State<NewTransactionPage> createState() => _NewTransactionPageState();
}

class _NewTransactionPageState extends State<NewTransactionPage> {
  late final NewTransactionController _form;
  late final TextEditingController _amount;
  late final TextEditingController _rate;
  @override
  void initState() {
    super.initState();
    _form =
        widget.controller ??
        NewTransactionController(widget.session.api, widget.session.user!);
    _amount = TextEditingController(text: _form.amount);
    _rate = TextEditingController(text: _form.rate);
    _form.addListener(_changed);
    if (_form.loading) _form.load();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _form.removeListener(_changed);
    if (widget.controller == null) _form.dispose();
    _amount.dispose();
    _rate.dispose();
    super.dispose();
  }

  String? _fieldError(String name) {
    if (_form.fieldErrors[name] case final String message) return message;
    if (!_form.invalidFields.contains(name)) return null;
    final l = AppLocalizations.of(context);
    return switch (name) {
      'amount' => l.positiveAmountRequired,
      'account_id' => l.accountRequired,
      _ => l.positiveRateRequired,
    };
  }

  void _key(String key) {
    final old = _amount.value;
    final selection = old.selection.isValid
        ? old.selection
        : TextSelection.collapsed(offset: old.text.length);
    var start = selection.start;
    final end = selection.end;
    if (key == 'backspace' && start == end && start > 0) start--;
    final input = key == 'backspace' ? '' : key;
    final text = old.text.replaceRange(start, end, input);
    final next = const DecimalTextFormatter(2).formatEditUpdate(
      old,
      TextEditingValue(
        text: text,
        selection: TextSelection.collapsed(offset: start + input.length),
      ),
    );
    if (next.text != old.text) {
      _amount.value = next;
      _form.edit(() => _form.amount = next.text);
    }
  }

  Future<void> _save() async {
    final session = widget.session;
    FocusScope.of(context).unfocus();
    final saved = await _form.save();
    if (!saved || session.user?.id != _form.user.id) return;
    // A successful in-flight save still refreshes Home if the user went back.
    session.transactionCreated();
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    final message = AppLocalizations.of(context).transactionSaved;
    Navigator.of(context).popUntil((route) => route.isFirst);
    messenger.showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _pickDate() async {
    final current = _form.limaTime;
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime(current.year, current.month, current.day),
      firstDate: DateTime(1900),
      lastDate: DateTime(9999),
    );
    if (date != null && mounted) {
      _form.selectLimaTime(
        DateTime(date.year, date.month, date.day, current.hour, current.minute),
      );
    }
  }

  Future<void> _pickTime() async {
    final current = _form.limaTime;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: current.hour, minute: current.minute),
    );
    if (time != null && mounted) {
      _form.selectLimaTime(
        DateTime(
          current.year,
          current.month,
          current.day,
          time.hour,
          time.minute,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final selected = _form.account;
    final financialColor = _form.income ? colors.income : colors.expense;
    return Scaffold(
      appBar: AppBar(title: Text(l.addTransaction)),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(20, 8, 20, 12),
        child: Center(
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                key: const Key('save-transaction'),
                onPressed: _form.busy || _form.loading ? null : _save,
                icon: _form.busy
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.check_rounded),
                label: Text(
                  _form.busy ? l.savingTransaction : l.saveTransaction,
                ),
              ),
            ),
          ),
        ),
      ),
      body: _form.loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              key: const Key('transaction-form-scroll'),
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 560),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_form.error case final error?) ...[
                        Text(
                          error.message(l),
                          key: const Key('transaction-form-error'),
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                        TextButton(
                          key: const Key('retry-transaction'),
                          onPressed: _form.busy
                              ? null
                              : _form.accounts.isEmpty
                              ? _form.load
                              : _save,
                          child: Text(l.retry),
                        ),
                      ],
                      AbsorbPointer(
                        absorbing: _form.busy,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            IncomeExpenseSelector(
                              income: _form.income,
                              onChanged: _form.selectIncome,
                            ),
                            if (_fieldError('kind') case final String error)
                              Text(
                                error,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              ),
                            const SizedBox(height: 18),
                            TextField(
                              key: const Key('transaction-amount'),
                              readOnly: _form.busy,
                              controller: _amount,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                    decimal: true,
                                  ),
                              inputFormatters: const [DecimalTextFormatter(2)],
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 36,
                                color: financialColor,
                                fontWeight: FontWeight.w600,
                              ),
                              decoration: InputDecoration(
                                labelText: l.transactionAmount,
                                prefixText:
                                    '${currencySymbol(selected?.currency ?? _form.user.baseCurrency, l.localeName)} ',
                                errorText: _fieldError('amount'),
                              ),
                              onChanged: (text) =>
                                  _form.edit(() => _form.amount = text),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              formatCurrency(
                                _form.amount.isEmpty ? '0' : _form.amount,
                                selected?.currency ?? _form.user.baseCurrency,
                                l.localeName,
                              ),
                              key: const Key('form-formatted-amount'),
                              textAlign: TextAlign.center,
                              style: TextStyle(color: colors.muted),
                            ),
                            const SizedBox(height: 12),
                            DecimalNumberPad(
                              onKey: _key,
                              onClear: () {
                                _amount.clear();
                                _form.edit(() => _form.amount = '');
                              },
                            ),
                            const SizedBox(height: 18),
                            Text(
                              l.transactionCategory,
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            TransactionCategoryGrid(
                              categories: _form.visibleCategories,
                              selectedId: _form.categoryId,
                              onSelected: (id) =>
                                  _form.edit(() => _form.categoryId = id),
                            ),
                            if (_fieldError('category_id')
                                case final String error)
                              Text(
                                error,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              ),
                            const SizedBox(height: 12),
                            DropdownButtonFormField<String>(
                              key: ValueKey('form-account-${selected?.id}'),
                              initialValue: selected?.id,
                              isExpanded: true,
                              decoration: InputDecoration(
                                labelText: l.transactionAccount,
                                errorText:
                                    _fieldError('account_id') ??
                                    _fieldError('currency'),
                              ),
                              items: [
                                for (final a in _form.accounts)
                                  DropdownMenuItem(
                                    value: a.id,
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.account_balance_wallet_outlined,
                                          color: accountColor(a.id, a.color),
                                          size: 22,
                                        ),
                                        const SizedBox(width: 9),
                                        Expanded(
                                          child: Text(
                                            a.name,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                        Text(
                                          currencySymbol(
                                            a.currency,
                                            l.localeName,
                                          ),
                                          style: TextStyle(
                                            color: accountColor(a.id, a.color),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                              ],
                              onChanged: (id) {
                                if (id != null) {
                                  _rate.clear();
                                  _form.selectAccount(
                                    _form.accounts.firstWhere(
                                      (a) => a.id == id,
                                    ),
                                  );
                                }
                              },
                            ),
                            const SizedBox(height: 14),
                            TextFormField(
                              key: const Key('transaction-title'),
                              readOnly: _form.busy,
                              initialValue: _form.title,
                              decoration: InputDecoration(
                                labelText: l.transactionTitle,
                                prefixIcon: const Icon(Icons.title),
                                errorText: _fieldError('title'),
                              ),
                              onChanged: (text) =>
                                  _form.edit(() => _form.title = text),
                            ),
                            const SizedBox(height: 14),
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    key: const Key('transaction-date'),
                                    onPressed: _pickDate,
                                    icon: const Icon(
                                      Icons.calendar_month_outlined,
                                    ),
                                    label: Text(
                                      DateFormat.yMMMd(l.localeName)
                                          .format(_form.limaTime),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton.icon(
                                  key: const Key('transaction-time'),
                                  onPressed: _pickTime,
                                  icon: const Icon(Icons.schedule),
                                  label: Text(
                                    DateFormat.Hm(l.localeName)
                                        .format(_form.limaTime),
                                  ),
                                ),
                              ],
                            ),
                            if (_fieldError('occurred_at')
                                case final String error)
                              Text(
                                error,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              ),
                            Text(
                              l.limaTimezone,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 12,
                                color: colors.muted,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Chip(
                                key: const Key('transaction-status'),
                                avatar: Icon(
                                  _form.scheduled
                                      ? Icons.event_outlined
                                      : Icons.check_circle_outline,
                                  size: 18,
                                ),
                                label: Text(
                                  _form.scheduled
                                      ? l.transactionScheduled
                                      : l.transactionPosted,
                                ),
                              ),
                            ),
                            if (_fieldError('status') case final String error)
                              Text(
                                error,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              ),
                            const SizedBox(height: 10),
                            TextFormField(
                              key: const Key('transaction-note'),
                              readOnly: _form.busy,
                              initialValue: _form.note,
                              minLines: 1,
                              maxLines: 4,
                              decoration: InputDecoration(
                                labelText: l.transactionNote,
                                prefixIcon: const Icon(
                                  Icons.sticky_note_2_outlined,
                                ),
                                errorText: _fieldError('note'),
                              ),
                              onChanged: (text) =>
                                  _form.edit(() => _form.note = text),
                            ),
                            if (_form.needsRate) ...[
                              const SizedBox(height: 14),
                              TextField(
                                key: const Key('transaction-rate'),
                                readOnly: _form.busy,
                                controller: _rate,
                                keyboardType:
                                    const TextInputType.numberWithOptions(
                                      decimal: true,
                                    ),
                                inputFormatters: const [
                                  DecimalTextFormatter(6),
                                ],
                                decoration: InputDecoration(
                                  labelText: l.exchangeRate,
                                  helperText: l.manualRateHint(
                                    currencySymbol(
                                      selected!.currency,
                                      l.localeName,
                                    ),
                                    currencySymbol(
                                      _form.user.baseCurrency,
                                      l.localeName,
                                    ),
                                  ),
                                  errorText: _fieldError('fx_rate_to_base'),
                                ),
                                onChanged: (text) =>
                                    _form.edit(() => _form.rate = text),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
