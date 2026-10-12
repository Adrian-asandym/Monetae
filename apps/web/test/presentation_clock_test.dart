import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/pages/budgets_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/presentation/clock.dart';
import 'package:monetae_web/widgets/budget_card.dart';
import 'package:monetae_web/widgets/goal_card.dart';

import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;

void main() {
  harness.loadGoldenFonts();
  testWidgets('cards follow the shared clock when its date changes', (
    tester,
  ) async {
    // Both dates are injected: the host's date cannot affect these assertions.
    for (final (date, goalLabel, inPeriod) in [
      (DateTime.utc(2026, 10, 9), '10,73 S/./día para 115 días', true),
      (DateTime.utc(2027, 2, 1), 'Objetivo atrasado', false),
    ]) {
      await harness.mount(
        tester,
        Brightness.light,
        (_, l) => Column(
          children: [
            GoalCard(goal: mockGoals(l).first),
            BudgetCard(budget: mockBudgets(l).first),
          ],
        ),
        now: () => date,
        captureSize: const Size(600, 700),
        viewSize: const Size(800, 800),
      );
      await tester.pumpAndSettle();
      expect(find.text(goalLabel), findsOneWidget);
      expect(
        find.byKey(const Key('today-marker')),
        inPeriod ? findsOneWidget : findsNothing,
      );
      expect(
        find.text('Puedes gastar 55,02 S/./día para 23 días más'),
        inPeriod ? findsOneWidget : findsNothing,
      );
      expect(tester.takeException(), isNull);
    }
  });

  for (final date in [
    DateTime.utc(2026, 10, 9, 15),
    DateTime.utc(2027, 2, 1, 15),
  ]) {
    testWidgets('pages use injected clock without today overrides: $date', (
      tester,
    ) async {
      final fixture = home.HomeFixture();
      addTearDown(fixture.close);
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => HomePage(session: fixture.session, animate: false),
        now: () => date,
      );
      await tester.pumpAndSettle();
      final expectedMonth =
          '${date.year}-${date.month.toString().padLeft(2, '0')}-01';
      expect(
        fixture.requests
            .where((r) => r.url.path == '/api/v1/reports/categories')
            .single
            .url
            .queryParameters['date_from'],
        expectedMonth,
      );
      final context = tester.element(find.byType(HomePage));
      expect(PresentationClock.read(context), date);
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => BudgetsPage(api: fixture.api),
        now: () => date,
        captureSize: const Size(650, 1200),
        viewSize: const Size(800, 1300),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('today-marker')),
        date.year == 2026 ? findsNWidgets(3) : findsNothing,
      );
      expect(tester.takeException(), isNull);
    });
  }
}
