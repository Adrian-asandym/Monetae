import 'package:flutter/material.dart';

import '../api/home_controller.dart';
import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

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
    return Material(
      color: MonetaeColors.of(context).card,
      borderRadius: BorderRadius.circular(15),
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 13),
            if (block.loading)
              const SizedBox(
                height: 80,
                child: Center(child: CircularProgressIndicator()),
              )
            else if (block.error != null) ...[
              Text(
                block.error!.message(l),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: TextButton(onPressed: block.load, child: Text(l.retry)),
              ),
            ] else if (block.data != null)
              builder(block.data as T),
          ],
        ),
      ),
    );
  }
}
