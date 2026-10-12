// Derived from Cashew pages/addTransactionPage.dart (SelectTransactionTypePopup).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-11: localized presentation
// cards and a synthetic action tutorial; selection belongs to the parent form.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_localizations.dart';
import '../../presentation/currency_format.dart';
import '../../theme/monetae_theme.dart';

typedef _T = TransactionFormTokens;

/// Only standard/upcoming map to the current posted/scheduled API status.
/// TODO(T-515): the remaining types are presentation only.
enum FormTransactionType {
  standard,
  upcoming,
  subscription,
  repetitive,
  lend,
  borrow,
}

class TransactionTypeSheet extends StatelessWidget {
  const TransactionTypeSheet({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final FormTransactionType selected;
  final ValueChanged<FormTransactionType> onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    return DefaultTextStyle.merge(
      style: TextStyle(color: form.typeText),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final type in FormTransactionType.values) ...[
            Material(
              key: Key('type-card-${type.name}'),
              color: selected == type ? form.chipSelected : form.sheet,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(_T.typeCardRadius),
                side: BorderSide(
                  color: form.fieldDivider,
                  width: _T.typeCardBorder,
                ),
              ),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => onSelected(type),
                child: Padding(
                  padding: const EdgeInsets.all(_T.typeCardPadding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Icon(
                            _icon(type),
                            size: _T.typeCardIconSize,
                            color: MonetaeColors.of(context).muted,
                          ),
                          const SizedBox(width: _T.typeCardIconGap),
                          Expanded(
                            child: Text(
                              _label(type, l),
                              style: TextStyle(
                                color: form.typeText,
                                fontSize: _T.typeCardTitleSize,
                                fontWeight: FontWeight.bold,
                                height: _T.typeCardTitleHeight,
                              ),
                            ),
                          ),
                          if (_hasMenu(type))
                            IconButton(
                              key: Key('type-menu-${type.name}'),
                              tooltip: l.formMenu,
                              style: IconButton.styleFrom(
                                foregroundColor: form.typeText,
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints.tightFor(
                                width: _T.typeMenuSize,
                                height: _T.typeMenuSize,
                              ),
                              icon: const Icon(
                                Icons.more_vert_rounded,
                                size: _T.typeMenuSize,
                              ),
                              // TODO(T-515): type settings are design only.
                              onPressed: () {},
                            ),
                        ],
                      ),
                      if (type != FormTransactionType.standard) ...[
                        const SizedBox(height: _T.typeDescriptionGap),
                        for (final text in _descriptions(type, l))
                          Padding(
                            padding: const EdgeInsets.only(
                              top: _T.typeBulletGap,
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  width: _T.typeBulletIndent,
                                  child: Text(
                                    '•',
                                    style: TextStyle(
                                      color: form.typeText,
                                      fontSize: _T.typeBulletSize,
                                      height: _T.typeBulletHeight,
                                    ),
                                  ),
                                ),
                                Expanded(
                                  child: Text(
                                    text,
                                    style: TextStyle(
                                      color: form.typeText,
                                      fontSize: _T.typeBulletSize,
                                      height: _T.typeBulletHeight,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: _T.typeCardGap),
          ],
          const _ActionTutorial(),
          const SizedBox(height: _T.typeCardGap),
        ],
      ),
    );
  }
}

bool _hasMenu(FormTransactionType type) => switch (type) {
  FormTransactionType.upcoming ||
  FormTransactionType.subscription ||
  FormTransactionType.repetitive => true,
  _ => false,
};

IconData _icon(FormTransactionType type) => switch (type) {
  FormTransactionType.standard => Icons.check_circle_rounded,
  FormTransactionType.upcoming => Icons.event_rounded,
  FormTransactionType.subscription => Icons.event_repeat_rounded,
  FormTransactionType.repetitive => Icons.repeat_rounded,
  FormTransactionType.lend => Icons.unarchive_rounded,
  FormTransactionType.borrow => Icons.archive_rounded,
};

String _label(FormTransactionType type, AppLocalizations l) => switch (type) {
  FormTransactionType.standard => l.formTypeDefault,
  FormTransactionType.upcoming => l.formTypeUpcoming,
  FormTransactionType.subscription => l.formTypeSubscription,
  FormTransactionType.repetitive => l.formTypeRepetitive,
  FormTransactionType.lend => l.formTypeLend,
  FormTransactionType.borrow => l.formTypeBorrow,
};

List<String> _descriptions(FormTransactionType type, AppLocalizations l) =>
    switch (type) {
      FormTransactionType.standard => const [],
      FormTransactionType.upcoming => [l.formTypeUnpaid, l.formTypeNotInTotal],
      FormTransactionType.subscription => [
        l.formTypeSubscriptionDescription,
        l.formTypeNotInTotal,
        l.formTypeNextGenerated,
      ],
      FormTransactionType.repetitive => [
        l.formTypeRepetitiveDescription,
        l.formTypeNotInTotal,
        l.formTypeNextGenerated,
      ],
      FormTransactionType.lend => [
        l.formTypeLendDescription,
        l.formTypeLendCashFlow,
      ],
      FormTransactionType.borrow => [
        l.formTypeBorrowDescription,
        l.formTypeBorrowCashFlow,
      ],
    };

class _ActionTutorial extends StatelessWidget {
  const _ActionTutorial();

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);
    return Container(
      key: const Key('type-sheet-help'),
      padding: const EdgeInsets.all(_T.typeExamplePadding),
      decoration: BoxDecoration(
        color: form.timeBox,
        borderRadius: BorderRadius.circular(_T.typeCardRadius),
        border: Border.all(color: form.fieldDivider, width: _T.typeCardBorder),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(_T.typeExamplePadding),
            child: Text(
              l.formTypeHelp,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: _T.typeHelpFontSize),
            ),
          ),
          const SizedBox(height: _T.typeHelpGap),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: _T.typeHelpActionGap,
            runSpacing: _T.typeHelpActionGap,
            children: [
              for (final type in FormTransactionType.values.skip(1))
                SizedBox.square(
                  dimension: _T.typeHelpActionSize,
                  child: IconButton.filled(
                    key: Key('type-example-action-${type.name}'),
                    tooltip: _label(type, l),
                    style: IconButton.styleFrom(
                      backgroundColor: form.chipSelected,
                      foregroundColor: colors.muted,
                      padding: EdgeInsets.zero,
                    ),
                    icon: Icon(_icon(type), size: _T.typeHelpActionIconSize),
                    // TODO(T-515): instructional actions are design only.
                    onPressed: () {},
                  ),
                ),
            ],
          ),
          const SizedBox(height: _T.typeHelpGap),
          Container(
            key: const Key('type-example-entry'),
            padding: const EdgeInsets.all(_T.typeExamplePadding),
            decoration: BoxDecoration(
              color: form.dateBox,
              borderRadius: BorderRadius.circular(_T.typeCardRadius),
              border: Border.all(
                color: form.fieldDivider,
                width: _T.typeCardBorder,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: _T.typeExampleAvatarSize,
                  height: _T.typeExampleAvatarSize,
                  decoration: BoxDecoration(
                    color: form.switchTrack,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: _T.typeBulletGap),
                Container(
                  width: _T.typeHelpActionSize,
                  height: _T.typeHelpActionSize,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: colors.expense,
                      width: _T.typeExampleHighlightBorder,
                    ),
                  ),
                  child: Icon(
                    Icons.repeat_rounded,
                    size: _T.typeHelpActionIconSize,
                    color: colors.muted,
                  ),
                ),
                const SizedBox(width: _T.typeBulletGap),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l.sampleUpcoming,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: _T.typeHelpFontSize),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: _T.typeExampleAccountInset,
                        ),
                        decoration: BoxDecoration(
                          color: form.switchTrack,
                          borderRadius: BorderRadius.circular(
                            _T.typeExampleAccountRadius,
                          ),
                        ),
                        child: Text(
                          l.sampleAccount,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: _T.captionSize),
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.sticky_note_2_rounded,
                  size: _T.typeExampleNoteSize,
                  color: colors.muted,
                ),
                const SizedBox(width: _T.typeBulletGap),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      DateFormat.Hm(l.localeName)
                          .format(DateTime(2026, 1, 1, 21, 49)),
                      style: TextStyle(
                        fontSize: _T.captionSize,
                        color: colors.muted,
                      ),
                    ),
                    Row(
                      children: [
                        Icon(
                          Icons.arrow_drop_down_rounded,
                          size: _T.typeExampleNoteSize,
                          color: colors.muted,
                        ),
                        Text(
                          formatTypedAmount('100', 'PEN', l.localeName),
                          style: TextStyle(
                            fontSize: _T.typeExampleAmountSize,
                            fontWeight: FontWeight.bold,
                            color: colors.muted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
