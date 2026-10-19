// Derived from Cashew pages/editHomePage.dart and widgets/editRowEntry.dart.
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-18: typed server
// preferences, six independent components and rollback on save failure.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../session/session_controller.dart';
import '../theme/monetae_theme.dart';
import 'home_page.dart';

// Cashew EditRowEntry: 18dp radius, 10/5dp outer insets, 18/16dp
// content insets, bold 17dp labels and a 40dp drag handle.
abstract final class _EditTokens {
  static const radius = 18.0;
  static const rowHeight = 80.0;
  static const labelSize = 17.0;
  static const iconGap = 13.0;
  static const handleWidth = 40.0;
  static const maxWidth = 760.0;
}

class EditHomePage extends StatefulWidget {
  const EditHomePage({super.key, required this.session});
  final SessionController session;

  @override
  State<EditHomePage> createState() => _EditHomePageState();
}

class _EditHomePageState extends State<EditHomePage> {
  late List<String> _visible;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _visible = List.of(
      visibleHomeWidgets(widget.session.user?.preferences.homeWidgets),
    );
  }

  List<String> get _order => [
    ..._visible,
    ...defaultHomeWidgets.where((key) => !_visible.contains(key)),
  ];

  Future<void> _save(List<String> next) async {
    final session = widget.session;
    if (session.saving || session.busy || session.user == null) return;
    final previous = _visible;
    setState(() {
      _visible = next;
      _failed = false;
    });
    await session.updateHomeWidgets(next);
    if (!mounted) return;
    setState(() {
      _failed = session.error != null;
      if (_failed) _visible = previous;
    });
  }

  void _toggle(String key) {
    if (_visible.contains(key)) {
      if (_visible.length > 1) {
        _save(_visible.where((item) => item != key).toList());
      }
    } else {
      _save([..._visible, key]);
    }
  }

  void _reorder(int oldIndex, int newIndex) {
    final order = _order;
    final key = order.removeAt(oldIndex);
    order.insert(newIndex, key);
    final next = order.where(_visible.contains).toList();
    // Hidden rows always return to the end, in default order.
    if (next.join(',') != _visible.join(',')) _save(next);
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.session,
    builder: (context, _) {
      final l = AppLocalizations.of(context);
      final session = widget.session;
      final disabled = session.saving || session.busy || session.user == null;
      final entries = {
        'accounts': (l.accounts, Icons.account_balance_wallet_rounded),
        'goals': (l.goals, Icons.flag_rounded),
        'budgets': (l.budgets, Icons.pie_chart_rounded),
        'categories': (l.categoryDistribution, Icons.donut_large_rounded),
        'cash_flow': (l.cumulativeCashFlow, Icons.show_chart_rounded),
        'transactions': (l.latestTransactions, Icons.payments_rounded),
      };
      final order = _order;
      return PopScope(
        canPop: !session.saving,
        child: Scaffold(
          appBar: AppBar(
            leading: BackButton(
              onPressed: () {
                if (!session.saving) Navigator.of(context).maybePop();
              },
            ),
            title: Text(l.editHomeTitle),
          ),
          body: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: _EditTokens.maxWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_failed && session.error != null)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        session.error!.message(l),
                        key: const Key('edit-home-error'),
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  if (session.saving)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(l.savingPreferences),
                    ),
                  Expanded(
                    child: ReorderableListView.builder(
                      buildDefaultDragHandles: false,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      itemCount: order.length,
                      onReorderItem: _reorder,
                      itemBuilder: (context, index) {
                        final key = order[index];
                        final (name, icon) = entries[key]!;
                        final visible = _visible.contains(key);
                        final last = visible && _visible.length == 1;
                        return Padding(
                          key: ValueKey('edit-home-$key'),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 5,
                          ),
                          child: Material(
                            color: MonetaeColors.of(context).card,
                            borderRadius: BorderRadius.circular(
                              _EditTokens.radius,
                            ),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(
                                _EditTokens.radius,
                              ),
                              onTap: disabled || last
                                  ? null
                                  : () => _toggle(key),
                              child: SizedBox(
                                height: _EditTokens.rowHeight,
                                child: Row(
                                  children: [
                                    const SizedBox(width: 18),
                                    Icon(icon),
                                    const SizedBox(width: _EditTokens.iconGap),
                                    Expanded(
                                      child: Text(
                                        name,
                                        style: const TextStyle(
                                          fontSize: _EditTokens.labelSize,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                    Tooltip(
                                      message: last ? l.editHomeMinimum : name,
                                      child: Switch(
                                        key: ValueKey('edit-home-switch-$key'),
                                        value: visible,
                                        activeTrackColor: MonetaeColors.of(
                                          context,
                                        ).muted,
                                        activeThumbColor: MonetaeColors.of(
                                          context,
                                        ).background,
                                        onChanged: disabled || last
                                            ? null
                                            : (_) => _toggle(key),
                                      ),
                                    ),
                                    ReorderableDragStartListener(
                                      key: ValueKey('edit-home-drag-$key'),
                                      index: index,
                                      enabled: !disabled,
                                      child: Tooltip(
                                        message: l.editHomeReorder(name),
                                        child: const SizedBox(
                                          width: _EditTokens.handleWidth,
                                          height: _EditTokens.rowHeight,
                                          child: Icon(
                                            Icons.drag_handle_rounded,
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    },
  );
}
