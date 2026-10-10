import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/new_transaction_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/pages/login_page.dart';
import 'package:monetae_web/pages/new_transaction_page.dart';
import 'package:monetae_web/presentation/decimal_input.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/widgets/transaction_category_grid.dart';

import 'api_session_test.dart' as fixtures;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;

final now = DateTime.utc(2026, 10, 10, 3, 30);
final l = fixtures.l;
const usdId = '00000000-0000-4000-8000-000000000002';

class FormFixture {
  FormFixture({
    String? preferred = mockAccountId,
    bool empty = false,
    String baseCurrency = 'PEN',
  }) {
    profile = {
      ...fixtures.profile(),
      'base_currency': baseCurrency,
      'report_currency': 'PEN',
      'preferences': {
        'theme': 'light',
        'home_widgets': <String>[],
        'default_account_id': preferred,
        'transaction_card': const TransactionCardPreferencesDto().toJson(),
      },
    };
    accounts = empty ? [] : backend.accounts;
    categories = [mockCategory(l), mockCategory(l, income: true)];
    api = ApiClient(cookies: () => cookie, client: MockClient(handle));
    session = SessionController(api)
      ..user = CurrentUserDto.fromJson(profile)
      ..loading = false;
    form = NewTransactionController(api, session.user!, now: () => clock);
  }
  late final Map<String, Object?> profile;
  late List<AccountDto> accounts;
  late List<CategoryDto> categories;
  late final ApiClient api;
  late final SessionController session;
  late final NewTransactionController form;
  final backend = home.HomeFixture();
  final requests = <http.Request>[];
  List<http.Request> get posts =>
      requests.where((r) => r.method == 'POST').toList();
  int status = 201;
  String cookie = 'monetae_csrf=synthetic.one';
  DateTime clock = now;
  Completer<http.Response>? pending;
  bool fieldError = false, networkError = false, paginated = false;
  int? catalogStatus;
  http.Response created(http.Request r) {
    final body = jsonDecode(r.body) as Map<String, Object?>;
    return http.Response(
      jsonEncode({
        ...mockTransactionJson(),
        ...body,
        'category_id': body['category_id'],
        'note': body['note'],
        'tag_ids': <String>[],
      }),
      201,
    );
  }

  Future<http.Response> handle(http.Request r) async {
    requests.add(r);
    if (r.method == 'POST') {
      if (networkError) throw http.ClientException('Synthetic disconnect');
      if (pending != null) return pending!.future;
      if (fieldError) {
        return http.Response(
          jsonEncode({
            'type': 'about:blank',
            'title': 'Validation',
            'status': 422,
            'detail': 'Synthetic validation',
            'errors': [
              {
                'field': 'body.amount',
                'message': 'Importe inválido sintético',
                'code': 'invalid',
              },
            ],
          }),
          422,
        );
      }
      return status == 201 ? created(r) : fixtures.problem(status);
    }
    switch (r.url.path) {
      case '/api/v1/users/me':
        return fixtures.ok(profile);
      case '/api/v1/accounts':
        if (catalogStatus != null) return fixtures.problem(catalogStatus!);
        if (paginated && r.url.queryParameters['cursor'] == null) {
          return fixtures.ok({
            'items': [accounts.first.toJson()],
            'next_cursor': 'second',
          });
        }
        return fixtures.ok({
          'items': (paginated ? accounts.skip(1) : accounts)
              .map((a) => a.toJson())
              .toList(),
          'next_cursor': null,
        });
      case '/api/v1/categories':
        if (paginated && r.url.queryParameters['cursor'] == null) {
          return fixtures.ok({
            'items': [categories.first.toJson()],
            'next_cursor': 'second',
          });
        }
        return fixtures.ok({
          'items': (paginated ? categories.skip(1) : categories)
              .map((c) => c.toJson())
              .toList(),
          'next_cursor': null,
        });
      default:
        return backend.handle(r);
    }
  }

  void close() {
    form.dispose();
    session.dispose();
    api.close();
    backend.close();
  }
}

Future<void> mountForm(
  WidgetTester tester,
  FormFixture f, {
  Brightness brightness = Brightness.light,
}) async {
  await harness.mount(
    tester,
    brightness,
    (_, _) => NewTransactionPage(session: f.session, controller: f.form),
    captureSize: const Size(430, 1120),
    viewSize: const Size(480, 1170),
  );
  await tester.pumpAndSettle();
}

Future<void> fillAmount(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('transaction-amount')), text);
  await tester.pump();
}

void main() {
  harness.loadGoldenFonts();
  test('decimal formatter rejects excess precision/signs and preserves huge exact strings', () {
    const f = DecimalTextFormatter(2), old = TextEditingValue(text: '12.50');
    for (final text in ['12.501', '-1', '1e2', '1.2.3', 'abc']) {
      expect(f.formatEditUpdate(old, TextEditingValue(text: text)), old);
    }
    expect(
      f
          .formatEditUpdate(
            old,
            const TextEditingValue(text: '9007199254740993.01'),
          )
          .text,
      '9007199254740993.01',
    );
    expect(
      f.formatEditUpdate(old, const TextEditingValue(text: '12,50')).text,
      '12.50',
    );
    expect(positiveDecimal('0.00', 2), isFalse);
    expect(positiveDecimal('0.01', 2), isTrue);
    expect(positiveDecimal('3.800001', 6), isTrue);
    expect(positiveDecimal('3.8000001', 6), isFalse);
    expect(amountWireText('0012.5'), '12.50');
  });
  test('UUIDs are distinct RFC 4122 v4 keys', () {
    final keys = List.generate(100, (_) => newIdempotencyKey());
    expect(keys.toSet(), hasLength(100));
    for (final key in keys) {
      expect(
        key,
        matches(
          RegExp(
            r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$',
          ),
        ),
      );
    }
  });
  for (final preferred in [usdId, null, 'unknown']) {
    test('default account uses active server order ($preferred)', () async {
      final f = FormFixture(preferred: preferred);
      addTearDown(f.close);
      f.accounts = [
        AccountDto.fromJson({
          ...f.accounts.first.toJson(),
          'id': 'archived',
          'archived_at': '2026-10-01T00:00:00Z',
        }),
        ...f.accounts,
      ];
      await f.form.load();
      expect(f.form.account!.id, preferred == usdId ? usdId : mockAccountId);
      expect(f.requests.first.url.queryParameters['include_archived'], 'false');
    });
  }
  test('pagination, deleted categories and kind/category reset', () async {
    final f = FormFixture(preferred: usdId)..paginated = true;
    addTearDown(f.close);
    f.categories.add(
      CategoryDto.fromJson({
        ...f.categories.first.toJson(),
        'id': 'deleted',
        'deleted_at': '2026-10-01T00:00:00Z',
      }),
    );
    await f.form.load();
    expect(f.form.account!.id, usdId);
    expect(f.form.visibleCategories.map((c) => c.id), [mockCategory(l).id]);
    f.form.edit(() => f.form.categoryId = mockCategory(l).id);
    f.form.selectIncome(true);
    expect(f.form.categoryId, isNull);
    expect(f.form.visibleCategories.map((c) => c.id), [
      mockCategory(l, income: true).id,
    ]);
    expect(
      f.requests.where((r) => r.url.queryParameters['cursor'] == 'second'),
      hasLength(2),
    );
  });
  for (final income in [false, true]) {
    test(
      'exact ${income ? 'income' : 'expense'} POST, empty title, CSRF and base rate',
      () async {
        final f = FormFixture();
        addTearDown(f.close);
        await f.form.load();
        f.form.selectIncome(income);
        f.form.edit(() => f.form.amount = '12.50');
        expect(await f.form.save(), isTrue);
        expect(jsonDecode(f.posts.single.body), {
          'account_id': mockAccountId,
          'kind': income ? 'income' : 'expense',
          'amount': income ? '12.50' : '-12.50',
          'currency': 'PEN',
          'occurred_at': '2026-10-10T03:30:00.000Z',
          'status': 'posted',
          'title': '',
          'fx_rate_to_base': '1.000000',
          'fx_rate_source': 'manual',
        });
        expect(f.posts.single.headers['X-CSRF-Token'], 'synthetic.one');
        expect(f.posts.single.headers['Idempotency-Key'], isNotEmpty);
        expect(f.form.limaTime, DateTime.utc(2026, 10, 9, 22, 30));
      },
    );
  }
  test(
    'foreign rate/category/title/note and future Lima date form exact body',
    () async {
      final f = FormFixture(preferred: usdId);
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() {
        f.form.amount = '12.50';
        f.form.rate = '3.800001';
        f.form.categoryId = mockCategory(l).id;
        f.form.title = 'Prueba';
        f.form.note = 'Nota';
      });
      f.form.selectLimaTime(DateTime(2026, 10, 11, 23, 45));
      expect(await f.form.save(), isTrue);
      expect(jsonDecode(f.posts.single.body), {
        'account_id': usdId,
        'category_id': mockCategory(l).id,
        'kind': 'expense',
        'amount': '-12.50',
        'currency': 'USD',
        'occurred_at': '2026-10-12T04:45:00.000Z',
        'status': 'scheduled',
        'title': 'Prueba',
        'note': 'Nota',
        'fx_rate_to_base': '3.800001',
        'fx_rate_source': 'manual',
      });
      f.form.selectAccount(f.accounts.first);
      expect(f.form.needsRate, isFalse);
      expect(f.form.rate, isEmpty);
      expect(await f.form.save(), isTrue);
      expect(
        (jsonDecode(f.posts.last.body) as Map)['fx_rate_to_base'],
        '1.000000',
      );
    },
  );
  test(
    'short foreign rate is padded on text and USD base uses unity rate',
    () async {
      final f = FormFixture(preferred: usdId);
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() {
        f.form.amount = '12.50';
        f.form.rate = '0003.8';
      });
      expect(await f.form.save(), isTrue);
      expect(
        (jsonDecode(f.posts.single.body) as Map)['fx_rate_to_base'],
        '3.800000',
      );
      final usd = FormFixture(preferred: usdId, baseCurrency: 'USD');
      addTearDown(usd.close);
      await usd.form.load();
      expect(usd.form.needsRate, isFalse);
      usd.form.edit(() => usd.form.amount = '12.50');
      expect(await usd.form.save(), isTrue);
      expect(
        (jsonDecode(usd.posts.single.body) as Map)['fx_rate_to_base'],
        '1.000000',
      );
    },
  );

  test(
    'scheduled retry retains its visible state after date passes until edited',
    () async {
      final f = FormFixture()..status = 500;
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() => f.form.amount = '12.50');
      f.form.selectLimaTime(DateTime(2026, 10, 11, 10, 30));
      expect(await f.form.save(), isFalse);
      f.clock = now.add(const Duration(days: 4));
      expect(f.form.scheduled, isTrue);
      expect(await f.form.save(), isFalse);
      expect(f.posts.last.body, f.posts.first.body);
      f.form.edit(() => f.form.title = 'Edited');
      expect(f.form.scheduled, isFalse);
    },
  );

  test('zero amounts, missing accounts and invalid rates never send', () async {
    final f = FormFixture(preferred: usdId);
    addTearDown(f.close);
    await f.form.load();
    expect(await f.form.save(), isFalse);
    expect(f.form.invalidFields, containsAll(['amount', 'fx_rate_to_base']));
    f.form.edit(() {
      f.form.amount = '12.50';
      f.form.rate = '0.000000';
    });
    expect(await f.form.save(), isFalse);
    f.form.edit(() => f.form.rate = '3.8000001');
    expect(await f.form.save(), isFalse);
    f.form.edit(() => f.form.account = null);
    expect(await f.form.save(), isFalse);
    expect(f.form.invalidFields, contains('account_id'));
    expect(f.posts, isEmpty);
  });
  for (final status in [409, 500]) {
    test(
      'retry $status retains body/key; edits renew key and CSRF rotates',
      () async {
        final f = FormFixture()..status = status;
        addTearDown(f.close);
        await f.form.load();
        f.form.edit(() => f.form.amount = '12.50');
        expect(await f.form.save(), isFalse);
        final first = f.posts.single;
        f.cookie = 'monetae_csrf=synthetic.two';
        f.clock = now.add(const Duration(days: 1));
        expect(await f.form.save(), isFalse);
        expect(
          f.posts.last.headers['Idempotency-Key'],
          first.headers['Idempotency-Key'],
        );
        expect(f.posts.last.body, first.body);
        expect(f.posts.last.headers['X-CSRF-Token'], 'synthetic.two');
        f.form.edit(() => f.form.title = 'Cambio');
        f.status = 201;
        expect(await f.form.save(), isTrue);
        expect(
          f.posts.last.headers['Idempotency-Key'],
          isNot(first.headers['Idempotency-Key']),
        );
      },
    );
  }
  test('ambiguous network failure retries exact huge amount with original key/body', () async {
    final f = FormFixture()..networkError = true;
    addTearDown(f.close);
    await f.form.load();
    f.form.edit(() => f.form.amount = '9007199254740993.01');
    expect(await f.form.save(), isFalse);
    f.networkError = false;
    expect(await f.form.save(), isTrue);
    expect(
      f.posts.last.headers['Idempotency-Key'],
      f.posts.first.headers['Idempotency-Key'],
    );
    expect(f.posts.last.body, f.posts.first.body);
    expect(
      (jsonDecode(f.posts.last.body) as Map)['amount'],
      '-9007199254740993.01',
    );
  });
  testWidgets(
    'keypad precision/delete/clear, hardware input and kind/category reset',
    (tester) async {
      final f = FormFixture();
      addTearDown(f.close);
      await mountForm(tester, f);
      for (final key in ['1', '2', '.', '5', '0', '9']) {
        await tester.tap(find.byKey(Key('amount-key-$key')));
        await tester.pump();
      }
      expect(f.form.amount, '12.50');
      expect(find.text('12,50 S/.'), findsOneWidget);
      await tester.tap(find.byKey(const Key('amount-key-backspace')));
      await tester.pump();
      expect(f.form.amount, '12.5');
      await tester.longPress(find.byKey(const Key('amount-key-backspace')));
      await tester.pump();
      expect(f.form.amount, isEmpty);
      await fillAmount(tester, '12.50');
      await tester.tap(find.byKey(Key('form-category-${mockCategory(l).id}')));
      await tester.pump();
      expect(f.form.categoryId, mockCategory(l).id);
      await tester.tap(find.byKey(const Key('select-income')));
      await tester.pumpAndSettle();
      expect(f.form.categoryId, isNull);
      expect(
        tester
            .widget<TransactionCategoryGrid>(
              find.byType(TransactionCategoryGrid),
            )
            .categories
            .single
            .kind,
        CategoryKind.income,
      );
    },
  );
  testWidgets(
    'preferred account, rate editing/account change and field errors',
    (tester) async {
      final f = FormFixture(preferred: usdId);
      addTearDown(f.close);
      await mountForm(tester, f);
      expect(find.byKey(const Key('transaction-rate')), findsOneWidget);
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pump();
      expect(find.text(l.positiveAmountRequired), findsOneWidget);
      expect(find.text(l.positiveRateRequired), findsOneWidget);
      await fillAmount(tester, '12.50');
      await tester.ensureVisible(find.byKey(const Key('transaction-rate')));
      await tester.enterText(
        find.byKey(const Key('transaction-rate')),
        '3.800001',
      );
      await tester.pump();
      expect(f.form.rate, '3.800001');
      await tester.tap(find.byKey(ValueKey('form-account-$usdId')));
      await tester.pumpAndSettle();
      await tester.tap(find.text(f.accounts.first.name).last);
      await tester.pumpAndSettle();
      expect(f.form.account!.id, mockAccountId);
      expect(find.byKey(const Key('transaction-rate')), findsNothing);
    },
  );
  testWidgets(
    'catalog failure can retry and empty active accounts never submit',
    (tester) async {
      final f = FormFixture(empty: true)..catalogStatus = 500;
      addTearDown(f.close);
      await mountForm(tester, f);
      expect(find.text(l.connectionError), findsOneWidget);
      f.catalogStatus = null;
      await tester.tap(find.byKey(const Key('retry-transaction')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pump();
      expect(find.text(l.accountRequired), findsOneWidget);
      expect(f.posts, isEmpty);
    },
  );
  testWidgets('double tap sends once and freezes edits until completion', (
    tester,
  ) async {
    final f = FormFixture();
    addTearDown(f.close);
    await mountForm(tester, f);
    await fillAmount(tester, '12.50');
    f.pending = Completer<http.Response>();
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pump();
    expect(f.posts, hasLength(1));
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('save-transaction')))
          .onPressed,
      isNull,
    );
    f.form.selectIncome(true);
    expect(f.form.income, isFalse);
    f.pending!.complete(fixtures.problem(500));
    await tester.pumpAndSettle();
    expect(f.form.busy, isFalse);
  });
  testWidgets(
    '422 appears at amount; unknown validation gives general notice',
    (tester) async {
      final f = FormFixture()..fieldError = true;
      addTearDown(f.close);
      await mountForm(tester, f);
      await fillAmount(tester, '12.50');
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pumpAndSettle();
      expect(find.text('Importe inválido sintético'), findsOneWidget);
      expect(find.text(l.requestInvalid), findsOneWidget);
      f.fieldError = false;
      f.status = 422;
      await tester.tap(find.byKey(const Key('retry-transaction')));
      await tester.pumpAndSettle();
      expect(find.text('Importe inválido sintético'), findsNothing);
      expect(find.text(l.requestInvalid), findsOneWidget);
    },
  );
  for (final status in [409, 500]) {
    testWidgets('$status has a working retry using original idempotency key', (
      tester,
    ) async {
      final f = FormFixture()..status = status;
      addTearDown(f.close);
      await mountForm(tester, f);
      await fillAmount(tester, '12.50');
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pumpAndSettle();
      expect(
        find.text(status == 409 ? l.requestConflict : l.connectionError),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const Key('retry-transaction')));
      await tester.pumpAndSettle();
      expect(f.posts, hasLength(2));
      expect(
        f.posts.last.headers['Idempotency-Key'],
        f.posts.first.headers['Idempotency-Key'],
      );
    });
  }
  testWidgets('401 removes private route and returns to login', (tester) async {
    final f = FormFixture()..status = 401;
    addTearDown(f.close);
    await tester.pumpWidget(MonetaeApp(api: f.api));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('add-transaction')));
    await tester.pumpAndSettle();
    await fillAmount(tester, '12.50');
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pumpAndSettle();
    expect(find.byType(LoginPage), findsOneWidget);
    expect(find.byType(NewTransactionPage), findsNothing);
  });
  testWidgets(
    '201 from Transactions returns Home, reloads all blocks and shows notice',
    (tester) async {
      final f = FormFixture();
      addTearDown(f.close);
      await tester.pumpWidget(MonetaeApp(api: f.api));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-1')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('transactions-add')));
      await tester.pumpAndSettle();
      await fillAmount(tester, '12.50');
      final before = f.requests.length;
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pumpAndSettle();
      expect(find.byType(NewTransactionPage), findsNothing);
      expect(find.byType(HomePage), findsOneWidget);
      expect(find.text(l.transactionSaved), findsOneWidget);
      for (final path in [
        'accounts',
        'goals',
        'budgets',
        'reports/categories',
        'reports/cash-flow',
        'transactions',
      ]) {
        expect(
          f.requests
              .skip(before)
              .where((r) => r.method == 'GET' && r.url.path == '/api/v1/$path'),
          isNotEmpty,
          reason: path,
        );
      }
      expect(
        tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex,
        0,
      );
    },
  );
  testWidgets(
    'leaving an in-flight form still refreshes Home when the save succeeds',
    (tester) async {
      final f = FormFixture();
      addTearDown(f.close);
      await tester.pumpWidget(MonetaeApp(api: f.api));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('add-transaction')));
      await tester.pumpAndSettle();
      await fillAmount(tester, '12.50');
      f.pending = Completer<http.Response>();
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pump();
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('transaction-amount')))
            .readOnly,
        isTrue,
      );
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      expect(find.byType(NewTransactionPage), findsNothing);
      final before = f.requests.length;
      f.pending!.complete(f.created(f.posts.single));
      await tester.pumpAndSettle();
      expect(
        f.requests.skip(before).where((r) => r.url.path == '/api/v1/accounts'),
        isNotEmpty,
      );
      expect(find.byType(HomePage), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'narrow and desktop forms retain working controls without overflow',
    (tester) async {
      final f = FormFixture(preferred: usdId);
      addTearDown(f.close);
      for (final size in [const Size(360, 800), const Size(1200, 900)]) {
        await harness.mount(
          tester,
          Brightness.dark,
          (_, _) => NewTransactionPage(session: f.session, controller: f.form),
          captureSize: size,
          viewSize: Size(size.width + 50, size.height + 50),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.byKey(const Key('save-transaction')), findsOneWidget);
        await tester.ensureVisible(find.byKey(const Key('transaction-rate')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      }
    },
  );

  for (final brightness in [Brightness.light, Brightness.dark]) {
    for (final variant in ['expense', 'income', 'foreign']) {
      testWidgets('golden form $variant ${brightness.name}', (tester) async {
        final f = FormFixture(
          preferred: variant == 'foreign' ? usdId : mockAccountId,
        );
        addTearDown(f.close);
        await f.form.load();
        f.form.edit(() {
          f.form.income = variant == 'income';
          f.form.amount = '12.50';
          f.form.categoryId = mockCategory(l, income: variant == 'income').id;
          f.form.rate = variant == 'foreign' ? '3.800001' : '';
        });
        if (variant == 'foreign') {
          f.form.selectLimaTime(DateTime(2026, 10, 11, 10, 30));
        }
        await mountForm(tester, f, brightness: brightness);
        expect(
          find.text(
            variant == 'foreign' ? l.transactionScheduled : l.transactionPosted,
          ),
          findsOneWidget,
        );
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile(
            'goldens/new_transaction_${variant}_${brightness.name}.png',
          ),
        );
      });
    }
  }
}
