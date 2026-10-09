// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Monetae';

  @override
  String get spikeTitle => 'Monetae components';

  @override
  String get syntheticData => 'Preview · synthetic data';

  @override
  String get transactions => 'Transactions';

  @override
  String get categoryChart => 'Spending by category';

  @override
  String get themePreview => 'Color palette';

  @override
  String get lightTheme => 'Light theme';

  @override
  String get darkTheme => 'Dark theme';

  @override
  String get language => 'Language';

  @override
  String get accent => 'Accent color';

  @override
  String get blueAccent => 'Blue';

  @override
  String get greenAccent => 'Green';

  @override
  String get purpleAccent => 'Purple';

  @override
  String get income => 'Income';

  @override
  String get expense => 'Expense';

  @override
  String get scheduled => 'Scheduled';

  @override
  String get loanMovement => 'Loan movement';

  @override
  String get sampleAccount => 'Sample cash account';

  @override
  String get dollarAccount => 'Sample USD account';

  @override
  String get foodCategory => 'Food';

  @override
  String get workCategory => 'Work';

  @override
  String get transportCategory => 'Transport';

  @override
  String get homeCategory => 'Home';

  @override
  String get sampleLunch => 'Sample lunch';

  @override
  String get sampleNote => 'Synthetic note for reviewing the component.';

  @override
  String get sampleWork => 'Sample work';

  @override
  String get sampleLoan => 'Sample loan payment';

  @override
  String get sampleUpcoming => 'Sample upcoming payment';

  @override
  String get sampleTag => 'Sample';

  @override
  String get emptyChart => 'No data';

  @override
  String get chartTotal => 'Sample total';

  @override
  String get selectionHint => 'Select a category';

  @override
  String get allCategories => 'All categories';

  @override
  String get fadePreview => 'Animated entry';

  @override
  String get replayAnimation => 'Replay animation';

  @override
  String get compact => 'Compact view';

  @override
  String cardSubtitle(String category, String account) {
    return '$category · $account';
  }

  @override
  String penAmount(String amount) {
    return 'S/ $amount';
  }

  @override
  String usdAmount(String amount) {
    return 'US\$ $amount';
  }

  @override
  String percent(String value) {
    return '$value%';
  }

  @override
  String get themeCard => 'Surface';

  @override
  String get themeBackground => 'Background';
}
