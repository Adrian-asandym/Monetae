import 'dart:convert';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/report_feed.dart';
import 'package:monetae_web/api/report_query.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/data/mock_reports.dart';
import 'package:monetae_web/l10n/app_localizations_es.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/pages/login_page.dart';

import 'api_session_test.dart' as session;

import 'package:monetae_web/presentation/account_color.dart';
import 'package:monetae_web/presentation/component_models.dart';
import 'package:monetae_web/presentation/currency_format.dart';
import 'package:monetae_web/widgets/cash_flow_chart.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/widgets/income_expense_summary.dart';
import 'package:monetae_web/widgets/report_dashboard.dart';
import 'package:monetae_web/widgets/transaction_card.dart';

import 'components_test.dart' as harness;

final l = AppLocalizationsEs();
http.Response page(List<Object?> items, {String? next}) =>
    http.Response(jsonEncode({'items': items, 'next_cursor': next}), 200);

void main() {
  harness.loadGoldenFonts();
  test('report params and exact nested totals, both endpoints', () async {
    final queries = <Map<String, String>>[];
    final api = ApiClient(
      client: MockClient((request) async {
        queries.add(request.url.queryParameters);
        expect(request.method, 'GET');
        expect(request.headers['Accept'], 'application/json');
        return page(
          request.url.path.endsWith('cash-flow')
              ? [mockReports(l).summary!.toJson()]
              : [mockReports(l).rows.first.toJson()],
        );
      }),
    );
    addTearDown(api.close);
    const query = ReportQuery(
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
      reportCurrency: 'USD',
      accountId: mockAccountId,
      personId: '00000000-0000-4000-8000-000000000900',
      period: ReportPeriod.weekly,
    );
    final flow = await api.cashFlow(query: query, cursor: 'next', limit: 7);
    final categories = await api.categoryReport(
      query: query,
      cursor: 'next',
      limit: 7,
    );
    expect(queries, [
      for (var i = 0; i < 2; i++)
        {
          'date_from': '2026-10-01',
          'date_to': '2026-10-31',
          'report_currency': 'USD',
          'account_id': mockAccountId,
          'person_id': '00000000-0000-4000-8000-000000000900',
          'period': 'weekly',
          'cursor': 'next',
          'limit': '7',
        },
    ]);
    expect(flow.items.single.expense.reportAmount, '170.00');
    expect(flow.items.single.income.byCurrency.single.currency, 'PEN');
    expect(flow.items.single.net.reportAmount, '330.00');
    expect(categories.items.single.total.byCurrency.single.amount, '110.00');
    expect(categories.items.single.total.unconvertedCount, 0);
    expect(const ReportQuery().toQuery(), {'limit': '100'});
  });
  test(
    'feed uses one monthly total, daily zeros, range categories, all pages',
    () async {
      final requests = <Uri>[];
      final data = mockReports(l);
      final api = ApiClient(
        client: MockClient((request) async {
          requests.add(request.url);
          if (request.url.path.endsWith('/categories') &&
              !request.url.path.contains('/reports/')) {
            return page(
              data.categories.values.map((item) => item.toJson()).toList(),
            );
          }
          if (request.url.path.endsWith('cash-flow')) {
            if (request.url.queryParameters['period'] == 'monthly') {
              return page([data.summary!.toJson()]);
            }
            if (request.url.queryParameters['cursor'] == null) {
              return page([data.flow.first.toJson()], next: 'two');
            }
            return page(
              data.flow.skip(1).map((item) => item.toJson()).toList(),
            );
          }
          expect(request.url.queryParameters.containsKey('period'), false);
          return page(data.rows.map((item) => item.toJson()).toList());
        }),
      );
      addTearDown(api.close);
      final feed = await ReportFeed.load(
        api,
        dateFrom: '2026-10-01',
        dateTo: '2026-10-31',
      );
      expect(feed.flow.map((row) => row.income.reportAmount), [
        '250.00',
        '80.00',
        '120.00',
        '0.00',
        '50.00',
        '0.00',
        '0.00',
      ]);
      expect(feed.summary!.income.reportAmount, '500.00');
      expect(feed.rows.length, 3);
      expect(feed.categories.length, 3);
      expect(
        requests
            .where((uri) => uri.path.contains('/reports/'))
            .every(
              (uri) =>
                  uri.queryParameters['date_from'] == '2026-10-01' &&
                  uri.queryParameters['date_to'] == '2026-10-31',
            ),
        true,
      );
    },
  );
  for (final status in [404, 501]) {
    for (final unavailablePath in ['cash-flow', 'categories']) {
      testWidgets(
        'empty home for $unavailablePath $status even HTML proxy error',
        (tester) async {
          final api = ApiClient(
            client: MockClient((request) async {
              if (request.url.path.endsWith(unavailablePath)) {
                return http.Response('<html>unavailable</html>', status);
              }
              return page(
                request.url.queryParameters['period'] == 'monthly'
                    ? [mockReports(l).summary!.toJson()]
                    : mockReports(l).flow.map((row) => row.toJson()).toList(),
              );
            }),
          );
          addTearDown(api.close);
          await harness.mount(
            tester,
            Brightness.light,
            (_, _) => HomePage(api: api),
          );
          await tester.pumpAndSettle();
          expect(find.byKey(const Key('empty-reports')), findsOneWidget);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
  testWidgets(
    'missing conversion warning retains original currency and zero slices',
    (tester) async {
      final row = CategoryReportRowDto(
        categoryId: null,
        kind: CategoryReportRowKind.expense,
        startOn: '2026-10-01',
        endOn: '2026-10-31',
        total: const ReportTotalDto(
          byCurrency: [CurrencyTotalDto(currency: 'EUR', amount: '25.30')],
          reportCurrency: 'PEN',
          reportAmount: '0.00',
          unconvertedCount: 1,
        ),
      );
      final api = ApiClient(
        client: MockClient((request) async {
          if (request.url.path == '/api/v1/reports/categories') {
            return page([row.toJson()]);
          }
          if (request.url.path == '/api/v1/categories') return page([]);
          return page([
            syntheticFlow(
              '2026-10-01',
              '0.00',
              '0.00',
              '0.00',
              '0.00',
            ).toJson(),
          ]);
        }),
      );
      addTearDown(api.close);
      final feed = await ReportFeed.load(
        api,
        dateFrom: '2026-10-01',
        dateTo: '2026-10-31',
      );
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => SingleChildScrollView(
          child: ReportDashboard(feed: feed, animate: false),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('unconverted-notice')), findsOneWidget);
      expect(find.byType(PieChart), findsNothing);
      expect(find.textContaining('25.30'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  test('exact localized currency strings and qualified shared symbols', () {
    expect(
      formatCurrency('12345678901234567890.01', 'EUR', 'es'),
      '€ 12,345,678,901,234,567,890.01',
    );
    expect(formatCurrency('-1234.50', 'USD', 'en'), '-US\$1,234.50');
    for (final currency in ['PEN', 'USD', 'EUR', 'CAD', 'AUD', 'JPY', 'CNY']) {
      expect(
        formatCurrency('10.00', currency, 'es'),
        isNot(contains(currency)),
      );
    }
    expect(currencySymbol('USD', 'es'), isNot(currencySymbol('CAD', 'es')));
    expect(currencySymbol('JPY', 'es'), isNot(currencySymbol('CNY', 'es')));
  });
  test(
    'account color preserves supplied color and has stable valid fallback',
    () {
      expect(accountColor('account', '#112233'), const Color(0xFF112233));
      expect(
        accountColor(mockAccountId, null),
        accountColor(mockAccountId, 'invalid'),
      );
      expect(accountPalette, contains(accountColor(mockAccountId, null)));
      expect(
        accountColor(mockAccountId, null),
        isNot(accountColor('00000000-0000-4000-8000-000000000002', null)),
      );
    },
  );
  testWidgets(
    'authenticated start shows reports; month refresh and expiry clear private routes',
    (tester) async {
      final queries = <Map<String, String>>[];
      var expired = false;
      final data = mockReports(l);
      final api = ApiClient(
        client: MockClient((request) async {
          if (expired) return session.problem(401);
          if (request.url.path == '/api/v1/users/me') {
            return session.ok(session.profile());
          }
          if (request.url.path == '/api/v1/categories') {
            return page(data.categories.values.map((c) => c.toJson()).toList());
          }
          queries.add(request.url.queryParameters);
          if (request.url.path == '/api/v1/reports/cash-flow') {
            return page(
              request.url.queryParameters['period'] == 'monthly'
                  ? [data.summary!.toJson()]
                  : data.flow.map((row) => row.toJson()).toList(),
            );
          }
          return page(data.rows.map((row) => row.toJson()).toList());
        }),
      );
      addTearDown(api.close);
      await tester.pumpWidget(MonetaeApp(api: api));
      await tester.pumpAndSettle();
      expect(find.byType(HomePage), findsOneWidget);
      expect(find.byType(IncomeExpenseSummary), findsOneWidget);
      expect(queries.every((query) => query['report_currency'] == 'USD'), true);
      final previous = DateTime.parse(queries.first['date_from']!);
      await tester.tap(find.byTooltip(l.previousMonth));
      await tester.pumpAndSettle();
      final changed = DateTime.parse(queries.last['date_from']!);
      expect(changed, DateTime(previous.year, previous.month - 1));
      expect(queries.length, 6);
      expired = true;
      await tester.tap(find.byTooltip(l.refresh));
      await tester.pumpAndSettle();
      expect(find.byType(LoginPage), findsOneWidget);
      expect(find.byType(ReportDashboard), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'server error stays distinct from unavailable reports; retry loads data',
    (tester) async {
      var status = 500;
      final api = ApiClient(
        client: MockClient((request) async {
          if (status != 200) return http.Response('error', status);
          if (request.url.path == '/api/v1/reports/categories' ||
              request.url.path == '/api/v1/categories') {
            return page([]);
          }
          return page([
            syntheticFlow(
              '2026-10-01',
              '0.00',
              '0.00',
              '0.00',
              '0.00',
            ).toJson(),
          ]);
        }),
      );
      addTearDown(api.close);
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => HomePage(api: api),
      );
      await tester.pumpAndSettle();
      expect(find.text(l.connectionError), findsOneWidget);
      expect(find.byKey(const Key('empty-reports')), findsNothing);
      status = 200;
      await tester.tap(find.text(l.retry));
      await tester.pumpAndSettle();
      expect(find.byType(IncomeExpenseSummary), findsOneWidget);
      expect(find.text(l.connectionError), findsNothing);
    },
  );
  testWidgets(
    'failed sign out leaves authenticated home and exposes its error',
    (tester) async {
      final api = ApiClient(
        client: MockClient((request) async {
          if (request.url.path == '/api/v1/users/me') {
            return session.ok(session.profile());
          }
          if (request.url.path == '/api/v1/auth/logout') {
            return session.problem(500);
          }
          return session.problem(404);
        }),
      );
      addTearDown(api.close);
      await tester.pumpWidget(MonetaeApp(api: api));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip(l.signOut));
      await tester.pumpAndSettle();
      expect(find.byType(HomePage), findsOneWidget);
      expect(find.byKey(const Key('session-error')), findsOneWidget);
      expect(find.text(l.connectionError), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  test('repeated report cursor fails instead of looping', () async {
    final api = ApiClient(
      client: MockClient((_) async => page([], next: 'same')),
    );
    addTearDown(api.close);
    await expectLater(
      ReportFeed.load(api, dateFrom: '2026-10-01', dateTo: '2026-10-31'),
      throwsA(isA<ApiException>()),
    );
  });
  test(
    'report DTO rejects numeric money and retains all original currencies',
    () {
      final wire = syntheticTotal('10.00').toJson();
      expect(
        () => ReportTotalDto.fromJson({...wire, 'report_amount': 10.0}),
        throwsFormatException,
      );
      final dto = ReportTotalDto.fromJson({
        ...wire,
        'unconverted_count': 2,
        'by_currency': [
          {'currency': 'EUR', 'amount': '10.00'},
          {'currency': 'USD', 'amount': '20.00'},
        ],
      });
      expect(dto.unconvertedCount, 2);
      expect(dto.byCurrency.map((total) => total.amount), ['10.00', '20.00']);
    },
  );
  testWidgets('direct demo theme toggle preserves report selection', (
    tester,
  ) async {
    await tester.pumpWidget(const DemoApp(showHome: true));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('home-theme-switch')));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(HomePage))).brightness,
      Brightness.dark,
    );
    expect(find.byType(ReportDashboard), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  for (final brightness in Brightness.values) {
    final mode = brightness.name;
    testWidgets('summary $mode', (tester) async {
      await harness.mount(
        tester,
        brightness,
        (_, l) => IncomeExpenseSummary(row: mockReports(l).summary!),
        captureSize: const Size(600, 190),
      );
      expect(find.text('S/ 170.00'), findsOneWidget);
      expect(find.text('S/ 500.00'), findsOneWidget);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/summary_$mode.png'),
      );
    });
    testWidgets('summary original currencies $mode', (tester) async {
      const expense = ReportTotalDto(
        byCurrency: [
          CurrencyTotalDto(currency: 'PEN', amount: '90.00'),
          CurrencyTotalDto(currency: 'USD', amount: '100.00'),
        ],
        reportCurrency: 'PEN',
        reportAmount: '470.00',
        unconvertedCount: 0,
      );
      const income = ReportTotalDto(
        byCurrency: [CurrencyTotalDto(currency: 'USD', amount: '100.00')],
        reportCurrency: 'PEN',
        reportAmount: '380.00',
        unconvertedCount: 0,
      );
      await harness.mount(
        tester,
        brightness,
        (_, _) => const IncomeExpenseSummary(
          row: CashFlowRowDto(
            startOn: '2026-10-01',
            endOn: '2026-10-31',
            expense: expense,
            income: income,
            cumulativeNet: ReportTotalDto(
              byCurrency: [],
              reportCurrency: 'PEN',
              reportAmount: '-90.00',
              unconvertedCount: 0,
            ),
            net: ReportTotalDto(
              byCurrency: [],
              reportCurrency: 'PEN',
              reportAmount: '-90.00',
              unconvertedCount: 0,
            ),
          ),
        ),
        captureSize: const Size(600, 190),
      );
      expect(find.text('S/ 470.00'), findsOneWidget);
      expect(find.text('S/ 90.00 · US\$ 100.00'), findsOneWidget);
      expect(find.text('S/ 380.00'), findsOneWidget);
      expect(find.text('US\$ 100.00'), findsOneWidget);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/summary_breakdown_$mode.png'),
      );
    });
    for (final emptyPeriods in [true, false]) {
      testWidgets('line chart $mode empty periods $emptyPeriods', (
        tester,
      ) async {
        await harness.mount(
          tester,
          brightness,
          (_, l) => CashFlowChart(
            rows: mockReports(l, emptyPeriods: emptyPeriods).flow,
            animate: false,
          ),
          captureSize: const Size(600, 300),
        );
        final chart = tester.widget<LineChart>(find.byType(LineChart));
        expect(
          chart.data.lineBarsData.first.spots.length,
          emptyPeriods ? 7 : 5,
        );
        expect(
          chart.data.lineBarsData.last.spots[emptyPeriods ? 3 : 2].y,
          emptyPeriods ? 0 : .48,
        );
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile(
            'goldens/line_${emptyPeriods ? 'zeros' : 'filled'}_$mode.png',
          ),
        );
      });
    }
    testWidgets('selector pie and home demo $mode', (tester) async {
      await harness.mount(
        tester,
        brightness,
        (_, l) => SingleChildScrollView(
          child: ReportDashboard(feed: mockReports(l), animate: false),
        ),
        captureSize: const Size(600, 640),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byType(CategoryPieChart));
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/selector_pie_$mode.png'),
      );
      final expense = tester.widget<CategoryPieChart>(
        find.byType(CategoryPieChart),
      );
      expect(expense.slices.length, 2);
      await tester.ensureVisible(find.byKey(const Key('select-income')));
      await tester.tap(find.byKey(const Key('select-income')));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<CategoryPieChart>(find.byType(CategoryPieChart))
            .slices
            .single
            .label,
        l.workCategory,
      );
      await tester.ensureVisible(find.byType(CategoryPieChart));
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/selector_income_$mode.png'),
      );
      await harness.mount(
        tester,
        brightness,
        (_, _) => const HomePage(),
        captureSize: const Size(760, 1150),
        viewSize: const Size(900, 1250),
      );
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/home_demo_$mode.png'),
      );
      tester.view.physicalSize = const Size(390, 900);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
    testWidgets('account colors and PEN USD EUR cards $mode', (tester) async {
      await harness.mount(
        tester,
        brightness,
        (_, l) => Column(
          children: [
            for (final currency in ['PEN', 'USD', 'EUR'])
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: TransactionCard(
                  preferences: const TransactionCardPreferencesDto(
                    showAccount: true,
                  ),
                  model: currencyCard(l, currency),
                ),
              ),
          ],
        ),
        captureSize: const Size(600, 480),
      );
      final tags = tester.widgetList<Container>(
        find.byKey(const Key('transaction-account-tag')),
      );
      expect(
        tags
            .map((tag) => (tag.decoration! as BoxDecoration).color)
            .toSet()
            .length,
        3,
      );
      final labels = tester
          .widgetList<Text>(find.byType(Text))
          .map((text) => text.data ?? '')
          .join(' ');
      for (final code in ['PEN', 'USD', 'EUR']) {
        expect(labels, isNot(contains(code)));
      }
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/account_currencies_$mode.png'),
      );
    });
  }
}

TransactionCardModel currencyCard(AppLocalizations l, String currency) {
  final source = mockCards(l).first;
  final index = ['PEN', 'USD', 'EUR'].indexOf(currency);
  final account = AccountDto.fromJson({
    ...mockAccount(l).toJson(),
    'id': '00000000-0000-4000-8000-00000000000${index + 1}',
    'name': l.sampleAccount,
    'currency': currency,
    'color': ['#5F85C2', '#BA7DBD', '#CA995A'][index],
  });
  return TransactionCardModel(
    transaction: TransactionDto.fromJson(
      mockTransactionJson(currency: currency, accountId: account.id),
    ),
    category: source.category,
    account: account,
    amountLabel: formatCurrency('48.50', currency, l.localeName),
    subtitle: source.subtitle,
    dateKey: source.dateKey,
    dateLabel: source.dateLabel,
    timeLabel: source.timeLabel,
    icon: source.icon,
    categoryColor: source.categoryColor,
    tone: source.tone,
    typeLabel: source.typeLabel,
  );
}
