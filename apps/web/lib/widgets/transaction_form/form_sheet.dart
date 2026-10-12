// Derived from Cashew widgets/openBottomSheet.dart (PopupFramework).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: Material modal sheet
// with Monetae tokens; Title Case heading and optional trailing action.
import 'package:flutter/material.dart';

import '../../theme/monetae_theme.dart';

typedef _T = TransactionFormTokens;

/// Opens a Cashew-style bottom sheet over a scrim.
Future<T?> showFormSheet<T>(
  BuildContext context, {
  required String title,
  required WidgetBuilder builder,
  Widget? trailing,
  Key? key,
  bool expand = false,
  double bottomPadding = _T.sheetPadding + 8,
}) {
  final form = TransactionFormColors.of(context);
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: form.sheet,
    barrierColor: Colors.black.withValues(alpha: .5),
    constraints: const BoxConstraints(maxWidth: _T.maxWidth),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(_T.sheetRadius)),
    ),
    builder: (context) {
      final body = _SheetBody(
        title: title,
        trailing: trailing,
        expand: expand,
        bottomPadding: bottomPadding,
        child: builder(context),
      );
      return Padding(
        key: key,
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: expand
            ? FractionallySizedBox(
                heightFactor: _T.expandedSheetHeightFraction,
                child: body,
              )
            : body,
      );
    },
  );
}

class _SheetBody extends StatelessWidget {
  const _SheetBody({
    required this.title,
    required this.child,
    required this.expand,
    required this.bottomPadding,
    this.trailing,
  });
  final String title;
  final Widget child;
  final Widget? trailing;
  final bool expand;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    final heading = Padding(
      padding: EdgeInsets.fromLTRB(
        _T.sheetPadding + 4,
        expand ? _T.expandedSheetHeadingTop : _T.sheetPadding + 8,
        _T.sheetPadding,
        expand ? _T.expandedSheetHeadingGap : _T.sheetPadding,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontSize: _T.sheetTitleSize,
                fontWeight: FontWeight.bold,
                height: 1.15,
              ),
            ),
          ),
          ?trailing,
        ],
      ),
    );
    final body = Padding(
      padding: EdgeInsets.fromLTRB(
        _T.sheetPadding,
        0,
        _T.sheetPadding,
        expand ? 0 : bottomPadding,
      ),
      child: child,
    );
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        heading,
        Flexible(child: expand ? body : SingleChildScrollView(child: body)),
      ],
    );
  }
}

/// Full-width rounded action used inside sheets ("Selecciona una categoría",
/// "Fijar importe").
class FormSheetButton extends StatelessWidget {
  const FormSheetButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.height = _T.sheetButtonHeight,
  });
  final String label;
  final VoidCallback? onPressed;
  final double height;

  @override
  Widget build(BuildContext context) {
    final form = TransactionFormColors.of(context);
    return SizedBox(
      height: height,
      child: FilledButton(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: form.sheetAction,
          foregroundColor: form.onAction,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_T.sheetButtonRadius),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontSize: _T.actionFontSize,
            fontWeight: FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
