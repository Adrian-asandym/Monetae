import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/transaction_feed.dart';
import '../l10n/app_localizations.dart';
import '../presentation/transaction_presenter.dart';
import '../session/session_controller.dart';
import '../widgets/brand_logo.dart';
import '../widgets/transaction_card_list.dart';
import '../widgets/transaction_card_settings.dart';
import 'home_page.dart';

class TransactionsPage extends StatefulWidget {
  const TransactionsPage({
    super.key,
    required this.session,
    required this.onDemo,
  });
  final SessionController session;
  final VoidCallback onDemo;
  @override
  State<TransactionsPage> createState() => _TransactionsPageState();
}

class _TransactionsPageState extends State<TransactionsPage> {
  late TransactionFeed _feed;
  bool _loading = true;
  ApiException? _error;
  @override
  void initState() {
    super.initState();
    widget.session.addListener(_sessionChanged);
    _feed = TransactionFeed(widget.session.api);
    _load(refresh: true);
  }

  void _sessionChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    widget.session.removeListener(_sessionChanged);
    super.dispose();
  }

  Future<void> _load({bool refresh = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (refresh) {
        final feed = TransactionFeed(widget.session.api);
        await feed.load();
        if (mounted) _feed = feed;
      } else {
        await _feed.loadMore();
      }
    } on ApiException catch (e) {
      if (mounted) _error = e;
    } on Object {
      if (mounted) _error = const ApiException(ApiErrorKind.unavailable);
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final profile = widget.session.user;
    if (profile == null) return const SizedBox.shrink();
    final error = _error ?? widget.session.error;
    return Scaffold(
      appBar: AppBar(
        leading: const Padding(
          padding: EdgeInsets.all(8),
          child: BrandLogo(size: 40),
        ),
        title: Text(l.transactions),
        actions: [
          IconButton(
            tooltip: l.home,
            icon: const Icon(Icons.home_outlined),
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute(
                builder: (_) => HomePage(
                  api: widget.session.api,
                  reportCurrency: profile.reportCurrency,
                ),
              ),
            ),
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
