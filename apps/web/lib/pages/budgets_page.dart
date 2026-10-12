// Derived from Cashew pages/budgetsListPage.dart. James Kokoska, GPL-3.0.
// Modified 2026-10-10: typed paginated API, independent loading and retry.
import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/home_controller.dart';
import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../presentation/clock.dart';
import '../widgets/budget_goal_lists.dart';
import '../widgets/home_block_view.dart';

class BudgetsPage extends StatefulWidget {
  const BudgetsPage({super.key, required this.api, this.today});
  final ApiClient api;
  final DateTime? today;
  @override
  State<BudgetsPage> createState() => _BudgetsPageState();
}

class _BudgetsPageState extends State<BudgetsPage> {
  late final HomeBlock<List<BudgetDto>> _block;
  @override
  void initState() {
    super.initState();
    _block = HomeBlock(() => loadBudgets(widget.api))..addListener(_changed);
    _block.load();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _block.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.budgets),
        actions: [
          IconButton(
            tooltip: l.refresh,
            onPressed: _block.load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(13),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: HomeBlockView(
              block: _block,
              title: l.budgets,
              builder: (budgets) => BudgetCardList(
                budgets: budgets,
                axis: Axis.vertical,
                today:
                    widget.today ??
                    PresentationClock.of(context)
                        .toUtc()
                        .subtract(const Duration(hours: 5)),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
