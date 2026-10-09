import 'dart:io';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/presentation/component_models.dart';
import 'package:monetae_web/presentation/category_icon_source.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/widgets/custom_delayed_curve.dart';
import 'package:monetae_web/widgets/fade_in.dart';
import 'package:monetae_web/widgets/theme_preview.dart';
import 'package:monetae_web/widgets/transaction_card.dart';

const _capture = Key('capture');
typedef ComponentBuilder = Widget Function(BuildContext, AppLocalizations);

Future<void> mount(
  WidgetTester tester,
  Brightness brightness,
  ComponentBuilder builder, {
  bool reducedMotion = false,
  Size captureSize = const Size(600, 520),
  Size viewSize = const Size(800, 700),
}) async {
  tester.view.physicalSize = viewSize;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: monetaeTheme(brightness: brightness),
      locale: const Locale('es'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Builder(
        builder: (context) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(disableAnimations: reducedMotion),
          child: Scaffold(
            body: Center(
              child: RepaintBoundary(
                key: _capture,
                child: Container(
                  width: captureSize.width,
                  height: captureSize.height,
                  padding: const EdgeInsets.all(24),
                  color: MonetaeColors.of(context).background,
                  child: Builder(
                    builder: (context) =>
                        builder(context, AppLocalizations.of(context)),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
}

void loadGoldenFonts() {
  setUpAll(() async {
    // Use Flutter's bundled Roboto instead of the block-shaped Ahem test font.
    // Locate it in the SDK running flutter_tester; no system font dependency.
    var sdk = File(Platform.resolvedExecutable).parent;
    File font;
    while (true) {
      font = File(
        '${sdk.path}/bin/cache/artifacts/material_fonts/Roboto-Regular.ttf',
      );
      if (font.existsSync()) break;
      if (sdk.parent.path == sdk.path) {
        throw StateError('Flutter SDK Roboto font not found');
      }
      sdk = sdk.parent;
    }
    final roboto = FontLoader('Roboto');
    roboto.addFont(
      Future.value(ByteData.sublistView(await font.readAsBytes())),
    );
    await roboto.load();
    final loader = FontLoader('MaterialIcons');
    loader.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await loader.load();
  });
}

void main() {
  loadGoldenFonts();
  for (final brightness in Brightness.values) {
    final mode = brightness.name;
    testWidgets('theme tokens, accent and preview $mode', (tester) async {
      await mount(tester, brightness, (_, _) => const ThemePreview());
      final colors = MonetaeColors.of(
        tester.element(find.byType(ThemePreview)),
      );
      expect(
        colors.income,
        brightness == Brightness.light
            ? const Color(0xFF59A849)
            : const Color(0xFF62CA77),
      );
      final alternative = monetaeTheme(
        brightness: brightness,
        accent: Colors.green,
      );
      expect(alternative.extension<MonetaeColors>()!.card, isNot(colors.card));
      expect(colors.copyWith(income: Colors.blue).income, Colors.blue);
      expect(colors.lerp(colors, .5).expense, colors.expense);
      await expectLater(
        find.byKey(_capture),
        matchesGoldenFile('goldens/theme_$mode.png'),
      );
    });

    testWidgets('transaction model, actions and golden $mode', (tester) async {
      var taps = 0;
      bool? selection;
      await mount(
        tester,
        brightness,
        (_, l) => Column(
          children: [
            for (final card in mockCards(l))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: TransactionCard(model: card, onTap: () => taps++),
              ),
          ],
        ),
      );
      expect(find.text('S/ 48.50'), findsOneWidget);
      expect(find.text('US\$ 12.00'), findsOneWidget);
      expect(find.text('Movimiento de préstamo'), findsOneWidget);
      await tester.tap(find.byType(TransactionCard).first);
      expect(taps, 1);
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(_capture),
        matchesGoldenFile('goldens/transactions_$mode.png'),
      );
      await mount(
        tester,
        brightness,
        (_, l) => TransactionCard(
          model: mockCards(l).first,
          selected: true,
          onSelectionChanged: (value) => selection = value,
        ),
      );
      await tester.tap(find.byType(Checkbox));
      expect(selection, false);
      await mount(
        tester,
        brightness,
        (_, l) => TransactionCard(model: mockCards(l).first, compact: true),
      );
      expect(find.byType(Tooltip), findsOneWidget);
      expect(find.text('Ejemplo'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('pie selection, zero filtering and golden $mode', (
      tester,
    ) async {
      String? selected;
      await mount(
        tester,
        brightness,
        (_, l) => Center(
          child: CategoryPieChart(
            slices: mockSlices(l),
            emptyLabel: l.emptyChart,
            selectedId: 'food',
            animate: false,
            onSelected: (value) => selected = value,
          ),
        ),
      );
      final pie = tester.widget<PieChart>(find.byType(PieChart));
      expect(pie.data.startDegreeOffset, -45);
      expect(pie.data.sections.length, 3);
      expect(pie.data.sections.first.radius, 106);
      await expectLater(
        find.byKey(_capture),
        matchesGoldenFile('goldens/pie_$mode.png'),
      );
      await tester.tap(find.byIcon(Icons.directions_bus_rounded));
      expect(selected, 'transport');
      await tester.tap(find.byIcon(Icons.restaurant_rounded));
      expect(selected, isNull);
      await mount(
        tester,
        brightness,
        (_, l) => Center(
          child: CategoryPieChart(
            slices: [
              const CategorySlice(
                id: 'zero',
                label: 'Zero',
                weight: 0,
                percentLabel: '0%',
                amountLabel: '0.00',
                color: Colors.grey,
                icon: CategoryIconSource.base('home'),
              ),
              ...mockSlices(l),
            ],
            emptyLabel: l.emptyChart,
            animate: false,
          ),
        ),
      );
      expect(
        tester.widget<PieChart>(find.byType(PieChart)).data.sections.length,
        3,
      );
      await mount(
        tester,
        brightness,
        (_, l) => Center(
          child: CategoryPieChart(
            slices: const [],
            emptyLabel: l.emptyChart,
            animate: false,
          ),
        ),
      );
      expect(find.text('Sin datos'), findsOneWidget);
      expect(find.byType(PieChart), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('fade progression, disposal and golden $mode', (tester) async {
      await mount(
        tester,
        brightness,
        (_, l) => FadeIn(child: TransactionCard(model: mockCards(l).first)),
      );
      await tester.pump(const Duration(milliseconds: 250));
      final fade = tester.widget<FadeTransition>(
        find.descendant(
          of: find.byType(FadeIn),
          matching: find.byType(FadeTransition),
        ),
      );
      expect(fade.opacity.value, closeTo(.5, .01));
      await expectLater(
        find.byKey(_capture),
        matchesGoldenFile('goldens/fade_$mode.png'),
      );
      await tester.pump(const Duration(milliseconds: 250));
      expect(fade.opacity.value, 1);
      await mount(
        tester,
        brightness,
        (_, l) => FadeIn(child: Text(l.fadePreview)),
        reducedMotion: true,
      );
      expect(
        tester
            .widget<FadeTransition>(
              find.descendant(
                of: find.byType(FadeIn),
                matching: find.byType(FadeTransition),
              ),
            )
            .opacity
            .value,
        1,
      );
      await mount(
        tester,
        brightness,
        (_, l) => FadeIn(child: Text(l.fadePreview)),
      );
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pumpWidget(const SizedBox());
      await tester.pump(const Duration(seconds: 1));
      expect(tester.takeException(), isNull);
    });
  }

  test('delayed curve preserves endpoints and delay', () {
    const curve = CustomDelayedCurve();
    expect(curve.transform(0), 0);
    expect(curve.transform(.2), 0);
    expect(curve.transform(.25), 0);
    expect(curve.transform(.625), closeTo(.5, .001));
    expect(curve.transform(1), 1);
  });

  testWidgets('demo switches theme, locale and accent without overflow', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1200, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const DemoApp());
    await tester.pumpAndSettle();
    expect(find.text('Transacciones'), findsOneWidget);
    await tester.tap(find.byKey(const Key('theme-switch')));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(SpikePage))).brightness,
      Brightness.dark,
    );
    await tester.tap(find.byKey(const Key('language-switch')));
    await tester.pumpAndSettle();
    expect(find.text('Transactions'), findsOneWidget);
    await tester.tap(find.byKey(const Key('accent-picker')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Green').last);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Card details'));
    await tester.pumpAndSettle();
    for (final field in ['time', 'account', 'actions']) {
      final toggle = find.byKey(Key('show-$field'));
      await tester.ensureVisible(toggle);
      await tester.tap(toggle);
      await tester.pumpAndSettle();
    }
    tester.view.physicalSize = const Size(390, 1000);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
