import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../session/session_controller.dart';
import '../widgets/transaction_card_settings.dart';

class MorePage extends StatefulWidget {
  const MorePage({super.key, required this.session});
  final SessionController session;
  @override
  State<MorePage> createState() => _MorePageState();
}

class _MorePageState extends State<MorePage> {
  @override
  void initState() {
    super.initState();
    widget.session.addListener(_changed);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    widget.session.removeListener(_changed);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final session = widget.session;
    final profile = session.user;
    if (profile == null) return const SizedBox.shrink();
    return Scaffold(
      appBar: AppBar(title: Text(l.more)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AbsorbPointer(
                  absorbing: session.saving || session.busy,
                  child: Column(
                    children: [
                      Text(l.theme),
                      DropdownButton<UserPreferencesTheme>(
                        key: const Key('theme-preference'),
                        isExpanded: true,
                        value:
                            profile.preferences.theme ??
                            UserPreferencesTheme.system,
                        items: [
                          DropdownMenuItem(
                            value: UserPreferencesTheme.system,
                            child: Text(l.systemTheme),
                          ),
                          DropdownMenuItem(
                            value: UserPreferencesTheme.light,
                            child: Text(l.lightTheme),
                          ),
                          DropdownMenuItem(
                            value: UserPreferencesTheme.dark,
                            child: Text(l.darkTheme),
                          ),
                        ],
                        onChanged: (theme) {
                          if (theme != null) session.updateTheme(theme);
                        },
                      ),
                      TransactionCardSettings(
                        preferences: profile.preferences.transactionCard,
                        onChanged: session.updateCard,
                      ),
                    ],
                  ),
                ),
                if (session.saving) Text(l.savingPreferences),
                if (session.error != null)
                  Text(
                    session.error!.message(l),
                    key: const Key('session-error'),
                  ),
                const SizedBox(height: 20),
                Text(
                  l.syntheticData,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                for (final route in [
                  '/demo',
                  '/demo/home',
                  '/demo/budgets-goals',
                ])
                  ListTile(
                    leading: const Icon(Icons.widgets_outlined),
                    title: Text(
                      route == '/demo/home'
                          ? l.home
                          : route == '/demo/budgets-goals'
                          ? l.budgetGoalDemo
                          : l.demo,
                    ),
                    subtitle: Text(l.syntheticData),
                    onTap: () => Navigator.of(context).pushNamed(route),
                  ),
                const SizedBox(height: 20),
                ListTile(
                  key: const Key('sign-out'),
                  leading: const Icon(Icons.logout),
                  title: Text(l.signOut),
                  onTap: session.busy ? null : session.logout,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
