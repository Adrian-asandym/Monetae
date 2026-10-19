import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/l10n/app_localizations_en.dart';
import 'package:monetae_web/pages/add_goal_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/widgets/budget_goal_lists.dart';
import 'package:monetae_web/widgets/transaction_form/form_sheet.dart';

import 'api_session_test.dart' as api;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;
import 'home_v2_test.dart' as mobile;

class GoalFixture extends home.HomeFixture {
  GoalFixture({super.empty = false}) : super(widgets: ['goals']);
  Map<String, Object?>? created;
  int status = 201;
  Completer<http.Response>? pending;
  final posts = <http.Request>[];
  int goalLoads = 0;

  @override
  Future<http.Response> handle(http.Request request) async {
    if (request.url.path != '/api/v1/goals') return super.handle(request);
    if (request.method == 'POST') {
      posts.add(request);
      if (pending != null) return pending!.future;
      if (status != 201) return api.problem(status);
      created = {
        ...mockGoals(home.l).first.toJson(),
        'due_on': null,
        ...jsonDecode(request.body) as Map<String, Object?>,
        'id': '00000000-0000-4000-8000-000000000099',
        'progress_amount': '0.00',
      };
      return http.Response(jsonEncode(created), 201);
    }
    goalLoads++;
    return api.ok({
      'items': [
        if (!empty) ...mockGoals(home.l).map((g) => g.toJson()),
        if (created != null) created,
      ],
      'next_cursor': null,
    });
  }
}

Future<void> mountPage(
  WidgetTester tester,
  GoalFixture f, {
  Brightness brightness = Brightness.light,
  String currency = 'PEN',
}) => mobile.mountMobile(
  tester,
  brightness,
  (_, _) => AddGoalPage(api: f.api, baseCurrency: currency),
);

Future<void> openFromHome(WidgetTester tester, GoalFixture f) async {
  await mobile.mountMobile(
    tester,
    Brightness.light,
    (_, _) => HomePage(session: f.session, today: home.today, animate: false),
  );
  if (!f.empty) {
    final scroll = find.descendant(
      of: find.byType(GoalCardList),
      matching: find.byType(SingleChildScrollView),
    );
    await tester.drag(scroll, const Offset(-2000, 0));
    await tester.pumpAndSettle();
  }
  await tester.tap(find.byType(HomeAddCard));
  await tester.pumpAndSettle();
}

Future<void> setAmount(WidgetTester tester, String value) async {
  await tester.tap(find.byKey(const Key('goal-target-amount')));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('account-amount-input')), value);
  await tester.pump();
  await tester.ensureVisible(find.byKey(const Key('account-amount-done')));
  await tester.tap(find.byKey(const Key('account-amount-done')));
  await tester.pumpAndSettle();
}

Future<void> chooseDate(WidgetTester tester) async {
  await tester.tap(find.byKey(const Key('goal-due-date')));
  await tester.pumpAndSettle();
  await tester.tap(find.text('15'));
  final labels = MaterialLocalizations.of(
    tester.element(find.byType(DatePickerDialog)),
  );
  await tester.tap(find.text(labels.okButtonLabel));
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();
  test('goal labels have English translations', () {
    final l = AppLocalizationsEn();
    expect(l.addGoal, 'Add goal');
    expect(l.goalSaving, 'Savings');
    expect(l.goalSpending, 'Spending');
    expect(l.goalNoDueDate, 'No due date');
    expect(l.goalAmountRequired, contains('greater than zero'));
  });
  for (final empty in [false, true]) {
    testWidgets('Home opens and reloads goals after creating; empty=$empty', (
      tester,
    ) async {
      final f = GoalFixture(empty: empty);
      addTearDown(f.close);
      await openFromHome(tester, f);
      expect(find.byType(AddGoalPage), findsOneWidget);
      final initialLoads = f.goalLoads;
      final save = find.byKey(const Key('goal-save'));
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await tester.enterText(find.byKey(const Key('goal-name')), '   ');
      await tester.pump();
      expect(find.text(home.l.goalNameRequired), findsOneWidget);
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await tester.enterText(find.byKey(const Key('goal-name')), '  Viaje  ');
      await tester.pump();
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await setAmount(tester, '1500');
      await tester.tap(save);
      await tester.pumpAndSettle();
      expect(f.posts, hasLength(1));
      expect(f.posts.single.headers['X-CSRF-Token'], 'synthetic.token');
      expect(jsonDecode(f.posts.single.body), {
        'name': 'Viaje',
        'kind': 'save',
        'target_amount': '1500.00',
        'currency': 'PEN',
        'color': '#59A849',
        'icon': null,
      });
      expect(f.goalLoads, initialLoads + 1);
      expect(find.byType(AddGoalPage), findsNothing);
      expect(
        tester
            .widget<GoalCardList>(find.byType(GoalCardList))
            .goals
            .map((g) => g.name),
        contains('Viaje'),
      );
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('zero, malformed and negative targets cannot be submitted', (
    tester,
  ) async {
    final f = GoalFixture();
    addTearDown(f.close);
    await mountPage(tester, f);
    await tester.enterText(find.byKey(const Key('goal-name')), 'Viaje');
    await tester.tap(find.byKey(const Key('goal-target-amount')));
    await tester.pumpAndSettle();
    final done = find.byKey(const Key('account-amount-done'));
    expect(tester.widget<FormSheetButton>(done).onPressed, isNull);
    expect(find.byKey(const Key('account-negative-balance')), findsNothing);
    for (final input in ['', '0', '0,00', '-20', 'abc']) {
      await tester.enterText(
        find.byKey(const Key('account-amount-input')),
        input,
      );
      await tester.pump();
      expect(tester.widget<FormSheetButton>(done).onPressed, isNull);
    }
    expect(f.posts, isEmpty);
  });
  testWidgets('spending goal sends exact cents, currency, color and date', (
    tester,
  ) async {
    final f = GoalFixture()..status = 422;
    addTearDown(f.close);
    await mountPage(tester, f);
    await tester.enterText(find.byKey(const Key('goal-name')), 'Equipo');
    await tester.tap(find.byKey(const Key('goal-kind-spend')));
    await tester.tap(find.byKey(const Key('account-color-1')));
    await tester.tap(find.byKey(const Key('goal-currency-picker')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('goal-currency-USD')));
    await tester.pumpAndSettle();
    await setAmount(tester, '9999999999999999,99');
    await chooseDate(tester);
    await tester.tap(find.byKey(const Key('goal-save')));
    await tester.pumpAndSettle();
    expect(jsonDecode(f.posts.single.body), {
      'name': 'Equipo',
      'kind': 'spend',
      'target_amount': '9999999999999999.99',
      'currency': 'USD',
      'due_on': '2026-10-15',
      'color': '#CA5A5A',
      'icon': null,
    });
    expect(tester.takeException(), isNull);
  });
  testWidgets('due date can be cleared and cancel does not post or reload', (
    tester,
  ) async {
    final f = GoalFixture();
    addTearDown(f.close);
    await openFromHome(tester, f);
    final initialLoads = f.goalLoads;
    await chooseDate(tester);
    await tester.tap(find.byKey(const Key('goal-clear-due-date')));
    await tester.pumpAndSettle();
    expect(find.text(home.l.goalNoDueDate), findsOneWidget);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(f.posts, isEmpty);
    expect(f.goalLoads, initialLoads);
    expect(find.byType(AddGoalPage), findsNothing);
  });
  testWidgets('zero precision base currency still sends two decimals', (
    tester,
  ) async {
    final f = GoalFixture()..status = 422;
    addTearDown(f.close);
    await mountPage(tester, f, currency: 'JPY');
    expect(find.text('JPY JP¥'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('goal-name')), 'Viaje');
    await setAmount(tester, '1234');
    await tester.tap(find.byKey(const Key('goal-save')));
    await tester.pumpAndSettle();
    final body = jsonDecode(f.posts.single.body) as Map<String, Object?>;
    expect(body['target_amount'], '1234.00');
    expect(body['currency'], 'JPY');
  });
  for (final status in [409, 422, 503]) {
    testWidgets('HTTP $status is visible and retry preserves form', (
      tester,
    ) async {
      final f = GoalFixture()..status = status;
      addTearDown(f.close);
      await openFromHome(tester, f);
      final loads = f.goalLoads;
      await tester.enterText(find.byKey(const Key('goal-name')), 'Viaje');
      await setAmount(tester, '0,01');
      await tester.tap(find.byKey(const Key('goal-save')));
      await tester.pumpAndSettle();
      expect(find.byType(AddGoalPage), findsOneWidget);
      expect(find.byKey(const Key('goal-save-error')), findsOneWidget);
      expect(
        find.text(switch (status) {
          409 => home.l.requestConflict,
          422 => home.l.requestInvalid,
          _ => home.l.connectionError,
        }),
        findsOneWidget,
      );
      expect(find.text('Viaje'), findsOneWidget);
      expect(f.goalLoads, loads);
      f.status = 201;
      await tester.tap(find.byKey(const Key('goal-save')));
      await tester.pumpAndSettle();
      expect(f.posts, hasLength(2));
      expect(find.byType(AddGoalPage), findsNothing);
      expect(f.goalLoads, loads + 1);
    });
  }
  testWidgets('pending request blocks double submit, edits and navigation', (
    tester,
  ) async {
    final f = GoalFixture()..pending = Completer<http.Response>();
    addTearDown(f.close);
    await openFromHome(tester, f);
    await tester.enterText(find.byKey(const Key('goal-name')), 'Viaje');
    await setAmount(tester, '1234,50');
    final save = find.byKey(const Key('goal-save'));
    await tester.tap(save);
    await tester.pump();
    await tester.tap(save);
    expect(f.posts, hasLength(1));
    expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
    expect(
      tester
          .widget<AbsorbPointer>(find.byKey(const Key('goal-fields')))
          .absorbing,
      isTrue,
    );
    await tester.tap(find.byType(BackButton));
    await tester.state<NavigatorState>(find.byType(Navigator).first).maybePop();
    await tester.pump();
    expect(find.byType(AddGoalPage), findsOneWidget);
    f.pending!.complete(api.problem(422));
    await tester.pumpAndSettle();
    expect(tester.widget<FormSheetButton>(save).onPressed, isNotNull);
  });
  for (final brightness in Brightness.values) {
    testWidgets('add goal ${brightness.name} golden with text', (tester) async {
      final f = GoalFixture();
      addTearDown(f.close);
      await mountPage(tester, f, brightness: brightness);
      await tester.enterText(
        find.byKey(const Key('goal-name')),
        'Fondo de viaje',
      );
      await setAmount(tester, '2500');
      await chooseDate(tester);
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/add_goal_${brightness.name}.png'),
      );
    });
  }
}
