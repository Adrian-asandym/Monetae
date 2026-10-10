import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

String getWelcomeMessage(AppLocalizations l, DateTime now) {
  final h24 = now.hour;
  if (h24 >= 5 && h24 < 12) {
    return l.goodMorning;
  } else if (h24 >= 12 && h24 < 19) {
    return l.goodAfternoon;
  } else {
    return l.goodEvening;
  }
}

class HomeGreeting extends StatelessWidget {
  const HomeGreeting({
    super.key,
    this.displayName,
    required this.now,
  });

  final String? displayName;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final hasName = displayName != null && displayName!.trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        if (hasName)
          Text(
            getWelcomeMessage(l, now),
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 20,
            ),
          ),
        Text(
          hasName ? displayName! : l.home,
          key: const Key('home-greeting'),
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 33,
          ),
        ),
      ],
    );
  }
}
