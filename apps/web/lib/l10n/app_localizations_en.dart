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
  String get dollarAccount => 'Sample dollar account';

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
  String get home => 'Home';

  @override
  String get cashFlow => 'Income and expenses';

  @override
  String get categoryDistribution => 'Categories';

  @override
  String get uncategorized => 'Uncategorized';

  @override
  String get emptyReports => 'There are no reports for this period yet.';

  @override
  String get unconvertedNotice =>
      'Some movements have no historical exchange rate and are excluded from converted totals.';

  @override
  String get previousMonth => 'Previous month';

  @override
  String get nextMonth => 'Next month';

  @override
  String get periodTotals => 'Period totals';

  @override
  String get budgets => 'Budgets';

  @override
  String get goals => 'Goals';

  @override
  String get budgetGoalDemo => 'Budgets and goals';

  @override
  String get emptyBudgets => 'No budgets yet.';

  @override
  String get emptyGoals => 'No goals yet.';

  @override
  String get createBudget => 'Create budget';

  @override
  String get createGoal => 'Create goal';

  @override
  String get dailyBudget => 'Daily';

  @override
  String get weeklyBudget => 'Weekly';

  @override
  String get monthlyBudget => 'Monthly';

  @override
  String get customBudget => 'Custom';

  @override
  String get savingsGoal => 'Savings goal';

  @override
  String get spendingGoal => 'Spending goal';

  @override
  String get goalComplete => 'Completed';

  @override
  String get progress => 'Progress';

  @override
  String get today => 'Today';

  @override
  String get horizontalList => 'Horizontal list';

  @override
  String get verticalList => 'Vertical list';

  @override
  String get showEmptyLists => 'Show empty lists';

  @override
  String get sampleFoodBudget => 'Food';

  @override
  String get sampleTravelBudget => 'Travel';

  @override
  String get sampleHomeBudget => 'Home';

  @override
  String get sampleSavingsGoal => 'Emergency fund';

  @override
  String get sampleSpendingGoal => 'New laptop';

  @override
  String get sampleHolidayGoal => 'Holiday';

  @override
  String budgetLeft(String amount, String total) {
    return '$amount left of $total';
  }

  @override
  String budgetOver(String amount, String total) {
    return '$amount over $total';
  }

  @override
  String budgetSpent(String amount, String total) {
    return 'Spent: $amount / $total';
  }

  @override
  String goalAmounts(String amount, String total) {
    return '$amount / $total';
  }

  @override
  String goalDue(String date) {
    return 'Due $date';
  }

  @override
  String convertedTotal(String amount) {
    return 'Converted total: $amount';
  }

  @override
  String get more => 'More';

  @override
  String get accounts => 'Accounts';

  @override
  String get emptyAccounts => 'No accounts yet.';

  @override
  String get defaultAccount => 'Default account';

  @override
  String get homeGreeting => 'Hello!';

  @override
  String get goodMorning => 'Good morning';

  @override
  String get goodAfternoon => 'Good afternoon';

  @override
  String get goodEvening => 'Good evening';

  @override
  String get viewAllTransactions => 'View all transactions';

  @override
  String get latestTransactions => 'Latest transactions';

  @override
  String get cumulativeCashFlow => 'Cumulative cash flow';

  @override
  String get addTransaction => 'Add transaction';

  @override
  String get comingSoon => 'Coming soon';

  @override
  String get theme => 'Theme';

  @override
  String get systemTheme => 'System theme';

  @override
  String accountTransactionCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count transactions',
      one: '1 transaction',
    );
    return '$_temp0';
  }

  @override
  String get transactionAmount => 'Amount';

  @override
  String get transactionCategory => 'Category (optional)';

  @override
  String get transactionAccount => 'Account';

  @override
  String get transactionTitle => 'Title (optional)';

  @override
  String get transactionNote => 'Note (optional)';

  @override
  String get transactionPosted => 'Posted';

  @override
  String get transactionScheduled => 'Scheduled · future date';

  @override
  String get limaTimezone => 'Lima time · UTC−5';

  @override
  String get exchangeRate => 'Manual exchange rate';

  @override
  String manualRateHint(String fromSymbol, String baseSymbol) {
    return 'For 1 $fromSymbol, how much in $baseSymbol?';
  }

  @override
  String get positiveAmountRequired =>
      'Enter an amount greater than 0 (up to 2 decimals).';

  @override
  String get accountRequired => 'Choose an active account.';

  @override
  String get positiveRateRequired =>
      'Enter a rate greater than 0 (up to 6 decimals).';

  @override
  String get saveTransaction => 'Save transaction';

  @override
  String get savingTransaction => 'Saving…';

  @override
  String get transactionSaved => 'Transaction saved';

  @override
  String get deleteDigit => 'Delete digit; hold to clear all';

  @override
  String get decimalPoint => 'Decimal point';

  @override
  String budgetCanSpendPerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days more days',
      one: '1 more day',
    );
    return 'You can spend $amount/day for $_temp0';
  }

  @override
  String budgetMustSavePerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days more days',
      one: '1 more day',
    );
    return 'You need to save $amount/day for $_temp0';
  }

  @override
  String goalPerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days days',
      one: '1 day',
    );
    return '$amount/day for $_temp0';
  }

  @override
  String get goalReached => 'Goal reached';

  @override
  String get goalOverdue => 'Goal overdue';

  @override
  String get addGoalLabel => 'Goal';

  @override
  String get addBudgetLabel => 'Budget';
}
