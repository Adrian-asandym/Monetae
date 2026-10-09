import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';

class TransactionCardSettings extends StatelessWidget {
  const TransactionCardSettings({
    super.key,
    required this.preferences,
    required this.onChanged,
  });
  final TransactionCardPreferencesDto preferences;
  final ValueChanged<TransactionCardPreferencesDto> onChanged;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: Text(l.cardSettings),
      children: [
        _toggle(
          'show-date',
          l.showDate,
          preferences.showDate,
          (v) => preferences.copyWith(showDate: v),
        ),
        _toggle(
          'show-time',
          l.showTime,
          preferences.showTime,
          (v) => preferences.copyWith(showTime: v),
        ),
        _toggle(
          'show-note',
          l.showNote,
          preferences.showNote,
          (v) => preferences.copyWith(showNote: v),
        ),
        _toggle(
          'show-tags',
          l.showTags,
          preferences.showTags,
          (v) => preferences.copyWith(showTags: v),
        ),
        _toggle(
          'show-account',
          l.showAccount,
          preferences.showAccount,
          (v) => preferences.copyWith(showAccount: v),
        ),
        _toggle(
          'show-actions',
          l.showActions,
          preferences.showActions,
          (v) => preferences.copyWith(showActions: v),
        ),
      ],
    );
  }

  Widget _toggle(
    String key,
    String label,
    bool value,
    TransactionCardPreferencesDto Function(bool) update,
  ) => SwitchListTile(
    key: Key(key),
    title: Text(label),
    value: value,
    onChanged: (v) => onChanged(update(v)),
  );
}
