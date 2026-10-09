import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations_es.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/presentation/decimal_progress.dart';
import 'package:monetae_web/widgets/budget_card.dart';
import 'package:monetae_web/widgets/budget_goal_lists.dart';
import 'package:monetae_web/widgets/budget_progress.dart';
import 'package:monetae_web/widgets/goal_card.dart';

import 'components_test.dart' as harness;

final l = AppLocalizationsEs();

void main() {
  harness.loadGoldenFonts();
  test('decimal quotient is bounded, exact before geometry conversion', () {
    for (final (amount, target, expected) in [
      ('0.00', '100.00', 0.0),
      ('25.00', '100.00', .25),
      ('100.00', '100.00', 1.0),
      ('120.00', '100.00', 1.0),
      ('-20.00', '100.00', 0.0),
      ('1.0', '2.0000', .5),
      ('1.00', '0.00', 0.0),
      ('9007199254740993.00', '18014398509481986.00', .5),
    ]) {
      expect(DecimalProgress.fromAmounts(amount, target).fraction, expected);
    }
    expect(DecimalProgress.fromAmounts('120.00', '100.00').percent, '120');
    expect(
      DecimalProgress.fromAmounts('99.999', '100.00').reachedTarget,
      false,
    );
    expect(
      DecimalProgress.fromAmounts('1.00', '3.00').fraction,
      closeTo(1 / 3, .000001),
    );
    expect(
      () => DecimalProgress.fromAmounts('NaN', '10.00'),
      throwsFormatException,
    );
  });

  test('today uses supplied calendar dates and hides outside/open ranges', () {
    expect(
      todayFraction('2026-10-01', '2026-10-31', DateTime.utc(2026, 10, 16)),
      .5,
    );
    expect(
      todayFraction('2026-10-01', '2026-10-31', DateTime(2026, 10, 1, 23, 59)),
      0,
    );
    expect(
      todayFraction('2026-10-01', '2026-10-31', DateTime.utc(2026, 10, 31)),
      1,
    );
    expect(todayFraction('2026-10-09', '2026-10-09', syntheticBudgetToday), 0);
    expect(
      todayFraction('2026-10-01', '2026-10-31', DateTime.utc(2026, 11, 1)),
      isNull,
    );
    expect(
      todayFraction('2026-10-01', '2026-10-31', DateTime.utc(2026, 9, 30)),
      isNull,
    );
    expect(todayFraction('2026-10-01', null, syntheticBudgetToday), isNull);
    expect(todayFraction('2026-10-01', '2026-10-31', null), isNull);
  });

  test(
    '0.5.0 budget/goal pages preserve exact values, nested limits and nulls',
    () {
      final budgets = BudgetPageDto.fromJson({
        'items': mockBudgets(l).map((item) => item.toJson()).toList(),
        'next_cursor': 'next',
      });
      final goals = GoalPageDto.fromJson({
        'items': mockGoals(l).map((item) => item.toJson()).toList(),
        'next_cursor': null,
      });
      expect(budgets.items[2].remainingAmount, '-240.00');
      expect(budgets.items[1].categoryLimits.single.limitAmount, '500.00');
      expect(budgets.nextCursor, 'next');
      expect(goals.items[1].dueOn, isNull);
      expect(goals.items[2].color, isNull);
      expect(goals.items[2].icon, 'custom:$mockCustomIconId');
      expect(goals.items[0].kind, GoalKind.save);
      expect(goals.items[1].kind, GoalKind.spend);
      expect(
        () => budgets.items.add(mockBudgets(l).first),
        throwsUnsupportedError,
      );
      expect(
        () => BudgetDto.fromJson({
          ...mockBudgets(l).first.toJson(),
          'spent_amount': 1234.5,
        }),
        throwsFormatException,
      );
      expect(
        () =>
            GoalDto.fromJson({...mockGoals(l).first.toJson(), 'kind': 'loan'}),
        throwsFormatException,
      );
      final missing = mockGoals(l).first.toJson()..remove('color');
      expect(() => GoalDto.fromJson(missing), throwsFormatException);
      expect(
        GoalDto.fromJson({
          ...mockGoals(l).first.toJson(),
          'progress_amount': '9007199254740993.99',
        }).toJson()['progress_amount'],
        '9007199254740993.99',
      );
    },
  );

  for (final brightness in Brightness.values) {
    final mode = brightness.name;
    for (final (index, name) in [(0, 'current'), (1, 'nearly'), (2, 'over')]) {
      testWidgets('budget $name Peruvian labels and golden $mode', (
        tester,
      ) async {
        await harness.mount(
          tester,
          brightness,
          (_, l) => Align(
            alignment: Alignment.topCenter,
            child: BudgetCard(
              budget: mockBudgets(l)[index],
              today: syntheticBudgetToday,
            ),
          ),
          captureSize: const Size(600, 300),
        );
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('today-marker')), findsOneWidget);
        expect(
          tester
              .widget<BudgetProgress>(find.byType(BudgetProgress))
              .progress
              .fraction,
          [0.4938, .96, 1.0][index],
        );
        if (index == 0) {
          expect(
            find.text('S/ 1,265.50 restante de S/ 2,500.00'),
            findsOneWidget,
          );
          expect(
            find.text('Gastado: S/ 1,234.50 / S/ 2,500.00'),
            findsOneWidget,
          );
          expect(find.textContaining('Total convertido'), findsNothing);
        } else if (index == 1) {
          expect(
            find.text(r'US$ 20.00 restante de US$ 500.00'),
            findsOneWidget,
          );
          expect(find.text('Total convertido: S/ 1,824.00'), findsOneWidget);
        } else {
          expect(
            find.text('S/ 240.00 excedido de S/ 1,200.00'),
            findsOneWidget,
          );
          expect(find.text('120 %'), findsOneWidget);
        }
        expect(tester.takeException(), isNull);
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile('goldens/budget_${name}_$mode.png'),
        );
      });
    }
    for (final (index, name) in [(0, 'half'), (1, 'complete')]) {
      testWidgets('goal $name Peruvian labels and golden $mode', (
        tester,
      ) async {
        await harness.mount(
          tester,
          brightness,
          (_, l) => Align(
            alignment: Alignment.topCenter,
            child: GoalCard(goal: mockGoals(l)[index]),
          ),
          captureSize: const Size(600, 320),
        );
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('today-marker')), findsNothing);
        expect(
          find.text(
            index == 0
                ? 'S/ 1,234.50 / S/ 2,469.00'
                : r'US$ 1,800.00 / US$ 1,800.00',
          ),
          findsOneWidget,
        );
        expect(
          find.text(index == 0 ? l.savingsGoal : l.spendingGoal),
          findsOneWidget,
        );
        expect(
          find.text(l.goalComplete),
          index == 0 ? findsNothing : findsOneWidget,
        );
        expect(
          find.textContaining('Hasta'),
          index == 0 ? findsOneWidget : findsNothing,
        );
        expect(tester.takeException(), isNull);
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile('goldens/goal_${name}_$mode.png'),
        );
      });
    }
    for (final axis in Axis.values) {
      for (final empty in [false, true]) {
        for (final budgets in [true, false]) {
          final name =
              '${budgets ? 'budgets' : 'goals'}_${axis.name}_${empty ? 'empty' : 'data'}';
          testWidgets('list $name golden $mode', (tester) async {
            final size = empty
                ? const Size(600, 220)
                : axis == Axis.horizontal
                ? const Size(1200, 360)
                : const Size(650, 920);
            await harness.mount(
              tester,
              brightness,
              (_, l) => Align(
                alignment: Alignment.topCenter,
                child: budgets
                    ? BudgetCardList(
                        budgets: empty ? [] : mockBudgets(l),
                        axis: axis,
                        today: syntheticBudgetToday,
                      )
                    : GoalCardList(
                        goals: empty ? [] : mockGoals(l),
                        axis: axis,
                        customIcons: {mockCustomIconId: mockHouseBytes},
                      ),
              ),
              captureSize: size,
              viewSize: Size(size.width + 100, size.height + 100),
            );
            await tester.pumpAndSettle();
            if (empty) {
              expect(
                find.text(budgets ? l.emptyBudgets : l.emptyGoals),
                findsOneWidget,
              );
            }
            expect(tester.takeException(), isNull);
            await expectLater(
              find.byKey(const Key('capture')),
              matchesGoldenFile('goldens/${name}_$mode.png'),
            );
          });
        }
      }
    }
  }

  testWidgets(
    'dark half-progress percentage stays entirely inside the light fill',
    (tester) async {
      await harness.mount(
        tester,
        Brightness.dark,
        (_, l) => Align(
          alignment: Alignment.topCenter,
          child: GoalCard(goal: mockGoals(l).first),
        ),
      );
      await tester.pumpAndSettle();
      final bar = tester.getRect(find.byType(BudgetProgress));
      final label = tester.getRect(find.text('50 %'));
      expect(label.left, greaterThanOrEqualTo(bar.left));
      expect(label.right, lessThanOrEqualTo(bar.left + bar.width * .5));
    },
  );

  testWidgets(
    'cards honor supplied amounts, accent, SVG and missing-rate warning',
    (tester) async {
      await harness.mount(
        tester,
        Brightness.dark,
        (context, l) => Column(
          children: [
            BudgetCard(
              budget: BudgetDto.fromJson({
                ...mockBudgets(l).first.toJson(),
                'remaining_amount': '9876.54',
                'color': null,
                'end_on': null,
                'report_total': {
                  ...mockBudgets(l).first.reportTotal.toJson(),
                  'unconverted_count': 1,
                },
              }),
              today: syntheticBudgetToday,
            ),
            const SizedBox(height: 12),
            GoalCard(
              goal: mockGoals(l)[2],
              customIcons: {mockCustomIconId: mockHouseBytes},
            ),
          ],
        ),
        captureSize: const Size(600, 680),
        viewSize: const Size(800, 800),
        reducedMotion: true,
      );
      await tester.pumpAndSettle();
      expect(find.text('S/ 9,876.54 restante de S/ 2,500.00'), findsOneWidget);
      expect(find.text(l.unconvertedNotice), findsOneWidget);
      expect(find.byType(SvgPicture), findsOneWidget);
      expect(find.byKey(const Key('today-marker')), findsNothing);
      final bars = tester.widgetList<BudgetProgress>(
        find.byType(BudgetProgress),
      );
      expect(
        bars.every(
          (bar) =>
              bar.color ==
              Theme.of(tester.element(find.byType(BudgetCard)))
                  .colorScheme
                  .primary,
        ),
        true,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('mobile horizontal list scroll, callbacks, and creation empty', (
    tester,
  ) async {
    var selections = 0;
    var creations = 0;
    await harness.mount(
      tester,
      Brightness.light,
      (_, l) => Column(
        children: [
          BudgetCardList(
            budgets: mockBudgets(l),
            today: syntheticBudgetToday,
            onSelected: (_) => selections++,
          ),
          const SizedBox(height: 12),
          GoalCardList(goals: const [], onCreate: () => creations++),
        ],
      ),
      captureSize: const Size(390, 600),
      viewSize: const Size(390, 700),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text(l.sampleFoodBudget));
    await tester.drag(
      find.byType(SingleChildScrollView),
      const Offset(-340, 0),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text(l.sampleTravelBudget));
    await tester.tap(find.text(l.createGoal));
    expect(selections, 2);
    expect(creations, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('isolated demo theme, language, layout and empty controls', (
    tester,
  ) async {
    await tester.pumpWidget(const DemoApp(showBudgetsGoals: true));
    await tester.pumpAndSettle();
    expect(find.byType(BudgetCardList), findsOneWidget);
    await tester.tap(find.byKey(const Key('budget-goal-theme')));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(BudgetCardList))).brightness,
      Brightness.dark,
    );
    await tester.tap(find.byKey(const Key('budget-goal-language')));
    await tester.pumpAndSettle();
    expect(find.text('Budgets'), findsOneWidget);
    await tester.tap(find.text('Vertical list'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<BudgetCardList>(find.byType(BudgetCardList)).axis,
      Axis.vertical,
    );
    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();
    expect(find.text('No budgets yet.'), findsOneWidget);
    expect(find.text('No goals yet.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
