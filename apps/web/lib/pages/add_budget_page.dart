// Adapted from Cashew pages/addBudgetPage.dart (name, amount, recurrence,
// dates, scope, color and fixed save action), James Kokoska, GPL-3.0.
// Modified 2026-10-18: typed API, i18n, exact money and supported periods only.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../api/home_controller.dart';
import '../data/api_dtos.dart';
import '../data/budget_create_dto.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/clock.dart';
import '../presentation/currency_format.dart';
import '../presentation/exact_decimal.dart';
import '../theme/monetae_theme.dart';
import '../widgets/account_balance_sheet.dart';
import '../widgets/color_picker.dart';
import '../widgets/currency_picker.dart';
import '../widgets/home_block_view.dart';
import '../widgets/transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;
typedef _A = AccountFormTokens;

class AddBudgetPage extends StatefulWidget {
  const AddBudgetPage({super.key, required this.api, this.baseCurrency});
  final ApiClient api;
  final String? baseCurrency;

  @override
  State<AddBudgetPage> createState() => _AddBudgetPageState();
}

class _AddBudgetPageState extends State<AddBudgetPage> {
  final _name = TextEditingController();
  String? _baseCurrency;
  String? _currency;
  BudgetPeriod _period = BudgetPeriod.monthly;
  BudgetScope _scope = BudgetScope.all;
  Color _color = accountPalette.first;
  String _amount = '0';
  Map<String, String> _selectedCategories = {};
  late DateTime _startOn;
  DateTime? _endOn;
  bool _busy = false;
  bool _loadingProfile = false;
  ApiException? _error;

  int get _decimals =>
      NumberFormat.currency(name: _currency).decimalDigits!.clamp(0, 2);
  bool get _validName => _name.text.trim().isNotEmpty;
  bool get _validAmount => ExactDecimal.parse(_amount).numerator > BigInt.zero;
  bool get _validDates =>
      _period != BudgetPeriod.custom ||
      (_endOn != null && !_endOn!.isBefore(_startOn));

  @override
  void initState() {
    super.initState();
    _startOn = DateUtils.dateOnly(
      PresentationClock.read(context)
          .toUtc()
          .subtract(const Duration(hours: 5)),
    );
    _baseCurrency = _currency = widget.baseCurrency;
    if (_currency == null) _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() {
      _loadingProfile = true;
      _error = null;
    });
    try {
      final profile = await widget.api.currentUser();
      if (mounted) {
        setState(() => _baseCurrency = _currency = profile.baseCurrency);
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loadingProfile = false);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_busy ||
        _currency == null ||
        !_validName ||
        !_validAmount ||
        !_validDates) {
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.createBudget(
        BudgetCreateDto(
          name: _name.text.trim(),
          categoryIds: _selectedCategories.keys.toList(),
          period: _period,
          startOn: DateFormat('yyyy-MM-dd').format(_startOn),
          endOn: _period == BudgetPeriod.custom
              ? DateFormat('yyyy-MM-dd').format(_endOn!)
              : null,
          amount: _amount,
          currency: _currency!,
          scope: _scope,
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

  Future<void> _editAmount() async {
    FocusScope.of(context).unfocus();
    final chosen = await showFormSheet<String>(
      context,
      key: const Key('budget-amount-sheet'),
      title: AppLocalizations.of(context).formEnterAmount,
      bottomPadding: _T.sheetPadding,
      builder: (_) => AccountBalanceSheet(
        initialBalance: _amount,
        currency: _currency!,
        decimals: _decimals,
        positiveOnly: true,
        amountLabel: AppLocalizations.of(context).budgetAmount,
      ),
    );
    if (mounted && chosen != null) setState(() => _amount = chosen);
  }

  Future<void> _editCategories() async {
    FocusScope.of(context).unfocus();
    final chosen = await showFormSheet<Map<String, String>>(
      context,
      title: AppLocalizations.of(context).budgetCategories,
      builder: (_) => _BudgetCategoriesSheet(
        api: widget.api,
        selected: _selectedCategories,
      ),
    );
    if (mounted && chosen != null) setState(() => _selectedCategories = chosen);
  }

  Future<void> _editCurrency() async {
    FocusScope.of(context).unfocus();
    final chosen = await showFormSheet<String>(
      context,
      title: AppLocalizations.of(context).accountCurrency,
      builder: (sheet) => CurrencyPicker(
        currencies: {_baseCurrency!, ...accountCurrencies},
        selected: _currency!,
        keyPrefix: 'budget-currency',
        onSelected: (value) => Navigator.of(sheet).pop(value),
      ),
    );
    if (mounted && chosen != null) {
      setState(() {
        _currency = chosen;
        _amount = ExactDecimal.parse(_amount).fixed(_decimals);
      });
    }
  }

  String _periodLabel(AppLocalizations l, BudgetPeriod period) =>
      switch (period) {
        BudgetPeriod.daily => l.budgetDaily,
        BudgetPeriod.weekly => l.budgetWeekly,
        BudgetPeriod.monthly => l.budgetMonthly,
        BudgetPeriod.custom => l.budgetCustom,
      };

  Future<void> _editPeriod() async {
    FocusScope.of(context).unfocus();
    final l = AppLocalizations.of(context);
    final chosen = await showFormSheet<BudgetPeriod>(
      context,
      title: l.budgetPeriod,
      builder: (sheet) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final period in BudgetPeriod.values)
            ListTile(
              key: Key('budget-period-${period.name}'),
              title: Text(_periodLabel(l, period)),
              trailing: _period == period
                  ? const Icon(Icons.check_rounded)
                  : null,
              onTap: () => Navigator.of(sheet).pop(period),
            ),
        ],
      ),
    );
    if (mounted && chosen != null) setState(() => _period = chosen);
  }

  Future<void> _editDate({required bool end}) async {
    FocusScope.of(context).unfocus();
    final chosen = await showDatePicker(
      context: context,
      helpText: end
          ? AppLocalizations.of(context).budgetEndDate
          : AppLocalizations.of(context).budgetStartDate,
      currentDate: DateUtils.dateOnly(
        PresentationClock.read(context)
            .toUtc()
            .subtract(const Duration(hours: 5)),
      ),
      initialDate: end ? _endOn ?? _startOn : _startOn,
      firstDate: DateTime(1900),
      lastDate: DateTime(2100, 12, 31),
    );
    if (mounted && chosen != null) {
      setState(() {
        if (end) {
          _endOn = chosen;
        } else {
          _startOn = chosen;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = TransactionFormColors.of(context);
    final error = _error;
    return PopScope(
      canPop: !_busy,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.addBudget),
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
            child: _currency == null
                ? Center(
                    child: _loadingProfile
                        ? const CircularProgressIndicator()
                        : TextButton(
                            onPressed: _loadProfile,
                            child: Text(l.retry),
                          ),
                  )
                : AbsorbPointer(
                    key: const Key('budget-fields'),
                    absorbing: _busy,
                    child: ListView(
                      padding: const EdgeInsets.all(_T.sidePadding),
                      children: [
                        TextField(
                          key: const Key('budget-name'),
                          controller: _name,
                          textCapitalization: TextCapitalization.sentences,
                          style: const TextStyle(
                            fontSize: _A.nameSize,
                            fontWeight: FontWeight.bold,
                          ),
                          decoration: InputDecoration(
                            hintText: l.budgetName,
                            border: InputBorder.none,
                            errorText: _name.text.isNotEmpty && !_validName
                                ? l.budgetNameRequired
                                : null,
                          ),
                          onChanged: (_) => setState(() => _error = null),
                        ),
                        const SizedBox(height: _A.sectionGap),
                        InkWell(
                          key: const Key('budget-amount'),
                          onTap: _editAmount,
                          borderRadius: BorderRadius.circular(_A.rowRadius),
                          child: Padding(
                            padding: const EdgeInsets.all(
                              _A.rowVerticalPadding,
                            ),
                            child: Text(
                              formatCurrency(_amount, _currency!, l.localeName),
                              key: const Key('budget-amount-value'),
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontSize: _A.amountSize,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                        ListTile(
                          key: const Key('budget-currency-picker'),
                          title: Text(l.accountCurrency),
                          trailing: Text(
                            '$_currency ${currencySymbol(_currency!, l.localeName)}',
                          ),
                          onTap: _editCurrency,
                        ),
                        // TODO(F1): every N periods; the API supports only N = 1.
                        ListTile(
                          key: const Key('budget-period'),
                          leading: const Icon(Icons.repeat_rounded),
                          title: Text(l.budgetPeriod),
                          trailing: Text(_periodLabel(l, _period)),
                          onTap: _editPeriod,
                        ),
                        ListTile(
                          key: const Key('budget-start-date'),
                          leading: const Icon(Icons.event_rounded),
                          title: Text(l.budgetStartDate),
                          trailing: Text(
                            DateFormat.yMMMd(l.localeName).format(_startOn),
                          ),
                          onTap: () => _editDate(end: false),
                        ),
                        if (_period == BudgetPeriod.custom) ...[
                          ListTile(
                            key: const Key('budget-end-date'),
                            leading: const Icon(Icons.event_rounded),
                            title: Text(l.budgetEndDate),
                            subtitle: Text(
                              _endOn == null
                                  ? l.budgetChooseEndDate
                                  : DateFormat.yMMMd(l.localeName)
                                        .format(_endOn!),
                            ),
                            onTap: () => _editDate(end: true),
                          ),
                          if (_endOn != null && !_validDates)
                            Text(
                              l.budgetDatesInvalid,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                        ],
                        const SizedBox(height: _A.sectionGap),
                        ListTile(
                          key: const Key('budget-categories'),
                          leading: const Icon(Icons.category_rounded),
                          title: Text(l.budgetCategories),
                          subtitle: Text(
                            _selectedCategories.isEmpty
                                ? l.budgetAllCategories
                                : _selectedCategories.values.join(', '),
                          ),
                          onTap: _editCategories,
                        ),
                        const SizedBox(height: _A.sectionGap),
                        SwitchListTile.adaptive(
                          key: const Key('budget-scope'),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(_A.rowRadius),
                          ),
                          tileColor: colors.field,
                          title: Text(l.budgetSelectedOnly),
                          subtitle: Text(l.budgetSelectedOnlyHint),
                          value: _scope == BudgetScope.selected,
                          onChanged: (selected) => setState(
                            () => _scope = selected
                                ? BudgetScope.selected
                                : BudgetScope.all,
                          ),
                        ),
                        const SizedBox(height: _A.sectionGap),
                        AccountColorPicker(
                          selected: _color,
                          onSelected: (color) => setState(() => _color = color),
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
                    error.message(l),
                    key: const Key('budget-save-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              FormSheetButton(
                key: const Key('budget-save'),
                height: _T.actionHeight,
                label: _busy ? l.savingTransaction : l.addBudget,
                onPressed:
                    !_validName ||
                        !_validAmount ||
                        !_validDates ||
                        _busy ||
                        _currency == null
                    ? null
                    : _save,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BudgetCategoriesSheet extends StatefulWidget {
  const _BudgetCategoriesSheet({required this.api, required this.selected});
  final ApiClient api;
  final Map<String, String> selected;

  @override
  State<_BudgetCategoriesSheet> createState() => _BudgetCategoriesSheetState();
}

class _BudgetCategoriesSheetState extends State<_BudgetCategoriesSheet> {
  late final _selected = Map<String, String>.of(widget.selected);
  late final HomeBlock<List<CategoryDto>> _categories;

  @override
  void initState() {
    super.initState();
    _categories = HomeBlock(() async {
      final all = await loadPages((cursor) async {
        final page = await widget.api.categories(cursor: cursor);
        return (page.items, page.nextCursor);
      });
      return all
          .where(
            (category) =>
                category.kind == CategoryKind.expense &&
                category.deletedAt == null &&
                category.systemKey !=
                    CategorySystemKey.balanceCorrectionExpense,
          )
          .toList();
    })..addListener(_changed);
    _categories.load();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _categories.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return HomeBlockView(
      block: _categories,
      title: l.budgetCategories,
      builder: (categories) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CheckboxListTile(
            key: const Key('budget-categories-all'),
            title: Text(l.budgetAllCategories),
            value: _selected.isEmpty,
            onChanged: (_) => setState(_selected.clear),
          ),
          for (final category in categories)
            CheckboxListTile(
              key: Key('budget-category-${category.id}'),
              title: Text(category.name),
              value: _selected.containsKey(category.id),
              onChanged: (selected) => setState(() {
                if (selected == true) {
                  _selected[category.id] = category.name;
                } else {
                  _selected.remove(category.id);
                }
              }),
            ),
          FormSheetButton(
            key: const Key('budget-categories-done'),
            height: _T.amountSheetButtonHeight,
            label: l.budgetCategoriesDone,
            onPressed: () => Navigator.of(context).pop(_selected),
          ),
        ],
      ),
    );
  }
}
