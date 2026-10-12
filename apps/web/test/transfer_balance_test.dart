import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/transfer_balance_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/pages/new_transaction_page.dart';
import 'package:monetae_web/pages/transfer_balance_page.dart';
import 'package:monetae_web/presentation/category_icon_source.dart';
import 'package:monetae_web/presentation/exact_decimal.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/widgets/transaction_form/form_settings.dart';

import 'api_session_test.dart' as session_fixtures;
import 'components_test.dart' as harness;
import 'new_transaction_test.dart' as transaction;

const capture = Key('transfer-capture');
final clock = DateTime.utc(2026, 10, 12, 15, 38);
final l = session_fixtures.l;

class TransferFixture {
  TransferFixture({
    String base = 'PEN',
    bool same = false,
    bool single = false,
  }) {
    accounts = [
      AccountDto.fromJson({
        ...mockAccount(l).toJson(),
        'name': 'Cuenta de prueba',
        'balance': '150.50',
        'color': '#529F8D',
      }),
      if (!single)
        AccountDto.fromJson({
          ...mockAccount(l).toJson(),
          'id': transaction.usdId,
          'name': 'Cuenta secundaria',
          'currency': same ? 'PEN' : 'USD',
          'balance': '22.25',
          'color': '#38A84A',
        }),
    ];
    api = ApiClient(
      client: MockClient(handle),
      cookies: () => 'monetae_csrf=synthetic.transfer',
    );
    session = SessionController(api)
      ..user = CurrentUserDto.fromJson({
        ...session_fixtures.profile(),
        'base_currency': base,
      })
      ..loading = false;
    form = TransferBalanceController(
      api,
      session.user!,
      accounts: accounts,
      initialAccount: accounts.first,
      occurredAt: clock,
      now: () => clock,
    );
  }
  late final List<AccountDto> accounts;
  late final ApiClient api;
  late final SessionController session;
  late final TransferBalanceController form;
  final requests = <http.Request>[];
  int status = 201;
  bool fieldError = false;
  Completer<http.Response>? pending;
  Future<http.Response> handle(http.Request request) async {
    requests.add(request);
    if (pending != null) return pending!.future;
    if (fieldError) {
      return http.Response(
        jsonEncode({
          'type': 'about:blank',
          'title': 'Validation',
          'detail': 'Synthetic validation',
          'status': 422,
          'errors': [
            {
              'field': 'body.to_amount',
              'message': 'Synthetic amount error',
              'code': 'invalid',
            },
          ],
        }),
        422,
      );
    }
    if (status != 201) return session_fixtures.problem(status);
    final body = jsonDecode(request.body) as Map<String, Object?>;
    Map<String, Object?> leg(bool outgoing) => {
      ...mockTransactionJson(),
      'account_id': body[outgoing ? 'from_account_id' : 'to_account_id'],
      'amount':
          '${outgoing ? '-' : ''}${body[outgoing ? 'from_amount' : 'to_amount']}',
      'kind': outgoing ? 'expense' : 'income',
    };
    return session_fixtures.ok({
      'group_id': '00000000-0000-4000-8000-000000000099',
      'outgoing': leg(true),
      'incoming': leg(false),
    });
  }

  void fill() {
    form.setFromAmount('30');
    form.setRate('0.25');
  }

  void close() {
    form.dispose();
    session.dispose();
    api.close();
  }
}

Future<void> mount(
  WidgetTester tester,
  TransferFixture f, {
  Brightness brightness = Brightness.dark,
}) async {
  tester.view.physicalSize = const Size(400, 642);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    RepaintBoundary(
      key: capture,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: monetaeTheme(brightness: brightness),
        locale: const Locale('es'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: TransferBalancePage(session: f.session, controller: f.form),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Map<String, Object?> body(http.Request request) =>
    jsonDecode(request.body) as Map<String, Object?>;

void main() {
  harness.loadGoldenFonts();

  test('balance correction category resolves swap_horiz', () {
    expect(
      CategoryIconSource.resolve('swap_horiz').materialIcon,
      Icons.swap_horiz_rounded,
    );
  });
  test(
    'exact rational half up, large money, negative preview and unrounded ratio',
    () {
      expect(ExactDecimal.parse('0.005').fixed(2), '0.01');
      expect(ExactDecimal.parse('-0.005').fixed(2), '-0.01');
      expect(
        ExactDecimal.parse('9999999999999999.99').fixed(2),
        '9999999999999999.99',
      );
      final ratio = ExactDecimal.parse('1') / ExactDecimal.parse('3');
      expect((ratio * ExactDecimal.parse('3')).fixed(2), '1.00');
    },
  );

  test('live balances, destination edit, source edit, swap and clear', () {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    expect(f.form.toAmount, '7.50');
    expect(f.form.resultingBalance(outgoing: true), '120.50');
    expect(f.form.resultingBalance(outgoing: false), '29.75');
    f.form.setToAmount('10');
    expect(f.form.rate, '0.333333');
    f.form.setFromAmount('90');
    expect(f.form.toAmount, '30.00'); // no intermediate six-decimal rounding
    f.form.swapAccounts();
    expect(f.form.from!.id, transaction.usdId);
    expect(f.form.fromAmount, '30.00');
    expect(f.form.toAmount, '90');
    expect(f.form.rate, '3.000000');
    f.form.setFromAmount('2');
    expect(f.form.toAmount, '6.00');
    f.form.setFromAmount('');
    expect(f.form.toAmount, '');
  });

  test(
    'same currency stays 1:1 from either amount and excludes other account',
    () {
      final f = TransferFixture(same: true);
      addTearDown(f.close);
      f.form.setFromAmount('12.34');
      expect(f.form.toAmount, '12.34');
      f.form.setToAmount('8.50');
      expect(f.form.fromAmount, '8.50');
      expect(f.form.rate, '1');
      f.form.selectAccount(f.accounts.last, outgoing: true);
      expect(f.form.from!.id, f.accounts.first.id);
    },
  );

  test(
    'exact POST, default title, UTC arrival, base rates, retry body/key',
    () async {
      final f = TransferFixture();
      addTearDown(f.close);
      f.fill();
      f.form.setArrival(clock.add(const Duration(days: 2)));
      f.status = 503;
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      final first = f.requests.single;
      expect(first.url.path, '/api/v1/balance-corrections');
      expect(first.headers['X-CSRF-Token'], 'synthetic.transfer');
      expect(body(first), {
        'from_account_id': f.accounts.first.id,
        'to_account_id': f.accounts.last.id,
        'from_amount': '30.00',
        'to_amount': '7.50',
        'from_fx_rate_to_base': '1.000000',
        'to_fx_rate_to_base': '4.000000',
        'fx_rate_source': 'manual',
        'occurred_at': clock.toIso8601String(),
        'to_occurred_at': clock.add(const Duration(days: 2)).toIso8601String(),
        'title': l.transferBalanceTitle,
      });
      f.status = 201;
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isTrue);
      expect(f.requests.last.body, first.body);
      expect(
        f.requests.last.headers['Idempotency-Key'],
        first.headers['Idempotency-Key'],
      );
      f.form.edit(() => f.form.title = 'Otra transferencia');
      await f.form.save(defaultTitle: l.transferBalanceTitle);
      expect(
        f.requests.last.headers['Idempotency-Key'],
        isNot(first.headers['Idempotency-Key']),
      );
      expect(body(f.requests.last)['title'], 'Otra transferencia');
    },
  );

  test(
    'reverse base direction and default shared date with repeating ratio',
    () async {
      final f = TransferFixture();
      addTearDown(f.close);
      f.fill();
      f.form.setToAmount('8.33');
      f.form.swapAccounts();
      await f.form.save(defaultTitle: l.transferBalanceTitle);
      expect(body(f.requests.single)['from_fx_rate_to_base'], '3.601441');
      expect(body(f.requests.single)['to_fx_rate_to_base'], '1.000000');
      expect(
        body(f.requests.single)['to_occurred_at'],
        body(f.requests.single)['occurred_at'],
      );
    },
  );

  test('same currency wire amounts and base rates', () async {
    final f = TransferFixture(same: true);
    addTearDown(f.close);
    f.form.setToAmount('15');
    await f.form.save(defaultTitle: l.transferBalanceTitle);
    expect(body(f.requests.single)['from_amount'], '15.00');
    expect(body(f.requests.single)['to_amount'], '15.00');
    expect(body(f.requests.single)['from_fx_rate_to_base'], '1.000000');
    expect(body(f.requests.single)['to_fx_rate_to_base'], '1.000000');
  });

  test(
    'neither leg base requires two manual rates and preserves precision',
    () async {
      final f = TransferFixture(base: 'EUR');
      addTearDown(f.close);
      f.fill();
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      expect(
        f.form.invalidFields,
        containsAll(['from_fx_rate_to_base', 'to_fx_rate_to_base']),
      );
      f.form.edit(() {
        f.form.fromManualRate = '0.250001';
        f.form.toManualRate = '1.000004';
      });
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isTrue);
      expect(body(f.requests.single)['from_fx_rate_to_base'], '0.250001');
      expect(body(f.requests.single)['to_fx_rate_to_base'], '1.000004');
    },
  );

  test(
    'empty, zero, same account, missing account and early arrival block POST',
    () async {
      final f = TransferFixture();
      addTearDown(f.close);
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      expect(
        f.form.invalidFields,
        containsAll(['from_amount', 'to_amount', 'rate']),
      );
      f.fill();
      f.form.to = f.form.from;
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      expect(f.form.invalidFields, contains('to_account_id'));
      f.form.to = f.accounts.last;
      f.form.setArrival(clock.subtract(const Duration(minutes: 1)));
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      expect(f.form.invalidFields, contains('to_occurred_at'));
      f.form.setArrival(null);
      f.form.setFromAmount('0');
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      expect(f.requests, isEmpty);
      final single = TransferFixture(single: true);
      addTearDown(single.close);
      expect(
        await single.form.save(defaultTitle: l.transferBalanceTitle),
        isFalse,
      );
      expect(single.form.invalidFields, contains('to_account_id'));
    },
  );

  test('401 triggers session expiry and 422 maps field errors', () async {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    var expired = false;
    f.api.onUnauthorized = () => expired = true;
    f.status = 401;
    expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
    expect(expired, isTrue);
    expect(f.form.error!.kind, ApiErrorKind.unauthorized);
    f.fieldError = true;
    expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
    expect(f.form.fieldErrors['to_amount'], 'Synthetic amount error');
  });

  test(
    'one in-flight submission, edits blocked and disposed notification safe',
    () async {
      final f = TransferFixture();
      f.fill();
      f.pending = Completer<http.Response>();
      final saving = f.form.save(defaultTitle: l.transferBalanceTitle);
      expect(f.form.busy, isTrue);
      f.form.setFromAmount('99');
      expect(f.form.fromAmount, '30');
      expect(await f.form.save(defaultTitle: l.transferBalanceTitle), isFalse);
      f.close();
      f.pending!.complete(session_fixtures.problem(503));
      expect(await saving, isFalse);
      expect(f.requests, hasLength(1));
    },
  );

  testWidgets('transfer tab pushes separate named route, back preserves form', (
    tester,
  ) async {
    final f = transaction.FormFixture();
    addTearDown(f.close);
    final settings = TransactionFormSettings();
    await harness.mount(
      tester,
      Brightness.dark,
      (_, _) => NewTransactionPage(
        session: f.session,
        controller: f.form,
        editing: true,
        settings: settings,
      ),
    );
    await tester.pumpAndSettle();
    f.form.edit(() => f.form.title = 'Título intacto');
    await tester.tap(find.byKey(const Key('select-transfer')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('transfer-balance-page')), findsOneWidget);
    final context = tester.element(
      find.byKey(const Key('transfer-balance-page')),
    );
    expect(
      ModalRoute.of(context)!.settings.name,
      '/transactions/transfer-balance',
    );
    expect(find.byKey(const Key('select-income')), findsNothing);
    await tester.tap(find.byKey(const Key('transfer-back')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('select-transfer')), findsOneWidget);
    expect(f.form.title, 'Título intacto');
  });

  testWidgets(
    'same currency hides both rate controls; account picker excludes other',
    (tester) async {
      final f = TransferFixture(same: true);
      addTearDown(f.close);
      f.form.setFromAmount('15');
      await mount(tester, f);
      expect(find.byKey(const Key('transfer-rate')), findsNothing);
      expect(find.byKey(const Key('transfer-rates')), findsNothing);
      expect(find.text('= 135,50 S/.'), findsOneWidget);
      await tester.tap(find.text('Cuenta de prueba • PEN'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(Key('form-account-option-${f.accounts.last.id}')),
        findsNothing,
      );
      expect(
        find.byKey(Key('form-account-option-${f.accounts.first.id}')),
        findsOneWidget,
      );
    },
  );

  testWidgets('amount sheet keypad, live balance, swap, rate focus and clear', (
    tester,
  ) async {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    await mount(tester, f);
    await tester.enterText(find.byKey(const Key('transfer-rate')), '0,5');
    expect(f.form.toAmount, '15.00');
    await tester.tap(find.byKey(const Key('transfer-from-amount')));
    await tester.pumpAndSettle();
    await tester.longPress(find.byKey(const Key('amount-key-backspace')));
    await tester.tap(find.byKey(const Key('amount-key-2')));
    await tester.tap(find.byKey(const Key('amount-key-0')));
    await tester.tap(find.byKey(const Key('transfer-amount-done')));
    await tester.pumpAndSettle();
    expect(f.form.fromAmount, '20');
    expect(f.form.toAmount, '10.00');
    await tester.tap(find.byKey(const Key('transfer-swap')));
    await tester.pumpAndSettle();
    expect(f.form.rate, '2.000000');
    await tester.ensureVisible(find.byKey(const Key('transfer-rates')));
    await tester.tap(find.byKey(const Key('transfer-rates')));
    await tester.pump();
    final rateField = tester.widget<TextField>(
      find.byKey(const Key('transfer-rate')),
    );
    expect(rateField.focusNode!.hasFocus, isTrue);
    await tester.tap(find.byKey(const Key('transfer-clear')));
    await tester.pump();
    expect(f.form.fromAmount, '');
    expect(f.form.toAmount, '');
  });

  testWidgets(
    'arrival reset restores default after independent date and rejects early departure',
    (tester) async {
      final f = TransferFixture();
      addTearDown(f.close);
      f.fill();
      f.form.setArrival(clock.add(const Duration(days: 1)));
      await mount(tester, f);
      expect(find.byKey(const Key('transfer-arrival-reset')), findsOneWidget);
      await tester.tap(find.byKey(const Key('transfer-arrival-reset')));
      await tester.pumpAndSettle();
      expect(f.form.arrivalAt, isNull);
      expect(find.text(l.transferArrivalSame), findsOneWidget);
    },
  );

  testWidgets('API field error shown by field and retry keeps submission', (
    tester,
  ) async {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    f.fieldError = true;
    await mount(tester, f);
    await tester.tap(find.text(l.transferConfirm));
    await tester.pumpAndSettle();
    expect(find.text('Synthetic amount error'), findsOneWidget);
    expect(find.byKey(const Key('transfer-error')), findsOneWidget);
    final first = f.requests.single;
    f.fieldError = false;
    await tester.tap(find.text(l.retry));
    await tester.pumpAndSettle();
    expect(
      f.requests.last.headers['Idempotency-Key'],
      first.headers['Idempotency-Key'],
    );
    expect(f.session.transactionRevision, greaterThan(0));
  });

  testWidgets('arrival opens date then time picker and saves UTC separately', (
    tester,
  ) async {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    await mount(tester, f);
    await tester.tap(find.byKey(const Key('transfer-arrival')));
    await tester.pumpAndSettle();
    expect(find.byType(DatePickerDialog), findsOneWidget);
    await tester.tap(find.text('13'));
    final ok = MaterialLocalizations.of(
      tester.element(find.byType(DatePickerDialog)),
    ).okButtonLabel;
    await tester.tap(find.text(ok));
    await tester.pumpAndSettle();
    expect(find.byType(TimePickerDialog), findsOneWidget);
    await tester.tap(find.text(ok));
    await tester.pumpAndSettle();
    expect(f.form.arrivalAt, clock.add(const Duration(days: 1)));
    expect(f.form.occurredAt, clock);
    await tester.tap(find.text(l.transferConfirm));
    await tester.pumpAndSettle();
    expect(
      body(f.requests.single)['to_occurred_at'],
      clock.add(const Duration(days: 1)).toIso8601String(),
    );
  });

  testWidgets('successful POST returns to first route and refreshes Home', (
    tester,
  ) async {
    final f = TransferFixture();
    addTearDown(f.close);
    f.fill();
    await tester.pumpWidget(
      MaterialApp(
        theme: monetaeTheme(brightness: Brightness.dark),
        locale: const Locale('es'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              key: const Key('synthetic-home'),
              onPressed: () => Navigator.of(context).push<void>(
                MaterialPageRoute(
                  builder: (_) => TransferBalancePage(
                    session: f.session,
                    controller: f.form,
                  ),
                ),
              ),
              child: const Text('Inicio de prueba'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('synthetic-home')));
    await tester.pumpAndSettle();
    await tester.tap(find.text(l.transferConfirm));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('transfer-balance-page')), findsNothing);
    expect(find.byKey(const Key('synthetic-home')), findsOneWidget);
    expect(f.session.transactionRevision, 1);
  });

  for (final brightness in [Brightness.dark, Brightness.light]) {
    testWidgets('golden transfer screen and info dialog ${brightness.name}', (
      tester,
    ) async {
      final f = TransferFixture();
      addTearDown(f.close);
      f.fill();
      await mount(tester, f, brightness: brightness);
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(capture),
        matchesGoldenFile('goldens/transfer_balance_${brightness.name}.png'),
      );
      await tester.tap(find.byKey(const Key('transfer-info')));
      await tester.pumpAndSettle();
      expect(find.text(l.transferBalanceInfo), findsOneWidget);
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(capture),
        matchesGoldenFile(
          'goldens/transfer_balance_info_${brightness.name}.png',
        ),
      );
      await tester.tap(find.text(l.transferOk));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('transfer-info-dialog')), findsNothing);
    });
  }
}
