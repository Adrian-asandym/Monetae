import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/transaction_feed.dart';
import '../widgets/transaction_category_grid.dart';
import '../widgets/transaction_form/form_sheet.dart';
import 'new_transaction_page.dart';
import '../l10n/app_localizations.dart';
import '../presentation/transaction_presenter.dart';
import '../session/session_controller.dart';
import '../widgets/brand_logo.dart';
import '../widgets/transaction_card_list.dart';
import '../widgets/transaction_card_settings.dart';

class TransactionsPage extends StatefulWidget {
  const TransactionsPage({
    super.key,
    required this.session,
    required this.onDemo,
    this.onHome,
    this.categoryIds = const [],
    this.dateFrom,
    this.dateTo,
  });
  final List<String> categoryIds;
  final String? dateFrom;
  final String? dateTo;
  final SessionController session;
  final VoidCallback onDemo;
  final VoidCallback? onHome;
  @override
  State<TransactionsPage> createState() => _TransactionsPageState();
}

class _TransactionsPageState extends State<TransactionsPage> {
  late TransactionFeed _feed;
  late List<String> _categoryIds;
  int _loadRevision = 0;
  bool _loading = true;
  ApiException? _error;
  late int _transactionRevision;
  @override
  void initState() {
    super.initState();
    _transactionRevision = widget.session.transactionRevision;
    widget.session.addListener(_sessionChanged);
    _categoryIds = List.of(widget.categoryIds);
    _feed = TransactionFeed(
      widget.session.api,
      categoryIds: _categoryIds,
      dateFrom: widget.dateFrom,
      dateTo: widget.dateTo,
    );
    _load(refresh: true);
  }

  void _sessionChanged() {
    if (_transactionRevision != widget.session.transactionRevision) {
      _transactionRevision = widget.session.transactionRevision;
      _load(refresh: true);
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    widget.session.removeListener(_sessionChanged);
    super.dispose();
  }

  Future<void> _load({bool refresh = false}) async {
    final revision = ++_loadRevision;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (refresh) {
        final feed = TransactionFeed(
          widget.session.api,
          categoryIds: List.of(_categoryIds),
          dateFrom: widget.dateFrom,
          dateTo: widget.dateTo,
        );
        await feed.load();
        if (mounted && revision == _loadRevision) _feed = feed;
      } else {
        await _feed.loadMore();
      }
    } on ApiException catch (e) {
      if (mounted && revision == _loadRevision) _error = e;
    } on Object {
      if (mounted && revision == _loadRevision) {
        _error = const ApiException(ApiErrorKind.unavailable);
      }
    }
    if (mounted && revision == _loadRevision) setState(() => _loading = false);
  }

  Future<void> _filter() async {
    final selected = await showFormSheet<String>(
      context,
      key: const Key('transaction-filter-sheet'),
      title: AppLocalizations.of(context).formCategorySheetTitle,
      expand: true,
      builder: (sheet) => TransactionCategoryGrid(
        showUncategorized: false,
        categories: _feed.categories.values
            .where((c) => c.deletedAt == null)
            .toList(),
        selectedId: _categoryIds.length == 1 ? _categoryIds.single : null,
        uncategorizedSelected: _categoryIds.isEmpty,
        onSelected: (id) => Navigator.pop(sheet, id ?? ''),
      ),
    );
    if (!mounted || selected == null) return;
    _categoryIds = selected.isEmpty ? [] : [selected];
    await _load(refresh: true);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final profile = widget.session.user;
    if (profile == null) return const SizedBox.shrink();
    final error = _error ?? widget.session.error;
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        key: const Key('transactions-add'),
        heroTag: 'transactions-add-transaction',
        tooltip: l.addTransaction,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
        onPressed: () => Navigator.of(context).pushNamed('/transactions/new'),
        child: const Icon(Icons.add_rounded, size: 32),
      ),
      appBar: AppBar(
        leading: Navigator.of(context).canPop()
            ? const BackButton()
            : const Padding(
                padding: EdgeInsets.all(8),
                child: BrandLogo(size: 40),
              ),
        title: Text(l.transactions),
        actions: [
          IconButton(
            key: const Key('transaction-category-filter'),
            tooltip: l.filterTransactionCategory,
            onPressed: _loading ? null : _filter,
            icon: const Icon(Icons.filter_alt_outlined),
          ),
          IconButton(
            tooltip: l.home,
            icon: const Icon(Icons.home_outlined),
            onPressed: widget.onHome,
          ),
          IconButton(
            tooltip: l.refresh,
            onPressed: _loading ? null : () => _load(refresh: true),
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: l.demo,
            onPressed: widget.onDemo,
            icon: const Icon(Icons.widgets_outlined),
          ),
          IconButton(
            tooltip: l.signOut,
            onPressed: widget.session.busy ? null : widget.session.logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_categoryIds.isNotEmpty)
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final id in _categoryIds)
                        InputChip(
                          key: Key('category-filter-$id'),
                          label: Text(
                            _feed.categories[id]?.name ??
                                l.filterTransactionCategory,
                          ),
                          onDeleted: () {
                            _categoryIds = _categoryIds
                                .where((value) => value != id)
                                .toList();
                            _load(refresh: true);
                          },
                        ),
                    ],
                  ),
                AbsorbPointer(
                  absorbing: widget.session.saving || widget.session.busy,
                  child: TransactionCardSettings(
                    preferences: profile.preferences.transactionCard,
                    onChanged: widget.session.updateCard,
                  ),
                ),
                if (widget.session.saving) Text(l.savingPreferences),
                if (error != null) ...[
                  Text(
                    error.message(l),
                    key: const Key('feed-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                  TextButton(
                    onPressed: _loading
                        ? null
                        : () => _load(refresh: _feed.transactions.isEmpty),
                    child: Text(l.retry),
                  ),
                ],
                if (!_loading && _feed.transactions.isEmpty && _error == null)
                  Text(l.emptyTransactions),
                TransactionCardList(
                  models: presentTransactions(_feed, l),
                  onTap: (model) => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => NewTransactionPage(
                        session: widget.session,
                        transactionId: model.transaction.id,
                      ),
                    ),
                  ),
                  onEdit: (model) => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => NewTransactionPage(
                        session: widget.session,
                        transactionId: model.transaction.id,
                      ),
                    ),
                  ),
                  preferences: profile.preferences.transactionCard,
                ),
                if (_loading) const Center(child: CircularProgressIndicator()),
                if (_feed.nextCursor != null && !_loading)
                  TextButton(
                    key: const Key('load-more'),
                    onPressed: _load,
                    child: Text(l.loadMore),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
