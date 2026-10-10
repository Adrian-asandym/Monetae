import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/api/home_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_reports.dart';
import 'package:monetae_web/widgets/home_category_carousel.dart';
import 'package:monetae_web/widgets/home_category_details.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/pages/app_shell.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/widgets/budget_goal_lists.dart';
import 'package:monetae_web/widgets/goal_card.dart';
import 'package:monetae_web/widgets/budget_card.dart';

import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;

Future<void> mountMobile(
  WidgetTester tester,
  Brightness brightness,
  harness.ComponentBuilder builder,
) async {
  tester.view.physicalSize = const Size(400, 642);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: monetaeTheme(brightness: brightness),
      locale: const Locale('es'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: RepaintBoundary(
        key: const Key('capture'),
        child: Builder(
          builder: (context) => MediaQuery(
            data: MediaQuery.of(context).copyWith(disableAnimations: true),
            child: builder(context, AppLocalizations.of(context)),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> golden(WidgetTester tester, String name) async {
  expect(tester.takeException(), isNull);
  await expectLater(
    find.byKey(const Key('capture')),
    matchesGoldenFile('goldens/t514_$name.png'),
  );
}

void main() {
  harness.loadGoldenFonts();
  for (final brightness in Brightness.values) {
    final mode = brightness.name;
    testWidgets('Home v2 at 400x642 $mode', (tester) async {
      final f = home.HomeFixture();
      addTearDown(f.close);
      await mountMobile(
        tester,
        brightness,
        (_, _) => AppShell(session: f.session, today: home.today),
      );
      await golden(tester, 'home_$mode');
    });
    for (final emptyIncome in [false, true]) {
      testWidgets(
        'same pie page for both kinds; empty income=$emptyIncome $mode',
        (tester) async {
          await mountMobile(tester, brightness, (_, l) {
            final report = mockReports(l);
            return Scaffold(
              body: Padding(
                padding: const EdgeInsets.all(13),
                child: HomeCategoryCarousel(
                  animate: false,
                  data: HomeCategoryData([
                    for (final row in report.rows)
                      if (!emptyIncome ||
                          row.kind != CategoryReportRowKind.income)
                        row,
                  ], report.categories),
                ),
              ),
            );
          });
          expect(
            tester
                .widget<HomeCategoryPiePage>(find.byType(HomeCategoryPiePage))
                .kind,
            CategoryReportRowKind.expense,
          );
          expect(find.byType(HomeCategoryDetails), findsNothing);
          expect(find.byIcon(Icons.chevron_left), findsNothing);
          expect(find.byIcon(Icons.arrow_drop_down), findsOneWidget);
          if (!emptyIncome) await golden(tester, 'pie_expense_$mode');
          await tester.drag(
            find.byKey(const Key('category-pages')),
            const Offset(-350, 0),
          );
          await tester.pumpAndSettle();
          expect(
            tester
                .widget<HomeCategoryPiePage>(find.byType(HomeCategoryPiePage))
                .kind,
            CategoryReportRowKind.income,
          );
          expect(find.byIcon(Icons.arrow_drop_up), findsOneWidget);
          final pie = tester.widget<CategoryPieChart>(
            find.byType(CategoryPieChart),
          );
          expect(pie.slices, emptyIncome ? isEmpty : hasLength(1));
          if (emptyIncome) expect(find.text('Sin datos'), findsOneWidget);
          await golden(
            tester,
            'pie_${emptyIncome ? 'empty_income' : 'income'}_$mode',
          );
          final active =
              tester
                      .widget<Container>(
                        find.byKey(const Key('category-dot-1')),
                      )
                      .decoration!
                  as BoxDecoration;
          final inactive =
              tester
                      .widget<Container>(
                        find.byKey(const Key('category-dot-0')),
                      )
                      .decoration!
                  as BoxDecoration;
          expect(active.color!.a, greaterThan(inactive.color!.a));
          await tester.tap(find.byKey(const Key('category-toggle-income')));
          await tester.pumpAndSettle();
          expect(
            tester
                .widget<HomeCategoryPiePage>(find.byType(HomeCategoryPiePage))
                .kind,
            CategoryReportRowKind.expense,
          );
        },
      );
    }
    for (final empty in [false, true]) {
      testWidgets('add cards end both carousels; empty=$empty $mode', (
        tester,
      ) async {
        var taps = 0;
        await mountMobile(
          tester,
          brightness,
          (_, l) => Scaffold(
            body: Padding(
              padding: const EdgeInsets.all(13),
              child: Column(
                children: [
                  GoalCardList(
                    goals: empty ? [] : [mockGoals(l).first],
                    onCreate: () => taps++,
                  ),
                  const SizedBox(height: 13),
                  BudgetCardList(
                    budgets: empty ? [] : [mockBudgets(l).first],
                    today: syntheticBudgetToday,
                    onCreate: () => taps++,
                  ),
                ],
              ),
            ),
          ),
        );
        expect(find.byType(HomeAddCard), findsNWidgets(2));
        if (empty) {
          expect(find.byType(GoalCard), findsNothing);
          expect(find.byType(BudgetCard), findsNothing);
        } else {
          for (final (cardType, listType) in [
            (GoalCard, GoalCardList),
            (BudgetCard, BudgetCardList),
          ]) {
            final list = find.byType(listType);
            final add = find.descendant(
              of: list,
              matching: find.byType(HomeAddCard),
            );
            final card = find.byType(cardType);
            expect(tester.getSize(add), tester.getSize(card));
            expect(
              tester.getTopLeft(add).dx,
              greaterThan(tester.getTopLeft(card).dx),
            );
            await tester.drag(
              find.descendant(
                of: list,
                matching: find.byType(SingleChildScrollView),
              ),
              const Offset(-400, 0),
            );
          }
          await tester.pumpAndSettle();
        }
        await tester.tap(find.text('Objetivo'));
        await tester.tap(find.text('Presupuesto'));
        expect(taps, 2);
        await tester.pumpAndSettle();
        await golden(tester, 'add_${empty ? 'empty' : 'data'}_$mode');
      });
    }
  }
}
