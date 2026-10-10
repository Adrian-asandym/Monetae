import 'dart:async';
import 'dart:convert';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/home_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/data/mock_budgets_goals.dart';
import 'package:monetae_web/data/mock_reports.dart';
import 'package:monetae_web/l10n/app_localizations_es.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/pages/app_shell.dart';
import 'package:monetae_web/pages/budgets_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/pages/login_page.dart';
import 'package:monetae_web/pages/new_transaction_page.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/widgets/app_navigation.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/widgets/cumulative_cash_flow_chart.dart';
import 'package:monetae_web/widgets/home_accounts.dart';
import 'package:monetae_web/widgets/home_category_carousel.dart';
import 'package:monetae_web/widgets/home_transaction_row.dart';

import 'api_session_test.dart' as fixtures;
import 'components_test.dart' as harness;

final l = AppLocalizationsEs();
final today = DateTime.utc(2026, 10, 9);

class HomeFixture {
  HomeFixture({this.empty = false, List<String>? widgets}) {
    profile = {
      ...fixtures.profile(),
      'report_currency': 'PEN',
      'preferences': {
        'theme': 'dark',
        'accent_color': '#BA7DBD',
        'home_widgets': widgets ?? [],
        'transaction_card': fixtures.all.toJson(),
        'default_account_id': mockAccountId,
      },
    };
    api = ApiClient(
      cookies: () => 'monetae_csrf=synthetic.token',
      client: MockClient(handle),
    );
    session = SessionController(api)
      ..user = CurrentUserDto.fromJson(profile)
      ..loading = false;
  }
  final bool empty;
  late Map<String, Object?> profile;
  late final ApiClient api;
  late final SessionController session;
  final requests = <http.Request>[];
  final statuses = <String, int>{};
  Completer<http.Response>? patch;
  final delayed = <String, Completer<http.Response>>{};
  List<Map<String, Object?>>? latest;
  final flow = [
    syntheticFlow('2026-10-01', '999.00', '10.00', '989.00', '100.00'),
    syntheticFlow('2026-10-02', '0.00', '40.00', '-40.00', '60.00'),
    syntheticFlow('2026-10-03', '0.00', '150.00', '-150.00', '-90.00'),
    syntheticFlow('2026-10-04', '90.00', '0.00', '90.00', '0.00'),
  ];
  List<AccountDto> get accounts => [
    AccountDto.fromJson({
      ...mockAccount(l).toJson(),
      'balance': '1234.50',
      'transaction_count': 35,
      'color': '#59A849',
    }),
    AccountDto.fromJson({
      ...mockAccount(l).toJson(),
      'id': '00000000-0000-4000-8000-000000000002',
      'name': l.dollarAccount,
      'currency': 'USD',
      'balance': '500.25',
      'transaction_count': 7,
      'color': '#CA995A',
    }),
  ];
  Future<http.Response> handle(http.Request request) async {
    requests.add(request);
    final path = request.url.path;
    if (delayed[path] case final Completer<http.Response> pending) {
      return pending.future;
    }
    if (request.method == 'PATCH') {
      if (patch != null) return patch!.future;
      profile = {
        ...profile,
        ...jsonDecode(request.body) as Map<String, Object?>,
      };
      return fixtures.ok(profile);
    }
    if (statuses[path] case final int status when status != 200) {
      return fixtures.problem(status);
    }
    if (path == '/api/v1/users/me') return fixtures.ok(profile);
    if (empty && path == '/api/v1/budgets') return fixtures.problem(404);
    if (empty && path == '/api/v1/goals') return fixtures.problem(501);
    final report = mockReports(l);
    final items = switch (path) {
      '/api/v1/accounts' =>
        empty ? <Object?>[] : accounts.map((a) => a.toJson()).toList(),
      '/api/v1/goals' => mockGoals(l).map((g) => g.toJson()).toList(),
      '/api/v1/budgets' => mockBudgets(l).map((b) => b.toJson()).toList(),
      '/api/v1/categories' =>
        report.categories.values.map((c) => c.toJson()).toList(),
      '/api/v1/reports/categories' =>
        empty ? <Object?>[] : report.rows.map((r) => r.toJson()).toList(),
      '/api/v1/reports/cash-flow' =>
        empty ? <Object?>[] : flow.map((r) => r.toJson()).toList(),
      '/api/v1/transactions' =>
        empty ? <Object?>[] : latest ?? [fixtures.transaction()],
      '/api/v1/tags' => [fixtures.tag.toJson()],
      _ => throw StateError('Unexpected request $request'),
    };
    return fixtures.ok({'items': items, 'next_cursor': null});
  }

  void close() {
    session.dispose();
    api.close();
  }
}

Future<void> mountHome(
  WidgetTester tester,
  HomeFixture fixture, {
  Brightness brightness = Brightness.light,
  double height = 2400,
  bool shell = false,
}) async {
  await harness.mount(
    tester,
    brightness,
    (_, _) => shell
        ? AppShell(session: fixture.session, today: today)
        : HomePage(session: fixture.session, today: today, animate: false),
    reducedMotion: true,
    captureSize: Size(650, height),
    viewSize: Size(800, height + 100),
  );
  await tester.pumpAndSettle();
}

void main() {
  harness.loadGoldenFonts();
  test('home widget keys, order, omissions and fallback match coordinator convention', () {
    expect(visibleHomeWidgets(null), defaultHomeWidgets);
    expect(visibleHomeWidgets([]), defaultHomeWidgets);
    expect(visibleHomeWidgets(['unknown']), defaultHomeWidgets);
    expect(visibleHomeWidgets(['transactions', 'unknown', 'accounts']), [
      'transactions',
      'accounts',
    ]);
  });
  testWidgets(
    'exact default order, latest page limit, server order and no real-home mocks',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      await mountHome(tester, f);
      var y = tester.getTopLeft(find.byKey(const Key('home-greeting'))).dy;
      for (final key in defaultHomeWidgets) {
        final next = tester.getTopLeft(find.byKey(Key('home-block-$key'))).dy;
        expect(next, greaterThan(y));
        y = next;
      }
      final transactions = f.requests
          .where((r) => r.url.path == '/api/v1/transactions')
          .toList();
      expect(transactions, hasLength(1));
      expect(transactions.single.url.queryParameters, {'limit': '25'});
      expect(find.byType(HomeTransactionRow), findsOneWidget);
      expect(find.text(l.accountTransactionCount(35)), findsOneWidget);
      expect(find.text(l.syntheticData), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'home_widgets reorders and hides blocks while greeting and + stay visible',
    (tester) async {
      final f = HomeFixture(widgets: ['transactions', 'accounts']);
      addTearDown(f.close);
      await mountHome(tester, f);
      expect(
        tester.getTopLeft(find.byKey(const Key('home-block-transactions'))).dy,
        lessThan(
          tester.getTopLeft(find.byKey(const Key('home-block-accounts'))).dy,
        ),
      );
      for (final key in ['goals', 'budgets', 'categories', 'cash_flow']) {
        expect(find.byKey(Key('home-block-$key')), findsNothing);
      }
      expect(find.byKey(const Key('home-greeting')), findsOneWidget);
      expect(find.byKey(const Key('add-transaction')), findsOneWidget);
    },
  );
  for (final status in [200, 500]) {
    testWidgets(
      'account selection sends full preferences + CSRF; response $status commits or reverts',
      (tester) async {
        final f = HomeFixture(widgets: ['accounts']);
        addTearDown(f.close);
        f.patch = Completer<http.Response>();
        await mountHome(tester, f, height: 600);
        final id = f.accounts.last.id;
        final target = find.byKey(Key('account-$id'));
        await tester.ensureVisible(target);
        await tester.pumpAndSettle();
        await tester.tap(target);
        await tester.pump();
        expect(
          tester.widget<HomeAccounts>(find.byType(HomeAccounts)).selectedId,
          id,
        );
        final request = f.requests.last;
        expect(request.method, 'PATCH');
        expect(request.url.path, '/api/v1/users/me');
        expect(request.headers['X-CSRF-Token'], 'synthetic.token');
        final preferences = {
          ...f.profile['preferences'] as Map<String, Object?>,
          'default_account_id': id,
        };
        expect(jsonDecode(request.body), {'preferences': preferences});
        f.patch!.complete(
          status == 200
              ? fixtures.ok({...f.profile, 'preferences': preferences})
              : fixtures.problem(500),
        );
        await tester.pumpAndSettle();
        expect(
          tester.widget<HomeAccounts>(find.byType(HomeAccounts)).selectedId,
          status == 200 ? id : mockAccountId,
        );
        expect(
          find.text(l.connectionError),
          status == 500 ? findsOneWidget : findsNothing,
        );
      },
    );
  }
  testWidgets(
    'swipe left changes to income; top-three legend ranks all four expense categories',
    (tester) async {
      final report = mockReports(l);
      final rows = [
        for (var i = 0; i < 4; i++)
          CategoryReportRowDto(
            categoryId: 'category-$i',
            kind: CategoryReportRowKind.expense,
            startOn: '2026-10-01',
            endOn: '2026-10-31',
            total: ReportTotalDto(
              byCurrency: const [
                CurrencyTotalDto(currency: 'USD', amount: '10.00'),
              ],
              reportCurrency: 'PEN',
              reportAmount: ['10.00', '40.00', '20.00', '30.00'][i],
              unconvertedCount: 0,
            ),
          ),
        ...report.rows.where((row) => row.kind == CategoryReportRowKind.income),
      ];
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => Material(
          color: Colors.transparent,
          child: HomeCategoryCarousel(
            month: DateTime.now(),
            onMoveMonth: (val) {},

            data: HomeCategoryData(rows, {
              ...report.categories,
              for (var i = 0; i < 4; i++)
                'category-$i': CategoryDto.fromJson({
                  ...mockCategory(l).toJson(),
                  'id': 'category-$i',
                  'name': 'Synthetic category $i',
                }),
            }),
            animate: false,
          ),
        ),
        reducedMotion: true,
        captureSize: const Size(600, 700),
      );
      await tester.pumpAndSettle();
      final legend = find.byWidgetPredicate(
        (w) => w.key is Key && w.key.toString().contains('legend-0-'),
      );
      expect(legend, findsNWidgets(3));
      expect(find.byKey(const Key('legend-0-category-0')), findsNothing);
      expect(find.textContaining('Synthetic category 0'), findsNothing);
      expect(
        tester.widget<CategoryPieChart>(find.byType(CategoryPieChart)).slices,
        hasLength(4),
      );
      await tester.tap(find.byKey(const Key('expense-income-toggle')));
      await tester.pumpAndSettle();
      
      expect(
        tester
            .widget<CategoryPieChart>(find.byType(CategoryPieChart))
            .slices
            .single
            .label,
        l.workCategory,
      );
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'line uses signed cumulative_net directly, including falling, negative and zero values',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => CumulativeCashFlowChart(rows: f.flow, animate: false),
      );
      final chart = tester.widget<LineChart>(find.byType(LineChart));
      expect(chart.data.lineBarsData, hasLength(1));
      expect(chart.data.lineBarsData.single.spots.map((s) => s.y), [
        1,
        .6,
        -.9,
        0,
      ]);
      expect(chart.data.minY, lessThan(0));
      final tooltip = chart.data.lineTouchData.touchTooltipData.getTooltipItems(
        [
          LineBarSpot(
            chart.data.lineBarsData.single,
            0,
            chart.data.lineBarsData.single.spots[2],
          ),
        ],
      );
      expect(tooltip.single!.text, contains('-90 S/.'));
    },
  );
  for (final status in [404, 501]) {
    testWidgets(
      'budgets and goals $status produce empty blocks, other blocks remain loaded',
      (tester) async {
        final f = HomeFixture();
        addTearDown(f.close);
        f.statuses.addAll({'/api/v1/budgets': status, '/api/v1/goals': status});
        await mountHome(tester, f);
        expect(find.text(l.emptyBudgets), findsOneWidget);
        expect(find.text(l.emptyGoals), findsOneWidget);
        expect(find.text(l.connectionError), findsNothing);
        expect(find.byType(HomeTransactionRow), findsOneWidget);
      },
    );
  }
  testWidgets(
    '500 affects one block; its retry reloads it without reloading other blocks',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      f.statuses['/api/v1/budgets'] = 500;
      await mountHome(tester, f);
      expect(find.text(l.connectionError), findsOneWidget);
      expect(find.byType(HomeTransactionRow), findsOneWidget);
      final before = f.requests.length;
      f.statuses.clear();
      await tester.tap(find.text(l.retry));
      await tester.pumpAndSettle();
      expect(find.text(l.connectionError), findsNothing);
      expect(f.requests.skip(before).map((r) => r.url.path), [
        '/api/v1/budgets',
      ]);
    },
  );
  testWidgets(
    'loading goals does not hide loaded accounts or latest transactions',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      final pending = Completer<http.Response>();
      f.delayed['/api/v1/goals'] = pending;
      await harness.mount(
        tester,
        Brightness.light,
        (_, _) => HomePage(session: f.session, today: today, animate: false),
        reducedMotion: true,
        captureSize: const Size(650, 2400),
        viewSize: const Size(800, 2500),
      );
      await tester.pump(const Duration(seconds: 1));
      expect(find.byType(HomeAccounts), findsOneWidget);
      expect(find.byType(HomeTransactionRow), findsOneWidget);
      expect(
        find.descendant(
          of: find.byKey(const Key('home-block-goals')),
          matching: find.byType(CircularProgressIndicator),
        ),
        findsOneWidget,
      );
      pending.complete(
        fixtures.ok({'items': <Object?>[], 'next_cursor': null}),
      );
      await tester.pumpAndSettle();
      expect(find.text(l.emptyGoals), findsOneWidget);
    },
  );
  test('latest feed requests one page of 25 and preserves the complete server sequence', () async {
    final f = HomeFixture();
    addTearDown(f.close);
    f.latest = [
      for (var i = 25; i > 0; i--) fixtures.transaction(id: 'synthetic-$i'),
    ];
    final home = HomeController(
      f.api,
      month: DateTime(2026, 10),
      reportCurrency: 'PEN',
    );
    addTearDown(home.dispose);
    await home.transactions.load();
    expect(home.transactions.error, isNull);
    expect(home.transactions.data!.transactions.map((t) => t.id), [
      for (var i = 25; i > 0; i--) 'synthetic-$i',
    ]);
    final reads = f.requests
        .where((r) => r.url.path == '/api/v1/transactions')
        .toList();
    expect(reads, hasLength(1));
    expect(reads.single.url.queryParameters, {'limit': '25'});
  });
  test('overlapping block refresh ignores the older response', () async {
    final first = Completer<List<String>>();
    final second = Completer<List<String>>();
    var call = 0;
    final block = HomeBlock(() => ++call == 1 ? first.future : second.future);
    addTearDown(block.dispose);
    final oldLoad = block.load();
    final newLoad = block.load();
    second.complete(['new']);
    await newLoad;
    first.complete(['old']);
    await oldLoad;
    expect(block.data, ['new']);
    expect(block.loading, isFalse);
  });
  for (final path in [
    '/api/v1/accounts',
    '/api/v1/reports/cash-flow',
    '/api/v1/goals',
    '/api/v1/budgets',
    '/api/v1/reports/categories',
    '/api/v1/transactions',
  ]) {
    testWidgets('401 from $path returns to login and removes private shell', (
      tester,
    ) async {
      final f = HomeFixture();
      addTearDown(f.close);
      f.statuses[path] = 401;
      await tester.pumpWidget(MonetaeApp(api: f.api));
      await tester.pumpAndSettle();
      expect(find.byType(LoginPage), findsOneWidget);
      expect(find.byType(AppShell), findsNothing);
      expect(tester.takeException(), isNull);
    });
  }
  test('pagination retains server order, empty compatibility, and rejects repeated cursors', () async {
    var count = 0;
    expect(
      await loadPages<int>((cursor) async {
        count++;
        return cursor == null ? ([3, 1], 'second') : ([2], null);
      }),
      [3, 1, 2],
    );
    expect(count, 2);
    await expectLater(
      loadPages<int>((_) async => (<int>[], 'same')),
      throwsA(isA<ApiException>()),
    );
    expect(
      await loadPages<int>(
        (_) async =>
            throw const ApiException(ApiErrorKind.unavailable, statusCode: 501),
        unavailableIsEmpty: true,
      ),
      isEmpty,
    );
  });
  testWidgets(
    'four tabs navigate; + opens the transaction form; wide shell uses rail',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      await tester.pumpWidget(MonetaeApp(api: f.api));
      await tester.pumpAndSettle();
      expect(find.byType(NavigationDestination), findsNWidgets(4));
      await tester.tap(find.byKey(const Key('add-transaction')));
      await tester.pumpAndSettle();
      expect(find.byType(NewTransactionPage), findsOneWidget);
      expect(find.byKey(const Key('transaction-amount')), findsOneWidget);
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-2')));
      await tester.pumpAndSettle();
      expect(find.byType(BudgetsPage), findsOneWidget);
      await tester.tap(find.byKey(const Key('nav-3')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('theme-preference')), findsOneWidget);
      expect(find.text(l.syntheticData), findsWidgets);
      await tester.tap(find.byKey(const Key('nav-0')));
      await tester.pumpAndSettle();
      expect(find.byType(HomePage), findsOneWidget);
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.binding.setSurfaceSize(const Size(1200, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('navigation-rail')), findsOneWidget);
      expect(find.byKey(const Key('bottom-navigation')), findsNothing);
    },
  );
  testWidgets(
    'More persists theme with the full existing preferences and preserves the default account',
    (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      await tester.pumpWidget(MonetaeApp(api: f.api));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-3')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('theme-preference')));
      await tester.pumpAndSettle();
      await tester.tap(find.text(l.lightTheme).last);
      await tester.pumpAndSettle();
      final request = f.requests.singleWhere((r) => r.method == 'PATCH');
      expect(request.headers['X-CSRF-Token'], 'synthetic.token');
      expect(jsonDecode(request.body), {
        'preferences': {
          'theme': 'light',
          'accent_color': '#BA7DBD',
          'home_widgets': <String>[],
          'transaction_card': fixtures.all.toJson(),
          'default_account_id': mockAccountId,
        },
      });
      final selector = tester.widget<DropdownButton<UserPreferencesTheme>>(
        find.byKey(const Key('theme-preference')),
      );
      expect(selector.value, UserPreferencesTheme.light);
      expect(
        Theme.of(tester.element(find.byKey(const Key('theme-preference'))))
            .brightness,
        Brightness.light,
      );
      expect(tester.takeException(), isNull);
    },
  );
  for (final brightness in Brightness.values) {
    for (final empty in [false, true]) {
      testWidgets(
        'assembled home ${empty ? 'empty' : 'data'} ${brightness.name} golden',
        (tester) async {
          final f = HomeFixture(empty: empty);
          addTearDown(f.close);
          await mountHome(tester, f, brightness: brightness, shell: true);
          expect(tester.takeException(), isNull);
          await expectLater(
            find.byKey(const Key('capture')),
            matchesGoldenFile(
              'goldens/assembled_home_${empty ? 'empty' : 'data'}_${brightness.name}.png',
            ),
          );
        },
      );
    }
    testWidgets('four-button navigation ${brightness.name} golden', (
      tester,
    ) async {
      await harness.mount(
        tester,
        brightness,
        (_, _) => AppNavigation(index: 0, onChanged: (_) {}),
        captureSize: const Size(600, 130),
      );
      await tester.pumpAndSettle();
      expect(find.byType(NavigationDestination), findsNWidgets(4));
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/navigation_${brightness.name}.png'),
      );
    });
    testWidgets('budgets page ${brightness.name} golden', (tester) async {
      final f = HomeFixture();
      addTearDown(f.close);
      await harness.mount(
        tester,
        brightness,
        (_, _) => BudgetsPage(api: f.api, today: today),
        reducedMotion: true,
        captureSize: const Size(650, 950),
        viewSize: const Size(800, 1050),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/budgets_page_${brightness.name}.png'),
      );
    });
  }
}
