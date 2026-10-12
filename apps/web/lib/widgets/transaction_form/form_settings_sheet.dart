// Derived from Cashew widgets/settingsContainers.dart and
// pages/editAssociatedTitlesPage.dart (AutoTitlesToggle),
// widgets/framework/popupFramework.dart (heading); capture 23.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-12 (T-515 piece 9):
// Monetae presentation preferences and design-only title/input settings.
import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../theme/monetae_theme.dart';
import 'form_settings.dart';
import 'form_sheet.dart';

typedef _T = TransactionFormTokens;

Future<void> showFormSettingsSheet(
  BuildContext context, {
  required TransactionFormSettings settings,
  required bool editing,
}) => showFormSheet<void>(
  context,
  key: const Key('form-settings-sheet'),
  title: editing
      ? AppLocalizations.of(context).formEditMenuTitle
      : AppLocalizations.of(context).formAddMenuTitle,
  horizontalPadding: _T.menuListInset,
  titleSize: _T.menuHeadingSize,
  headingTop: _T.menuHeadingTop,
  headingGap: _T.menuHeadingGap,
  bottomPadding: _T.menuBottomPadding,
  builder: (_) => FormSettingsSheet(settings: settings),
);

class FormSettingsSheet extends StatelessWidget {
  const FormSettingsSheet({super.key, required this.settings});
  final TransactionFormSettings settings;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final form = TransactionFormColors.of(context);
    final colors = MonetaeColors.of(context);

    Widget row({
      required String id,
      required IconData icon,
      required String title,
      required String subtitle,
      required VoidCallback onTap,
      bool? value,
      ValueChanged<bool>? onChanged,
    }) => InkWell(
      key: Key('form-setting-row-$id'),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _T.menuRowHorizontalPadding,
          vertical: _T.menuRowVerticalPadding,
        ),
        child: Row(
          children: [
            Icon(icon, size: _T.menuIconSize, color: colors.muted),
            const SizedBox(width: _T.menuIconGap),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: _T.menuTitleSize,
                      height: _T.menuTextHeight,
                      fontWeight: FontWeight.bold,
                      color: form.typeText,
                    ),
                  ),
                  const SizedBox(height: _T.menuSubtitleGap),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: _T.menuSubtitleSize,
                      height: _T.menuTextHeight,
                      color: form.menuSubtitle,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: _T.menuTrailingGap),
            if (value != null)
              Switch(
                key: Key('form-setting-$id'),
                padding: EdgeInsets.zero,
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
              )
            else
              SizedBox(
                width: _T.menuChevronWidth,
                child: Icon(
                  Icons.chevron_right_rounded,
                  size: _T.menuIconSize,
                  color: colors.muted,
                ),
              ),
          ],
        ),
      ),
    );

    return ListenableBuilder(
      listenable: settings,
      builder: (_, _) => Column(
        children: [
          row(
            id: 'transfer',
            icon: Icons.swap_horiz_rounded,
            title: l.formSettingTransferTitle,
            subtitle: l.formSettingTransferSubtitle,
            value: settings.showTransfer,
            onChanged: (value) => settings.showTransfer = value,
            onTap: () => settings.showTransfer = !settings.showTransfer,
          ),
          row(
            id: 'attachment',
            icon: Icons.attach_file_rounded,
            title: l.formSettingAttachmentTitle,
            subtitle: l.formSettingAttachmentSubtitle,
            value: settings.showAttachment,
            onChanged: (value) => settings.showAttachment = value,
            onTap: () => settings.showAttachment = !settings.showAttachment,
          ),
          row(
            id: 'auto-title',
            icon: Icons.post_add_rounded,
            title: l.formSettingAutoTitleTitle,
            subtitle: l.formSettingAutoTitleSubtitle,
            value: true,
            // TODO(T-515): automatic title/category associations are design only.
            onChanged: (_) {},
            onTap: () {},
          ),
          row(
            id: 'initial-input',
            icon: Icons.edit_square,
            title: l.formSettingInitialInputTitle,
            subtitle: l.formSettingInitialInputSubtitle,
            // TODO(T-515): initial input preference sheet is design only.
            onTap: () {},
          ),
        ],
      ),
    );
  }
}
