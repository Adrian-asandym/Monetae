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
  String get formEnterAmount => 'Enter The Amount';

  @override
  String get formSetAmount => 'Set amount';

  @override
  String get formDivide => 'Divide';

  @override
  String get formMultiply => 'Multiply';

  @override
  String get formSubtract => 'Subtract';

  @override
  String get formAdd => 'Add';

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
  String get decimalPoint => 'Decimal separator';

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
  String get addGoal => 'Add goal';

  @override
  String get goalName => 'Goal name';

  @override
  String get goalNameRequired => 'Enter a name for the goal.';

  @override
  String get goalSaving => 'Savings';

  @override
  String get goalSpending => 'Spending';

  @override
  String get goalTargetAmount => 'Target amount';

  @override
  String get goalAmountRequired => 'Enter an amount greater than zero.';

  @override
  String get goalDueDate => 'Due date';

  @override
  String get goalNoDueDate => 'No due date';

  @override
  String get goalClearDueDate => 'Clear due date';

  @override
  String get addBudgetLabel => 'Budget';

  @override
  String get editHome => 'Edit';

  @override
  String get formAddMenuTitle => 'Add Transaction';

  @override
  String get formEditMenuTitle => 'Edit Transaction';

  @override
  String get formSettingTransferTitle => 'Balance transfer tab';

  @override
  String get formSettingTransferSubtitle =>
      'On the \'Add new transaction\' page';

  @override
  String get formSettingAttachmentTitle => 'Add attachments button';

  @override
  String get formSettingAttachmentSubtitle => 'Show below the notes section';

  @override
  String get formSettingAutoTitleTitle => 'Add titles automatically';

  @override
  String get formSettingAutoTitleSubtitle => 'When a transaction is created';

  @override
  String get formSettingInitialInputTitle => 'Initial input prompts';

  @override
  String get formSettingInitialInputSubtitle =>
      'When adding a transaction for the first time';

  @override
  String get formTransfer => 'Transfer';

  @override
  String get formTypeDefault => 'Default';

  @override
  String get formTypeUpcoming => 'Upcoming';

  @override
  String get formTypeSubscription => 'Subscription';

  @override
  String get formTypeRepetitive => 'Repetitive';

  @override
  String get formTypeLend => 'Lend';

  @override
  String get formTypeBorrow => 'Borrow';

  @override
  String get formTypeInfo => 'Transaction types';

  @override
  String get formAllAccounts => 'All accounts';

  @override
  String get formAccountSheetTitle => 'Select Account';

  @override
  String get formNoBudget => 'No budget';

  @override
  String get formNoGoal => 'No goal';

  @override
  String get formNoLoan => 'No loan';

  @override
  String get formCreateBudget => 'Create budget';

  @override
  String get formCreateGoal => 'Create goal';

  @override
  String get formTitleHint => 'Title';

  @override
  String get formEnterTitle => 'Enter A Title';

  @override
  String get formChooseDate => 'Choose date';

  @override
  String get formNotesHint => 'Notes';

  @override
  String get formAddAttachment => 'Add an attachment';

  @override
  String get formMoreOptions => 'More options';

  @override
  String get formIncludeAmount => 'Include amount';

  @override
  String get formExcludeBudget => 'Exclude from budget';

  @override
  String get formSelectCategory => 'Select a category';

  @override
  String get formCategorySheetTitle => 'Select A Category';

  @override
  String get formMenu => 'More actions';

  @override
  String get formEditTitle => 'Edit transaction';

  @override
  String get formTypeSheetTitle => 'Select The Transaction Type';

  @override
  String get formTypeUnpaid => 'A transaction that is not paid';

  @override
  String get formTypeNotInTotal =>
      'Does not count towards your total unless marked as \'Paid\' or \'Deposited\'';

  @override
  String get formTypeSubscriptionDescription =>
      'Recurring transaction displayed on the subscriptions page';

  @override
  String get formTypeNextGenerated =>
      'Next transaction generated when the current one is marked as \"Paid\" or \"Deposited\"';

  @override
  String get formTypeRepetitiveDescription => 'Recurring transaction';

  @override
  String get formTypeLendDescription => 'A transaction you lent';

  @override
  String get formTypeLendCashFlow =>
      'Negative cash flow until marked as \'Collected\'';

  @override
  String get formTypeBorrowDescription => 'A transaction borrowed from someone';

  @override
  String get formTypeBorrowCashFlow =>
      'Positive cash flow until marked as \'Settled\'';

  @override
  String get formTypeHelp =>
      'Mark a special transaction by tapping the action button on the transaction entry';

  @override
  String get formTypeNotice =>
      'Not yet available: it will be saved as a normal transaction';

  @override
  String get transferBalanceTitle => 'Transfer balance';

  @override
  String get transferBalanceInfo =>
      'Transfer an amount from one account to another. A transfer creates two \"Balance correction\" transactions: one \"account outflow\" and one \"account inflow\". Each is an independent transaction and can be edited at any time from the transaction list.';

  @override
  String get transferCorrectionCategory => 'Balance Correction';

  @override
  String get transactionResourceReadOnly =>
      'Read only: edit this transaction from its transfer or loan.';

  @override
  String get transactionCorrectionLocked =>
      'The kind and category of a balance correction cannot be changed.';

  @override
  String get filterTransactionCategory => 'Filter by category';

  @override
  String get transferConfirm => 'Transfer amount';

  @override
  String get transferRates => 'Exchange rates';

  @override
  String get transferSwap => 'Swap accounts';

  @override
  String get transferClear => 'Clear amount';

  @override
  String get transferArrivalSame => 'Arrival: same as departure';

  @override
  String transferArrivalLabel(String date) {
    return 'Arrival: $date';
  }

  @override
  String get transferArrivalReset => 'Same as departure';

  @override
  String get transferInfoLabel => 'About transferring balance';

  @override
  String get transferOk => 'OK';

  @override
  String get transferRateSheetTitle => 'Exchange Rate';

  @override
  String transferRateSuggested(String date) {
    return 'Suggested · your last purchase ($date)';
  }

  @override
  String get transferRateManual => 'Manual';

  @override
  String get transferRateInverted => 'Opposite direction · inverted rate';

  @override
  String get transferRateLoading => 'Looking for a suggested rate…';

  @override
  String get transferRateApply => 'Apply';

  @override
  String get transferRateUseSuggested => 'Use suggested';

  @override
  String get transferRateViewAll => 'View all exchange rates';

  @override
  String get addAccountLabel => 'Account';

  @override
  String get addAccount => 'Add account';

  @override
  String get accountName => 'Name';

  @override
  String get accountNameRequired => 'Enter an account name.';

  @override
  String get accountColor => 'Color';

  @override
  String get accountCurrency => 'Currency';

  @override
  String get accountStartingAt => 'Starting at';

  @override
  String get accountDuplicateName =>
      'An account with this name already exists. Choose another name.';

  @override
  String get accountNegativeBalance => 'Negative balance';

  @override
  String get accountBalanceInvalid => 'Enter a valid balance.';

  @override
  String accountColorOption(int number) {
    return 'Color $number';
  }
}
