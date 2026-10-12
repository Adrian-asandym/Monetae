// Derived from Cashew pages/addTransactionPage.dart (header, date row,
// SelectChips rows, TextInput, SaveBottomButton) and widgets/selectChips.dart.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: Monetae theme tokens,
// typed callbacks and stable test keys; presentation only.
// Modified 2026-10-11 (T-515 piece 5): expandable options divider and include
// amount card; callbacks only update local presentation state.
// Modified 2026-10-12 (T-515 piece 7): selected category name under the amount.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../l10n/app_localizations.dart';
import '../../theme/monetae_theme.dart';

typedef _T = TransactionFormTokens;

/// Gasto / Ingreso / Transferir tabs in three equal parts.
class FormKindTabs extends StatelessWidget {
  const FormKindTabs({
    super.key,
    required this.income,
    required this.onChanged,
    this.showTransfer = true,
  });
  final bool income;
  final bool showTransfer;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final colors = MonetaeColors.of(context);
    final form = TransactionFormColors.of(context);
    Widget tab(
      Key key,
      String label,
      Widget icon,
      bool selected,
      VoidCallback? onTap,
    ) => Expanded(
      child: Semantics(
        selected: selected,
        button: true,
        child: Material(
          color: selected ? form.header : form.tabIdle,
          child: InkWell(
            key: key,
            onTap: onTap,
            child: SizedBox(
              height: _T.tabHeight,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  icon,
                  const SizedBox(width: 4),
                  Flexible(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: _T.tabFontSize,
                        color: selected ? null : colors.muted,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    Widget triangle(bool up, Color color) => RotatedBox(
      quarterTurns: up ? 2 : 0,
      child: Icon(Icons.arrow_drop_down_rounded, size: 24, color: color),
    );
    return Row(
      children: [
        tab(
          const Key('select-expense'),
          l.expense,
          triangle(false, colors.expense),
          !income,
          () => onChanged(false),
        ),
        tab(
          const Key('select-income'),
          l.income,
          triangle(true, colors.income),
          income,
          () => onChanged(true),
        ),
        // TODO(T-515): transfers exist in the API (/transfers) but not in the
        // web client; this tab is design only until that flow is built.
        if (showTransfer)
          tab(
            const Key('select-transfer'),
            l.formTransfer,
            Icon(Icons.swap_horiz_rounded, size: 22, color: colors.muted),
            false,
            null,
          ),
      ],
    );
  }
}

/// Category square on the left and amount with category name on the right.
class FormAmountHeader extends StatelessWidget {
  const FormAmountHeader({
    super.key,
    required this.category,
    required this.amount,
    required this.onCategoryTap,
    required this.onAmountTap,
    this.categoryName,
    this.error,
  });

  /// Null while no category was chosen.
  final Widget? category;
  final String? categoryName;
  final String amount;
  final VoidCallback onCategoryTap;
  final VoidCallback onAmountTap;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    return Container(
      color: form.header,
      height: _T.headerHeight,
      padding: const EdgeInsets.symmetric(horizontal: _T.sidePadding),
      child: Row(
        children: [
          Material(
            color: form.emptyCategory,
            borderRadius: BorderRadius.circular(_T.categoryRadius),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              key: const Key('form-category-button'),
              onTap: onCategoryTap,
              child: SizedBox.square(
                dimension: _T.categorySquare,
                child: category,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: InkWell(
              key: const Key('form-amount'),
              borderRadius: BorderRadius.circular(_T.categoryRadius),
              onTap: onAmountTap,
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: _T.categorySquare),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        amount,
                        key: const Key('form-formatted-amount'),
                        style: const TextStyle(
                          fontSize: _T.amountFontSize,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    if (categoryName != null)
                      Text(
                        categoryName!,
                        key: const Key('form-category-name'),
                        textAlign: TextAlign.end,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: _T.headerCategoryNameSize,
                          height: _T.headerCategoryNameHeight,
                          color: form.headerCategoryName,
                        ),
                      ),
                    if (error != null)
                      Text(
                        error!,
                        textAlign: TextAlign.end,
                        style: TextStyle(
                          fontSize: _T.captionSize,
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// "Hoy" + "21 : 16" container; taps open the existing pickers.
class FormDateBox extends StatelessWidget {
  const FormDateBox({
    super.key,
    required this.date,
    required this.hour,
    required this.minute,
    required this.onDate,
    required this.onTime,
  });
  final String date;
  final String hour;
  final String minute;
  final VoidCallback onDate;
  final VoidCallback onTime;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    Widget timeBox(String text) => Container(
      constraints: const BoxConstraints(minWidth: _T.timeBoxWidth),
      padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 2),
      decoration: BoxDecoration(
        color: form.timeBox,
        borderRadius: BorderRadius.circular(_T.timeBoxRadius),
      ),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: _T.timeFontSize,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
    return Material(
      color: form.dateBox,
      borderRadius: BorderRadius.circular(_T.dateRadius),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: _T.dateHeight,
        child: Row(
          children: [
            Expanded(
              child: InkWell(
                key: const Key('transaction-date'),
                onTap: onDate,
                child: Row(
                  children: [
                    const SizedBox(width: 9),
                    Container(
                      width: _T.dateIconBox,
                      height: _T.dateIconBox,
                      decoration: BoxDecoration(
                        color: form.dateIcon,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.calendar_month_rounded, size: 20),
                    ),
                    const SizedBox(width: 15),
                    Flexible(
                      child: Text(
                        date,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: _T.dateFontSize,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            InkWell(
              key: const Key('transaction-time'),
              onTap: onTime,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(
                  children: [
                    timeBox(hour),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 5),
                      child: Text(
                        ':',
                        style: TextStyle(
                          fontSize: _T.timeFontSize,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    timeBox(minute),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class FormChipData {
  const FormChipData({
    required this.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.color,
  });
  final Key key;
  final String label;
  final bool selected;
  final VoidCallback? onTap;

  /// Border color of the entity (account, budget, goal); neutral when null.
  final Color? color;
}

/// One horizontally scrolling chip row, with optional leading/trailing buttons.
class FormChipRow extends StatelessWidget {
  const FormChipRow({
    super.key,
    required this.chips,
    this.leading,
    this.trailing,
    this.horizontalPadding = _T.sidePadding,
  });
  final List<FormChipData> chips;
  final Widget? leading;
  final Widget? trailing;
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    // Rows are short; a non-lazy scroll keeps leading/trailing buttons alive.
    return SizedBox(
      height: _T.chipHeight,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
        child: Row(
          children: [
            if (leading != null) ...[
              leading!,
              const SizedBox(width: _T.chipGap),
            ],
            for (final chip in chips) ...[
              Semantics(
                selected: chip.selected,
                button: true,
                child: Material(
                  color: chip.selected ? form.chipSelected : Colors.transparent,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(_T.chipRadius),
                    side: BorderSide(
                      color: chip.color ?? form.chipBorder,
                      width: _T.chipBorder,
                    ),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    key: chip.key,
                    onTap: chip.onTap,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: _T.chipPadding,
                      ),
                      child: Center(
                        child: Text(
                          chip.label,
                          style: const TextStyle(fontSize: _T.chipFontSize),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: _T.chipGap),
            ],
            ?trailing,
          ],
        ),
      ),
    );
  }
}

/// Square outlined button used for ▼ (all accounts) and "+" (create).
class FormSquareButton extends StatelessWidget {
  const FormSquareButton({
    super.key,
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });
  final IconData icon;
  final String tooltip;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(_T.chipRadius),
          side: BorderSide(color: form.chipBorder, width: _T.chipBorder),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: SizedBox(
            width: _T.chipHeight + 7,
            height: _T.chipHeight,
            child: Icon(icon, size: 20, color: colors.muted),
          ),
        ),
      ),
    );
  }
}

/// Filled single-line field ("Título", exchange rate) without underline.
class FormFilledField extends StatelessWidget {
  const FormFilledField({
    super.key,
    required this.hint,
    required this.onChanged,
    this.icon,
    this.controller,
    this.initialValue,
    this.readOnly = false,
    this.errorText,
    this.helperText,
    this.keyboardType,
    this.inputFormatters,
    this.autofocus = false,
    this.onSubmitted,
  });
  final String hint;
  final IconData? icon;
  final TextEditingController? controller;
  final String? initialValue;
  final ValueChanged<String> onChanged;
  final bool readOnly;
  final String? errorText;
  final String? helperText;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool autofocus;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: _T.fieldHeight,
          decoration: BoxDecoration(
            color: form.field,
            borderRadius: BorderRadius.circular(_T.fieldRadius),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: controller,
                  initialValue: controller == null ? initialValue : null,
                  readOnly: readOnly,
                  autofocus: autofocus,
                  keyboardType: keyboardType,
                  inputFormatters: inputFormatters,
                  onChanged: onChanged,
                  onFieldSubmitted: onSubmitted,
                  style: const TextStyle(fontSize: _T.fieldFontSize),
                  decoration: InputDecoration.collapsed(
                    hintText: hint,
                    hintStyle: TextStyle(
                      fontSize: _T.fieldFontSize,
                      color: colors.muted,
                    ),
                  ),
                ),
              ),
              if (icon != null) Icon(icon, size: 22, color: colors.muted),
            ],
          ),
        ),
        if ((errorText ?? helperText) case final String text)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Text(
              text,
              style: TextStyle(
                fontSize: _T.captionSize,
                color: errorText != null
                    ? Theme.of(context).colorScheme.error
                    : colors.muted,
              ),
            ),
          ),
      ],
    );
  }
}

/// "Notas" panel with the attachment row below a thin divider.
class FormNotesPanel extends StatelessWidget {
  const FormNotesPanel({
    super.key,
    required this.fieldKey,
    required this.initialValue,
    required this.onChanged,
    required this.readOnly,
    this.showAttachment = true,
    this.errorText,
  });
  final Key fieldKey;
  final String initialValue;
  final ValueChanged<String> onChanged;
  final bool readOnly;
  final String? errorText;
  final bool showAttachment;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Material(
          color: form.field,
          borderRadius: BorderRadius.circular(_T.fieldRadius),
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: [
              SizedBox(
                height: _T.notesHeight,
                child: Stack(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 44, 8),
                      child: TextFormField(
                        key: fieldKey,
                        initialValue: initialValue,
                        readOnly: readOnly,
                        maxLines: null,
                        expands: true,
                        onChanged: onChanged,
                        style: const TextStyle(fontSize: _T.fieldFontSize),
                        decoration: InputDecoration.collapsed(
                          hintText: l.formNotesHint,
                          hintStyle: TextStyle(
                            fontSize: _T.fieldFontSize,
                            color: colors.muted,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      right: 14,
                      bottom: 12,
                      child: Icon(
                        Icons.sticky_note_2_rounded,
                        size: 20,
                        color: colors.muted,
                      ),
                    ),
                  ],
                ),
              ),
              if (showAttachment) ...[
                Divider(height: 1, thickness: 1, color: form.fieldDivider),
                InkWell(
                  key: const Key('form-add-attachment'),
                  // TODO(T-515): attachments are a Phase 6 feature; design only.
                  onTap: () {},
                  child: SizedBox(
                    height: _T.attachmentHeight,
                    child: Row(
                      children: [
                        const SizedBox(width: 14),
                        const Icon(Icons.attach_file_rounded, size: 22),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            l.formAddAttachment,
                            style: const TextStyle(fontSize: _T.fieldFontSize),
                          ),
                        ),
                        const Icon(Icons.add_rounded, size: 24),
                        const SizedBox(width: 14),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        if (errorText != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Text(
              errorText!,
              style: TextStyle(
                fontSize: _T.captionSize,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
          ),
      ],
    );
  }
}

/// Grey "Más opciones" pill.
class FormMoreOptionsPill extends StatelessWidget {
  const FormMoreOptionsPill({
    super.key,
    required this.onTap,
    this.expanded = false,
  });
  final VoidCallback onTap;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    if (expanded) {
      Widget line() => Expanded(
        child: Divider(
          height: _T.moreDividerThickness,
          thickness: _T.moreDividerThickness,
          color: form.emptyCategory,
        ),
      );
      return InkWell(
        key: const Key('form-more-options'),
        onTap: onTap,
        child: SizedBox(
          height: _T.moreDividerHeight,
          child: Row(
            children: [
              line(),
              const SizedBox(width: _T.moreDividerLabelGap),
              Text(
                l.formMoreOptions,
                style: TextStyle(
                  fontSize: _T.pillFontSize,
                  height: _T.optionLabelHeight,
                  color: colors.muted,
                ),
              ),
              const SizedBox(width: _T.moreDividerLabelGap),
              line(),
            ],
          ),
        ),
      );
    }
    return Center(
      child: Material(
        color: form.pill,
        borderRadius: BorderRadius.circular(_T.pillRadius),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: const Key('form-more-options'),
          onTap: onTap,
          child: Container(
            height: _T.pillHeight,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Center(
              widthFactor: 1,
              child: Text(
                l.formMoreOptions,
                style: TextStyle(
                  fontSize: _T.pillFontSize,
                  color: colors.muted,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Cashew's include-amount switch; persistence remains the caller's concern.
class FormIncludeAmountCard extends StatelessWidget {
  const FormIncludeAmountCard({
    super.key,
    required this.value,
    required this.onChanged,
  });
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    return Material(
      key: const Key('form-include-amount-card'),
      color: form.card,
      borderRadius: BorderRadius.circular(_T.optionCardRadius),
      child: SizedBox(
        height: _T.optionCardHeight,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: _T.sidePadding),
          child: Row(
            children: [
              Icon(
                value ? Icons.check_circle_rounded : Icons.cancel_rounded,
                size: _T.optionIconSize,
                color: colors.muted,
              ),
              const SizedBox(width: _T.optionSectionGap),
              Expanded(
                child: Text(
                  l.formIncludeAmount,
                  style: const TextStyle(
                    fontSize: _T.optionLabelSize,
                    height: _T.optionLabelHeight,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Switch(
                key: const Key('form-include-amount'),
                value: value,
                onChanged: onChanged,
                activeTrackColor: form.switchTrack,
                activeThumbColor: form.switchThumb,
                inactiveTrackColor: form.field,
                inactiveThumbColor: colors.muted,
                trackOutlineColor: WidgetStateProperty.resolveWith(
                  (states) => states.contains(WidgetState.selected)
                      ? form.switchTrack
                      : form.chipBorder,
                ),
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Bottom bar with rounded top corners; select-category or save.
class FormBottomAction extends StatelessWidget {
  const FormBottomAction({
    super.key,
    required this.label,
    required this.busy,
    required this.onPressed,
  });
  final String label;
  final bool busy;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    return Center(
      heightFactor: 1,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: _T.maxWidth),
        child: SizedBox(
          width: double.infinity,
          height: _T.actionHeight + MediaQuery.paddingOf(context).bottom,
          child: FilledButton(
            key: const Key('save-transaction'),
            onPressed: onPressed,
            style: FilledButton.styleFrom(
              backgroundColor: form.action,
              foregroundColor: form.onAction,
              disabledBackgroundColor: form.action.withValues(alpha: .6),
              disabledForegroundColor: form.onAction.withValues(alpha: .6),
              padding: EdgeInsets.only(
                bottom: MediaQuery.paddingOf(context).bottom,
              ),
              shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(_T.actionRadius),
                ),
              ),
            ),
            child: busy
                ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: form.onAction,
                    ),
                  )
                : Text(
                    label,
                    style: const TextStyle(
                      fontSize: _T.actionFontSize,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}
