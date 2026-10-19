// Derived from Cashew pages/homePage/homePage.dart, homePageUsername.dart,
// homeTransactions.dart and widgets/navigationFramework.dart (AddFAB).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-10: independent API blocks,
// persisted preferences, server cumulative chart and Monetae navigation.
import 'package:flutter/material.dart';

import '../api/home_controller.dart';
import '../l10n/app_localizations.dart';
import '../presentation/clock.dart';
import '../presentation/transaction_presenter.dart';
import '../session/session_controller.dart';
import '../widgets/home_edit_button.dart';
import '../widgets/budget_goal_lists.dart';
import '../widgets/cumulative_cash_flow_chart.dart';
import '../widgets/home_accounts.dart';
import '../widgets/home_block_view.dart';
import '../widgets/home_category_carousel.dart';
import '../widgets/home_greeting.dart';
import '../widgets/transaction_card_list.dart';
import 'add_account_page.dart';
import 'add_goal_page.dart';
import 'new_transaction_page.dart';

const defaultHomeWidgets = [
  'accounts',
  'goals',
  'budgets',
  'categories',
  'cash_flow',
  'transactions',
];

List<String> visibleHomeWidgets(List<String>? preference) {
  final known =
      preference?.where(defaultHomeWidgets.contains).toSet().toList() ??
      <String>[];
  return known.isEmpty ? defaultHomeWidgets : known;
}

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.session,
    this.today,
    this.animate = true,
    this.onViewTransactions,
  });
  final SessionController session;
  final DateTime? today;
  final bool animate;
  final VoidCallback? onViewTransactions;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late final HomeController _home;
  late final DateTime _today;
  late int _transactionRevision;
  @override
  void initState() {
    super.initState();
    _transactionRevision = widget.session.transactionRevision;
    _today =
        widget.today ??
        PresentationClock.read(context)
            .toUtc()
            .subtract(const Duration(hours: 5));
    _home = HomeController(
      widget.session.api,
      month: DateTime(_today.year, _today.month),
      reportCurrency: widget.session.user?.reportCurrency,
    );
    widget.session.addListener(_changed);
    for (final block in _home.blocks) {
      block.addListener(_changed);
    }
    _home.load();
  }

  void _changed() {
    if (_transactionRevision != widget.session.transactionRevision) {
      _transactionRevision = widget.session.transactionRevision;
      _home.load();
    }
    if (mounted) setState(() {});
  }

  Future<void> _createAccount() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => AddAccountPage(
          api: widget.session.api,
          baseCurrency: widget.session.user!.baseCurrency,
        ),
      ),
    );
    if (mounted && created == true) await _home.accounts.load();
  }

  @override
  void dispose() {
    widget.session.removeListener(_changed);
    _home.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final session = widget.session;
    final profile = session.user;
    if (profile == null) return const SizedBox.shrink();
    final sections = <String, Widget>{
      'accounts': HomeBlockView(
        block: _home.accounts,
        title: l.accounts,
        builder: (accounts) => HomeAccounts(
          accounts: accounts,
          selectedId: session.selectedAccountId,
          onCreate: _createAccount,
          onSelected: session.saving || session.busy
              ? null
              : session.updateDefaultAccount,
        ),
      ),
      'goals': HomeBlockView(
        block: _home.goals,
        title: l.goals,
        builder: (goals) => GoalCardList(
          goals: goals,
          onCreate: () async {
            final created = await Navigator.of(context).push<bool>(
              MaterialPageRoute(
                builder: (_) => AddGoalPage(
                  api: session.api,
                  baseCurrency: profile.baseCurrency,
                ),
              ),
            );
            if (mounted && created == true) await _home.goals.load();
          },
        ),
      ),
      'budgets': HomeBlockView(
        block: _home.budgets,
        title: l.budgets,
        builder: (budgets) => BudgetCardList(
          budgets: budgets,
          today: _today,
          onCreate: () {
            // TODO(T-514): connect when the budget creation form exists.
          },
        ),
      ),
      'categories': HomeBlockView(
        block: _home.categories,
        title: l.categoryDistribution,
        builder: (data) =>
            HomeCategoryCarousel(data: data, animate: widget.animate),
      ),
      'cash_flow': HomeBlockView(
        block: _home.flow,
        title: l.cumulativeCashFlow,
        builder: (rows) =>
            CumulativeCashFlowChart(rows: rows, animate: widget.animate),
      ),
      'transactions': HomeBlockView(
        block: _home.transactions,
        title: l.latestTransactions,
        builder: (feed) => feed.transactions.isEmpty
            ? Text(l.emptyTransactions)
            : TransactionCardList(
                models: presentTransactions(feed, l, homeToday: _today),
                preferences: profile.preferences.transactionCard,
                dailyFlow:
                    _home.dailyFlow.loading || _home.dailyFlow.error != null
                    ? null
                    : _home.dailyFlow.data,
                onViewTransactions: widget.onViewTransactions,
                isHome: true,
                onTap: (model) => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => NewTransactionPage(
                      session: widget.session,
                      transactionId: model.transaction.id,
                    ),
                  ),
                ),
              ),
      ),
    };
    return Scaffold(
      body: SingleChildScrollView(
        key: const Key('home-scroll'),
        padding: const EdgeInsets.fromLTRB(13, 13, 13, 96),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: HomeGreeting(
                        now: _today,
                        displayName: profile.displayName,
                      ),
                    ),
                    HomeEditButton(
                      onPressed: () {
                        // TODO(T-514): connect Home component reordering UI.
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                if (session.error != null)
                  Text(
                    session.error!.message(l),
                    key: const Key('session-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                if (session.saving) Text(l.savingPreferences),
                for (final key in visibleHomeWidgets(
                  profile.preferences.homeWidgets,
                ))
                  Padding(
                    key: Key('home-block-$key'),
                    padding: const EdgeInsets.only(bottom: 13),
                    child: sections[key],
                  ),
              ],
            ),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        key: const Key('add-transaction'),
        heroTag: 'home-add-transaction',
        tooltip: l.addTransaction,
        backgroundColor: Theme.of(context).brightness == Brightness.light
            ? Colors.grey.shade300
            : Colors.grey.shade700,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        onPressed: () => Navigator.of(context).pushNamed('/transactions/new'),
        child: const Icon(Icons.add_rounded, size: 32),
      ),
    );
  }
}
