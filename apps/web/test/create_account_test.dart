import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/l10n/app_localizations_en.dart';
import 'package:monetae_web/pages/add_account_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/widgets/budget_goal_lists.dart';
import 'package:monetae_web/widgets/home_accounts.dart';
import 'package:monetae_web/widgets/transaction_form/form_sheet.dart';

import 'api_session_test.dart' as api;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;
import 'home_v2_test.dart' as mobile;

class CreateFixture extends home.HomeFixture {
  CreateFixture({super.empty = false}) : super(widgets: ['accounts']);
  Map<String, Object?>? created;
  int status = 201;
  Completer<http.Response>? pending;
  final posts = <http.Request>[];
  int accountLoads = 0;
  @override
  Future<http.Response> handle(http.Request request) async {
    if (request.url.path == '/api/v1/accounts') {
      if (request.method == 'POST') {
        posts.add(request);
        if (pending != null) return pending!.future;
        if (status != 201) return api.problem(status);
        created = {
          ...accounts.first.toJson(),
          ...jsonDecode(request.body) as Map<String, Object?>,
          'id': '00000000-0000-4000-8000-000000000099',
          'balance': (jsonDecode(
            request.body,
          ) as Map<String, Object?>)['initial_balance'],
          'transaction_count': 0,
        };
        return http.Response(jsonEncode(created), 201);
      }
      accountLoads++;
      return api.ok({
        'items': [
          if (!empty) ...accounts.map((a) => a.toJson()),
          if (created != null) created,
        ],
        'next_cursor': null,
      });
    }
    return super.handle(request);
  }
}

Future<void> mountPage(
  WidgetTester tester,
  CreateFixture f, {
  Brightness brightness = Brightness.light,
  String currency = 'PEN',
}) => mobile.mountMobile(
  tester,
  brightness,
  (_, _) => AddAccountPage(api: f.api, baseCurrency: currency),
);

Future<void> openFromHome(WidgetTester tester, CreateFixture f) async {
  await mobile.mountMobile(
    tester,
    Brightness.light,
    (_, _) => HomePage(session: f.session, today: home.today, animate: false),
  );
  final scroll = find.descendant(
    of: find.byType(HomeAccounts),
    matching: find.byType(SingleChildScrollView),
  );
  await tester.drag(scroll, const Offset(-1000, 0));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('add-account-card')));
  await tester.pumpAndSettle();
}

Future<void> setBalance(
  WidgetTester tester,
  String value, {
  bool negative = false,
}) async {
  await tester.tap(find.byKey(const Key('account-initial-balance')));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('account-amount-input')), value);
  if (negative) {
    await tester.tap(find.byKey(const Key('account-negative-balance')));
  }
  await tester.pumpAndSettle();
  await tester.ensureVisible(find.byKey(const Key('account-amount-done')));
  await tester.tap(find.byKey(const Key('account-amount-done')));
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();
  test('new account texts are localized in English', () {
    final l = AppLocalizationsEn();
    expect(l.addAccount, 'Add account');
    expect(l.accountStartingAt, 'Starting at');
    expect(l.accountDuplicateName, contains('already exists'));
  });
  for (final empty in [false, true]) {
    testWidgets(
      'create from Home and reload accounts without changing default; empty=$empty',
      (tester) async {
        final f = CreateFixture(empty: empty);
        addTearDown(f.close);
        final defaultId = f.session.selectedAccountId;
        await openFromHome(tester, f);
        final initialLoads = f.accountLoads;
        expect(find.byType(AddAccountPage), findsOneWidget);
        expect(find.byKey(const Key('account-balance-value')), findsOneWidget);
        expect(find.text('0 S/.'), findsOneWidget);
        final save = find.byKey(const Key('account-save'));
        expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
        await tester.enterText(find.byKey(const Key('account-name')), '   ');
        await tester.pump();
        expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
        expect(find.text(home.l.accountNameRequired), findsOneWidget);
        await tester.enterText(
          find.byKey(const Key('account-name')),
          '  Fondo nuevo  ',
        );
        await tester.pump();
        await tester.tap(save);
        await tester.pumpAndSettle();
        expect(f.posts, hasLength(1));
        expect(f.posts.single.headers['X-CSRF-Token'], 'synthetic.token');
        expect(jsonDecode(f.posts.single.body), {
          'name': 'Fondo nuevo',
          'type': 'other',
          'currency': 'PEN',
          'initial_balance': '0.00',
          'color': '#59A849',
        });
        expect(f.accountLoads, initialLoads + 1);
        expect(find.byType(AddAccountPage), findsNothing);
        expect(
          tester
              .widget<HomeAccounts>(find.byType(HomeAccounts))
              .accounts
              .map((a) => a.name),
          contains('Fondo nuevo'),
        );
        expect(f.session.selectedAccountId, defaultId);
        expect(f.requests.where((r) => r.method == 'PATCH'), isEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }
  for (final negative in [false, true]) {
    testWidgets(
      'exact decimal balance, selected currency and color; negative=$negative',
      (tester) async {
        final f = CreateFixture();
        addTearDown(f.close);
        await openFromHome(tester, f);
        await tester.enterText(
          find.byKey(const Key('account-name')),
          'Reserva',
        );
        await tester.tap(find.byKey(const Key('account-color-1')));
        await tester.tap(find.byKey(const Key('account-currency-USD')));
        await tester.pumpAndSettle();
        await setBalance(tester, '1234,50', negative: negative);
        expect(find.text('${negative ? '-' : ''}1.234,50 \$'), findsOneWidget);
        await tester.tap(find.byKey(const Key('account-save')));
        await tester.pumpAndSettle();
        expect(jsonDecode(f.posts.single.body), {
          'name': 'Reserva',
          'type': 'other',
          'currency': 'USD',
          'initial_balance': '${negative ? '-' : ''}1234.50',
          'color': '#CA5A5A',
        });
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets('large initial balance retains every digit on the wire', (
    tester,
  ) async {
    final f = CreateFixture()..status = 422;
    addTearDown(f.close);
    await mountPage(tester, f);
    await tester.enterText(find.byKey(const Key('account-name')), 'Reserva');
    await setBalance(tester, '9999999999999999.99');
    await tester.tap(find.byKey(const Key('account-save')));
    await tester.pumpAndSettle();
    expect(
      (jsonDecode(f.posts.single.body)
          as Map<String, Object?>)['initial_balance'],
      '9999999999999999.99',
    );
  });
  testWidgets(
    'zero precision currency is first and cannot receive fractional digits',
    (tester) async {
      final f = CreateFixture()..status = 422;
      addTearDown(f.close);
      await mountPage(tester, f, currency: 'JPY');
      expect(
        tester.widgetList<ListTile>(find.byType(ListTile)).first.key,
        const Key('account-currency-JPY'),
      );
      await tester.tap(find.byKey(const Key('account-initial-balance')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('account-amount-input')),
        '1234',
      );
      await tester.tap(find.byKey(const Key('amount-key-.')));
      await tester.tap(find.byKey(const Key('amount-key-5')));
      await tester.pump();
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('account-amount-input')))
            .controller!
            .text,
        '1234.',
      );
      await tester.tap(find.byKey(const Key('amount-key-backspace')));
      await tester.tap(find.byKey(const Key('account-amount-done')));
      await tester.pumpAndSettle();
      expect(find.text('1.234 JP¥'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('account-name')), 'Reserva');
      await tester.pump();
      await tester.tap(find.byKey(const Key('account-save')));
      await tester.pumpAndSettle();
      expect(
        (jsonDecode(f.posts.single.body)
            as Map<String, Object?>)['initial_balance'],
        '1234.00',
      );
    },
  );
  for (final status in [409, 422, 503]) {
    testWidgets('HTTP $status remains on the form and enables retry', (
      tester,
    ) async {
      final f = CreateFixture()..status = status;
      addTearDown(f.close);
      await mountPage(tester, f);
      await tester.enterText(find.byKey(const Key('account-name')), 'Reserva');
      await tester.pump();
      await tester.tap(find.byKey(const Key('account-save')));
      await tester.pumpAndSettle();
      expect(find.byType(AddAccountPage), findsOneWidget);
      expect(
        find.text(switch (status) {
          409 => home.l.accountDuplicateName,
          422 => home.l.requestInvalid,
          _ => home.l.connectionError,
        }),
        findsOneWidget,
      );
      expect(
        tester
            .widget<FormSheetButton>(find.byKey(const Key('account-save')))
            .onPressed,
        isNotNull,
      );
      expect(find.text('Reserva'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('pending POST blocks double submit and edits', (tester) async {
    final f = CreateFixture()..pending = Completer<http.Response>();
    addTearDown(f.close);
    await mountPage(tester, f);
    await tester.enterText(find.byKey(const Key('account-name')), 'Reserva');
    await tester.pump();
    final save = find.byKey(const Key('account-save'));
    await tester.tap(save);
    await tester.pump();
    await tester.tap(save);
    expect(f.posts, hasLength(1));
    expect(tester.widget<FormSheetButton>(save).onPressed, isNull);
    expect(
      tester
          .widget<AbsorbPointer>(find.byKey(const Key('account-fields')))
          .absorbing,
      isTrue,
    );
    f.pending!.complete(api.problem(422));
    await tester.pumpAndSettle();
    expect(tester.widget<FormSheetButton>(save).onPressed, isNotNull);
  });
  for (final brightness in Brightness.values) {
    testWidgets('add account page ${brightness.name} golden', (tester) async {
      final f = CreateFixture();
      addTearDown(f.close);
      await mountPage(tester, f, brightness: brightness);
      await tester.enterText(
        find.byKey(const Key('account-name')),
        'Fondo de viaje',
      );
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/add_account_${brightness.name}.png'),
      );
    });
    for (final empty in [false, true]) {
      testWidgets(
        'account carousel add card last empty=$empty ${brightness.name} golden',
        (tester) async {
          final f = CreateFixture();
          addTearDown(f.close);
          var taps = 0;
          await mobile.mountMobile(
            tester,
            brightness,
            (_, _) => Scaffold(
              body: Padding(
                padding: const EdgeInsets.all(13),
                child: HomeAccounts(
                  accounts: empty ? [] : [f.accounts.first],
                  selectedId: f.accounts.first.id,
                  onSelected: (_) {},
                  onCreate: () => taps++,
                ),
              ),
            ),
          );
          expect(find.byType(HomeAddCard), findsOneWidget);
          if (!empty) {
            expect(
              tester.getTopLeft(find.byType(HomeAddCard)).dx,
              greaterThan(
                tester
                    .getTopLeft(
                      find.byKey(Key('account-${f.accounts.first.id}')),
                    )
                    .dx,
              ),
            );
          }
          await tester.tap(find.byKey(const Key('add-account-card')));
          await tester.pumpAndSettle();
          expect(taps, 1);
          expect(tester.takeException(), isNull);
          await expectLater(
            find.byKey(const Key('capture')),
            matchesGoldenFile(
              'goldens/account_add_${empty ? 'empty' : 'data'}_${brightness.name}.png',
            ),
          );
        },
      );
    }
  }
}
