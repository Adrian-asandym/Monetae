import 'package:flutter/material.dart';

import 'data/mock_data.dart';
import 'data/api_dtos.dart';
import 'widgets/brand_logo.dart';
import 'widgets/category_icon.dart';
import 'widgets/transaction_card_list.dart';
import 'widgets/transaction_card_settings.dart';
import 'l10n/app_localizations.dart';
import 'theme/monetae_theme.dart';
import 'widgets/category_pie_chart.dart';
import 'widgets/fade_in.dart';
import 'widgets/theme_preview.dart';
import 'widgets/transaction_card.dart';

void main() => runApp(const MonetaeApp());

class MonetaeApp extends StatefulWidget {
  const MonetaeApp({super.key});
  @override
  State<MonetaeApp> createState() => _MonetaeAppState();
}

class _MonetaeAppState extends State<MonetaeApp> {
  bool _dark = false;
  Locale _locale = const Locale('es');
  Color _accent = const Color(0xFF5F85C2);
  @override
  Widget build(BuildContext context) => MaterialApp(
    onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
    debugShowCheckedModeBanner: false,
    locale: _locale,
    supportedLocales: AppLocalizations.supportedLocales,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    theme: monetaeTheme(brightness: Brightness.light, accent: _accent),
    darkTheme: monetaeTheme(brightness: Brightness.dark, accent: _accent),
    themeMode: _dark ? ThemeMode.dark : ThemeMode.light,
    home: SpikePage(
      dark: _dark,
      accent: _accent,
      locale: _locale,
      onDarkChanged: (value) => setState(() => _dark = value),
      onLocaleChanged: (value) => setState(() => _locale = value),
      onAccentChanged: (value) => setState(() => _accent = value),
    ),
  );
}

class SpikePage extends StatefulWidget {
  const SpikePage({
    super.key,
    required this.dark,
    required this.accent,
    required this.locale,
    required this.onDarkChanged,
    required this.onLocaleChanged,
    required this.onAccentChanged,
  });
  final bool dark;
  final Color accent;
  final Locale locale;
  final ValueChanged<bool> onDarkChanged;
  final ValueChanged<Locale> onLocaleChanged;
  final ValueChanged<Color> onAccentChanged;
  @override
  State<SpikePage> createState() => _SpikePageState();
}

class _SpikePageState extends State<SpikePage> {
  String? _selectedCategory;
  bool _compact = false;
  bool _tintCategoryIcons = false;
  TransactionCardPreferencesDto _preferences =
      const TransactionCardPreferencesDto();
  int _animationRevision = 0;
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final slices = mockSlices(l);
    final cards = mockCards(l);
    final chart = _panel(
      context,
      l.categoryChart,
      Column(
        children: [
          const SizedBox(height: 20),
          CategoryPieChart(
            slices: slices,
            tintCategoryIcons: _tintCategoryIcons,
            emptyLabel: l.emptyChart,
            selectedId: _selectedCategory,
            onSelected: (value) => setState(() => _selectedCategory = value),
          ),
          const SizedBox(height: 30),
          Text(l.selectionHint, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 12),
          for (final slice in slices)
            ListTile(
              dense: true,
              selected: _selectedCategory == slice.id,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              leading: CategoryIcon(
                source: slice.icon,
                color: slice.color,
                tintCustom: _tintCategoryIcons,
              ),
              title: Text(slice.label),
              subtitle: Text(slice.percentLabel),
              trailing: Text(slice.amountLabel),
              onTap: () => setState(
                () => _selectedCategory = _selectedCategory == slice.id
                    ? null
                    : slice.id,
              ),
            ),
          const Divider(),
          ListTile(
            title: Text(l.chartTotal),
            trailing: Text(l.penAmount('300.00')),
          ),
        ],
      ),
    );
    final transactions = _panel(
      context,
      l.transactions,
      Column(
        children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l.compact),
            value: _compact,
            onChanged: (value) => setState(() => _compact = value),
          ),
          TransactionCardSettings(
            preferences: _preferences,
            onChanged: (value) => setState(() => _preferences = value),
          ),
          TransactionCardList(
            models: cards,
            preferences: _preferences,
            compact: _compact,
            tintCategoryIcons: _tintCategoryIcons,
            onEdit: (_) => _previewAction(l.editTransaction),
            onDuplicate: (_) => _previewAction(l.duplicateTransaction),
            onDelete: (_) => _previewAction(l.deleteTransaction),
          ),
        ],
      ),
    );
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const BrandLogo(),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              l.spikeTitle,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            Text(l.syntheticData),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Wrap(
                    spacing: 20,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            widget.dark
                                ? Icons.dark_mode_outlined
                                : Icons.light_mode_outlined,
                          ),
                          const SizedBox(width: 8),
                          Text(widget.dark ? l.darkTheme : l.lightTheme),
                          Switch(
                            key: const Key('theme-switch'),
                            value: widget.dark,
                            onChanged: widget.onDarkChanged,
                          ),
                        ],
                      ),
                      OutlinedButton.icon(
                        key: const Key('language-switch'),
                        onPressed: () => widget.onLocaleChanged(
                          Locale(
                            widget.locale.languageCode == 'es' ? 'en' : 'es',
                          ),
                        ),
                        icon: const Icon(Icons.translate),
                        label: Text(l.language),
                      ),
                      DropdownButton<Color>(
                        key: const Key('accent-picker'),
                        value: widget.accent,
                        hint: Text(l.accent),
                        items: [
                          DropdownMenuItem(
                            value: const Color(0xFF5F85C2),
                            child: Text(l.blueAccent),
                          ),
                          DropdownMenuItem(
                            value: const Color(0xFF59A849),
                            child: Text(l.greenAccent),
                          ),
                          DropdownMenuItem(
                            value: const Color(0xFFBA7DBD),
                            child: Text(l.purpleAccent),
                          ),
                        ],
                        onChanged: (value) {
                          if (value != null) widget.onAccentChanged(value);
                        },
                      ),
                    ],
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(l.tintCategoryIcons),
                    value: _tintCategoryIcons,
                    onChanged: (value) =>
                        setState(() => _tintCategoryIcons = value),
                  ),
                  const SizedBox(height: 24),
                  LayoutBuilder(
                    builder: (context, constraints) =>
                        constraints.maxWidth >= 850
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(flex: 3, child: transactions),
                              const SizedBox(width: 20),
                              Expanded(flex: 2, child: chart),
                            ],
                          )
                        : Column(
                            children: [
                              transactions,
                              const SizedBox(height: 20),
                              chart,
                            ],
                          ),
                  ),
                  const SizedBox(height: 20),
                  _panel(context, l.themePreview, const ThemePreview()),
                  const SizedBox(height: 20),
                  _panel(
                    context,
                    l.fadePreview,
                    Column(
                      children: [
                        FadeIn(
                          key: ValueKey(_animationRevision),
                          child: TransactionCard(
                            model: cards.first,
                            preferences: _preferences,
                            tintCategoryIcon: _tintCategoryIcons,
                            onEdit: () => _previewAction(l.editTransaction),
                            onDuplicate: () =>
                                _previewAction(l.duplicateTransaction),
                            onDelete: () => _previewAction(l.deleteTransaction),
                          ),
                        ),
                        TextButton.icon(
                          onPressed: () => setState(() => _animationRevision++),
                          icon: const Icon(Icons.replay),
                          label: Text(l.replayAnimation),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _previewAction(String action) => ScaffoldMessenger.of(context)
      .showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).actionPreview(action)),
        ),
      );

  Widget _panel(BuildContext context, String title, Widget child) => SizedBox(
    width: double.infinity,
    child: Material(
      color: MonetaeColors.of(context).card,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    ),
  );
}
