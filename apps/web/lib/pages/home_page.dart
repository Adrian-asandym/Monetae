import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../api/report_feed.dart';
import '../data/mock_reports.dart';
import '../l10n/app_localizations.dart';
import '../widgets/brand_logo.dart';
import '../widgets/report_dashboard.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    this.api,
    this.reportCurrency,
    this.onTransactions,
    this.onDemo,
    this.onLogout,
    this.onThemeToggle,
    this.sessionError,
  });
  final ApiException? sessionError;
  final ApiClient? api;
  final String? reportCurrency;
  final VoidCallback? onTransactions;
  final VoidCallback? onDemo;
  final VoidCallback? onLogout;
  final VoidCallback? onThemeToggle;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late DateTime _month;
  ReportFeed? _feed;
  ApiException? _error;
  bool _loading = false;
  int _revision = 0;
  @override
  void initState() {
    super.initState();
    // Calendar display defaults to Lima; explicit boundaries are sent, never
    // depend on the browser timezone. The server buckets in the profile zone.
    final today = DateTime.now().toUtc().subtract(const Duration(hours: 5));
    _month = widget.api == null
        ? DateTime(2026, 10)
        : DateTime(today.year, today.month);
    if (widget.api != null) _load();
  }

  Future<void> _load() async {
    final api = widget.api;
    if (api == null) return;
    final revision = ++_revision;
    setState(() {
      _loading = true;
      _error = null;
      _feed = null;
    });
    try {
      final feed = await ReportFeed.load(
        api,
        dateFrom: DateFormat('yyyy-MM-dd').format(_month),
        dateTo: DateFormat('yyyy-MM-dd')
            .format(DateTime(_month.year, _month.month + 1, 0)),
        reportCurrency: widget.reportCurrency,
      );
      if (mounted && revision == _revision) setState(() => _feed = feed);
    } on ApiException catch (e) {
      if (mounted && revision == _revision) setState(() => _error = e);
    } on Object {
      if (mounted && revision == _revision) {
        setState(() => _error = const ApiException(ApiErrorKind.unavailable));
      }
    }
    if (mounted && revision == _revision) setState(() => _loading = false);
  }

  void _move(int delta) {
    setState(() => _month = DateTime(_month.year, _month.month + delta));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final feed = widget.api == null ? mockReports(l) : _feed;
    return Scaffold(
      appBar: AppBar(
        title: Text(l.home),
        actions: [
          if (widget.onTransactions != null)
            IconButton(
              key: const Key('home-transactions'),
              tooltip: l.transactions,
              onPressed: widget.onTransactions,
              icon: const Icon(Icons.receipt_long_outlined),
            ),
          if (widget.onDemo != null)
            IconButton(
              tooltip: l.demo,
              onPressed: widget.onDemo,
              icon: const Icon(Icons.widgets_outlined),
            ),
          if (widget.onLogout != null)
            IconButton(
              tooltip: l.signOut,
              onPressed: widget.onLogout,
              icon: const Icon(Icons.logout),
            ),
          if (widget.onThemeToggle != null)
            IconButton(
              key: const Key('home-theme-switch'),
              tooltip: Theme.of(context).brightness == Brightness.dark
                  ? l.lightTheme
                  : l.darkTheme,
              onPressed: widget.onThemeToggle,
              icon: const Icon(Icons.brightness_6_outlined),
            ),
          const BrandLogo(size: 36),
          if (widget.api != null)
            IconButton(
              tooltip: l.refresh,
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          const SizedBox(width: 12),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(13),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.api == null) Text(l.syntheticData),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      tooltip: l.previousMonth,
                      onPressed: widget.api == null ? null : () => _move(-1),
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Text(
                      DateFormat.yMMMM(l.localeName).format(_month),
                      style: const TextStyle(fontSize: 18),
                    ),
                    IconButton(
                      tooltip: l.nextMonth,
                      onPressed: widget.api == null ? null : () => _move(1),
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
                const SizedBox(height: 13),
                if (widget.sessionError != null)
                  Text(
                    widget.sessionError!.message(l),
                    key: const Key('session-error'),
                  ),
                if (_loading) const Center(child: CircularProgressIndicator()),
                if (_error != null) ...[
                  Text(_error!.message(l)),
                  TextButton(onPressed: _load, child: Text(l.retry)),
                ],
                if (feed != null) ReportDashboard(feed: feed),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
