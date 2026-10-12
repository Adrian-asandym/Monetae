// Derived from Cashew pages/addWalletPage.dart:1022 (TransferBalancePopup)
// and pages/addTransactionPage.dart:1002 (entry point).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-12 (T-519 piece 10).
// That local reference predates captures 24–25: cards, dialog, clear and swap
// follow those captures and the coordinator's explicit clarification instead.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../api/transfer_balance_controller.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_input.dart';
import '../session/session_controller.dart';
import '../theme/monetae_theme.dart';
import '../widgets/decimal_number_pad.dart';
import '../widgets/transaction_form/account_selection_sheet.dart';
import '../widgets/transaction_form/form_controls.dart';
import '../widgets/transaction_form/exchange_rate_sheet.dart';
import '../widgets/transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;

class TransferBalancePage extends StatefulWidget {
  const TransferBalancePage({
    super.key,
    required this.session,
    required this.controller,
  });
  final SessionController session;
  final TransferBalanceController controller;
  @override
  State<TransferBalancePage> createState() => _TransferBalancePageState();
}

class _TransferBalancePageState extends State<TransferBalancePage> {
  TransferBalanceController get form => widget.controller;
  final _fromBaseRate = TextEditingController();
  final _toBaseRate = TextEditingController();
  @override
  void initState() {
    super.initState();
    _fromBaseRate.text = form.fromManualRate;
    _toBaseRate.text = form.toManualRate;
    form.addListener(_changed);
    unawaited(form.loadSuggestion());
  }

  void _changed() {
    if (!mounted) return;
    if (_fromBaseRate.text != form.fromManualRate) {
      _fromBaseRate.text = form.fromManualRate;
    }
    if (_toBaseRate.text != form.toManualRate) {
      _toBaseRate.text = form.toManualRate;
    }
    setState(() {});
  }

  @override
  void dispose() {
    form.removeListener(_changed);
    _fromBaseRate.dispose();
    _toBaseRate.dispose();
    // The caller owns the controller until any in-flight save completes.
    super.dispose();
  }

  String? _error(String field) =>
      form.fieldErrors[field] ??
      (form.invalidFields.contains(field)
          ? AppLocalizations.of(context).requestInvalid
          : null);
  Widget _fieldError(String field) {
    final text = _error(field);
    return text == null
        ? const SizedBox.shrink()
        : Text(
            text,
            key: Key('transfer-error-$field'),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          );
  }

  Future<void> _rateSheet() async {
    if (form.busy ||
        form.sameCurrency ||
        form.from == null ||
        form.to == null) {
      return;
    }
    await showExchangeRateSheet(context, form);
  }

  Future<void> _accounts(bool outgoing) async {
    if (form.busy) return;
    final other = outgoing ? form.to : form.from;
    final selected = await showAccountSelectionSheet(
      context,
      accounts: form.accounts.where((a) => a.id != other?.id).toList(),
      selectedId: (outgoing ? form.from : form.to)?.id,
    );
    if (mounted && selected != null) {
      form.selectAccount(selected, outgoing: outgoing);
    }
  }

  Future<void> _amount(bool outgoing) async {
    if (form.busy) return;
    final l = AppLocalizations.of(context);
    String value() => outgoing ? form.fromAmount : form.toAmount;
    void set(String text) =>
        outgoing ? form.setFromAmount(text) : form.setToAmount(text);
    void key(String key) {
      final old = value();
      final next = key == 'backspace'
          ? old.isEmpty
                ? ''
                : old.substring(0, old.length - 1)
          : old + key;
      set(
        const DecimalTextFormatter(2)
            .formatEditUpdate(
              TextEditingValue(text: old),
              TextEditingValue(
                text: next,
                selection: TextSelection.collapsed(offset: next.length),
              ),
            )
            .text,
      );
    }

    await showFormSheet<void>(
      context,
      key: const Key('transfer-amount-sheet'),
      title: l.formEnterAmount,
      builder: (sheet) => Focus(
        autofocus: true,
        onKeyEvent: (_, event) {
          if ((event is! KeyDownEvent && event is! KeyRepeatEvent) ||
              ModalRoute.of(sheet)?.isCurrent != true ||
              HardwareKeyboard.instance.isControlPressed ||
              HardwareKeyboard.instance.isMetaPressed ||
              HardwareKeyboard.instance.isAltPressed) {
            return KeyEventResult.ignored;
          }
          if (event.logicalKey == LogicalKeyboardKey.enter ||
              event.logicalKey == LogicalKeyboardKey.numpadEnter) {
            Navigator.pop(sheet);
            return KeyEventResult.handled;
          }
          if (event.logicalKey == LogicalKeyboardKey.backspace) {
            key('backspace');
            return KeyEventResult.handled;
          }
          final text = event.character ?? event.logicalKey.keyLabel;
          if (RegExp(r'^[0-9]$').hasMatch(text)) {
            key(text);
            return KeyEventResult.handled;
          }
          if (text == '.' || text == ',') {
            key('.');
            return KeyEventResult.handled;
          }
          return KeyEventResult.ignored;
        },
        child: ListenableBuilder(
          listenable: form,
          builder: (_, _) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerRight,
                child: Text(
                  formatTypedAmount(
                    value(),
                    (outgoing ? form.from : form.to)?.currency ??
                        form.user.baseCurrency,
                    l.localeName,
                  ),
                  key: const Key('transfer-amount-value'),
                  style: const TextStyle(
                    fontSize: _T.amountSheetFontSize,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: _T.amountSheetGap),
              Align(
                alignment: Alignment.centerLeft,
                child: FormSquareButton(
                  icon: Icons.keyboard_arrow_down_rounded,
                  tooltip: l.formAccountSheetTitle,
                  onTap: () => _accounts(outgoing),
                ),
              ),
              const SizedBox(height: _T.amountSheetGap),
              DecimalNumberPad(onKey: key, onClear: () => set('')),
              const SizedBox(height: _T.amountSheetActionGap),
              FormSheetButton(
                key: const Key('transfer-amount-done'),
                height: _T.amountSheetButtonHeight,
                label: l.formSetAmount,
                onPressed: () => Navigator.pop(sheet),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _date({bool arrival = false, bool timeOnly = false}) async {
    if (form.busy) return;
    final current = arrival ? form.arrivalTime : form.limaTime;
    final minimum = arrival ? form.limaTime : DateTime(1900);
    final date = timeOnly
        ? current
        : await showDatePicker(
            context: context,
            initialDate: current.isBefore(minimum) ? minimum : current,
            firstDate: DateTime(minimum.year, minimum.month, minimum.day),
            lastDate: DateTime(9999),
          );
    if (date == null || !mounted) return;
    final time = (arrival || timeOnly)
        ? await showTimePicker(
            context: context,
            initialTime: TimeOfDay.fromDateTime(current),
          )
        : TimeOfDay.fromDateTime(current);
    if (time == null || !mounted) return;
    final utc = DateTime.utc(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    ).add(const Duration(hours: 5));
    if (arrival) {
      form.setArrival(utc);
    } else {
      form.setDeparture(utc);
    }
  }

  Future<void> _save() async {
    final session = widget.session;
    final userId = form.user.id;
    final l = AppLocalizations.of(context);
    FocusScope.of(context).unfocus();
    final saved = await form.save(defaultTitle: l.transferBalanceTitle);
    if (!saved || session.user?.id != userId) return;
    session.transactionCreated();
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    Navigator.of(context).popUntil((route) => route.isFirst);
    messenger.showSnackBar(SnackBar(content: Text(l.transactionSaved)));
  }

  Future<void> _info() => showDialog<void>(
    context: context,
    builder: (dialog) {
      final l = AppLocalizations.of(dialog);
      final c = TransactionFormColors.of(dialog);
      return Dialog(
        key: const Key('transfer-info-dialog'),
        backgroundColor: c.transferDialog,
        insetPadding: const EdgeInsets.all(_T.transferDialogInset),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(_T.transferDialogRadius),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(_T.transferDialogPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.swap_horiz_rounded,
                size: _T.transferDialogIconSize,
                color: c.switchThumb,
              ),
              const SizedBox(height: _T.transferDialogIconGap),
              Text(
                l.transferBalanceTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: _T.transferDialogTitleSize,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: _T.transferDialogTextGap),
              Text(
                l.transferBalanceInfo,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: _T.transferDialogBodySize,
                  height: _T.transferDialogLineHeight,
                ),
              ),
              const SizedBox(height: _T.transferDialogActionTop),
              FormSheetButton(
                label: l.transferOk,
                height: _T.transferDialogButtonHeight,
                onPressed: () => Navigator.pop(dialog),
              ),
              const SizedBox(height: _T.transferDialogButtonGap),
              FormSheetButton(
                label: l.transferCorrectionCategory,
                height: _T.transferDialogButtonHeight,
                color: c.action,
                // TODO(T-519): TransactionsPage has no category filter yet.
                // Local Cashew predates this button; follows captures + clarification.
                onPressed: () {},
              ),
            ],
          ),
        ),
      );
    },
  );

  Widget _card(bool outgoing) {
    final l = AppLocalizations.of(context);
    final c = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    final account = outgoing ? form.from : form.to;
    final amount = outgoing ? form.fromAmount : form.toAmount;
    String money(String value) => formatCurrency(
      value.isEmpty ? '0' : value,
      account?.currency ?? form.user.baseCurrency,
      l.localeName,
    );
    final tone = outgoing ? colors.expense : colors.income;
    return Material(
      color: c.transferCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(_T.transferCardRadius),
        side: BorderSide(
          width: _T.transferBorder,
          color: account == null
              ? colors.muted
              : accountColor(account.id, account.color),
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: Key(outgoing ? 'transfer-from-card' : 'transfer-to-card'),
        onTap: () => _accounts(outgoing),
        child: SizedBox(
          height: _T.transferCardHeight,
          child: Padding(
            padding: const EdgeInsets.all(_T.transferCardPadding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  account == null
                      ? l.formAccountSheetTitle
                      : '${account.name} • ${account.currency}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: _T.transferNameSize,
                    height: _T.transferNameHeight,
                  ),
                ),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${money(account?.balance ?? '0')} ${outgoing ? '−' : '+'} ${money(amount)}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: _T.transferBalanceSize,
                              color: c.transferMuted,
                            ),
                          ),
                          Text(
                            '= ${money(form.resultingBalance(outgoing: outgoing))}',
                            key: Key(
                              outgoing
                                  ? 'transfer-from-result'
                                  : 'transfer-to-result',
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: _T.transferBalanceSize,
                              fontWeight: FontWeight.bold,
                              color: c.transferMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (outgoing)
                      Padding(
                        padding: const EdgeInsets.only(
                          right: _T.transferAmountPadding,
                        ),
                        child: SizedBox(
                          width: _T.transferClearSize,
                          height: _T.transferClearSize,
                          child: IconButton.filled(
                            key: const Key('transfer-clear'),
                            tooltip: l.transferClear,
                            style: IconButton.styleFrom(
                              backgroundColor: c.card,
                              foregroundColor: colors.muted,
                              padding: EdgeInsets.zero,
                            ),
                            onPressed: () => form.setFromAmount(''),
                            icon: const Icon(Icons.close_rounded),
                          ),
                        ),
                      ),
                    ConstrainedBox(
                      constraints: const BoxConstraints(
                        maxWidth: _T.transferAmountMaxWidth,
                      ),
                      child: Material(
                        color: c.transferAmount,
                        borderRadius: BorderRadius.circular(
                          _T.transferAmountRadius,
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: InkWell(
                          key: Key(
                            outgoing
                                ? 'transfer-from-amount'
                                : 'transfer-to-amount',
                          ),
                          onTap: () => _amount(outgoing),
                          child: SizedBox(
                            height: _T.transferAmountHeight,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: _T.transferAmountPadding,
                              ),
                              child: FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      outgoing
                                          ? Icons.arrow_drop_down_rounded
                                          : Icons.arrow_drop_up_rounded,
                                      color: tone,
                                      size: _T.transferDirectionSize,
                                    ),
                                    Text(
                                      money(amount),
                                      style: TextStyle(
                                        fontSize: _T.transferAmountSize,
                                        fontWeight: FontWeight.bold,
                                        color: tone,
                                      ),
                                    ),
                                  ],
                                ),
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
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final c = TransactionFormColors.of(context);
    final date = form.limaTime;
    final now = form.now().toUtc().subtract(const Duration(hours: 5));
    final today =
        date.year == now.year && date.month == now.month && date.day == now.day;
    return Scaffold(
      key: const Key('transfer-balance-page'),
      backgroundColor: c.transferBackground,
      appBar: AppBar(
        leading: BackButton(
          key: const Key('transfer-back'),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        centerTitle: true,
        backgroundColor: c.transferBackground,
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        title: Text(
          l.transferBalanceTitle,
          style: const TextStyle(
            fontSize: _T.titleSize,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          IconButton(
            key: const Key('transfer-info'),
            tooltip: l.transferInfoLabel,
            onPressed: _info,
            icon: const Icon(Icons.info_outline_rounded),
          ),
        ],
      ),
      bottomNavigationBar: FormBottomAction(
        color: c.sheetAction,
        label: form.busy ? l.savingTransaction : l.transferConfirm,
        busy: form.busy,
        onPressed: form.busy ? null : _save,
      ),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: _T.maxWidth),
          child: SingleChildScrollView(
            key: const Key('transfer-scroll'),
            child: AbsorbPointer(
              absorbing: form.busy,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (form.error case final error?)
                    Padding(
                      padding: const EdgeInsets.all(_T.transferInset),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              error.message(l),
                              key: const Key('transfer-error'),
                            ),
                          ),
                          TextButton(onPressed: _save, child: Text(l.retry)),
                        ],
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      _T.transferInset,
                      _T.transferTop,
                      _T.transferInset,
                      0,
                    ),
                    child: Column(
                      children: [
                        _card(true),
                        _fieldError('from_account_id'),
                        _fieldError('from_amount'),
                        SizedBox(
                          height: _T.transferControlHeight,
                          child: Row(
                            children: [
                              SizedBox(
                                width: _T.transferSwapSize,
                                height: _T.transferSwapSize,
                                child: IconButton.filled(
                                  key: const Key('transfer-swap'),
                                  tooltip: l.transferSwap,
                                  style: IconButton.styleFrom(
                                    backgroundColor: c.field,
                                    foregroundColor: c.typeText,
                                    padding: EdgeInsets.zero,
                                  ),
                                  onPressed: form.swapAccounts,
                                  icon: const Icon(
                                    Icons.arrow_downward_rounded,
                                  ),
                                ),
                              ),
                              const Spacer(),
                              if (!form.sameCurrency)
                                Material(
                                  color: c.dateBox,
                                  borderRadius: BorderRadius.circular(
                                    _T.transferAmountRadius,
                                  ),
                                  clipBehavior: Clip.antiAlias,
                                  child: InkWell(
                                    key: const Key('transfer-rate'),
                                    onTap: _rateSheet,
                                    child: SizedBox(
                                      width: _T.transferRateWidth,
                                      height: _T.transferRateHeight,
                                      child: Center(
                                        child: Text(
                                          '× ${form.rateLabel}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: _T.transferRateSize,
                                            color: MonetaeColors.of(context)
                                                .muted,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        _fieldError('rate'),
                        _card(false),
                        _fieldError('to_account_id'),
                        _fieldError('to_amount'),
                      ],
                    ),
                  ),
                  const SizedBox(height: _T.transferDetailsGap),
                  Divider(color: c.fieldDivider, height: _T.transferBorder),
                  Padding(
                    padding: const EdgeInsets.all(_T.transferDetailInset),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        FormDateBox(
                          date: today
                              ? l.today
                              : DateFormat.MMMd(l.localeName).format(date),
                          hour: DateFormat('HH').format(date),
                          minute: DateFormat('mm').format(date),
                          onDate: () => _date(),
                          onTime: () => _date(timeOnly: true),
                        ),
                        _fieldError('occurred_at'),
                        Row(
                          children: [
                            Expanded(
                              child: InkWell(
                                key: const Key('transfer-arrival'),
                                onTap: () => _date(arrival: true),
                                child: Text(
                                  form.arrivalAt == null
                                      ? l.transferArrivalSame
                                      : l.transferArrivalLabel(
                                          DateFormat.yMMMd(l.localeName)
                                              .add_Hm()
                                              .format(form.arrivalTime),
                                        ),
                                  style: TextStyle(
                                    fontSize: _T.transferArrivalSize,
                                    color: MonetaeColors.of(context).muted,
                                  ),
                                ),
                              ),
                            ),
                            if (form.arrivalAt != null)
                              IconButton(
                                key: const Key('transfer-arrival-reset'),
                                tooltip: l.transferArrivalReset,
                                onPressed: () => form.setArrival(null),
                                icon: const Icon(Icons.close_rounded),
                              ),
                          ],
                        ),
                        _fieldError('to_occurred_at'),
                        const SizedBox(height: _T.transferTitleGap),
                        FormFilledField(
                          key: const Key('transfer-title'),
                          hint: l.transferBalanceTitle,
                          icon: Icons.title_rounded,
                          initialValue: form.title,
                          errorText: _error('title'),
                          onChanged: (value) =>
                              form.edit(() => form.title = value),
                        ),
                        if (form.neitherBase) ...[
                          const SizedBox(height: _T.transferTitleGap),
                          FormFilledField(
                            key: const Key('transfer-from-base-rate'),
                            controller: _fromBaseRate,
                            hint: l.exchangeRate,
                            icon: Icons.currency_exchange_rounded,
                            inputFormatters: const [DecimalTextFormatter(6)],
                            errorText: _error('from_fx_rate_to_base'),
                            helperText: l.manualRateHint(
                              form.from!.currency,
                              form.user.baseCurrency,
                            ),
                            onChanged: (value) =>
                                form.edit(() => form.fromManualRate = value),
                          ),
                          const SizedBox(height: _T.transferTitleGap),
                          FormFilledField(
                            key: const Key('transfer-to-base-rate'),
                            controller: _toBaseRate,
                            hint: l.exchangeRate,
                            icon: Icons.currency_exchange_rounded,
                            inputFormatters: const [DecimalTextFormatter(6)],
                            errorText: _error('to_fx_rate_to_base'),
                            helperText: l.manualRateHint(
                              form.to!.currency,
                              form.user.baseCurrency,
                            ),
                            onChanged: (value) =>
                                form.edit(() => form.toManualRate = value),
                          ),
                        ] else ...[
                          _fieldError('from_fx_rate_to_base'),
                          _fieldError('to_fx_rate_to_base'),
                        ],
                        if (!form.sameCurrency)
                          Padding(
                            padding: const EdgeInsets.only(
                              top: _T.transferPillTop,
                            ),
                            child: Center(
                              child: TextButton(
                                key: const Key('transfer-rates'),
                                style: TextButton.styleFrom(
                                  backgroundColor: c.pill,
                                  foregroundColor: MonetaeColors.of(context)
                                      .muted,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(
                                      _T.transferAmountRadius,
                                    ),
                                  ),
                                ),
                                onPressed: _rateSheet,
                                child: Text(l.transferRates),
                              ),
                            ),
                          ),
                      ],
                    ),
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
