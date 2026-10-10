import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

/// T-510 will replace this route with the transaction form.
class NewTransactionPage extends StatelessWidget {
  const NewTransactionPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.addTransaction)),
      body: Center(child: Text(l.comingSoon)),
    );
  }
}
