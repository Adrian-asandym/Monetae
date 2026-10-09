import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/presentation/category_icon_source.dart';
import 'package:monetae_web/theme/monetae_theme.dart';
import 'package:monetae_web/widgets/brand_logo.dart';
import 'package:monetae_web/widgets/category_icon.dart';
import 'package:monetae_web/widgets/category_pie_chart.dart';
import 'package:monetae_web/widgets/transaction_card_list.dart';
import 'package:monetae_web/widgets/transaction_card.dart';
import 'package:monetae_web/widgets/transaction_card_settings.dart';

import 'components_test.dart' as harness;

const allDetails = TransactionCardPreferencesDto(
  showDate: true,
  showTime: true,
  showNote: true,
  showTags: true,
  showAccount: true,
  showActions: true,
);
const noDetails = TransactionCardPreferencesDto(
  showDate: false,
  showTime: false,
  showNote: false,
  showTags: false,
  showAccount: false,
  showActions: false,
);
final hostileSvg = mockHouseSvg
    .replaceFirst(
      'viewBox=',
      'onload="throw new Error(\'ONLOAD_EXECUTED\')" viewBox=',
    )
    .replaceFirst(
      '</svg>',
      '<script>throw new Error("SCRIPT_EXECUTED");</script></svg>',
    );

Future<Uint8List> raster(String svg) async {
  final info = await vg.loadPicture(SvgStringLoader(svg), null);
  final image = await info.picture.toImage(32, 32);
  try {
    return (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!.buffer
        .asUint8List();
  } finally {
    image.dispose();
    info.picture.dispose();
  }
}

void main() {
  // Reuse the spike font loader without registering its tests again.
  harness.loadGoldenFonts();

  test('preferences derive defaults from the contract, remain strict and round trip', () {
    final p = TransactionCardPreferencesDto.fromJson({});
    expect(p.toJson(), {
      'show_date': true,
      'show_time': false,
      'show_note': true,
      'show_tags': true,
      'show_account': false,
      'show_actions': false,
    });
    expect(
      TransactionCardPreferencesDto.fromJson(allDetails.toJson()).showAccount,
      isTrue,
    );
    for (final bad in [null, 'true', 1]) {
      expect(
        () => TransactionCardPreferencesDto.fromJson({'show_time': bad}),
        throwsFormatException,
      );
    }
    expect(
      () => TransactionCardPreferencesDto.fromJson({'other': false}),
      throwsFormatException,
    );
  });

  test(
    'custom icon bytes are immutable and missing icons have a base fallback',
    () {
      final bytes = mockHouseBytes;
      final source = CategoryIconSource.resolve(
        'custom:$mockCustomIconId',
        customIcons: {mockCustomIconId: bytes},
      );
      bytes[0] = 0;
      expect(source.svgBytes!.first, 60);
      expect(() => source.svgBytes![0] = 0, throwsUnsupportedError);
      expect(
        CategoryIconSource.resolve('custom:missing').materialIcon,
        Icons.category_rounded,
      );
      expect(
        CategoryIconSource.resolve('restaurant').materialIcon,
        Icons.restaurant_rounded,
      );
    },
  );

  test(
    'SVG scripts and onload are inert and preserve exact raster output',
    () async {
      expect(
        await raster(hostileSvg),
        orderedEquals(await raster(mockHouseSvg)),
      );
    },
  );

  for (final brightness in Brightness.values) {
    final mode = brightness.name;
    testWidgets('brand follows app theme and golden $mode', (tester) async {
      await harness.mount(
        tester,
        brightness,
        (_, _) => const Center(child: BrandLogo(size: 150)),
      );
      await tester.pumpAndSettle();
      final svg = tester.widget<SvgPicture>(find.byType(SvgPicture));
      expect(
        (svg.bytesLoader as SvgAssetLoader).assetName,
        contains(brightness == Brightness.dark ? '-dark.svg' : 'Monetae.svg'),
      );
      if (brightness == Brightness.dark) {
        final colors = MonetaeColors.of(tester.element(find.byType(BrandLogo)));
        expect(
          colors.background,
          pastel(const Color(0xFF5F85C2), brightness, .92),
        );
        expect(colors.card, pastel(const Color(0xFF5F85C2), brightness, .8));
      }
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/brand_$mode.png'),
      );
    });

    for (final (name, preferences) in [
      ('default', const TransactionCardPreferencesDto()),
      ('all', allDetails),
      ('none', noDetails),
    ]) {
      testWidgets('card $name visibility, callbacks and golden $mode', (
        tester,
      ) async {
        var edited = 0;
        var duplicated = 0;
        var deleted = 0;
        await harness.mount(
          tester,
          brightness,
          (_, l) => TransactionCardList(
            models: mockCards(l).take(2).toList(),
            preferences: preferences,
            onEdit: (_) => edited++,
            onDuplicate: (_) => duplicated++,
            onDelete: (_) => deleted++,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byKey(const ValueKey('date-2026-10-09')),
          preferences.showDate ? findsOneWidget : findsNothing,
        );
        expect(
          find.byKey(const Key('transaction-time')),
          preferences.showTime ? findsNWidgets(2) : findsNothing,
        );
        expect(
          find.text('Nota sintética para revisar el componente.'),
          preferences.showNote ? findsOneWidget : findsNothing,
        );
        expect(
          find.text('Ejemplo'),
          preferences.showTags ? findsOneWidget : findsNothing,
        );
        expect(
          find.text('Efectivo de prueba'),
          preferences.showAccount ? findsNWidgets(2) : findsNothing,
        );
        expect(
          find.byTooltip('Editar'),
          preferences.showActions ? findsNWidgets(2) : findsNothing,
        );
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile('goldens/card_${name}_$mode.png'),
        );
        if (preferences.showActions) {
          await tester.tap(find.byTooltip('Editar').first);
          await tester.tap(find.byTooltip('Duplicar').first);
          await tester.tap(find.byTooltip('Borrar').first);
          expect([edited, duplicated, deleted], [1, 1, 1]);
        }
        expect(tester.takeException(), isNull);
      });
    }

    for (final (name, svg) in [
      ('custom', mockHouseSvg),
      ('script', hostileSvg),
    ]) {
      testWidgets('category SVG $name renders and golden $mode', (
        tester,
      ) async {
        final source = CategoryIconSource.custom(
          mockCustomIconId,
          Uint8List.fromList(utf8.encode(svg)),
        );
        await harness.mount(
          tester,
          brightness,
          (_, l) => Column(
            children: [
              TransactionCardList(
                models: [mockCards(l, customSvgBytes: source.svgBytes).last],
              ),
              const SizedBox(height: 15),
              CategoryPieChart(
                slices: mockSlices(l, customSvgBytes: source.svgBytes),
                emptyLabel: l.emptyChart,
                animate: false,
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CategoryIcon(source: source, color: Colors.blue, size: 50),
                  CategoryIcon(
                    source: source,
                    color: Colors.blue,
                    size: 50,
                    tintCustom: true,
                  ),
                ],
              ),
            ],
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(SvgPicture), findsNWidgets(4));
        expect(
          tester.getSize(find.byType(SvgPicture).first),
          const Size(27, 27),
        );
        expect(tester.takeException(), isNull);
        await expectLater(
          find.byKey(const Key('capture')),
          matchesGoldenFile('goldens/category_${name}_$mode.png'),
        );
      });
    }
  }

  testWidgets(
    'daily headers hide without hiding records, including compact notes',
    (tester) async {
      for (final preferences in [
        const TransactionCardPreferencesDto(),
        noDetails,
      ]) {
        await harness.mount(
          tester,
          Brightness.light,
          (_, l) => SingleChildScrollView(
            child: TransactionCardList(
              models: mockCards(l),
              compact: true,
              preferences: preferences,
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(TransactionCard), findsNWidgets(4));
        expect(
          find.text('Ejemplo'),
          preferences.showTags ? findsOneWidget : findsNothing,
        );
        expect(
          find.byKey(const ValueKey('date-2026-10-09')),
          preferences.showDate ? findsOneWidget : findsNothing,
        );
        expect(
          find.byKey(const ValueKey('date-2026-10-10')),
          preferences.showDate ? findsOneWidget : findsNothing,
        );
        expect(
          find.byTooltip('Nota sintética para revisar el componente.'),
          preferences.showNote ? findsOneWidget : findsNothing,
        );
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets('settings update all six fields independently', (tester) async {
    var preferences = const TransactionCardPreferencesDto();
    await harness.mount(
      tester,
      Brightness.light,
      (_, _) => StatefulBuilder(
        builder: (context, setState) => SingleChildScrollView(
          child: Material(
            child: TransactionCardSettings(
              preferences: preferences,
              onChanged: (value) => setState(() => preferences = value),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Detalles de la tarjeta'));
    await tester.pumpAndSettle();
    for (final field in [
      'date',
      'time',
      'note',
      'tags',
      'account',
      'actions',
    ]) {
      final toggle = find.byKey(Key('show-$field'));
      await tester.ensureVisible(toggle);
      await tester.tap(toggle);
      await tester.pumpAndSettle();
    }
    expect(preferences.toJson(), {
      'show_date': false,
      'show_time': true,
      'show_note': false,
      'show_tags': false,
      'show_account': true,
      'show_actions': true,
    });
    expect(tester.takeException(), isNull);
  });
}
