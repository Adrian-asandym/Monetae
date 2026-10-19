import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/new_transaction_controller.dart';
import 'package:monetae_web/api/transaction_feed.dart';
import 'package:monetae_web/api/transfer_balance_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/pages/new_transaction_page.dart';
import 'package:monetae_web/pages/transactions_page.dart';
import 'package:monetae_web/pages/transfer_balance_page.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/widgets/transaction_card.dart';
import 'package:monetae_web/widgets/home_transaction_row.dart';

import 'api_session_test.dart' as fixtures;
import 'components_test.dart' as harness;
import 'new_transaction_test.dart' as creation;

const correctionOut = '00000000-0000-4000-8000-000000000021';
const correctionIn = '00000000-0000-4000-8000-000000000022';

class EditFixture {
  EditFixture({Map<String, Object?> changes = const {}}) {
    record = {
      ...mockTransactionJson(
        title: 'Compra sintética',
        note: 'Nota de prueba',
        amount: '-12.50',
        occurredAt: '2026-10-08T15:45:00Z',
      ),
      ...changes,
    };
    base.categories.addAll([
      for (final income in [false, true])
        CategoryDto.fromJson({
          ...base.categories.first.toJson(),
          'id': income ? correctionIn : correctionOut,
          // Deliberately unrelated to the displayed name: lookup uses system_key.
          'name': income ? 'Entrada sintética' : 'Salida sintética',
          'kind': income ? 'income' : 'expense',
          'system_key': income
              ? 'balance_correction_income'
              : 'balance_correction_expense',
          'is_system': true,
        }),
    ]);
    api = ApiClient(
      client: MockClient(handle),
      cookies: () => 'monetae_csrf=synthetic.edit',
    );
    session = SessionController(api)
      ..user = base.session.user
      ..loading = false;
    form = NewTransactionController(
      api,
      session.user!,
      transactionId: record['id']! as String,
      now: () => creation.now,
    );
  }

  final base = creation.FormFixture();
  late Map<String, Object?> record;
  late final ApiClient api;
  late final SessionController session;
  late final NewTransactionController form;
  final requests = <http.Request>[];
  int patchStatus = 200;
  int? transactionStatus;
  bool paginate = false;
  List<http.Request> get patches =>
      requests.where((r) => r.method == 'PATCH').toList();
  List<http.Request> get feeds => requests
      .where((r) => r.method == 'GET' && r.url.path == '/api/v1/transactions')
      .toList();

  Future<http.Response> handle(http.Request r) async {
    requests.add(r);
    if (r.url.path == '/api/v1/transactions/${record['id']}') {
      if (r.method == 'PATCH') {
        if (patchStatus != 200) return fixtures.problem(patchStatus);
        record = {...record, ...jsonDecode(r.body) as Map<String, Object?>};
      } else if (transactionStatus != null) {
        return fixtures.problem(transactionStatus!);
      }
      return fixtures.ok(record);
    }
    if (r.url.path == '/api/v1/transactions') {
      return fixtures.ok({
        'items': [record],
        'next_cursor': paginate && r.url.queryParameters['cursor'] == null
            ? 'next'
            : null,
      });
    }
    if (r.url.path == '/api/v1/tags') {
      return fixtures.ok({
        'items': [fixtures.tag.toJson()],
        'next_cursor': null,
      });
    }
    if (r.url.path == '/api/v1/tags/${fixtures.tag.id}') {
      return fixtures.ok(fixtures.tag.toJson());
    }
    if (r.url.path.startsWith('/api/v1/accounts/')) {
      return fixtures.ok(base.accounts.first.toJson());
    }
    return base.handle(r);
  }

  void close() {
    form.dispose();
    session.dispose();
    api.close();
    base.close();
  }
}

Future<void> mountEditor(
  WidgetTester tester,
  EditFixture f, {
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

Future<void> mountRoute(WidgetTester tester, EditFixture f, Widget page) async {
  tester.view.physicalSize = const Size(900, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: monetaeTheme(brightness: Brightness.light),
      locale: const Locale('es'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: page,
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();

  test('loads exact fields, large decimals, tags, rate source and saved status', () async {
    final f = EditFixture(
      changes: {
        'amount': '-90071992547409.93',
        'account_id': creation.usdId,
        'currency': 'USD',
        'fx_rate_to_base': '3.800001',
        'fx_rate_source': 'auto',
        'tag_ids': [fixtures.tag.id],
        // Even if overdue, do not silently post a saved scheduled transaction.
        'status': 'scheduled',
      },
    );
    addTearDown(f.close);
    await f.form.load();
    expect(f.form.error, isNull);
    expect(f.form.amount, '90071992547409.93');
    expect(f.form.account!.id, creation.usdId);
    expect(f.form.categoryId, f.record['category_id']);
    expect(f.form.title, 'Compra sintética');
    expect(f.form.note, 'Nota de prueba');
    expect(f.form.rate, '3.800001');
    expect(f.form.tags.single.id, fixtures.tag.id);
    expect(f.form.limaTime, DateTime.utc(2026, 10, 8, 10, 45));
    expect(f.form.scheduled, isTrue);
    expect(await f.form.save(), isTrue);
    expect(f.patches, isEmpty);
    f.form.edit(() => f.form.title = 'Título editado');
    expect(await f.form.save(), isTrue);
    expect(jsonDecode(f.patches.single.body), {'title': 'Título editado'});
    expect(f.patches.single.headers['X-CSRF-Token'], 'synthetic.edit');
    expect(f.requests.any((r) => r.method == 'POST'), isFalse);
  });

  test('PATCH sends only edits with exact two-decimal signed money and null clearing', () async {
    final f = EditFixture();
    addTearDown(f.close);
    await f.form.load();
    f.form.edit(() {
      f.form.amount = '90071992547409.91';
      f.form.note = '';
      f.form.categoryId = null;
    });
    expect(await f.form.save(), isTrue);
    expect(jsonDecode(f.patches.single.body), {
      'amount': '-90071992547409.91',
      'note': null,
      'category_id': null,
    });
  });

  test('PATCH handles kind/account/rate changes and pads decimals', () async {
    final f = EditFixture(
      changes: {
        'account_id': creation.usdId,
        'currency': 'USD',
        'amount': '12.50',
        'kind': 'income',
        'fx_rate_to_base': '3.800001',
        'fx_rate_source': 'auto',
      },
    );
    addTearDown(f.close);
    await f.form.load();
    f.form.selectIncome(false);
    f.form.edit(() {
      f.form.amount = '40';
      f.form.rate = '3.9';
    });
    expect(await f.form.save(), isTrue);
    expect(jsonDecode(f.patches.single.body), {
      'kind': 'expense',
      'category_id': null,
      'amount': '-40.00',
      'fx_rate_to_base': '3.900000',
      'fx_rate_source': 'manual',
    });
    expect(f.form.accounts.every((a) => a.currency == 'USD'), isTrue);
  });

  test(
    'failed PATCH retains changes for retry and surfaces server validation',
    () async {
      final f = EditFixture()..patchStatus = 422;
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() => f.form.title = 'Cambio pendiente');
      expect(await f.form.save(), isFalse);
      expect(f.form.error!.kind, ApiErrorKind.validation);
      f.patchStatus = 200;
      expect(await f.form.save(), isTrue);
      expect(f.patches.map((r) => r.body).toSet().length, 1);
    },
  );

  test(
    'changing accounts preserves currency and sends only account_id',
    () async {
      final f = EditFixture();
      addTearDown(f.close);
      final other = AccountDto.fromJson({
        ...f.base.accounts.first.toJson(),
        'id': '00000000-0000-4000-8000-000000000003',
        'name': 'Otra cuenta de prueba',
      });
      f.base.accounts.add(other);
      await f.form.load();
      f.form.selectAccount(other);
      expect(await f.form.save(), isTrue);
      expect(jsonDecode(f.patches.single.body), {'account_id': other.id});
    },
  );

  test(
    'equivalent rate text preserves the existing automatic source',
    () async {
      final f = EditFixture(
        changes: {
          'account_id': creation.usdId,
          'currency': 'USD',
          'fx_rate_to_base': '3.800000',
          'fx_rate_source': 'auto',
        },
      );
      addTearDown(f.close);
      await f.form.load();
      f.form.edit(() => f.form.rate = '3.8');
      expect(await f.form.save(), isTrue);
      expect(f.patches, isEmpty);
    },
  );

  testWidgets(
    'preloads title, note, rate and tags without opening creation sheets',
    (tester) async {
      final f = EditFixture(
        changes: {
          'account_id': creation.usdId,
          'currency': 'USD',
          'fx_rate_to_base': '3.800001',
          'tag_ids': [fixtures.tag.id],
        },
      );
      addTearDown(f.close);
      await mountEditor(tester, f);
      expect(find.text(fixtures.l.formEditTitle), findsOneWidget);
      expect(find.byKey(const Key('title-sheet')), findsNothing);
      expect(find.text('Compra sintética'), findsOneWidget);
      expect(find.text('Nota de prueba'), findsOneWidget);
      expect(find.text('3.800001'), findsOneWidget);
      expect(find.text(fixtures.tag.name), findsOneWidget);
      expect(find.text(fixtures.l.saveTransaction), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'correction locks kind/category and still edits arrival date and amount',
    (tester) async {
      final f = EditFixture(
        changes: {
          'kind': 'income',
          'amount': '12.50',
          'category_id': correctionIn,
          'transfer_group_id': '00000000-0000-4000-8000-000000000030',
        },
      );
      addTearDown(f.close);
      await mountEditor(tester, f);
      expect(
        find.byKey(const Key('transaction-correction-locked')),
        findsOneWidget,
      );
      await tester.tap(
        find.byKey(const Key('select-expense')),
        warnIfMissed: false,
      );
      await tester.tap(find.byKey(const Key('form-category-button')));
      await tester.pumpAndSettle();
      expect(f.form.income, isTrue);
      expect(f.form.categoryId, correctionIn);
      expect(find.byKey(const Key('category-sheet')), findsNothing);
      await tester.tap(find.byKey(const Key('transaction-date')));
      await tester.pumpAndSettle();
      expect(find.byType(DatePickerDialog), findsOneWidget);
      await tester.tap(find.text('9').last);
      final pickerContext = tester.element(find.byType(DatePickerDialog));
      await tester.tap(
        find.text(MaterialLocalizations.of(pickerContext).okButtonLabel),
      );
      await tester.pumpAndSettle();
      expect(f.form.occurredAt, DateTime.utc(2026, 10, 9, 15, 45));
      await tester.tap(find.byKey(const Key('transaction-time')));
      await tester.pumpAndSettle();
      expect(find.byType(TimePickerDialog), findsOneWidget);
      final timeContext = tester.element(find.byType(TimePickerDialog));
      await tester.tap(
        find.text(MaterialLocalizations.of(timeContext).cancelButtonLabel),
      );
      await tester.pumpAndSettle();
      f.form.edit(() => f.form.amount = '15');
      expect(await f.form.save(), isTrue);
      expect(jsonDecode(f.patches.single.body), {
        'amount': '15.00',
        'occurred_at': '2026-10-09T15:45:00.000Z',
      });
    },
  );

  for (final kind in ['transfer', 'loan', 'expense']) {
    testWidgets('$kind resource opens read only without save', (tester) async {
      final f = EditFixture(
        changes: {
          'kind': kind,
          if (kind == 'expense')
            'loan_id': '00000000-0000-4000-8000-000000000040',
        },
      );
      addTearDown(f.close);
      await mountEditor(tester, f);
      expect(find.byKey(const Key('transaction-read-only')), findsOneWidget);
      expect(find.byKey(const Key('save-transaction')), findsNothing);
      final old = f.form.title;
      f.form.edit(() => f.form.title = 'No debe cambiar');
      expect(f.form.title, old);
      expect(await f.form.save(), isFalse);
      expect(f.patches, isEmpty);
    });
  }

  test(
    'feed repeats category_id on every page and preserves pagination',
    () async {
      final f = EditFixture()..paginate = true;
      addTearDown(f.close);
      final feed = TransactionFeed(
        f.api,
        categoryIds: [correctionOut, correctionIn],
      );
      await feed.load();
      await feed.loadMore();
      expect(f.feeds.length, 2);
      for (final request in f.feeds) {
        expect(request.url.queryParametersAll['category_id'], [
          correctionOut,
          correctionIn,
        ]);
      }
      expect(f.feeds.last.url.queryParameters['cursor'], 'next');
      expect(feed.transactions.length, 1);
    },
  );

  testWidgets(
    'category chips remove filters and category sheet selects a server filter',
    (tester) async {
      final f = EditFixture();
      addTearDown(f.close);
      await mountRoute(
        tester,
        f,
        TransactionsPage(
          session: f.session,
          onDemo: () {},
          categoryIds: const [correctionOut, correctionIn],
        ),
      );
      expect(find.byType(InputChip), findsNWidgets(2));
      final chip = tester.widget<InputChip>(
        find.byKey(const Key('category-filter-$correctionOut')),
      );
      chip.onDeleted!();
      await tester.pumpAndSettle();
      expect(f.feeds.last.url.queryParametersAll['category_id'], [
        correctionIn,
      ]);
      tester.widget<InputChip>(find.byType(InputChip)).onDeleted!();
      await tester.pumpAndSettle();
      expect(f.feeds.last.url.queryParametersAll['category_id'], isNull);
      await tester.tap(find.byKey(const Key('transaction-category-filter')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('form-category-$correctionOut')));
      await tester.pumpAndSettle();
      expect(f.feeds.last.url.queryParametersAll['category_id'], [
        correctionOut,
      ]);
      expect(
        find.byKey(const Key('category-filter-$correctionOut')),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'list tap loads server record, PATCH saves and refreshes the filtered list',
    (tester) async {
      final f = EditFixture();
      addTearDown(f.close);
      await mountRoute(
        tester,
        f,
        TransactionsPage(
          session: f.session,
          onDemo: () {},
          categoryIds: const [correctionOut, correctionIn],
        ),
      );
      await tester.ensureVisible(find.byType(TransactionCard));
      await tester.tap(find.byType(TransactionCard));
      await tester.pumpAndSettle();
      expect(find.byType(NewTransactionPage), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('transaction-title')));
      await tester.enterText(
        find.descendant(
          of: find.byKey(const Key('transaction-title')),
          matching: find.byType(TextField),
        ),
        'Compra editada',
      );
      await tester.tap(find.byKey(const Key('save-transaction')));
      await tester.pumpAndSettle();
      expect(jsonDecode(f.patches.single.body), {'title': 'Compra editada'});
      expect(f.session.transactionRevision, 1);
      expect(f.feeds.length, 2);
      expect(f.feeds.last.url.queryParametersAll['category_id'], [
        correctionOut,
        correctionIn,
      ]);
      expect(find.byType(NewTransactionPage), findsNothing);
      expect(find.text('Compra editada'), findsOneWidget);
    },
  );

  testWidgets('Home latest transaction tap edits and reloads Home after save', (
    tester,
  ) async {
    final f = EditFixture();
    addTearDown(f.close);
    await mountRoute(
      tester,
      f,
      HomePage(session: f.session, onViewTransactions: () {}, animate: false),
    );
    await tester.ensureVisible(find.byType(HomeTransactionRow).first);
    await tester.pumpAndSettle();
    await tester.tap(
      find.descendant(
        of: find.byType(HomeTransactionRow).first,
        matching: find.text('Compra sintética'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(NewTransactionPage), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('transaction-title')));
    await tester.enterText(
      find.descendant(
        of: find.byKey(const Key('transaction-title')),
        matching: find.byType(TextField),
      ),
      'Cambio desde Inicio',
    );
    final count = f.feeds.length;
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pumpAndSettle();
    expect(find.byType(NewTransactionPage), findsNothing);
    expect(f.feeds.length, greaterThan(count));
    expect(f.session.transactionRevision, 1);
    expect(find.text('Cambio desde Inicio'), findsOneWidget);
  });

  testWidgets('transfer dialog opens history for both system keys', (
    tester,
  ) async {
    final f = EditFixture();
    addTearDown(f.close);
    final transfer = TransferBalanceController(
      f.api,
      f.session.user!,
      accounts: f.base.accounts,
      initialAccount: f.base.accounts.first,
      occurredAt: creation.now,
      now: () => creation.now,
    );
    addTearDown(transfer.dispose);
    await mountRoute(
      tester,
      f,
      TransferBalancePage(session: f.session, controller: transfer),
    );
    await tester.tap(find.byKey(const Key('transfer-info')));
    await tester.pumpAndSettle();
    await tester.tap(find.text(fixtures.l.transferCorrectionCategory));
    await tester.pumpAndSettle();
    expect(find.byType(TransactionsPage), findsOneWidget);
    await tester.ensureVisible(find.byType(TransactionCard));
    await tester.tap(find.byType(TransactionCard));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('save-transaction')));
    await tester.pumpAndSettle();
    expect(find.byType(TransactionsPage), findsOneWidget);
    expect(f.feeds.last.url.queryParametersAll['category_id'], [
      correctionOut,
      correctionIn,
    ]);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'failed record fetch can retry without creating a new transaction',
    (tester) async {
      final f = EditFixture()..transactionStatus = 404;
      addTearDown(f.close);
      await mountEditor(tester, f);
      expect(find.byKey(const Key('transaction-form-error')), findsOneWidget);
      expect(find.byKey(const Key('title-sheet')), findsNothing);
      f.transactionStatus = null;
      await tester.tap(find.byKey(const Key('retry-transaction')));
      await tester.pumpAndSettle();
      expect(f.form.original, isNotNull);
      expect(find.byKey(const Key('transaction-form-error')), findsNothing);
      expect(f.requests.any((r) => r.method == 'POST'), isFalse);
    },
  );

  for (final brightness in Brightness.values) {
    testWidgets('golden edit saved transaction ${brightness.name}', (
      tester,
    ) async {
      final f = EditFixture(
        changes: {
          'tag_ids': [fixtures.tag.id],
        },
      );
      addTearDown(f.close);
      await mountEditor(tester, f, brightness: brightness);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/edit_transaction_${brightness.name}.png'),
      );
    });
  }
}
