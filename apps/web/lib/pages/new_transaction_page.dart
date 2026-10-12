// Derived from Cashew pages/addTransactionPage.dart (form, SelectTitle,
// TransactionNotesTextInput) and widgets/util/showDatePicker.dart (date selection).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: API form with exact
// decimals, manual exchange rate, UTC/Lima dates and server error handling.
// Modified 2026-10-10 (T-515): Cashew layout — kind tabs, amount header, date
// box, chip rows, filled title/notes and bottom action bar.
// Modified 2026-10-11 (T-515 piece 2): initial title sheet and shared title input.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/home_controller.dart';
import '../api/new_transaction_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/category_icon_source.dart';
import '../presentation/currency_format.dart';
import '../presentation/decimal_input.dart';
import '../presentation/transaction_presenter.dart';
import '../session/session_controller.dart';
import '../theme/monetae_theme.dart';
import '../widgets/category_icon.dart';
import '../widgets/decimal_number_pad.dart';
import '../widgets/transaction_category_grid.dart';
import '../widgets/transaction_form/form_controls.dart';
import '../widgets/transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;

/// Cashew transaction types. Only [standard] and [upcoming] exist in the
/// model (status posted / scheduled); the rest are design only (T-515).
enum FormTransactionType {
  standard,
  upcoming,
  subscription,
  repetitive,
  lend,
  borrow,
}

class NewTransactionPage extends StatefulWidget {
  const NewTransactionPage({
    super.key,
    required this.session,
    this.controller,
    this.editing = false,
  });
  final SessionController session;
  final NewTransactionController? controller;

  /// Only switches the title; there is no edit route yet (TODO T-515).
  final bool editing;
  @override
  State<NewTransactionPage> createState() => _NewTransactionPageState();
}

class _NewTransactionPageState extends State<NewTransactionPage> {
  late final NewTransactionController _form;
  late final TextEditingController _rate;
  late final TextEditingController _title;
  bool _initialTitleOpened = false;
  bool _uncategorizedChosen = false;
  FormTransactionType _designType = FormTransactionType.standard;
  List<BudgetDto> _budgets = const [];
  List<GoalDto> _goals = const [];
  String? _budgetId;
  String? _goalId;

  @override
  void initState() {
    super.initState();
    _form =
        widget.controller ??
        NewTransactionController(widget.session.api, widget.session.user!);
    _rate = TextEditingController(text: _form.rate);
    _title = TextEditingController(text: _form.title);
    _form.addListener(_changed);
    if (_form.loading) _form.load();
    _loadChipCatalogs();
    _scheduleTitleSheet();
  }

  /// Budgets and goals only feed the chip rows; failures leave them empty.
  Future<void> _loadChipCatalogs() async {
    final api = widget.session.api;
    final result = await Future.wait([
      loadBudgets(api),
      loadPages<GoalDto>((cursor) async {
        final page = await api.goals(cursor: cursor);
        return (page.items, page.nextCursor);
      }, unavailableIsEmpty: true),
    ]).catchError((Object _) => <List<Object>>[const [], const []]);
    if (!mounted) return;
    setState(() {
      _budgets = result[0]
          .cast<BudgetDto>()
          .where((b) => b.deletedAt == null)
          .toList();
      _goals = result[1]
          .cast<GoalDto>()
          .where((g) => g.deletedAt == null)
          .toList();
    });
  }

  void _changed() {
    if (!mounted) return;
    if (_title.text != _form.title) _title.text = _form.title;
    setState(() {});
    _scheduleTitleSheet();
  }

  void _scheduleTitleSheet() {
    if (widget.editing || _form.loading || _initialTitleOpened) return;
    _initialTitleOpened = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_form.loading) {
        _initialTitleOpened = false;
        return;
      }
      _openTitleSheet();
    });
  }

  Future<void> _openTitleSheet() async {
    final l = AppLocalizations.of(context);
    final next = await showFormSheet<bool>(
      context,
      key: const Key('title-sheet'),
      title: l.formEnterTitle,
      trailing: IconButton(
        key: const Key('title-sheet-date'),
        tooltip: l.formChooseDate,
        padding: EdgeInsets.zero,
        style: IconButton.styleFrom(
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        constraints: const BoxConstraints.tightFor(
          width: _T.sheetTitleSize,
          height: _T.sheetTitleSize,
        ),
        icon: const Icon(Icons.calendar_month_rounded, size: _T.sheetTitleSize),
        onPressed: _pickDate,
      ),
      builder: (sheet) {
        void continueToCategories() {
          FocusScope.of(sheet).unfocus();
          Navigator.of(sheet).pop(true);
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            FormFilledField(
              key: const Key('title-sheet-field'),
              controller: _title,
              hint: l.formTitleHint,
              icon: Icons.title_rounded,
              autofocus: true,
              onChanged: (text) => _form.edit(() => _form.title = text),
              onSubmitted: (_) => continueToCategories(),
            ),
            const SizedBox(height: _T.sheetFieldGap),
            FormSheetButton(
              key: const Key('title-sheet-next'),
              label: l.formSelectCategory,
              onPressed: continueToCategories,
            ),
          ],
        );
      },
    );
    if (mounted && next == true) await _openCategorySheet();
  }

  @override
  void dispose() {
    _form.removeListener(_changed);
    if (widget.controller == null) _form.dispose();
    _rate.dispose();
    _title.dispose();
    super.dispose();
  }

  bool get _categoryChosen => _form.categoryId != null || _uncategorizedChosen;

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

  void _selectIncome(bool income) {
    if (_form.busy || income == _form.income) return;
    setState(() => _uncategorizedChosen = false);
    _form.selectIncome(income);
  }

  void _selectCategory(String? id) {
    setState(() => _uncategorizedChosen = id == null);
    _form.edit(() => _form.categoryId = id);
  }

  /// Applies one keypad key with the same two-decimal rules as typing.
  void _applyKey(String key) {
    final old = TextEditingValue(
      text: _form.amount,
      selection: TextSelection.collapsed(offset: _form.amount.length),
    );
    final text = key == 'backspace'
        ? (old.text.isEmpty ? '' : old.text.substring(0, old.text.length - 1))
        : old.text + key;
    final next = const DecimalTextFormatter(2).formatEditUpdate(
      old,
      TextEditingValue(
        text: text,
        selection: TextSelection.collapsed(offset: text.length),
      ),
    );
    if (next.text != old.text) _form.edit(() => _form.amount = next.text);
  }

  Future<void> _openCategorySheet() async {
    if (_form.busy) return;
    final l = AppLocalizations.of(context);
    // TODO(T-515 piece 3): Cashew category sheet (capture 15).
    await showFormSheet<void>(
      context,
      title: l.formSelectCategory,
      builder: (sheet) => TransactionCategoryGrid(
        categories: _form.visibleCategories,
        selectedId: _form.categoryId,
        onSelected: (id) {
          _selectCategory(id);
          Navigator.of(sheet).pop();
        },
      ),
    );
  }

  Future<void> _openAmountSheet() async {
    if (_form.busy) return;
    final l = AppLocalizations.of(context);
    // TODO(T-515 piece 4): Cashew amount sheet (capture 16).
    await showFormSheet<void>(
      context,
      title: l.transactionAmount,
      builder: (sheet) => ListenableBuilder(
        listenable: _form,
        builder: (_, _) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _amountText(l),
              textAlign: TextAlign.end,
              style: const TextStyle(fontSize: 40, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            DecimalNumberPad(
              onKey: _applyKey,
              onClear: () => _form.edit(() => _form.amount = ''),
            ),
            const SizedBox(height: 12),
            FormSheetButton(
              key: const Key('amount-sheet-done'),
              label: l.saveTransaction,
              onPressed: () => Navigator.of(sheet).pop(),
            ),
          ],
        ),
      ),
    );
  }

  String _amountText(AppLocalizations l) => formatTypedAmount(
    _form.amount,
    _form.account?.currency ?? _form.user.baseCurrency,
    l.localeName,
  );

  Future<void> _onAction() async {
    if (!_categoryChosen) return _openCategorySheet();
    return _save();
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

  DateTime get _limaNow =>
      _form.now().toUtc().subtract(const Duration(hours: 5));

  /// "Predeterminado" and "Próximamente" are the posted/scheduled status, which
  /// the controller derives from the date; other types are design only.
  FormTransactionType get _shownType => switch (_designType) {
    FormTransactionType.standard || FormTransactionType.upcoming =>
      _form.scheduled
          ? FormTransactionType.upcoming
          : FormTransactionType.standard,
    final other => other,
  };

  void _selectType(FormTransactionType type) {
    if (_form.busy) return;
    setState(() => _designType = type);
    final now = _limaNow;
    if (type == FormTransactionType.standard && _form.scheduled) {
      _form.selectLimaTime(now);
    } else if (type == FormTransactionType.upcoming && !_form.scheduled) {
      final t = _form.limaTime;
      _form.selectLimaTime(
        DateTime(now.year, now.month, now.day + 1, t.hour, t.minute),
      );
    }
  }

  Future<void> _showAllAccounts() async {
    final l = AppLocalizations.of(context);
    await showFormSheet<void>(
      context,
      title: l.formAllAccounts,
      builder: (sheet) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final a in _form.accounts)
            ListTile(
              key: Key('form-account-option-${a.id}'),
              leading: Icon(
                Icons.circle,
                size: 14,
                color: accountColor(a.id, a.color),
              ),
              title: Text(a.name),
              trailing: Text(currencySymbol(a.currency, l.localeName)),
              selected: a.id == _form.account?.id,
              onTap: () {
                _selectAccount(a);
                Navigator.of(sheet).pop();
              },
            ),
        ],
      ),
    );
  }

  void _selectAccount(AccountDto account) {
    if (account.id == _form.account?.id) return;
    _rate.clear();
    _form.selectAccount(account);
  }

  Widget? _headerCategory() {
    final colors = MonetaeColors.of(context);
    if (_form.categoryId case final String id) {
      final category = _form.categories.where((c) => c.id == id).firstOrNull;
      final color = presentationColor(category?.color, fallback: colors.muted);
      return ColoredBox(
        color: color,
        child: Center(
          child: category == null
              ? null
              : CategoryIcon(
                  source: CategoryIconSource.resolve(category.icon),
                  color: Colors.white,
                  size: _T.categoryIconSize,
                ),
        ),
      );
    }
    if (_uncategorizedChosen) {
      return Icon(
        Icons.category_outlined,
        size: _T.categoryIconSize,
        color: colors.muted,
      );
    }
    return null;
  }

  Widget _error(String? text) => text == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.fromLTRB(
            _T.sidePadding + 4,
            4,
            _T.sidePadding,
            0,
          ),
          child: Text(
            text,
            style: TextStyle(
              fontSize: _T.captionSize,
              color: Theme.of(context).colorScheme.error,
            ),
          ),
        );

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final busy = _form.busy;
    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        backgroundColor: colors.background,
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        title: Text(
          widget.editing ? l.formEditTitle : l.addTransaction,
          style: const TextStyle(
            fontSize: _T.titleSize,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          IconButton(
            key: const Key('form-menu'),
            tooltip: l.formMenu,
            icon: const Icon(Icons.more_vert_rounded),
            // TODO(T-515): Cashew's menu (duplicate, delete…) needs edit mode.
            onPressed: () {},
          ),
        ],
      ),
      bottomNavigationBar: FormBottomAction(
        label: _categoryChosen
            ? (busy ? l.savingTransaction : l.saveTransaction)
            : l.formSelectCategory,
        busy: busy,
        onPressed: busy || _form.loading ? null : _onAction,
      ),
      body: _form.loading
          ? const Center(child: CircularProgressIndicator())
          : Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: _T.maxWidth),
                child: SingleChildScrollView(
                  key: const Key('transaction-form-scroll'),
                  padding: const EdgeInsets.only(bottom: 24),
                  child: AbsorbPointer(
                    absorbing: busy,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: _formChildren(l, colors),
                    ),
                  ),
                ),
              ),
            ),
    );
  }

  List<Widget> _formChildren(AppLocalizations l, MonetaeColors colors) {
    final limaTime = _form.limaTime;
    final now = _limaNow;
    final isToday =
        limaTime.year == now.year &&
        limaTime.month == now.month &&
        limaTime.day == now.day;
    final pad = const EdgeInsets.symmetric(horizontal: _T.sidePadding);
    final shownType = _shownType;
    FormChipData typeChip(FormTransactionType type, String label) =>
        FormChipData(
          key: Key('form-type-${type.name}'),
          label: label,
          selected: shownType == type,
          onTap: () => _selectType(type),
        );
    return [
      if (_form.error case final error?)
        Padding(
          padding: const EdgeInsets.fromLTRB(
            _T.sidePadding,
            8,
            _T.sidePadding,
            0,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  error.message(l),
                  key: const Key('transaction-form-error'),
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
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
          ),
        ),
      FormKindTabs(income: _form.income, onChanged: _selectIncome),
      _error(_fieldError('kind')),
      FormAmountHeader(
        category: _headerCategory(),
        amount: _amountText(l),
        error: _fieldError('amount'),
        onCategoryTap: _openCategorySheet,
        onAmountTap: _openAmountSheet,
      ),
      const SizedBox(height: 10),
      Padding(
        padding: pad,
        child: FormDateBox(
          date: isToday
              ? l.today
              : DateFormat.MMMd(l.localeName).format(limaTime),
          hour: DateFormat('HH').format(limaTime),
          minute: DateFormat('mm').format(limaTime),
          onDate: _pickDate,
          onTime: _pickTime,
        ),
      ),
      _error(_fieldError('occurred_at')),
      Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Text(
          l.limaTimezone,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: _T.captionSize, color: colors.muted),
        ),
      ),
      if (_form.needsRate) ...[
        const SizedBox(height: 10),
        Padding(
          padding: pad,
          child: FormFilledField(
            key: const Key('transaction-rate'),
            controller: _rate,
            hint: l.exchangeRate,
            icon: Icons.currency_exchange_rounded,
            readOnly: _form.busy,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [DecimalTextFormatter(6)],
            errorText: _fieldError('fx_rate_to_base'),
            helperText: l.manualRateHint(
              currencySymbol(_form.account!.currency, l.localeName),
              currencySymbol(_form.user.baseCurrency, l.localeName),
            ),
            onChanged: (text) => _form.edit(() => _form.rate = text),
          ),
        ),
      ],
      const SizedBox(height: _T.rowGap),
      FormChipRow(
        key: const Key('form-type-row'),
        leading: IconButton(
          key: const Key('form-type-info'),
          tooltip: l.formTypeInfo,
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints.tightFor(
            width: _T.chipHeight,
            height: _T.chipHeight,
          ),
          icon: const Icon(Icons.info_outline_rounded, size: 26),
          // TODO(T-515 piece 6): transaction type sheet (captures 17–19).
          onPressed: () {},
        ),
        chips: [
          typeChip(FormTransactionType.standard, l.formTypeDefault),
          typeChip(FormTransactionType.upcoming, l.formTypeUpcoming),
          // TODO(T-515): subscriptions, repeating, lend and borrow are not
          // transaction types in Monetae's model; design only.
          typeChip(FormTransactionType.subscription, l.formTypeSubscription),
          typeChip(FormTransactionType.repetitive, l.formTypeRepetitive),
          typeChip(FormTransactionType.lend, l.formTypeLend),
          typeChip(FormTransactionType.borrow, l.formTypeBorrow),
        ],
      ),
      _error(_fieldError('status')),
      const SizedBox(height: _T.rowGap),
      FormChipRow(
        key: const Key('form-account-row'),
        leading: FormSquareButton(
          key: const Key('form-account-list'),
          icon: Icons.keyboard_arrow_down_rounded,
          tooltip: l.formAllAccounts,
          onTap: _showAllAccounts,
        ),
        chips: [
          for (final a in _form.accounts)
            FormChipData(
              key: Key('form-account-${a.id}'),
              label: a.name,
              color: accountColor(a.id, a.color),
              selected: a.id == _form.account?.id,
              onTap: () => _selectAccount(a),
            ),
        ],
      ),
      _error(_fieldError('account_id') ?? _fieldError('currency')),
      const SizedBox(height: _T.rowGap),
      // TODO(T-515): budget/goal selection is visual only; linking needs
      // PUT /budgets|goals/{id}/transactions after creating the transaction.
      FormChipRow(
        key: const Key('form-budget-row'),
        chips: [
          FormChipData(
            key: const Key('form-budget-none'),
            label: l.formNoBudget,
            selected: _budgetId == null,
            onTap: () => setState(() => _budgetId = null),
          ),
          for (final b in _budgets)
            FormChipData(
              key: Key('form-budget-${b.id}'),
              label: b.name,
              color: presentationColor(b.color, fallback: colors.muted),
              selected: _budgetId == b.id,
              onTap: () => setState(() => _budgetId = b.id),
            ),
        ],
        trailing: FormSquareButton(
          key: const Key('form-budget-add'),
          icon: Icons.add_rounded,
          tooltip: l.formCreateBudget,
          // TODO(F1): the create-budget form does not exist yet.
          onTap: () {},
        ),
      ),
      const SizedBox(height: _T.rowGap),
      FormChipRow(
        key: const Key('form-goal-row'),
        chips: [
          FormChipData(
            key: const Key('form-goal-none'),
            label: l.formNoGoal,
            selected: _goalId == null,
            onTap: () => setState(() => _goalId = null),
          ),
          for (final g in _goals)
            FormChipData(
              key: Key('form-goal-${g.id}'),
              label: g.name,
              color: presentationColor(g.color, fallback: colors.muted),
              selected: _goalId == g.id,
              onTap: () => setState(() => _goalId = g.id),
            ),
        ],
        trailing: FormSquareButton(
          key: const Key('form-goal-add'),
          icon: Icons.add_rounded,
          tooltip: l.formCreateGoal,
          // TODO(F1): the create-goal form does not exist yet.
          onTap: () {},
        ),
      ),
      const SizedBox(height: _T.rowGap),
      // TODO(T-515): the web client has no loan DTO; only "Sin préstamo".
      FormChipRow(
        key: const Key('form-loan-row'),
        chips: [
          FormChipData(
            key: const Key('form-loan-none'),
            label: l.formNoLoan,
            selected: true,
            onTap: () {},
          ),
        ],
      ),
      const SizedBox(height: _T.rowGap + 4),
      Padding(
        padding: pad,
        child: FormFilledField(
          key: const Key('transaction-title'),
          hint: l.formTitleHint,
          icon: Icons.title_rounded,
          controller: _title,
          readOnly: _form.busy,
          errorText: _fieldError('title'),
          onChanged: (text) => _form.edit(() => _form.title = text),
        ),
      ),
      const SizedBox(height: 18),
      Padding(
        padding: pad,
        child: FormNotesPanel(
          fieldKey: const Key('transaction-note'),
          initialValue: _form.note,
          readOnly: _form.busy,
          errorText: _fieldError('note'),
          onChanged: (text) => _form.edit(() => _form.note = text),
        ),
      ),
      const SizedBox(height: 18),
      // TODO(T-515 piece 5): expands the "Más opciones" section (capture 14).
      FormMoreOptionsPill(onTap: () {}),
    ];
  }
}
