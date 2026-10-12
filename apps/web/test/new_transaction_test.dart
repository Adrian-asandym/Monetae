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
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/pages/login_page.dart';
import 'package:monetae_web/pages/new_transaction_page.dart';
import 'package:monetae_web/presentation/decimal_input.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/widgets/transaction_category_grid.dart';
import 'package:monetae_web/widgets/category_icon.dart';

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
  Completer<http.Response>? pendingAccounts;
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
        if (pendingAccounts != null) return pendingAccounts!.future;
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
  bool keepTitleSheet = false,
  bool editing = false,
}) async {
  await harness.mount(
    tester,
    brightness,
    (_, _) => NewTransactionPage(
      session: f.session,
      controller: f.form,
      editing: editing,
    ),
    captureSize: const Size(430, 1120),
    viewSize: const Size(480, 1170),
  );
  await tester.pumpAndSettle();
  if (!keepTitleSheet) await dismissTitleSheet(tester);
}

Future<void> dismissTitleSheet(WidgetTester tester) async {
  final sheet = find.byKey(const Key('title-sheet'));
  if (sheet.evaluate().isEmpty) return;
  await tester.tapAt(const Offset(10, 10));
  await tester.pumpAndSettle();
}

Future<void> fillAmount(WidgetTester tester, String text) async {
  await dismissTitleSheet(tester);
  await tester.tap(find.byKey(const Key('form-amount')));
  await tester.pumpAndSettle();
  for (final key in text.split('')) {
    await tester.tap(find.byKey(Key('amount-key-$key')));
    await tester.pump();
  }
  await tester.tap(find.byKey(const Key('amount-sheet-done')));
  await tester.pumpAndSettle();
}

/// The bottom action asks for a category first; null picks "Sin categoría".
Future<void> chooseCategory(WidgetTester tester, [String? id]) async {
  await tester.tap(find.byKey(const Key('form-category-button')));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(Key('form-category-${id ?? 'none'}')));
  await tester.pumpAndSettle();
  expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
  await tester.tap(find.byKey(const Key('amount-sheet-done')));
  await tester.pumpAndSettle();
}

/// Synthetic catalog with enough rows to exercise scrolling and truncation.
List<CategoryDto> sheetCategories() {
  const names = [
    'Comida',
    'Transporte',
    'Hogar',
    'Salud',
    'Compras',
    'Educación',
    'Servicios',
    'Entretenimiento y actividades',
  ];
  const colors = [
    '#40545F',
    '#B3A329',
    '#A23355',
    '#317347',
    '#6151A0',
    '#25678F',
    '#AE542F',
    '#259A92',
  ];
  const icons = [
    'restaurant',
    'transport',
    'home',
    'wallet',
    'calendar',
    'work',
    'loan',
  ];
  return List.generate(
    28,
    (i) => CategoryDto.fromJson({
      ...mockCategory(l).toJson(),
      'id': '00000000-0000-4000-8000-${(201 + i).toString().padLeft(12, '0')}',
      'name': i < names.length ? names[i] : 'Categoría sintética ${i + 1}',
      'color': colors[i % colors.length],
      'icon': icons[i % icons.length],
    }),
  );
}

Future<void> mountCategoryForm(
  WidgetTester tester,
  FormFixture f, {
  Brightness brightness = Brightness.dark,
  Size size = const Size(400, 642),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    RepaintBoundary(
      key: const Key('category-sheet-capture'),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: monetaeTheme(brightness: brightness),
        locale: const Locale('es'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: NewTransactionPage(session: f.session, controller: f.form),
      ),
    ),
  );
  await tester.pumpAndSettle();
  await dismissTitleSheet(tester);
  await tester.tap(find.byKey(const Key('form-category-button')));
  await tester.pumpAndSettle();
}

BoxDecoration tileDecoration(WidgetTester tester, String? id) =>
    tester
            .widget<Container>(
              find.descendant(
                of: find.byKey(Key('form-category-${id ?? 'none'}')),
                matching: find.byType(Container),
              ),
            )
            .decoration!
        as BoxDecoration;

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
  testWidgets('title sheet waits for catalogs and opens only once', (
    tester,
  ) async {
    final f = FormFixture()..pendingAccounts = Completer<http.Response>();
    addTearDown(f.close);
    await harness.mount(
      tester,
      Brightness.dark,
      (_, _) => NewTransactionPage(session: f.session, controller: f.form),
    );
    await tester.pump();
    expect(f.form.loading, isTrue);
    expect(find.byKey(const Key('title-sheet')), findsNothing);
    f.pendingAccounts!.complete(
      fixtures.ok({
        'items': f.accounts.map((a) => a.toJson()).toList(),
        'next_cursor': null,
      }),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('title-sheet')), findsOneWidget);
    final input = find.descendant(
      of: find.byKey(const Key('title-sheet-field')),
      matching: find.byType(EditableText),
    );
    expect(tester.widget<EditableText>(input).focusNode.hasFocus, isTrue);
    await tester.enterText(input, 'Título sintético');
    await dismissTitleSheet(tester);
    expect(f.form.title, 'Título sintético');
    final formInput = find.descendant(
      of: find.byKey(const Key('transaction-title')),
      matching: find.byType(EditableText),
    );
    expect(
      tester.widget<EditableText>(formInput).controller.text,
      f.form.title,
    );
    await tester.ensureVisible(formInput);
    await tester.enterText(formInput, 'Título actualizado');
    await tester.pumpAndSettle();
    expect(f.form.title, 'Título actualizado');
    await f.form.load();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('title-sheet')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  for (final submit in ['button', 'enter', 'empty']) {
    testWidgets('title sheet chains categories via $submit', (tester) async {
      final f = FormFixture();
      addTearDown(f.close);
      await mountForm(tester, f, keepTitleSheet: true);
      final input = find.descendant(
        of: find.byKey(const Key('title-sheet-field')),
        matching: find.byType(EditableText),
      );
      if (submit != 'empty') await tester.enterText(input, 'Título sintético');
      if (submit == 'enter') {
        await tester.testTextInput.receiveAction(TextInputAction.done);
      } else {
        await tester.tap(find.byKey(const Key('title-sheet-next')));
      }
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('title-sheet')), findsNothing);
      expect(find.byType(TransactionCategoryGrid), findsOneWidget);
      expect(f.form.title, submit == 'empty' ? '' : 'Título sintético');
      expect(f.posts, isEmpty);
      await tester.tap(find.byKey(const Key('form-category-none')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('title-sheet')), findsNothing);
      expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();
      expect(find.text(l.saveTransaction), findsOneWidget);
    });
  }

  testWidgets('swiping the title sheet preserves input', (tester) async {
    final f = FormFixture();
    addTearDown(f.close);
    await mountForm(tester, f, keepTitleSheet: true);
    await tester.enterText(
      find.descendant(
        of: find.byKey(const Key('title-sheet-field')),
        matching: find.byType(EditableText),
      ),
      'Borrador sintético',
    );
    await tester.fling(find.text(l.formEnterTitle), const Offset(0, 400), 1500);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('title-sheet')), findsNothing);
    expect(f.form.title, 'Borrador sintético');
    expect(find.byType(TransactionCategoryGrid), findsNothing);
  });

  testWidgets('title sheet calendar changes the form date', (tester) async {
    final f = FormFixture();
    addTearDown(f.close);
    await mountForm(tester, f, keepTitleSheet: true);
    await tester.tap(find.byKey(const Key('title-sheet-date')));
    await tester.pumpAndSettle();
    expect(find.byType(DatePickerDialog), findsOneWidget);
    await tester.tap(find.text('12').last);
    await tester.tap(find.byType(TextButton).last);
    await tester.pumpAndSettle();
    expect(f.form.limaTime, DateTime.utc(2026, 10, 12, 22, 30));
    expect(find.byKey(const Key('title-sheet')), findsOneWidget);
    await dismissTitleSheet(tester);
    expect(find.byKey(const Key('title-sheet')), findsNothing);
  });

  testWidgets(
    'editing skips the initial sheet and synchronizes existing title',
    (tester) async {
      final f = FormFixture();
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() => f.form.title = 'Título existente');
      await mountForm(tester, f, editing: true, keepTitleSheet: true);
      expect(find.byKey(const Key('title-sheet')), findsNothing);
      final input = find.descendant(
        of: find.byKey(const Key('transaction-title')),
        matching: find.byType(EditableText),
      );
      expect(
        tester.widget<EditableText>(input).controller.text,
        'Título existente',
      );
      f.form.edit(() => f.form.title = 'Título externo');
      await tester.pump();
      expect(
        tester.widget<EditableText>(input).controller.text,
        'Título externo',
      );
    },
  );

  for (final brightness in Brightness.values) {
    testWidgets('golden title sheet ${brightness.name} at 400x642', (
      tester,
    ) async {
      final f = FormFixture();
      addTearDown(f.close);
      tester.view.physicalSize = const Size(400, 642);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        RepaintBoundary(
          key: const Key('title-sheet-capture'),
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            theme: monetaeTheme(brightness: brightness),
            locale: const Locale('es'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: NewTransactionPage(session: f.session, controller: f.form),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text(l.formEnterTitle), findsOneWidget);
      await expectLater(
        find.byKey(const Key('title-sheet-capture')),
        matchesGoldenFile(
          'goldens/new_transaction_title_sheet_${brightness.name}.png',
        ),
      );
      tester.view.viewInsets = const FakeViewPadding(bottom: 300);
      addTearDown(tester.view.resetViewInsets);
      await tester.pumpAndSettle();
      final next = find.byKey(const Key('title-sheet-next'));
      expect(tester.getRect(next).bottom, lessThanOrEqualTo(342));
      expect(tester.takeException(), isNull);
    });
  }

  for (final uncategorized in [false, true]) {
    testWidgets('category choice $uncategorized opens amount and keeps title', (
      tester,
    ) async {
      final f = FormFixture();
      addTearDown(f.close);
      await mountForm(tester, f, keepTitleSheet: true);
      await tester.enterText(
        find.descendant(
          of: find.byKey(const Key('title-sheet-field')),
          matching: find.byType(EditableText),
        ),
        'Título sintético',
      );
      await tester.tap(find.byKey(const Key('title-sheet-next')));
      await tester.pumpAndSettle();
      final id = uncategorized ? null : mockCategory(l).id;
      await tester.tap(find.byKey(Key('form-category-${id ?? 'none'}')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('category-sheet')), findsNothing);
      expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
      expect(f.form.categoryId, id);
      expect(f.form.title, 'Título sintético');
      expect(f.posts, isEmpty);
      await tester.tap(find.byKey(const Key('amount-key-7')));
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();
      expect(f.form.amount, '7');
      expect(find.text(l.saveTransaction), findsOneWidget);
      await tester.tap(find.byKey(const Key('form-category-button')));
      await tester.pumpAndSettle();
      expect(tileDecoration(tester, id).border, isNotNull);
      expect(tileDecoration(tester, id).border!.top.width, 3);
      if (!uncategorized) expect(tileDecoration(tester, null).border, isNull);
    });
  }

  testWidgets('category dismissal and menu never open amount or save', (
    tester,
  ) async {
    final f = FormFixture();
    addTearDown(f.close);
    await mountCategoryForm(tester, f);
    expect(tileDecoration(tester, null).border, isNull);
    await tester.tap(find.byKey(const Key('category-sheet-menu')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('category-sheet')), findsOneWidget);
    await tester.tapAt(const Offset(10, 10));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('category-sheet')), findsNothing);
    expect(find.byKey(const Key('amount-sheet-done')), findsNothing);
    expect(f.form.categoryId, isNull);
    expect(find.text(l.formSelectCategory), findsOneWidget);
    expect(f.posts, isEmpty);
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pumpAndSettle();
    await tester.fling(
      find.text(l.formCategorySheetTitle),
      const Offset(0, 650),
      1500,
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('category-sheet')), findsNothing);
    expect(find.byKey(const Key('amount-sheet-done')), findsNothing);
  });

  testWidgets(
    'category grid has solid squares, light icons and truncated labels',
    (tester) async {
      final f = FormFixture()..categories = sheetCategories();
      addTearDown(f.close);
      await mountCategoryForm(tester, f);
      final first = f.categories.first;
      final grid = tester.widget<GridView>(
        find.byKey(const Key('category-sheet-grid')),
      );
      expect(
        (grid.gridDelegate as SliverGridDelegateWithFixedCrossAxisCount)
            .crossAxisCount,
        4,
      );
      expect(tileDecoration(tester, first.id).color, const Color(0xFF40545F));
      final square = find.descendant(
        of: find.byKey(Key('form-category-${first.id}')),
        matching: find.byType(Container),
      );
      expect(tester.getSize(square), const Size(64, 64));
      final icon = tester.widget<CategoryIcon>(
        find.descendant(
          of: find.byKey(Key('form-category-${first.id}')),
          matching: find.byType(CategoryIcon),
        ),
      );
      expect(icon.color, Colors.white);
      expect(icon.tintCustom, isTrue);
      final label = tester.widget<Text>(find.text(f.categories[7].name));
      expect(label.maxLines, 1);
      expect(label.overflow, TextOverflow.ellipsis);
      expect(label.textAlign, TextAlign.center);
      final none = tester.getRect(find.byKey(const Key('form-category-none')));
      final real = tester.getRect(find.byKey(Key('form-category-${first.id}')));
      expect(none.top, real.top);
      expect(none.left, lessThan(real.left));
      final last = find.byKey(Key('form-category-${f.categories.last.id}'));
      await tester.scrollUntilVisible(
        last,
        200,
        scrollable: find.descendant(
          of: find.byKey(const Key('category-sheet-grid')),
          matching: find.byType(Scrollable),
        ),
      );
      await tester.tap(last);
      await tester.pumpAndSettle();
      expect(f.form.categoryId, f.categories.last.id);
      expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  for (final brightness in Brightness.values) {
    for (final empty in [false, true]) {
      testWidgets(
        'golden category sheet ${brightness.name} empty=$empty at 400x642',
        (tester) async {
          final f = FormFixture()..categories = empty ? [] : sheetCategories();
          addTearDown(f.close);
          await f.form.load();
          if (!empty) f.form.edit(() => f.form.categoryId = f.categories[2].id);
          await mountCategoryForm(tester, f, brightness: brightness);
          expect(find.text(l.formCategorySheetTitle), findsOneWidget);
          expect(find.text(l.uncategorized), findsOneWidget);
          expect(tester.takeException(), isNull);
          await expectLater(
            find.byKey(const Key('category-sheet-capture')),
            matchesGoldenFile(
              'goldens/new_transaction_category_sheet_${empty ? 'empty_' : ''}${brightness.name}.png',
            ),
          );
          if (empty) {
            await tester.tap(find.byKey(const Key('form-category-none')));
            await tester.pumpAndSettle();
            expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
          }
        },
      );
    }
  }

  testWidgets('keypad precision/delete/clear and kind/category reset', (
    tester,
  ) async {
    final f = FormFixture();
    addTearDown(f.close);
    await mountForm(tester, f);
    expect(find.text(l.formSelectCategory), findsOneWidget);
    await tester.tap(find.byKey(const Key('form-amount')));
    await tester.pumpAndSettle();
    for (final key in ['1', '2', '.', '5', '0', '9']) {
      await tester.tap(find.byKey(Key('amount-key-$key')));
      await tester.pump();
    }
    expect(f.form.amount, '12.50');
    expect(find.text('12,50 S/.'), findsWidgets);
    await tester.tap(find.byKey(const Key('amount-key-backspace')));
    await tester.pump();
    expect(f.form.amount, '12.5');
    await tester.longPress(find.byKey(const Key('amount-key-backspace')));
    await tester.pump();
    expect(f.form.amount, isEmpty);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await fillAmount(tester, '12.50');
    // With no category chosen, the bottom action opens the category sheet.
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('form-category-${mockCategory(l).id}')));
    await tester.pumpAndSettle();
    expect(f.form.categoryId, mockCategory(l).id);
    expect(find.byKey(const Key('amount-sheet-done')), findsOneWidget);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.text(l.saveTransaction), findsOneWidget);
    expect(f.posts, isEmpty);
    await tester.tap(find.byKey(const Key('select-income')));
    await tester.pumpAndSettle();
    expect(f.form.categoryId, isNull);
    expect(find.text(l.formSelectCategory), findsOneWidget);
    await tester.tap(find.byKey(const Key('form-category-button')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<TransactionCategoryGrid>(find.byType(TransactionCategoryGrid))
          .categories
          .single
          .kind,
      CategoryKind.income,
    );
  });
  testWidgets(
    'preferred account, rate editing/account change and field errors',
    (tester) async {
      final f = FormFixture(preferred: usdId);
      addTearDown(f.close);
      await mountForm(tester, f);
      expect(find.byKey(const Key('transaction-rate')), findsOneWidget);
      await chooseCategory(tester);
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pump();
      expect(find.text(l.positiveAmountRequired), findsOneWidget);
      expect(find.text(l.positiveRateRequired), findsOneWidget);
      await fillAmount(tester, '12.50');
      await tester.ensureVisible(find.byKey(const Key('transaction-rate')));
      await tester.enterText(
        find.descendant(
          of: find.byKey(const Key('transaction-rate')),
          matching: find.byType(EditableText),
        ),
        '3.800001',
      );
      await tester.pump();
      expect(f.form.rate, '3.800001');
      await tester.ensureVisible(
        find.byKey(Key('form-account-$mockAccountId')),
      );
      await tester.tap(find.byKey(Key('form-account-$mockAccountId')));
      await tester.pumpAndSettle();
      expect(f.form.account!.id, mockAccountId);
      expect(find.byKey(const Key('transaction-rate')), findsNothing);
      await tester.ensureVisible(find.byKey(const Key('form-account-list')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('form-account-list')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(Key('form-account-option-$usdId')));
      await tester.pumpAndSettle();
      expect(f.form.account!.id, usdId);
      expect(f.form.rate, isEmpty);
      await tester.tap(find.byKey(Key('form-account-$mockAccountId')));
      await tester.pumpAndSettle();
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
      await chooseCategory(tester);
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
    await chooseCategory(tester);
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
      await chooseCategory(tester);
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
      await chooseCategory(tester);
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
    await chooseCategory(tester);
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
      await chooseCategory(tester);
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
      await chooseCategory(tester);
      f.pending = Completer<http.Response>();
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pump();
      expect(
        tester
            .widget<FilledButton>(find.byKey(const Key('save-transaction')))
            .onPressed,
        isNull,
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
        await dismissTitleSheet(tester);
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
        expect(f.form.scheduled, variant == 'foreign');
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
