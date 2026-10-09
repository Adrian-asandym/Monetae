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

  @override
  String get cardSettings => 'Card details';

  @override
  String get showDate => 'Date groups';

  @override
  String get showTime => 'Time';

  @override
  String get showNote => 'Note';

  @override
  String get showTags => 'Tags';

  @override
  String get showAccount => 'Account';

  @override
  String get showActions => 'Actions';

  @override
  String get editTransaction => 'Edit';

  @override
  String get duplicateTransaction => 'Duplicate';

  @override
  String get deleteTransaction => 'Delete';

  @override
  String get tintCategoryIcons => 'Tint custom icons';

  @override
  String actionPreview(String action) {
    return 'Preview: $action';
  }

  @override
  String get sampleLoanParty => 'Example person';

  @override
  String get loginTitle => 'Welcome to Monetae';

  @override
  String get loginSubtitle => 'Your finances, all in one place.';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get signIn => 'Sign in';

  @override
  String get signOut => 'Sign out';

  @override
  String get sessionRequired => 'Sign in to continue.';

  @override
  String get requestForbidden =>
      'The request could not be verified. Reload and try again.';

  @override
  String get requestConflict => 'The data has changed. Reload and try again.';

  @override
  String get requestInvalid => 'Check your details and try again.';

  @override
  String get tooManyAttempts => 'Too many attempts. Wait before trying again.';

  @override
  String get connectionError => 'Could not connect to the server.';

  @override
  String get loadMore => 'Load more';

  @override
  String get retry => 'Try again';

  @override
  String get refresh => 'Refresh';

  @override
  String get emptyTransactions => 'No transactions yet.';

  @override
  String get demo => 'View demo';

  @override
  String get backToApp => 'Back to Monetae';

  @override
  String get savingPreferences => 'Saving preferences…';

  @override
  String get unavailableAccount => 'Account unavailable';

  @override
  String get unavailableTag => 'Tag unavailable';

  @override
  String get transfer => 'Transfer';

  @override
  String currencyAmount(String currency, String amount) {
    return '$currency $amount';
  }
}
