import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/l10n/app_localizations_en.dart';
import 'package:monetae_web/pages/edit_home_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/widgets/home_edit_button.dart';

import 'api_session_test.dart' as api;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;
import 'home_v2_test.dart' as mobile;

Finder toggle(String key) => find.byKey(ValueKey('edit-home-switch-$key'));

List<String> rows(WidgetTester tester) => tester
    .widgetList<Padding>(
      find.byWidgetPredicate(
        (widget) =>
            widget is Padding &&
            widget.key is ValueKey<String> &&
            (widget.key! as ValueKey<String>).value.startsWith('edit-home-'),
      ),
    )
    .map((widget) => (widget.key! as ValueKey<String>).value)
    .toList();

Future<void> mount(
  WidgetTester tester,
  home.HomeFixture f, {
  Brightness brightness = Brightness.light,
}) => mobile.mountMobile(
  tester,
  brightness,
  (_, _) => EditHomePage(session: f.session),
);

List<http.Request> patches(home.HomeFixture f) =>
    f.requests.where((r) => r.method == 'PATCH').toList();

Future<void> dragAccounts(WidgetTester tester) async {
  final gesture = await tester.startGesture(
    tester.getCenter(find.byKey(const ValueKey('edit-home-drag-accounts'))),
  );
  await tester.pump(const Duration(milliseconds: 100));
  await gesture.moveBy(const Offset(0, 20));
  await tester.pump();
  await gesture.moveBy(const Offset(0, 160));
  await tester.pumpAndSettle();
  await gesture.moveBy(const Offset(0, 1));
  await tester.pumpAndSettle();
  await gesture.up();
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();

  test('English editor texts', () {
    final l = AppLocalizationsEn();
    expect(l.editHomeTitle, 'Edit Home');
    expect(l.editHomeMinimum, 'Keep at least one component visible.');
    expect(l.editHomeReorder('Accounts'), 'Reorder Accounts');
  });

  testWidgets('open from Edit, hide and show, Home updates without reload', (
    tester,
  ) async {
    final f = home.HomeFixture();
    addTearDown(f.close);
    await mobile.mountMobile(
      tester,
      Brightness.light,
      (_, _) => HomePage(session: f.session, today: home.today, animate: false),
    );
    await tester.tap(find.byType(HomeEditButton));
    await tester.pumpAndSettle();
    expect(find.text('Editar Inicio'), findsOneWidget);
    await tester.tap(toggle('accounts'));
    await tester.pumpAndSettle();
    expect(f.session.user!.preferences.homeWidgets, defaultHomeWidgets.skip(1));
    expect(rows(tester).last, 'edit-home-accounts');
    await tester.tap(toggle('accounts'));
    await tester.pumpAndSettle();
    expect(f.session.user!.preferences.homeWidgets, [
      ...defaultHomeWidgets.skip(1),
      'accounts',
    ]);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    final goalPosition = tester.getTopLeft(
      find.byKey(const Key('home-block-goals')),
    );
    final budgetPosition = tester.getTopLeft(
      find.byKey(const Key('home-block-budgets')),
    );
    expect(goalPosition.dy, lessThan(budgetPosition.dy));
    expect(
      tester.getTopLeft(find.byKey(const Key('home-block-accounts'))).dy,
      greaterThan(budgetPosition.dy),
    );
    expect(find.byKey(const Key('home-block-accounts')), findsOneWidget);
    expect(f.session.user!.preferences.homeWidgets!.last, 'accounts');
    expect(tester.takeException(), isNull);
  });

  testWidgets('drag saves exact JSON and preserves other preferences', (
    tester,
  ) async {
    final f = home.HomeFixture();
    addTearDown(f.close);
    final initial = f.session.user!.preferences.toJson();
    await mount(tester, f);
    await dragAccounts(tester);
    final expected = ['goals', 'accounts', ...defaultHomeWidgets.skip(2)];
    expect(patches(f), hasLength(1));
    expect(patches(f).single.url.path, '/api/v1/users/me');
    expect(patches(f).single.headers['X-CSRF-Token'], 'synthetic.token');
    expect(jsonDecode(patches(f).single.body), {
      'preferences': {...initial, 'home_widgets': expected},
    });
    expect(rows(tester).take(2), ['edit-home-goals', 'edit-home-accounts']);
  });

  testWidgets(
    'known visible order then hidden in default order; last cannot hide',
    (tester) async {
      final f = home.HomeFixture(widgets: ['transactions']);
      addTearDown(f.close);
      await mount(tester, f);
      expect(rows(tester), [
        'edit-home-transactions',
        ...defaultHomeWidgets.take(5).map((k) => 'edit-home-$k'),
      ]);
      expect(tester.widget<Switch>(toggle('transactions')).onChanged, isNull);
      await tester.tap(find.text(home.l.latestTransactions));
      await tester.pumpAndSettle();
      expect(patches(f), isEmpty);
      await tester.tap(toggle('goals'));
      await tester.pumpAndSettle();
      expect(f.session.user!.preferences.homeWidgets, [
        'transactions',
        'goals',
      ]);
      await tester.tap(toggle('transactions'));
      await tester.pumpAndSettle();
      expect(f.session.user!.preferences.homeWidgets, ['goals']);
      expect(tester.widget<Switch>(toggle('goals')).onChanged, isNull);
    },
  );

  testWidgets('save failure reverts visibility and order; retry works', (
    tester,
  ) async {
    final f = home.HomeFixture();
    addTearDown(f.close);
    f.patch = Completer<http.Response>();
    await mount(tester, f);
    await tester.tap(toggle('accounts'));
    await tester.pump();
    expect(tester.widget<Switch>(toggle('accounts')).value, isFalse);
    expect(tester.widget<Switch>(toggle('goals')).onChanged, isNull);
    expect(
      tester
          .widget<ReorderableDragStartListener>(
            find.byKey(const ValueKey('edit-home-drag-goals')),
          )
          .enabled,
      isFalse,
    );
    f.patch!.complete(api.problem(503));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('edit-home-error')), findsOneWidget);
    expect(tester.widget<Switch>(toggle('accounts')).value, isTrue);
    expect(rows(tester), defaultHomeWidgets.map((k) => 'edit-home-$k'));
    expect(f.session.user!.preferences.homeWidgets, isEmpty);
    // Failed drag also restores the original ordering.
    f.patch = Completer<http.Response>()..complete(api.problem(503));
    final beforeDrag = patches(f).length;
    await dragAccounts(tester);
    expect(patches(f), hasLength(beforeDrag + 1));
    expect(rows(tester), defaultHomeWidgets.map((k) => 'edit-home-$k'));
    f.patch = null;
    await tester.tap(toggle('accounts'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('edit-home-error')), findsNothing);
    expect(f.session.user!.preferences.homeWidgets, defaultHomeWidgets.skip(1));
  });

  testWidgets(
    'empty and unknown keys use Home fallback; hidden drag does not save',
    (tester) async {
      final f = home.HomeFixture(widgets: ['unknown']);
      addTearDown(f.close);
      await mount(tester, f);
      expect(rows(tester), defaultHomeWidgets.map((k) => 'edit-home-$k'));
      await tester.tap(toggle('accounts'));
      await tester.pumpAndSettle();
      final count = patches(f).length;
      tester
          .widget<ReorderableListView>(find.byType(ReorderableListView))
          .onReorderItem!(5, 0);
      await tester.pumpAndSettle();
      expect(patches(f), hasLength(count));
      expect(rows(tester).last, 'edit-home-accounts');
    },
  );

  for (final brightness in Brightness.values) {
    testWidgets('editor golden ${brightness.name}', (tester) async {
      final f = home.HomeFixture(
        widgets: ['accounts', 'goals', 'budgets', 'transactions'],
      );
      addTearDown(f.close);
      await mount(tester, f, brightness: brightness);
      expect(find.text(home.l.accounts), findsOneWidget);
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/edit_home_${brightness.name}.png'),
      );
    });
  }
}
