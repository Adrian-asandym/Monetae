import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:monetae_web/api/category_detail_controller.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_reports.dart';
import 'package:monetae_web/l10n/app_localizations_en.dart';
import 'package:monetae_web/pages/category_detail_page.dart';
import 'package:monetae_web/pages/home_page.dart';
import 'package:monetae_web/pages/transactions_page.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/widgets/home_category_carousel.dart';
import 'package:monetae_web/widgets/home_category_details.dart';

import 'api_session_test.dart' as api;
import 'components_test.dart' as harness;
import 'home_assembly_test.dart' as home;
import 'home_v2_test.dart' as mobile;

class CategoryFixture extends home.HomeFixture {
  CategoryFixture() : super(widgets: ['categories']);
  List<CategoryReportRowDto> rows = mockReports(home.l).rows.reversed.toList();
  final pending = <String, Completer<http.Response>>{};
  final reports = <Uri>[];
  final transactionQueries = <Uri>[];
  bool paginate = false;
  int reportStatus = 200;

  @override
  Future<http.Response> handle(http.Request request) async {
    final uri = request.url;
    if (uri.path == '/api/v1/reports/categories') {
      reports.add(uri);
      if (pending[uri.queryParameters['date_from']] case final response?) {
        return response.future;
      }
      if (reportStatus != 200) return api.problem(reportStatus);
      final nextPage = uri.queryParameters['cursor'] != null;
      return api.ok({
        'items': (paginate ? (nextPage ? rows.skip(1) : rows.take(1)) : rows)
            .map((row) => row.toJson())
            .toList(),
        'next_cursor': paginate && !nextPage ? 'categories-next' : null,
      });
    }
    if (uri.path == '/api/v1/transactions' &&
        uri.queryParameters.containsKey('category_id')) {
      transactionQueries.add(uri);
      return api.ok({
        'items': <Object?>[],
        'next_cursor': uri.queryParameters['cursor'] == null
            ? 'transactions-next'
            : null,
      });
    }
    return super.handle(request);
  }
}

Future<void> mountDetail(
  WidgetTester tester,
  CategoryFixture f, {
  Brightness brightness = Brightness.light,
  DateTime? month,
}) => mobile.mountMobile(
  tester,
  brightness,
  (_, _) => CategoryDetailPage(
    session: f.session,
    month: month ?? DateTime(2026, 10),
    animate: false,
  ),
);

ListTile tile(WidgetTester tester, String id) =>
    tester.widget<ListTile>(find.byKey(Key('category-detail-$id')));

void main() {
  harness.loadGoldenFonts();
  test('English title is localized', () {
    expect(AppLocalizationsEn().categoryDetailTitle, 'Category details');
  });

  for (final income in [false, true]) {
    testWidgets(
      'Home opens detail from ${income ? 'income' : 'expense'} card including chart surface',
      (tester) async {
        final f = CategoryFixture();
        addTearDown(f.close);
        await mobile.mountMobile(
          tester,
          Brightness.light,
          (_, _) =>
              HomePage(session: f.session, today: home.today, animate: false),
        );
        if (income) {
          await tester.tap(find.byKey(const Key('category-toggle-expense')));
          await tester.pumpAndSettle();
        }
        final chart = find.descendant(
          of: find.byWidgetPredicate(
            (widget) =>
                widget is HomeCategoryPiePage &&
                widget.kind ==
                    (income
                        ? CategoryReportRowKind.income
                        : CategoryReportRowKind.expense),
          ),
          matching: find.byType(CategoryPieChart),
        );
        await tester.tapAt(tester.getCenter(chart) + const Offset(65, -45));
        await tester.pumpAndSettle();
        expect(find.byType(CategoryDetailPage), findsOneWidget);
        expect(find.text('Detalle de categorías'), findsOneWidget);
        expect(
          tester
              .widget<CategoryDetailPage>(find.byType(CategoryDetailPage))
              .initialKind,
          income ? CategoryReportRowKind.income : CategoryReportRowKind.expense,
        );
        expect(find.text('octubre de 2026'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'Home card padding opens detail and swiping keeps income selection',
    (tester) async {
      final f = CategoryFixture();
      addTearDown(f.close);
      await mobile.mountMobile(
        tester,
        Brightness.light,
        (_, _) =>
            HomePage(session: f.session, today: home.today, animate: false),
      );
      await tester.drag(
        find.byKey(const Key('category-pages')),
        const Offset(-350, 0),
      );
      await tester.pumpAndSettle();
      final card = tester.getRect(find.byType(HomeCategoryCarousel));
      await tester.tapAt(Offset(card.left + 10, card.bottom - 5));
      await tester.pumpAndSettle();
      expect(find.byType(CategoryDetailPage), findsOneWidget);
      expect(
        tester
            .widget<CategoryDetailPage>(find.byType(CategoryDetailPage))
            .initialKind,
        CategoryReportRowKind.income,
      );
    },
  );

  testWidgets(
    'income drill-down uses the selected month across a year boundary',
    (tester) async {
      final f = CategoryFixture();
      addTearDown(f.close);
      await mountDetail(tester, f, month: DateTime(2026, 12));
      await tester.tap(find.byTooltip(home.l.nextMonth));
      await tester.pumpAndSettle();
      expect(f.reports.last.queryParameters['date_from'], '2027-01-01');
      expect(f.reports.last.queryParameters['date_to'], '2027-01-31');
      await tester.tap(find.byKey(const Key('category-toggle-expense')));
      await tester.pumpAndSettle();
      final id = mockReports(home.l).rows.last.categoryId!;
      await tester.tap(find.byKey(Key('category-detail-$id')));
      await tester.pumpAndSettle();
      final query = f.transactionQueries.single.queryParameters;
      expect(query['category_id'], id);
      expect(query['date_from'], '2027-01-01T05:00:00Z');
      expect(query['date_to'], '2027-02-01T05:00:00Z');
    },
  );

  testWidgets(
    'calendar report ranges, leap February, report currency and kind ranking',
    (tester) async {
      final f = CategoryFixture()..paginate = true;
      f.session.user = CurrentUserDto.fromJson({
        ...f.profile,
        'report_currency': 'USD',
      });
      addTearDown(f.close);
      await mountDetail(tester, f, month: DateTime(2028, 3));
      expect(f.reports, hasLength(2));
      expect(
        f.reports.first.queryParameters,
        containsPair('date_from', '2028-03-01'),
      );
      expect(
        f.reports.last.queryParameters,
        containsPair('date_to', '2028-03-31'),
      );
      expect(
        f.reports.every(
          (uri) => uri.queryParameters['report_currency'] == 'USD',
        ),
        isTrue,
      );
      final ranked = tester
          .widget<HomeCategoryDetails>(find.byType(HomeCategoryDetails))
          .ranked;
      expect(ranked.map((slice) => slice.amountLabel), ['110 S/.', '60 S/.']);
      expect(ranked.map((slice) => slice.percentLabel), ['64,7%', '35,3%']);
      await tester.tap(find.byTooltip(home.l.previousMonth));
      await tester.pumpAndSettle();
      expect(
        f.reports.last.queryParameters,
        containsPair('date_from', '2028-02-01'),
      );
      expect(
        f.reports.last.queryParameters,
        containsPair('date_to', '2028-02-29'),
      );
      expect(find.text('febrero de 2028'), findsOneWidget);
      await tester.tap(find.byKey(const Key('category-toggle-expense')));
      await tester.pumpAndSettle();
      final income = tester
          .widget<HomeCategoryDetails>(find.byType(HomeCategoryDetails))
          .ranked;
      expect(income, hasLength(1));
      expect(income.single.amountLabel, '500 S/.');
      expect(income.single.percentLabel, '100%');
      expect(f.reports, hasLength(4)); // Kind switching uses the same report.
      await tester.tap(find.byTooltip(home.l.nextMonth));
      await tester.pumpAndSettle();
      expect(
        f.reports.last.queryParameters,
        containsPair('date_to', '2028-03-31'),
      );
    },
  );

  testWidgets(
    'category drill-down keeps exclusive Lima boundaries on pagination and refresh',
    (tester) async {
      final f = CategoryFixture();
      addTearDown(f.close);
      await mountDetail(tester, f);
      final id = mockReports(home.l).rows.first.categoryId!;
      await tester.tap(find.byKey(Key('category-detail-$id')));
      await tester.pumpAndSettle();
      expect(find.byType(TransactionsPage), findsOneWidget);
      expect(f.transactionQueries, hasLength(1));
      await tester.ensureVisible(find.byKey(const Key('load-more')));
      await tester.tap(find.byKey(const Key('load-more')));
      await tester.pumpAndSettle();
      expect(
        f.transactionQueries.last.queryParameters['cursor'],
        'transactions-next',
      );
      await tester.tap(find.byTooltip(home.l.refresh));
      await tester.pumpAndSettle();
      expect(f.transactionQueries, hasLength(3));
      for (final query in f.transactionQueries) {
        expect(query.queryParametersAll['category_id'], [id]);
        expect(query.queryParameters['date_from'], '2026-10-01T05:00:00Z');
        expect(query.queryParameters['date_to'], '2026-11-01T05:00:00Z');
      }
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      expect(find.byType(CategoryDetailPage), findsOneWidget);
      expect(find.text('octubre de 2026'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'late old-month report cannot replace current range and retry works',
    (tester) async {
      final f = CategoryFixture();
      addTearDown(f.close);
      await mountDetail(tester, f);
      final old = Completer<http.Response>();
      f.pending['2026-09-01'] = old;
      await tester.tap(find.byTooltip(home.l.previousMonth));
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byType(ListTile), findsNothing);
      await tester.tap(find.byTooltip(home.l.nextMonth));
      await tester.pumpAndSettle();
      old.complete(api.ok({'items': <Object?>[], 'next_cursor': null}));
      await tester.pumpAndSettle();
      expect(find.byType(ListTile), findsNWidgets(2));
      expect(find.text('octubre de 2026'), findsOneWidget);
      f.reportStatus = 503;
      await tester.tap(find.byTooltip(home.l.nextMonth));
      await tester.pumpAndSettle();
      expect(find.byType(ListTile), findsNothing);
      expect(find.text(home.l.retry), findsOneWidget);
      f.reportStatus = 200;
      await tester.tap(find.text(home.l.retry));
      await tester.pumpAndSettle();
      expect(find.byType(ListTile), findsNWidgets(2));
      expect(f.reports.last.queryParameters['date_from'], '2026-11-01');
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'report pagination captures month even while changing selection',
    () async {
      final f = CategoryFixture()..paginate = true;
      addTearDown(f.close);
      final old = Completer<http.Response>();
      f.pending['2026-10-01'] = old;
      final controller = CategoryDetailController(
        f.api,
        month: DateTime(2026, 10),
      );
      addTearDown(controller.dispose);
      final firstLoad = controller.categories.load();
      await controller.moveMonth(1);
      f.pending.remove('2026-10-01');
      old.complete(api.ok({'items': <Object?>[], 'next_cursor': 'old-next'}));
      await firstLoad;
      expect(f.reports.last.queryParameters['cursor'], 'old-next');
      expect(f.reports.last.queryParameters['date_from'], '2026-10-01');
      expect(controller.month, DateTime(2026, 11));
      expect(controller.categories.data!.rows, hasLength(3));
    },
  );

  for (final brightness in Brightness.values) {
    for (final state in ['expense', 'income', 'empty', 'unconverted']) {
      testWidgets('category detail $state golden ${brightness.name}', (
        tester,
      ) async {
        final f = CategoryFixture();
        addTearDown(f.close);
        if (state == 'empty') f.rows = [];
        if (state == 'unconverted') {
          f.rows = [
            CategoryReportRowDto(
              categoryId: null,
              kind: CategoryReportRowKind.expense,
              startOn: '2026-10-01',
              endOn: '2026-10-31',
              total: const ReportTotalDto(
                reportAmount: '0.00',
                reportCurrency: 'PEN',
                unconvertedCount: 1,
                byCurrency: [
                  CurrencyTotalDto(currency: 'USD', amount: '25.30'),
                ],
              ),
            ),
          ];
        }
        await mountDetail(tester, f, brightness: brightness);
        if (state == 'income') {
          await tester.tap(find.byKey(const Key('category-toggle-expense')));
          await tester.pumpAndSettle();
        }
        if (state == 'unconverted') {
          expect(find.byKey(const Key('unconverted-notice')), findsOneWidget);
          expect(find.textContaining(r'25,30 $'), findsOneWidget);
          expect(tile(tester, 'uncategorized').onTap, isNull);
        }
        expect(tester.takeException(), isNull);
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile(
            'goldens/category_detail_${state}_${brightness.name}.png',
          ),
        );
      });
    }
  }
}
