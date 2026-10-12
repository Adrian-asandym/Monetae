import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/widgets/transaction_form/exchange_rate_sheet.dart';
import 'package:monetae_web/widgets/transaction_form/form_sheet.dart';

import 'api_session_test.dart' as fixtures;
import 'components_test.dart' as harness;
import 'transfer_balance_test.dart' as transfer;

Map<String, Object?> correction(
  String rate, {
  String? fromId,
  String? toId,
  String fromCurrency = 'PEN',
  String toCurrency = 'USD',
  DateTime? date,
}) => {
  'group_id': '00000000-0000-4000-8000-000000000099',
  'implicit_rate': rate,
  'outgoing': {
    'id': '00000000-0000-4000-8000-000000000091',
    'account_id': fromId ?? '00000000-0000-4000-8000-000000000001',
    'currency': fromCurrency,
    'amount': rate == '0.000000' ? '-9999999999999999.99' : '-30.00',
    'occurred_at': (date ?? transfer.clock).toIso8601String(),
  },
  'incoming': {
    'id': '00000000-0000-4000-8000-000000000092',
    'account_id': toId ?? '00000000-0000-4000-8000-000000000002',
    'currency': toCurrency,
    'amount': {
      '0.000000': '0.01',
      '0.200000': '6.00',
      '0.250000': '7.50',
      '0.300000': '9.00',
      '0.400000': '12.00',
      '3.750000': '112.50',
    }[rate]!,
    'occurred_at': (date ?? transfer.clock).toIso8601String(),
  },
};
http.Response page(List<Map<String, Object?>> items, {String? cursor}) =>
    fixtures.ok({'items': items, 'next_cursor': cursor});

void main() {
  harness.loadGoldenFonts();

  test('Peru convention in either direction preserves exact reciprocal', () {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    f.form.setFromAmount('30');
    f.form.setDisplayedRate('3,75');
    expect(f.form.rate, '0.266667');
    expect(f.form.toAmount, '8.00');
    expect(f.form.displayFromCurrency, 'USD');
    expect(f.form.displayToCurrency, 'PEN');
    expect(f.form.displayedRate, '3.75');
    f.form.setFromAmount('90000');
    expect(
      f.form.toAmount,
      '24000.00',
    ); // unrounded inverse, not 0.266667 * 90000 = 24000.03
    f.form.swapAccounts();
    expect(f.form.displayedRate, '3.75');
    expect(f.form.rate, '3.750000');
    f.form.setDisplayedRate('4.5');
    expect(f.form.toAmount, '108000.00');
    expect(f.form.isManualRate, isTrue);
  });

  test('non-PEN equation uses source to destination, zero/empty invalid', () {
    final f = transfer.TransferFixture(base: 'EUR', fromCurrency: 'EUR');
    addTearDown(f.close);
    f.form.setFromAmount('12');
    f.form.setDisplayedRate('1,25');
    expect(f.form.displayFromCurrency, 'EUR');
    expect(f.form.displayToCurrency, 'USD');
    expect(f.form.toAmount, '15.00');
    expect(f.form.rate, '1.250000');
    f.form.setDisplayedRate('0');
    expect(f.form.hasRate, isFalse);
    expect(f.form.toAmount, '');
    f.form.setDisplayedRate('');
    expect(f.form.displayedRate, '');
  });

  test('priority 1: same accounts, currencies and latest API row; no broader query', () async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    f.form.setFromAmount('30');
    f.historyHandler = (_) async => page([
      correction('0.250000', date: transfer.clock),
      correction(
        '0.200000',
        date: transfer.clock.subtract(const Duration(days: 1)),
      ),
    ]);
    await f.form.loadSuggestion();
    expect(f.form.rate, '0.250000');
    expect(f.form.toAmount, '7.50');
    expect(f.form.suggestionActive, isTrue);
    expect(f.form.suggestion!.occurredAt, transfer.clock);
    expect(f.historyRequests.single.url.queryParameters, {
      'limit': '1',
      'from_account_id': f.accounts.first.id,
      'to_account_id': f.accounts.last.id,
      'from_currency': 'PEN',
      'to_currency': 'USD',
    });
  });

  test('priority 2: currency pair even when accounts differ', () async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    f.form.setFromAmount('30');
    f.historyHandler = (r) async => page(
      r.url.queryParameters.containsKey('from_account_id')
          ? []
          : [
              correction(
                '0.300000',
                fromId: '00000000-0000-4000-8000-000000000007',
                toId: '00000000-0000-4000-8000-000000000008',
              ),
            ],
    );
    await f.form.loadSuggestion();
    expect(f.historyRequests, hasLength(2));
    expect(f.historyRequests.last.url.queryParameters, {
      'limit': '1',
      'from_currency': 'PEN',
      'to_currency': 'USD',
    });
    expect(f.form.toAmount, '9.00');
    expect(f.form.suggestion!.inverted, isFalse);
  });

  test(
    'priority 3: opposite currency direction is inverted exactly and marked',
    () async {
      final f = transfer.TransferFixture();
      addTearDown(f.close);
      f.form.setFromAmount('30');
      f.historyHandler = (r) async => page(
        r.url.queryParameters['from_currency'] == 'USD'
            ? [correction('3.750000', fromCurrency: 'USD', toCurrency: 'PEN')]
            : [],
      );
      await f.form.loadSuggestion();
      expect(f.historyRequests, hasLength(3));
      expect(f.historyRequests.last.url.queryParameters, {
        'limit': '1',
        'from_currency': 'USD',
        'to_currency': 'PEN',
      });
      expect(f.form.rate, '0.266667');
      expect(f.form.displayedRate, '3.75');
      expect(f.form.toAmount, '8.00');
      expect(f.form.suggestion!.inverted, isTrue);
      f.form.setFromAmount('90000');
      expect(f.form.toAmount, '24000.00');
      expect(f.form.suggestionActive, isTrue);
    },
  );

  test(
    'priorities 4–5: no market call, no history leaves required field empty',
    () async {
      final f = transfer.TransferFixture();
      addTearDown(f.close);
      f.form.setFromAmount('30');
      await f.form.loadSuggestion();
      expect(f.historyRequests, hasLength(3));
      expect(
        f.historyRequests.every(
          (r) => r.url.path == '/api/v1/balance-corrections',
        ),
        isTrue,
      );
      expect(f.form.suggestion, isNull);
      expect(f.form.rate, '');
      expect(f.form.toAmount, '');
      expect(
        await f.form.save(defaultTitle: transfer.l.transferBalanceTitle),
        isFalse,
      );
      expect(f.form.invalidFields, contains('rate'));
      expect(f.requests, isEmpty);
    },
  );

  test(
    'zero rounded history skipped with cursor, linked pair date used',
    () async {
      final f = transfer.TransferFixture();
      addTearDown(f.close);
      f.historyHandler = (r) async => r.url.queryParameters['cursor'] == null
          ? page([correction('0.000000')], cursor: 'synthetic-next')
          : page([correction('0.250000')]);
      await f.form.loadSuggestion();
      expect(f.historyRequests, hasLength(2));
      expect(
        f.historyRequests.last.url.queryParameters['cursor'],
        'synthetic-next',
      );
      expect(f.form.rate, '0.250000');
    },
  );

  test('destination edit switches to Manual, source edit keeps exact rate, restore suggestion', () async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    f.historyHandler = (_) async => page([correction('0.250000')]);
    f.form.setFromAmount('30');
    await f.form.loadSuggestion();
    f.form.setToAmount('10');
    expect(f.form.isManualRate, isTrue);
    expect(f.form.rate, '0.333333');
    expect(f.form.displayedRate, '3');
    f.form.setFromAmount('90000');
    expect(f.form.toAmount, '30000.00');
    f.form.useSuggestedRate();
    expect(f.form.rate, '0.250000');
    expect(f.form.toAmount, '22500.00');
    expect(f.form.suggestionActive, isTrue);
    expect(f.form.displayedRate, '4');
  });

  test(
    'late history never replaces manual input but remains explicitly reusable',
    () async {
      final f = transfer.TransferFixture();
      addTearDown(f.close);
      final pending = Completer<http.Response>();
      f.historyHandler = (_) => pending.future;
      final loading = f.form.loadSuggestion();
      f.form.setFromAmount('30');
      f.form.setDisplayedRate('5');
      pending.complete(page([correction('0.250000')]));
      await loading;
      expect(f.form.rate, '0.200000');
      expect(f.form.toAmount, '6.00');
      expect(f.form.isManualRate, isTrue);
      expect(f.form.suggestion, isNotNull);
      f.form.useSuggestedRate();
      expect(f.form.toAmount, '7.50');
    },
  );

  test('old pair response and disposal do not update current state', () async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    final pending = Completer<http.Response>();
    f.accounts.add(
      AccountDto.fromJson({
        ...f.accounts.last.toJson(),
        'id': '00000000-0000-4000-8000-000000000003',
        'name': 'Otra cuenta sintética',
      }),
    );
    f.historyHandler = (r) =>
        r.url.queryParameters['to_account_id'] == f.accounts[1].id
        ? pending.future
        : Future.value(page([correction('0.400000')]));
    final original = f.form.loadSuggestion();
    f.form.selectAccount(f.accounts[2], outgoing: false);
    await Future<void>.delayed(Duration.zero);
    pending.complete(page([correction('0.250000')]));
    await original;
    expect(f.form.to!.id, f.accounts[2].id);
    expect(f.form.rate, '0.400000');
    expect(f.form.loadingSuggestion, isFalse);

    final disposed = transfer.TransferFixture();
    final delayed = Completer<http.Response>();
    disposed.historyHandler = (_) => delayed.future;
    final lookup = disposed.form.loadSuggestion();
    disposed.close();
    delayed.complete(page([correction('0.250000')]));
    await lookup;
    expect(disposed.form.suggestion, isNull);
  });

  test('history failure is retryable, manual rate remains usable and 401 expires session', () async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    f.historyHandler = (_) async => fixtures.problem(503);
    await f.form.loadSuggestion();
    expect(f.form.suggestionError!.kind, ApiErrorKind.unavailable);
    f.form.setFromAmount('30');
    f.form.setDisplayedRate('4');
    expect(
      await f.form.save(defaultTitle: transfer.l.transferBalanceTitle),
      isTrue,
    );
    f.historyHandler = (_) async => page([correction('0.250000')]);
    await f.form.loadSuggestion();
    expect(f.form.suggestionError, isNull);
    expect(f.form.isManualRate, isTrue);
    f.historyHandler = (_) async => fixtures.problem(401);
    await f.form.loadSuggestion();
    expect(f.session.user, isNull);
    expect(f.form.suggestionError!.kind, ApiErrorKind.unauthorized);
  });

  test('same currency never requests history', () async {
    final f = transfer.TransferFixture(same: true);
    addTearDown(f.close);
    await f.form.loadSuggestion();
    expect(f.historyRequests, isEmpty);
    expect(f.form.rate, '1');
  });

  testWidgets(
    'both entry points open same sheet, comma/dot work, no edit on reopening',
    (tester) async {
      final f = transfer.TransferFixture();
      addTearDown(f.close);
      f.fill();
      await transfer.mount(tester, f);
      await tester.tap(find.byKey(const Key('transfer-rate')));
      await tester.pumpAndSettle();
      expect(find.byType(ExchangeRateSheet), findsOneWidget);
      expect(find.text('1 USD ='), findsOneWidget);
      expect(find.text('PEN'), findsOneWidget);
      await tester.enterText(
        find.byKey(const Key('exchange-rate-input')),
        '3.75',
      );
      await tester.pump();
      final input = tester.widget<TextField>(
        find.descendant(
          of: find.byKey(const Key('exchange-rate-input')),
          matching: find.byType(TextField),
        ),
      );
      expect(input.controller!.text, '3,75');
      expect(f.form.toAmount, '8.00');
      expect(
        tester
            .widget<Text>(find.byKey(const Key('exchange-rate-equivalent')))
            .data,
        '× 0.266667',
      );
      await tester.tap(find.byKey(const Key('exchange-rate-apply')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('transfer-rates')));
      await tester.pumpAndSettle();
      expect(find.byType(ExchangeRateSheet), findsOneWidget);
      await tester.tap(find.byKey(const Key('exchange-rate-apply')));
      await tester.pumpAndSettle();
      f.form.setFromAmount('90000');
      expect(f.form.toAmount, '24000.00');
    },
  );

  testWidgets('required positive rate, Apply does not close invalid input', (
    tester,
  ) async {
    final f = transfer.TransferFixture();
    addTearDown(f.close);
    await transfer.mount(tester, f);
    await tester.tap(find.byKey(const Key('transfer-rate')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('exchange-rate-input')), '0');
    await tester.tap(find.byKey(const Key('exchange-rate-apply')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('exchange-rate-sheet')), findsOneWidget);
    expect(find.text(transfer.l.requestInvalid), findsOneWidget);
    expect(
      tester
          .widget<FormSheetButton>(
            find.byKey(const Key('exchange-rate-suggested')),
          )
          .onPressed,
      isNull,
    );
  });

  for (final brightness in [Brightness.dark, Brightness.light]) {
    for (final variant in ['manual', 'suggested', 'inverted', 'empty']) {
      testWidgets('golden rate sheet $variant ${brightness.name} at 400x642', (
        tester,
      ) async {
        final f = transfer.TransferFixture();
        addTearDown(f.close);
        f.form.setFromAmount('30');
        if (variant != 'empty') {
          f.historyHandler = (r) async => page(
            variant != 'inverted' ||
                    r.url.queryParameters['from_currency'] == 'USD'
                ? [correction(variant == 'inverted' ? '3.750000' : '0.250000')]
                : [],
          );
          await f.form.loadSuggestion();
          if (variant == 'manual') f.form.setDisplayedRate('3,75');
        }
        await transfer.mount(tester, f, brightness: brightness);
        await tester.tap(find.byKey(const Key('transfer-rate')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await expectLater(
          find.byKey(transfer.capture),
          matchesGoldenFile(
            'goldens/exchange_rate_${variant}_${brightness.name}.png',
          ),
        );
        if (variant == 'manual') {
          await tester.tap(find.byKey(const Key('exchange-rate-suggested')));
          await tester.pumpAndSettle();
          expect(f.form.suggestionActive, isTrue);
          expect(f.form.toAmount, '7.50');
          expect(
            find.byKey(const Key('exchange-rate-suggested')),
            findsNothing,
          );
        }
      });
    }
  }
}
