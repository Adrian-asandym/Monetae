import 'package:flutter/material.dart';

import '../api/home_controller.dart';
import '../l10n/app_localizations.dart';

class HomeBlockView<T> extends StatelessWidget {
  const HomeBlockView({
    super.key,
    required this.block,
    required this.title,
    required this.builder,
  });
  final HomeBlock<T> block;
  final String title;
  final Widget Function(T) builder;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (block.loading) {
      return const SizedBox(
        height: 80,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (block.error != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            block.error!.message(l),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton(onPressed: block.load, child: Text(l.retry)),
          ),
        ],
      );
    }
    if (block.data != null) {
      return builder(block.data as T);
    }
    return const SizedBox.shrink();
  }
}
