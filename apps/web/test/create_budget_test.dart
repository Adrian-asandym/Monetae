import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations_en.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/presentation/clock.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/pages/add_budget_page.dart';
import 'package:monetae_web/pages/budgets_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/widgets/budget_goal_lists.dart';
import 'package:monetae_web/widgets/transaction_form/form_sheet.dart';

import 'api_session_test.dart' as api;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;
import 'home_v2_test.dart' as mobile;

class BudgetFixture extends home.HomeFixture {
  BudgetFixture({super.empty = false}) : super(widgets: ['budgets']);
  Map<String, Object?>? created;
  int status = 201;
  Completer<http.Response>? pending;
  final posts = <http.Request>[];
  int budgetLoads = 0;
  List<List<Map<String, Object?>>>? categoryPages;
  int categoryLoads = 0;
  bool categoryFailure = false;

  @override
  Future<http.Response> handle(http.Request request) async {
    if (request.url.path == '/api/v1/categories' && categoryPages != null) {
      categoryLoads++;
      if (categoryFailure) return api.problem(503);
      final page = int.parse(request.url.queryParameters['cursor'] ?? '0');
      return api.ok({
        'items': categoryPages![page],
        'next_cursor': page + 1 < categoryPages!.length ? '${page + 1}' : null,
      });
    }
    if (request.url.path != '/api/v1/budgets') return super.handle(request);
    if (request.method == 'POST') {
      posts.add(request);
      if (pending != null) return pending!.future;
      if (status != 201) return api.problem(status);
      created = {
        ...mockBudgets(home.l).first.toJson(),
        'end_on': null,
        ...jsonDecode(request.body) as Map<String, Object?>,
        'id': '00000000-0000-4000-8000-000000000099',
        'spent_amount': '0.00',
      };
      return http.Response(jsonEncode(created), 201);
    }
    budgetLoads++;
    return api.ok({
      'items': [
        if (!empty) ...mockBudgets(home.l).map((g) => g.toJson()),
        if (created != null) created,
      ],
      'next_cursor': null,
    });
  }
}

Future<void> mountPage(
  WidgetTester tester,
  BudgetFixture f, {
  Brightness brightness = Brightness.light,
  String? currency = 'PEN',
}) async {
  tester.view.physicalSize = const Size(400, 642);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    PresentationClock(
      now: () => home.today,
      child: RepaintBoundary(
        key: const Key('budget-app-capture'),
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: monetaeTheme(brightness: brightness),
          locale: const Locale('es'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: RepaintBoundary(
            key: const Key('capture'),
            child: Builder(
              builder: (context) => MediaQuery(
                data: MediaQuery.of(context).copyWith(disableAnimations: true),
                child: AddBudgetPage(api: f.api, baseCurrency: currency),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> openFromList(
  WidgetTester tester,
  BudgetFixture f, {
  bool budgetsTab = false,
}) async {
  await mobile.mountMobile(
    tester,
    Brightness.light,
    (_, _) => budgetsTab
        ? BudgetsPage(api: f.api, today: home.today)
        : HomePage(session: f.session, today: home.today, animate: false),
  );
  if (!f.empty && !budgetsTab) {
    await tester.drag(
      find.descendant(
        of: find.byType(BudgetCardList),
        matching: find.byType(SingleChildScrollView),
      ),
      const Offset(-3000, 0),
    );
    await tester.pumpAndSettle();
  }
  final add = budgetsTab
      ? find.text(home.l.addBudgetLabel)
      : find.byType(HomeAddCard);
  await tester.ensureVisible(add);
  await tester.tap(add);
  await tester.pumpAndSettle();
}

Future<void> tapField(WidgetTester tester, String key) async {
  final field = find.byKey(Key(key));
  await Scrollable.ensureVisible(tester.element(field), alignment: 0.5);
  await tester.pumpAndSettle();
  await tester.tap(field);
  await tester.pumpAndSettle();
}

Future<void> setAmount(WidgetTester tester, String value) async {
  await tapField(tester, 'budget-amount');
  await tester.enterText(find.byKey(const Key('account-amount-input')), value);
  await tester.pump();
  await tester.ensureVisible(find.byKey(const Key('account-amount-done')));
  await tester.tap(find.byKey(const Key('account-amount-done')));
  await tester.pumpAndSettle();
}

Future<void> choosePeriod(WidgetTester tester, String period) async {
  await tapField(tester, 'budget-period');
  await tester.tap(find.byKey(Key('budget-period-$period')));
  await tester.pumpAndSettle();
}

Future<void> chooseDate(WidgetTester tester, String key, String day) async {
  await tapField(tester, key);
  await tester.tap(find.text(day));
  final labels = MaterialLocalizations.of(
    tester.element(find.byType(DatePickerDialog)),
  );
  await tester.tap(find.text(labels.okButtonLabel));
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();
  test('budget labels have English translations', () {
    final l = AppLocalizationsEn();
    expect(l.addBudget, 'Add budget');
    expect(l.budgetSelectedOnly, 'Only added transactions');
    expect(l.budgetCustom, 'Custom');
    expect(l.budgetDatesInvalid, contains('on or after'));
  });
  for (final tab in [false, true]) {
    for (final empty in [false, true]) {
      testWidgets('opens and reloads budgets tab=$tab empty=$empty', (
        tester,
      ) async {
        final f = BudgetFixture(empty: empty);
        addTearDown(f.close);
        await openFromList(tester, f, budgetsTab: tab);
        expect(find.byType(AddBudgetPage), findsOneWidget);
        final loads = f.budgetLoads;
        final save = find.byKey(const Key('budget-save'));
        expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
        await tester.enterText(find.byKey(const Key('budget-name')), '   ');
        await tester.pump();
        expect(find.text(home.l.budgetNameRequired), findsOneWidget);
        await setAmount(tester, '100');
        expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
        await tester.enterText(
          find.byKey(const Key('budget-name')),
          '  Compras  ',
        );
        await tester.pump();
        await tester.tap(save);
        await tester.pumpAndSettle();
        expect(f.posts, hasLength(1));
        expect(f.posts.single.headers['X-CSRF-Token'], 'synthetic.token');
        expect(jsonDecode(f.posts.single.body), {
          'name': 'Compras',
          'period': 'monthly',
          'start_on': '2026-10-08',
          'amount': '100.00',
          'currency': 'PEN',
          'scope': 'all',
          'color': '#59A849',
          'category_limits': <Object?>[],
        });
        expect(f.budgetLoads, loads + 1);
        expect(find.byType(AddBudgetPage), findsNothing);
        expect(
          tester
              .widget<BudgetCardList>(find.byType(BudgetCardList))
              .budgets
              .map((b) => b.name),
          contains('Compras'),
        );
        expect(tester.takeException(), isNull);
      });
    }
  }
  testWidgets('zero, malformed and negative amounts cannot be submitted', (
    tester,
  ) async {
    final f = BudgetFixture();
    addTearDown(f.close);
    await mountPage(tester, f);
    await tester.enterText(find.byKey(const Key('budget-name')), 'Viaje');
    await tapField(tester, 'budget-amount');
    final done = find.byKey(const Key('account-amount-done'));
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
  testWidgets(
    'custom end is required, before start rejected, equality accepted',
    (tester) async {
      final f = BudgetFixture()..status = 422;
      addTearDown(f.close);
      await mountPage(tester, f);
      await tester.enterText(find.byKey(const Key('budget-name')), 'Viaje');
      await setAmount(tester, '0,01');
      await choosePeriod(tester, 'custom');
      final save = find.byKey(const Key('budget-save'));
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await chooseDate(tester, 'budget-end-date', '7');
      expect(find.text(home.l.budgetDatesInvalid), findsOneWidget);
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await chooseDate(tester, 'budget-end-date', '8');
      expect(tester.widget<FormSheetButton>(save).onPressed, isNotNull);
      await tester.tap(save);
      await tester.pumpAndSettle();
      expect(jsonDecode(f.posts.single.body), {
        'name': 'Viaje',
        'period': 'custom',
        'start_on': '2026-10-08',
        'end_on': '2026-10-08',
        'amount': '0.01',
        'currency': 'PEN',
        'scope': 'all',
        'color': '#59A849',
        'category_limits': <Object?>[],
      });
      await chooseDate(tester, 'budget-start-date', '9');
      expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
      await choosePeriod(tester, 'weekly');
      expect(find.byKey(const Key('budget-end-date')), findsNothing);
      await tester.tap(save);
      await tester.pumpAndSettle();
      final body = jsonDecode(f.posts.last.body) as Map<String, Object?>;
      expect(body['period'], 'weekly');
      expect(body['start_on'], '2026-10-09');
      expect(body.containsKey('end_on'), isFalse);
    },
  );
  testWidgets(
    'daily budget sends exact cents, currency, color and selected scope',
    (tester) async {
      final f = BudgetFixture()..status = 422;
      addTearDown(f.close);
      await mountPage(tester, f);
      await tester.enterText(find.byKey(const Key('budget-name')), 'Equipo');
      await choosePeriod(tester, 'daily');
      await tapField(tester, 'budget-currency-picker');
      await tester.tap(find.byKey(const Key('budget-currency-USD')));
      await tester.pumpAndSettle();
      await setAmount(tester, '9999999999999999,99');
      await tapField(tester, 'budget-scope');
      await tapField(tester, 'account-color-1');
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      expect(jsonDecode(f.posts.single.body), {
        'name': 'Equipo',
        'period': 'daily',
        'start_on': '2026-10-08',
        'amount': '9999999999999999.99',
        'currency': 'USD',
        'scope': 'selected',
        'color': '#CA5A5A',
        'category_limits': <Object?>[],
      });
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'included categories paginate, filter expenses and send total as limit',
    (tester) async {
      final food = mockCategory(home.l).toJson();
      final other = {
        ...food,
        'id': '00000000-0000-4000-8000-000000000066',
        'name': 'Equipo',
      };
      final income = {
        ...food,
        'id': '00000000-0000-4000-8000-000000000067',
        'kind': 'income',
      };
      final correction = {
        ...food,
        'id': '00000000-0000-4000-8000-000000000068',
        'system_key': 'balance_correction_expense',
      };
      final deleted = {
        ...food,
        'id': '00000000-0000-4000-8000-000000000069',
        'deleted_at': '2026-10-01T00:00:00Z',
      };
      final f = BudgetFixture()
        ..status = 422
        ..categoryPages = [
          [food, income, correction, deleted],
          [other],
        ];
      addTearDown(f.close);
      await mountPage(tester, f);
      await tester.enterText(find.byKey(const Key('budget-name')), 'Compras');
      await setAmount(tester, '2500');
      await tapField(tester, 'budget-categories');
      expect(f.categoryLoads, 2);
      expect(find.byType(CheckboxListTile), findsNWidgets(3));
      await tapField(tester, 'budget-category-${food['id']}');
      await tapField(tester, 'budget-category-${other['id']}');
      await tapField(tester, 'budget-categories-done');
      await setAmount(tester, '1234,50');
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      expect(jsonDecode(f.posts.single.body), {
        'name': 'Compras',
        'period': 'monthly',
        'start_on': '2026-10-08',
        'amount': '1234.50',
        'currency': 'PEN',
        'scope': 'all',
        'color': '#59A849',
        'category_limits': [
          {'category_id': food['id'], 'limit_amount': '1234.50'},
          {'category_id': other['id'], 'limit_amount': '1234.50'},
        ],
      });
      await tapField(tester, 'budget-categories');
      await tapField(tester, 'budget-categories-all');
      await tapField(tester, 'budget-categories-done');
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      expect(
        (jsonDecode(f.posts.last.body)
            as Map<String, Object?>)['category_limits'],
        isEmpty,
      );
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'category loading errors can retry and dismiss without losing selection',
    (tester) async {
      final food = mockCategory(home.l).toJson();
      final f = BudgetFixture()
        ..categoryPages = [
          [food],
        ]
        ..categoryFailure = true;
      addTearDown(f.close);
      await mountPage(tester, f);
      await tapField(tester, 'budget-categories');
      expect(find.text(home.l.connectionError), findsOneWidget);
      f.categoryFailure = false;
      await tester.tap(find.text(home.l.retry));
      await tester.pumpAndSettle();
      await tapField(tester, 'budget-category-${food['id']}');
      await tapField(tester, 'budget-categories-done');
      await tapField(tester, 'budget-categories');
      expect(
        tester
            .widget<CheckboxListTile>(
              find.byKey(Key('budget-category-${food['id']}')),
            )
            .value,
        isTrue,
      );
      await tapField(tester, 'budget-categories-all');
      await tester
          .state<NavigatorState>(find.byType(Navigator).first)
          .maybePop();
      await tester.pumpAndSettle();
      await tapField(tester, 'budget-categories');
      expect(
        tester
            .widget<CheckboxListTile>(
              find.byKey(Key('budget-category-${food['id']}')),
            )
            .value,
        isTrue,
      );
    },
  );
  testWidgets('cancel does not post or reload', (tester) async {
    final f = BudgetFixture();
    addTearDown(f.close);
    await openFromList(tester, f);
    final loads = f.budgetLoads;
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(f.posts, isEmpty);
    expect(f.budgetLoads, loads);
    expect(find.byType(AddBudgetPage), findsNothing);
  });
  testWidgets(
    'profile base currency and zero precision still sends two decimals',
    (tester) async {
      final f = BudgetFixture()..status = 422;
      addTearDown(f.close);
      f.profile['base_currency'] = 'JPY';
      await mountPage(tester, f, currency: null);
      expect(find.text('JPY JP¥'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('budget-name')), 'Viaje');
      await setAmount(tester, '1234');
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      final body = jsonDecode(f.posts.single.body) as Map<String, Object?>;
      expect(body['amount'], '1234.00');
      expect(body['currency'], 'JPY');
    },
  );
  testWidgets('profile failure is visible and can be retried', (tester) async {
    final f = BudgetFixture();
    addTearDown(f.close);
    f.statuses['/api/v1/users/me'] = 503;
    await mountPage(tester, f, currency: null);
    expect(find.text(home.l.connectionError), findsOneWidget);
    f.statuses.clear();
    await tester.tap(find.text(home.l.retry));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('budget-name')), findsOneWidget);
    expect(find.byKey(const Key('budget-save-error')), findsNothing);
  });
  for (final status in [409, 422, 503]) {
    testWidgets('HTTP $status is visible and retry preserves form', (
      tester,
    ) async {
      final f = BudgetFixture()..status = status;
      addTearDown(f.close);
      await openFromList(tester, f);
      final loads = f.budgetLoads;
      await tester.enterText(find.byKey(const Key('budget-name')), 'Viaje');
      await setAmount(tester, '0,01');
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      expect(find.byType(AddBudgetPage), findsOneWidget);
      expect(find.byKey(const Key('budget-save-error')), findsOneWidget);
      expect(
        find.text(switch (status) {
          409 => home.l.requestConflict,
          422 => home.l.requestInvalid,
          _ => home.l.connectionError,
        }),
        findsOneWidget,
      );
      expect(find.text('Viaje'), findsOneWidget);
      expect(f.budgetLoads, loads);
      f.status = 201;
      await tester.tap(find.byKey(const Key('budget-save')));
      await tester.pumpAndSettle();
      expect(f.posts, hasLength(2));
      expect(find.byType(AddBudgetPage), findsNothing);
      expect(f.budgetLoads, loads + 1);
    });
  }
  testWidgets('pending request blocks double submit, edits and navigation', (
    tester,
  ) async {
    final f = BudgetFixture()..pending = Completer<http.Response>();
    addTearDown(f.close);
    await openFromList(tester, f);
    await tester.enterText(find.byKey(const Key('budget-name')), 'Viaje');
    await setAmount(tester, '1234,50');
    final save = find.byKey(const Key('budget-save'));
    await tester.tap(save);
    await tester.pump();
    await tester.tap(save);
    expect(f.posts, hasLength(1));
    expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
    expect(
      tester
          .widget<AbsorbPointer>(find.byKey(const Key('budget-fields')))
          .absorbing,
      isTrue,
    );
    await tester.tap(find.byType(BackButton));
    await tester.state<NavigatorState>(find.byType(Navigator).first).maybePop();
    await tester.pump();
    expect(find.byType(AddBudgetPage), findsOneWidget);
    f.pending!.complete(api.problem(422));
    await tester.pumpAndSettle();
    expect(tester.widget<FormSheetButton>(save).onPressed, isNotNull);
  });
  for (final brightness in Brightness.values) {
    testWidgets('add budget ${brightness.name} golden with text', (
      tester,
    ) async {
      final f = BudgetFixture();
      addTearDown(f.close);
      await mountPage(tester, f, brightness: brightness);
      await tester.enterText(
        find.byKey(const Key('budget-name')),
        'Compras del mes',
      );
      await setAmount(tester, '2500');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/add_budget_${brightness.name}.png'),
      );
      await choosePeriod(tester, 'custom');
      await chooseDate(tester, 'budget-end-date', '15');
      await tapField(tester, 'budget-scope');
      await tapField(tester, 'account-color-1');
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/add_budget_custom_${brightness.name}.png'),
      );
      await tapField(tester, 'budget-categories');
      // The route overlay lives above the page's capture boundary.
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile(
          'goldens/add_budget_categories_${brightness.name}.png',
        ),
      );
    });
  }
}
