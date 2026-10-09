import 'package:flutter/material.dart';

import '../data/mock_budgets_goals.dart';
import '../data/mock_data.dart';
import '../l10n/app_localizations.dart';
import '../widgets/budget_goal_lists.dart';

/// Isolated component route; does not assemble/reorder the application's Home.
class BudgetGoalDemoPage extends StatefulWidget {
  const BudgetGoalDemoPage({
    super.key,
    required this.onThemeToggle,
    required this.onLocaleToggle,
  });
  final VoidCallback onThemeToggle;
  final VoidCallback onLocaleToggle;

  @override
  State<BudgetGoalDemoPage> createState() => _BudgetGoalDemoPageState();
}

class _BudgetGoalDemoPageState extends State<BudgetGoalDemoPage> {
  Axis _axis = Axis.horizontal;
  bool _empty = false;
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.budgetGoalDemo),
        actions: [
          IconButton(
            key: const Key('budget-goal-theme'),
            onPressed: widget.onThemeToggle,
            tooltip: Theme.of(context).brightness == Brightness.light
                ? l.darkTheme
                : l.lightTheme,
            icon: const Icon(Icons.brightness_6_outlined),
          ),
          IconButton(
            key: const Key('budget-goal-language'),
            onPressed: widget.onLocaleToggle,
            tooltip: l.language,
            icon: const Icon(Icons.translate),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(l.syntheticData),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  children: [
                    ChoiceChip(
                      label: Text(l.horizontalList),
                      selected: _axis == Axis.horizontal,
                      onSelected: (_) =>
                          setState(() => _axis = Axis.horizontal),
                    ),
                    ChoiceChip(
                      label: Text(l.verticalList),
                      selected: _axis == Axis.vertical,
                      onSelected: (_) => setState(() => _axis = Axis.vertical),
                    ),
                  ],
                ),
                SwitchListTile(
                  title: Text(l.showEmptyLists),
                  value: _empty,
                  onChanged: (value) => setState(() => _empty = value),
                  contentPadding: EdgeInsets.zero,
                ),
                const SizedBox(height: 16),
                Text(l.goals, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                GoalCardList(
                  goals: _empty ? [] : mockGoals(l),
                  axis: _axis,
                  customIcons: {mockCustomIconId: mockHouseBytes},
                ),
                const SizedBox(height: 24),
                Text(l.budgets, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                BudgetCardList(
                  budgets: _empty ? [] : mockBudgets(l),
                  axis: _axis,
                  today: syntheticBudgetToday,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
