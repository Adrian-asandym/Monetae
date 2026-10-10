// Derived from Cashew widgets/{bottomNavBar,navigationSidebar}.dart and
// struct/navBarIconsData.dart. Copyright James Kokoska, GPL-3.0.
// Modified 2026-10-10: four fixed destinations, native bar/rail and i18n.
import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';

class AppNavigation extends StatelessWidget {
  const AppNavigation({
    super.key,
    required this.index,
    required this.onChanged,
    this.rail = false,
  });
  final int index;
  final ValueChanged<int> onChanged;
  final bool rail;
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final labels = [l.home, l.transactions, l.budgets, l.more];
    const icons = [
      Icons.home_rounded,
      Icons.payments_rounded,
      Icons.donut_small_rounded,
      Icons.more_horiz_rounded,
    ];
    if (rail) {
      return NavigationRail(
        key: const Key('navigation-rail'),
        backgroundColor: MonetaeColors.of(context).background,
        indicatorColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        selectedIndex: index,
        onDestinationSelected: onChanged,
        labelType: NavigationRailLabelType.all,
        destinations: [
          for (var i = 0; i < 4; i++)
            NavigationRailDestination(
              icon: Icon(icons[i]),
              label: Text(labels[i]),
            ),
        ],
      );
    }
    return NavigationBarTheme(
      data: NavigationBarThemeData(
        backgroundColor: MonetaeColors.of(context).background,
        indicatorColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        surfaceTintColor: Colors.transparent,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 13,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.bold
                : FontWeight.normal,
          ),
        ),
      ),
      child: NavigationBar(
        key: const Key('bottom-navigation'),
        selectedIndex: index,
        onDestinationSelected: onChanged,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        destinations: [
          for (var i = 0; i < 4; i++)
            NavigationDestination(
              key: Key('nav-$i'),
              icon: Icon(icons[i]),
              label: labels[i],
            ),
        ],
      ),
    );
  }
}
