// Adapted from Cashew pages/addObjectivePage.dart (type, name, color, target,
// dates and fixed save action), Copyright James Kokoska, GPL-3.0.
// Modified 2026-10-18: typed API, i18n and exact money; optional due date only.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../data/api_dtos.dart';
import '../data/goal_create_dto.dart';
import '../l10n/app_localizations.dart';
import '../presentation/account_color.dart';
import '../presentation/clock.dart';
import '../presentation/currency_format.dart';
import '../presentation/exact_decimal.dart';
import '../theme/monetae_theme.dart';
import '../widgets/account_balance_sheet.dart';
import '../widgets/color_picker.dart';
import '../widgets/currency_picker.dart';
import '../widgets/transaction_form/form_sheet.dart';

typedef _T = TransactionFormTokens;
typedef _A = AccountFormTokens;

class AddGoalPage extends StatefulWidget {
  const AddGoalPage({super.key, required this.api, required this.baseCurrency});
  final ApiClient api;
  final String baseCurrency;

  @override
  State<AddGoalPage> createState() => _AddGoalPageState();
}

class _AddGoalPageState extends State<AddGoalPage> {
  final _name = TextEditingController();
  late String _currency = widget.baseCurrency;
  GoalKind _kind = GoalKind.save;
  Color _color = accountPalette.first;
  String _amount = '0';
  DateTime? _dueOn;
  bool _busy = false;
  ApiException? _error;
  int get _decimals =>
      NumberFormat.currency(name: _currency).decimalDigits!.clamp(0, 2);
  bool get _validName => _name.text.trim().isNotEmpty;
  bool get _validAmount => ExactDecimal.parse(_amount).numerator > BigInt.zero;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_busy || !_validName || !_validAmount) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.createGoal(
        GoalCreateDto(
          name: _name.text.trim(),
          kind: _kind,
          targetAmount: _amount,
          currency: _currency,
          dueOn: _dueOn == null
              ? null
              : DateFormat('yyyy-MM-dd').format(_dueOn!),
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
      key: const Key('goal-amount-sheet'),
      title: AppLocalizations.of(context).formEnterAmount,
      bottomPadding: _T.sheetPadding,
      builder: (_) => AccountBalanceSheet(
        initialBalance: _amount,
        currency: _currency,
        decimals: _decimals,
        positiveOnly: true,
      ),
    );
    if (mounted && chosen != null) setState(() => _amount = chosen);
  }

  Future<void> _editCurrency() async {
    FocusScope.of(context).unfocus();
    final chosen = await showFormSheet<String>(
      context,
      title: AppLocalizations.of(context).accountCurrency,
      builder: (sheet) => CurrencyPicker(
        currencies: {widget.baseCurrency, ...accountCurrencies},
        selected: _currency,
        keyPrefix: 'goal-currency',
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

  Future<void> _editDueDate() async {
    FocusScope.of(context).unfocus();
    final today = PresentationClock.read(context)
        .toUtc()
        .subtract(const Duration(hours: 5));
    final chosen = await showDatePicker(
      context: context,
      helpText: AppLocalizations.of(context).goalDueDate,
      currentDate: today,
      initialDate: _dueOn ?? DateUtils.dateOnly(today),
      firstDate: DateTime(1900),
      lastDate: DateTime(2100, 12, 31),
    );
    if (mounted && chosen != null) setState(() => _dueOn = chosen);
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
          title: Text(l.addGoal),
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
              key: const Key('goal-fields'),
              absorbing: _busy,
              child: ListView(
                padding: const EdgeInsets.all(_T.sidePadding),
                children: [
                  Row(
                    children: [
                      for (final kind in [GoalKind.spend, GoalKind.save])
                        Expanded(
                          child: Semantics(
                            selected: _kind == kind,
                            child: Material(
                              color: _kind == kind
                                  ? colors.header
                                  : colors.tabIdle,
                              borderRadius: BorderRadius.circular(_A.rowRadius),
                              child: InkWell(
                                key: Key('goal-kind-${kind.name}'),
                                borderRadius: BorderRadius.circular(
                                  _A.rowRadius,
                                ),
                                onTap: () => setState(() => _kind = kind),
                                child: SizedBox(
                                  height: _T.tabHeight,
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        kind == GoalKind.save
                                            ? Icons.arrow_upward_rounded
                                            : Icons.arrow_downward_rounded,
                                        size: _T.tabFontSize,
                                      ),
                                      const SizedBox(width: _A.colorGap),
                                      Text(
                                        kind == GoalKind.save
                                            ? l.goalSaving
                                            : l.goalSpending,
                                        style: const TextStyle(
                                          fontSize: _T.tabFontSize,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: _A.sectionGap),
                  // TODO(F1): icon selector; the request sends icon: null.
                  TextField(
                    key: const Key('goal-name'),
                    controller: _name,
                    textCapitalization: TextCapitalization.sentences,
                    style: const TextStyle(
                      fontSize: _A.nameSize,
                      fontWeight: FontWeight.bold,
                    ),
                    decoration: InputDecoration(
                      hintText: l.goalName,
                      border: InputBorder.none,
                      errorText: _name.text.isNotEmpty && !_validName
                          ? l.goalNameRequired
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
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(_A.rowRadius),
                      border: Border.all(color: Theme.of(context).dividerColor),
                    ),
                    child: Column(
                      children: [
                        InkWell(
                          key: const Key('goal-target-amount'),
                          borderRadius: BorderRadius.circular(_A.rowRadius),
                          onTap: _editAmount,
                          child: Padding(
                            padding: const EdgeInsets.all(
                              _A.rowVerticalPadding,
                            ),
                            child: Wrap(
                              alignment: WrapAlignment.center,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Text(
                                  '${l.addGoalLabel} ',
                                  style: const TextStyle(
                                    fontSize: _T.actionFontSize,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  formatCurrency(
                                    _amount,
                                    _currency,
                                    l.localeName,
                                  ),
                                  key: const Key('goal-amount-value'),
                                  style: const TextStyle(
                                    fontSize: _A.amountSize,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          key: const Key('goal-due-date'),
                          leading: const Icon(Icons.event_rounded),
                          title: Text(l.goalDueDate),
                          subtitle: Text(
                            _dueOn == null
                                ? l.goalNoDueDate
                                : DateFormat.yMMMd(l.localeName)
                                      .format(_dueOn!),
                          ),
                          trailing: _dueOn == null
                              ? null
                              : IconButton(
                                  key: const Key('goal-clear-due-date'),
                                  tooltip: l.goalClearDueDate,
                                  icon: const Icon(Icons.close_rounded),
                                  onPressed: () =>
                                      setState(() => _dueOn = null),
                                ),
                          onTap: _editDueDate,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: _A.sectionGap),
                  ListTile(
                    key: const Key('goal-currency-picker'),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(_A.rowRadius),
                    ),
                    tileColor: colors.field,
                    title: Text(l.accountCurrency),
                    trailing: Text(
                      '$_currency ${currencySymbol(_currency, l.localeName)}',
                    ),
                    onTap: _editCurrency,
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
                    key: const Key('goal-save-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              FormSheetButton(
                key: const Key('goal-save'),
                height: _T.actionHeight,
                label: _busy ? l.savingTransaction : l.addGoal,
                onPressed: !_validName || !_validAmount || _busy ? null : _save,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
