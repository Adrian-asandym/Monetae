// Derived from Cashew widgets/navigationFramework.dart. James Kokoska, GPL-3.0.
// Modified 2026-10-10: authenticated tab shell, lazy mounting and native rail.
import 'package:flutter/material.dart';

import '../session/session_controller.dart';
import '../widgets/app_navigation.dart';
import 'home_page.dart';
import 'transactions_page.dart';
import 'budgets_page.dart';
import 'more_page.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.session, this.today});
  final SessionController session;
  final DateTime? today;
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;
  final _visited = <int>{0};
  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    final pages = <Widget>[
      HomePage(session: session, today: widget.today),
      TransactionsPage(
        session: session,
        onDemo: () => Navigator.of(context).pushNamed('/demo'),
        onHome: () => _select(0),
      ),
      BudgetsPage(api: session.api, today: widget.today),
      MorePage(session: session),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1000;
        return Scaffold(
          body: Row(
            children: [
              if (wide)
                AppNavigation(index: _index, onChanged: _select, rail: true),
              Expanded(
                key: const Key('app-pages'),
                child: IndexedStack(
                  index: _index,
                  children: [
                    for (var i = 0; i < pages.length; i++)
                      _visited.contains(i) ? pages[i] : const SizedBox.shrink(),
                  ],
                ),
              ),
            ],
          ),
          bottomNavigationBar: wide
              ? null
              : AppNavigation(index: _index, onChanged: _select),
        );
      },
    );
  }

  void _select(int index) => setState(() {
    _index = index;
    _visited.add(index);
  });
}
