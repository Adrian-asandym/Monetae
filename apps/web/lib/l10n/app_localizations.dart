import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_es.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('es'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In es, this message translates to:
  /// **'Monetae'**
  String get appTitle;

  /// No description provided for @spikeTitle.
  ///
  /// In es, this message translates to:
  /// **'Componentes de Monetae'**
  String get spikeTitle;

  /// No description provided for @syntheticData.
  ///
  /// In es, this message translates to:
  /// **'Vista de prueba · datos sintéticos'**
  String get syntheticData;

  /// No description provided for @transactions.
  ///
  /// In es, this message translates to:
  /// **'Transacciones'**
  String get transactions;

  /// No description provided for @categoryChart.
  ///
  /// In es, this message translates to:
  /// **'Gastos por categoría'**
  String get categoryChart;

  /// No description provided for @themePreview.
  ///
  /// In es, this message translates to:
  /// **'Paleta de colores'**
  String get themePreview;

  /// No description provided for @lightTheme.
  ///
  /// In es, this message translates to:
  /// **'Tema claro'**
  String get lightTheme;

  /// No description provided for @darkTheme.
  ///
  /// In es, this message translates to:
  /// **'Tema oscuro'**
  String get darkTheme;

  /// No description provided for @language.
  ///
  /// In es, this message translates to:
  /// **'Idioma'**
  String get language;

  /// No description provided for @accent.
  ///
  /// In es, this message translates to:
  /// **'Color de acento'**
  String get accent;

  /// No description provided for @blueAccent.
  ///
  /// In es, this message translates to:
  /// **'Azul'**
  String get blueAccent;

  /// No description provided for @greenAccent.
  ///
  /// In es, this message translates to:
  /// **'Verde'**
  String get greenAccent;

  /// No description provided for @purpleAccent.
  ///
  /// In es, this message translates to:
  /// **'Morado'**
  String get purpleAccent;

  /// No description provided for @income.
  ///
  /// In es, this message translates to:
  /// **'Ingreso'**
  String get income;

  /// No description provided for @expense.
  ///
  /// In es, this message translates to:
  /// **'Gasto'**
  String get expense;

  /// No description provided for @scheduled.
  ///
  /// In es, this message translates to:
  /// **'Programada'**
  String get scheduled;

  /// No description provided for @loanMovement.
  ///
  /// In es, this message translates to:
  /// **'Movimiento de préstamo'**
  String get loanMovement;

  /// No description provided for @sampleAccount.
  ///
  /// In es, this message translates to:
  /// **'Efectivo de prueba'**
  String get sampleAccount;

  /// No description provided for @dollarAccount.
  ///
  /// In es, this message translates to:
  /// **'Cuenta en dólares de prueba'**
  String get dollarAccount;

  /// No description provided for @foodCategory.
  ///
  /// In es, this message translates to:
  /// **'Alimentación'**
  String get foodCategory;

  /// No description provided for @workCategory.
  ///
  /// In es, this message translates to:
  /// **'Trabajo'**
  String get workCategory;

  /// No description provided for @transportCategory.
  ///
  /// In es, this message translates to:
  /// **'Transporte'**
  String get transportCategory;

  /// No description provided for @homeCategory.
  ///
  /// In es, this message translates to:
  /// **'Hogar'**
  String get homeCategory;

  /// No description provided for @sampleLunch.
  ///
  /// In es, this message translates to:
  /// **'Almuerzo de ejemplo'**
  String get sampleLunch;

  /// No description provided for @sampleNote.
  ///
  /// In es, this message translates to:
  /// **'Nota sintética para revisar el componente.'**
  String get sampleNote;

  /// No description provided for @sampleWork.
  ///
  /// In es, this message translates to:
  /// **'Trabajo de ejemplo'**
  String get sampleWork;

  /// No description provided for @sampleLoan.
  ///
  /// In es, this message translates to:
  /// **'Cobro de préstamo de ejemplo'**
  String get sampleLoan;

  /// No description provided for @sampleUpcoming.
  ///
  /// In es, this message translates to:
  /// **'Pago próximo de ejemplo'**
  String get sampleUpcoming;

  /// No description provided for @sampleTag.
  ///
  /// In es, this message translates to:
  /// **'Ejemplo'**
  String get sampleTag;

  /// No description provided for @emptyChart.
  ///
  /// In es, this message translates to:
  /// **'Sin datos'**
  String get emptyChart;

  /// No description provided for @chartTotal.
  ///
  /// In es, this message translates to:
  /// **'Total de ejemplo'**
  String get chartTotal;

  /// No description provided for @selectionHint.
  ///
  /// In es, this message translates to:
  /// **'Selecciona una categoría'**
  String get selectionHint;

  /// No description provided for @allCategories.
  ///
  /// In es, this message translates to:
  /// **'Todas las categorías'**
  String get allCategories;

  /// No description provided for @fadePreview.
  ///
  /// In es, this message translates to:
  /// **'Entrada animada'**
  String get fadePreview;

  /// No description provided for @replayAnimation.
  ///
  /// In es, this message translates to:
  /// **'Repetir animación'**
  String get replayAnimation;

  /// No description provided for @compact.
  ///
  /// In es, this message translates to:
  /// **'Vista compacta'**
  String get compact;

  /// No description provided for @cardSubtitle.
  ///
  /// In es, this message translates to:
  /// **'{category} · {account}'**
  String cardSubtitle(String category, String account);

  /// No description provided for @percent.
  ///
  /// In es, this message translates to:
  /// **'{value}%'**
  String percent(String value);

  /// No description provided for @themeCard.
  ///
  /// In es, this message translates to:
  /// **'Superficie'**
  String get themeCard;

  /// No description provided for @themeBackground.
  ///
  /// In es, this message translates to:
  /// **'Fondo'**
  String get themeBackground;

  /// No description provided for @cardSettings.
  ///
  /// In es, this message translates to:
  /// **'Detalles de la tarjeta'**
  String get cardSettings;

  /// No description provided for @showDate.
  ///
  /// In es, this message translates to:
  /// **'Fecha por día'**
  String get showDate;

  /// No description provided for @showTime.
  ///
  /// In es, this message translates to:
  /// **'Hora'**
  String get showTime;

  /// No description provided for @showNote.
  ///
  /// In es, this message translates to:
  /// **'Nota'**
  String get showNote;

  /// No description provided for @showTags.
  ///
  /// In es, this message translates to:
  /// **'Etiquetas'**
  String get showTags;

  /// No description provided for @showAccount.
  ///
  /// In es, this message translates to:
  /// **'Cuenta'**
  String get showAccount;

  /// No description provided for @showActions.
  ///
  /// In es, this message translates to:
  /// **'Acciones'**
  String get showActions;

  /// No description provided for @editTransaction.
  ///
  /// In es, this message translates to:
  /// **'Editar'**
  String get editTransaction;

  /// No description provided for @duplicateTransaction.
  ///
  /// In es, this message translates to:
  /// **'Duplicar'**
  String get duplicateTransaction;

  /// No description provided for @deleteTransaction.
  ///
  /// In es, this message translates to:
  /// **'Borrar'**
  String get deleteTransaction;

  /// No description provided for @tintCategoryIcons.
  ///
  /// In es, this message translates to:
  /// **'Teñir íconos propios'**
  String get tintCategoryIcons;

  /// No description provided for @actionPreview.
  ///
  /// In es, this message translates to:
  /// **'Vista de prueba: {action}'**
  String actionPreview(String action);

  /// No description provided for @sampleLoanParty.
  ///
  /// In es, this message translates to:
  /// **'Persona de prueba'**
  String get sampleLoanParty;

  /// No description provided for @loginTitle.
  ///
  /// In es, this message translates to:
  /// **'Bienvenido a Monetae'**
  String get loginTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Tus finanzas, en un solo lugar.'**
  String get loginSubtitle;

  /// No description provided for @email.
  ///
  /// In es, this message translates to:
  /// **'Correo electrónico'**
  String get email;

  /// No description provided for @password.
  ///
  /// In es, this message translates to:
  /// **'Contraseña'**
  String get password;

  /// No description provided for @signIn.
  ///
  /// In es, this message translates to:
  /// **'Iniciar sesión'**
  String get signIn;

  /// No description provided for @signOut.
  ///
  /// In es, this message translates to:
  /// **'Cerrar sesión'**
  String get signOut;

  /// No description provided for @sessionRequired.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión para continuar.'**
  String get sessionRequired;

  /// No description provided for @requestForbidden.
  ///
  /// In es, this message translates to:
  /// **'No se pudo verificar la solicitud. Recarga e inténtalo de nuevo.'**
  String get requestForbidden;

  /// No description provided for @requestConflict.
  ///
  /// In es, this message translates to:
  /// **'Los datos han cambiado. Recarga e inténtalo de nuevo.'**
  String get requestConflict;

  /// No description provided for @requestInvalid.
  ///
  /// In es, this message translates to:
  /// **'Revisa los datos e inténtalo de nuevo.'**
  String get requestInvalid;

  /// No description provided for @tooManyAttempts.
  ///
  /// In es, this message translates to:
  /// **'Demasiados intentos. Espera antes de volver a intentarlo.'**
  String get tooManyAttempts;

  /// No description provided for @connectionError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo conectar con el servidor.'**
  String get connectionError;

  /// No description provided for @loadMore.
  ///
  /// In es, this message translates to:
  /// **'Cargar más'**
  String get loadMore;

  /// No description provided for @retry.
  ///
  /// In es, this message translates to:
  /// **'Reintentar'**
  String get retry;

  /// No description provided for @refresh.
  ///
  /// In es, this message translates to:
  /// **'Actualizar'**
  String get refresh;

  /// No description provided for @emptyTransactions.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay transacciones.'**
  String get emptyTransactions;

  /// No description provided for @demo.
  ///
  /// In es, this message translates to:
  /// **'Ver demostración'**
  String get demo;

  /// No description provided for @backToApp.
  ///
  /// In es, this message translates to:
  /// **'Volver a Monetae'**
  String get backToApp;

  /// No description provided for @savingPreferences.
  ///
  /// In es, this message translates to:
  /// **'Guardando preferencias…'**
  String get savingPreferences;

  /// No description provided for @unavailableAccount.
  ///
  /// In es, this message translates to:
  /// **'Cuenta no disponible'**
  String get unavailableAccount;

  /// No description provided for @unavailableTag.
  ///
  /// In es, this message translates to:
  /// **'Etiqueta no disponible'**
  String get unavailableTag;

  /// No description provided for @transfer.
  ///
  /// In es, this message translates to:
  /// **'Transferencia'**
  String get transfer;

  /// No description provided for @home.
  ///
  /// In es, this message translates to:
  /// **'Inicio'**
  String get home;

  /// No description provided for @cashFlow.
  ///
  /// In es, this message translates to:
  /// **'Ingresos y gastos'**
  String get cashFlow;

  /// No description provided for @categoryDistribution.
  ///
  /// In es, this message translates to:
  /// **'Categorías'**
  String get categoryDistribution;

  /// No description provided for @categoryDetailTitle.
  ///
  /// In es, this message translates to:
  /// **'Detalle de categorías'**
  String get categoryDetailTitle;

  /// No description provided for @uncategorized.
  ///
  /// In es, this message translates to:
  /// **'Sin categoría'**
  String get uncategorized;

  /// No description provided for @emptyReports.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay reportes para este periodo.'**
  String get emptyReports;

  /// No description provided for @unconvertedNotice.
  ///
  /// In es, this message translates to:
  /// **'Algunos movimientos no tienen tasa histórica y quedan fuera de los totales convertidos.'**
  String get unconvertedNotice;

  /// No description provided for @previousMonth.
  ///
  /// In es, this message translates to:
  /// **'Mes anterior'**
  String get previousMonth;

  /// No description provided for @nextMonth.
  ///
  /// In es, this message translates to:
  /// **'Mes siguiente'**
  String get nextMonth;

  /// No description provided for @periodTotals.
  ///
  /// In es, this message translates to:
  /// **'Totales del periodo'**
  String get periodTotals;

  /// No description provided for @budgets.
  ///
  /// In es, this message translates to:
  /// **'Presupuestos'**
  String get budgets;

  /// No description provided for @goals.
  ///
  /// In es, this message translates to:
  /// **'Objetivos'**
  String get goals;

  /// No description provided for @budgetGoalDemo.
  ///
  /// In es, this message translates to:
  /// **'Presupuestos y objetivos'**
  String get budgetGoalDemo;

  /// No description provided for @emptyBudgets.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay presupuestos.'**
  String get emptyBudgets;

  /// No description provided for @emptyGoals.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay objetivos.'**
  String get emptyGoals;

  /// No description provided for @createBudget.
  ///
  /// In es, this message translates to:
  /// **'Crear presupuesto'**
  String get createBudget;

  /// No description provided for @createGoal.
  ///
  /// In es, this message translates to:
  /// **'Crear objetivo'**
  String get createGoal;

  /// No description provided for @dailyBudget.
  ///
  /// In es, this message translates to:
  /// **'Diario'**
  String get dailyBudget;

  /// No description provided for @weeklyBudget.
  ///
  /// In es, this message translates to:
  /// **'Semanal'**
  String get weeklyBudget;

  /// No description provided for @monthlyBudget.
  ///
  /// In es, this message translates to:
  /// **'Mensual'**
  String get monthlyBudget;

  /// No description provided for @customBudget.
  ///
  /// In es, this message translates to:
  /// **'Personalizado'**
  String get customBudget;

  /// No description provided for @savingsGoal.
  ///
  /// In es, this message translates to:
  /// **'Objetivo de ahorro'**
  String get savingsGoal;

  /// No description provided for @spendingGoal.
  ///
  /// In es, this message translates to:
  /// **'Objetivo de gasto'**
  String get spendingGoal;

  /// No description provided for @goalComplete.
  ///
  /// In es, this message translates to:
  /// **'Completado'**
  String get goalComplete;

  /// No description provided for @progress.
  ///
  /// In es, this message translates to:
  /// **'Progreso'**
  String get progress;

  /// No description provided for @today.
  ///
  /// In es, this message translates to:
  /// **'Hoy'**
  String get today;

  /// No description provided for @horizontalList.
  ///
  /// In es, this message translates to:
  /// **'Lista horizontal'**
  String get horizontalList;

  /// No description provided for @verticalList.
  ///
  /// In es, this message translates to:
  /// **'Lista vertical'**
  String get verticalList;

  /// No description provided for @showEmptyLists.
  ///
  /// In es, this message translates to:
  /// **'Mostrar listas vacías'**
  String get showEmptyLists;

  /// No description provided for @sampleFoodBudget.
  ///
  /// In es, this message translates to:
  /// **'Alimentación'**
  String get sampleFoodBudget;

  /// No description provided for @sampleTravelBudget.
  ///
  /// In es, this message translates to:
  /// **'Viaje'**
  String get sampleTravelBudget;

  /// No description provided for @sampleHomeBudget.
  ///
  /// In es, this message translates to:
  /// **'Hogar'**
  String get sampleHomeBudget;

  /// No description provided for @sampleSavingsGoal.
  ///
  /// In es, this message translates to:
  /// **'Fondo de emergencia'**
  String get sampleSavingsGoal;

  /// No description provided for @sampleSpendingGoal.
  ///
  /// In es, this message translates to:
  /// **'Nueva laptop'**
  String get sampleSpendingGoal;

  /// No description provided for @sampleHolidayGoal.
  ///
  /// In es, this message translates to:
  /// **'Vacaciones'**
  String get sampleHolidayGoal;

  /// No description provided for @budgetLeft.
  ///
  /// In es, this message translates to:
  /// **'{amount} restante de {total}'**
  String budgetLeft(String amount, String total);

  /// No description provided for @budgetOver.
  ///
  /// In es, this message translates to:
  /// **'{amount} excedido de {total}'**
  String budgetOver(String amount, String total);

  /// No description provided for @budgetSpent.
  ///
  /// In es, this message translates to:
  /// **'Gastado: {amount} / {total}'**
  String budgetSpent(String amount, String total);

  /// No description provided for @goalAmounts.
  ///
  /// In es, this message translates to:
  /// **'{amount} / {total}'**
  String goalAmounts(String amount, String total);

  /// No description provided for @goalDue.
  ///
  /// In es, this message translates to:
  /// **'Hasta {date}'**
  String goalDue(String date);

  /// No description provided for @convertedTotal.
  ///
  /// In es, this message translates to:
  /// **'Total convertido: {amount}'**
  String convertedTotal(String amount);

  /// No description provided for @more.
  ///
  /// In es, this message translates to:
  /// **'Más'**
  String get more;

  /// No description provided for @accounts.
  ///
  /// In es, this message translates to:
  /// **'Cuentas'**
  String get accounts;

  /// No description provided for @emptyAccounts.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay cuentas.'**
  String get emptyAccounts;

  /// No description provided for @defaultAccount.
  ///
  /// In es, this message translates to:
  /// **'Cuenta por defecto'**
  String get defaultAccount;

  /// No description provided for @homeGreeting.
  ///
  /// In es, this message translates to:
  /// **'¡Hola!'**
  String get homeGreeting;

  /// No description provided for @goodMorning.
  ///
  /// In es, this message translates to:
  /// **'Buenos días'**
  String get goodMorning;

  /// No description provided for @goodAfternoon.
  ///
  /// In es, this message translates to:
  /// **'Buenas tardes'**
  String get goodAfternoon;

  /// No description provided for @goodEvening.
  ///
  /// In es, this message translates to:
  /// **'Buenas noches'**
  String get goodEvening;

  /// No description provided for @viewAllTransactions.
  ///
  /// In es, this message translates to:
  /// **'Ver todas las transacciones'**
  String get viewAllTransactions;

  /// No description provided for @latestTransactions.
  ///
  /// In es, this message translates to:
  /// **'Últimas transacciones'**
  String get latestTransactions;

  /// No description provided for @cumulativeCashFlow.
  ///
  /// In es, this message translates to:
  /// **'Evolución acumulada'**
  String get cumulativeCashFlow;

  /// No description provided for @addTransaction.
  ///
  /// In es, this message translates to:
  /// **'Agregar transacción'**
  String get addTransaction;

  /// No description provided for @comingSoon.
  ///
  /// In es, this message translates to:
  /// **'Próximamente'**
  String get comingSoon;

  /// No description provided for @theme.
  ///
  /// In es, this message translates to:
  /// **'Tema'**
  String get theme;

  /// No description provided for @systemTheme.
  ///
  /// In es, this message translates to:
  /// **'Tema del sistema'**
  String get systemTheme;

  /// No description provided for @accountTransactionCount.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, =1{1 transacción} other{{count} transacciones}}'**
  String accountTransactionCount(int count);

  /// No description provided for @transactionAmount.
  ///
  /// In es, this message translates to:
  /// **'Importe'**
  String get transactionAmount;

  /// No description provided for @formEnterAmount.
  ///
  /// In es, this message translates to:
  /// **'Introduce El Importe'**
  String get formEnterAmount;

  /// No description provided for @formSetAmount.
  ///
  /// In es, this message translates to:
  /// **'Fijar importe'**
  String get formSetAmount;

  /// No description provided for @formDivide.
  ///
  /// In es, this message translates to:
  /// **'Dividir'**
  String get formDivide;

  /// No description provided for @formMultiply.
  ///
  /// In es, this message translates to:
  /// **'Multiplicar'**
  String get formMultiply;

  /// No description provided for @formSubtract.
  ///
  /// In es, this message translates to:
  /// **'Restar'**
  String get formSubtract;

  /// No description provided for @formAdd.
  ///
  /// In es, this message translates to:
  /// **'Sumar'**
  String get formAdd;

  /// No description provided for @transactionCategory.
  ///
  /// In es, this message translates to:
  /// **'Categoría (opcional)'**
  String get transactionCategory;

  /// No description provided for @transactionAccount.
  ///
  /// In es, this message translates to:
  /// **'Cuenta'**
  String get transactionAccount;

  /// No description provided for @transactionTitle.
  ///
  /// In es, this message translates to:
  /// **'Título (opcional)'**
  String get transactionTitle;

  /// No description provided for @transactionNote.
  ///
  /// In es, this message translates to:
  /// **'Nota (opcional)'**
  String get transactionNote;

  /// No description provided for @transactionPosted.
  ///
  /// In es, this message translates to:
  /// **'Publicada'**
  String get transactionPosted;

  /// No description provided for @transactionScheduled.
  ///
  /// In es, this message translates to:
  /// **'Programada · fecha futura'**
  String get transactionScheduled;

  /// No description provided for @limaTimezone.
  ///
  /// In es, this message translates to:
  /// **'Hora de Lima · UTC−5'**
  String get limaTimezone;

  /// No description provided for @exchangeRate.
  ///
  /// In es, this message translates to:
  /// **'Tipo de cambio manual'**
  String get exchangeRate;

  /// No description provided for @manualRateHint.
  ///
  /// In es, this message translates to:
  /// **'Por 1 {fromSymbol}, ¿cuánto en {baseSymbol}?'**
  String manualRateHint(String fromSymbol, String baseSymbol);

  /// No description provided for @positiveAmountRequired.
  ///
  /// In es, this message translates to:
  /// **'Escribe un importe mayor que 0 (hasta 2 decimales).'**
  String get positiveAmountRequired;

  /// No description provided for @accountRequired.
  ///
  /// In es, this message translates to:
  /// **'Elige una cuenta activa.'**
  String get accountRequired;

  /// No description provided for @positiveRateRequired.
  ///
  /// In es, this message translates to:
  /// **'Escribe una tasa mayor que 0 (hasta 6 decimales).'**
  String get positiveRateRequired;

  /// No description provided for @saveTransaction.
  ///
  /// In es, this message translates to:
  /// **'Guardar transacción'**
  String get saveTransaction;

  /// No description provided for @savingTransaction.
  ///
  /// In es, this message translates to:
  /// **'Guardando…'**
  String get savingTransaction;

  /// No description provided for @transactionSaved.
  ///
  /// In es, this message translates to:
  /// **'Transacción guardada'**
  String get transactionSaved;

  /// No description provided for @deleteDigit.
  ///
  /// In es, this message translates to:
  /// **'Borrar dígito; mantén pulsado para borrar todo'**
  String get deleteDigit;

  /// No description provided for @decimalPoint.
  ///
  /// In es, this message translates to:
  /// **'Separador decimal'**
  String get decimalPoint;

  /// No description provided for @budgetCanSpendPerDay.
  ///
  /// In es, this message translates to:
  /// **'Puedes gastar {amount}/día para {days, plural, =1{1 día más} other{{days} días más}}'**
  String budgetCanSpendPerDay(String amount, int days);

  /// No description provided for @budgetMustSavePerDay.
  ///
  /// In es, this message translates to:
  /// **'Tienes que ahorrar {amount}/día para {days, plural, =1{1 día más} other{{days} días más}}'**
  String budgetMustSavePerDay(String amount, int days);

  /// No description provided for @goalPerDay.
  ///
  /// In es, this message translates to:
  /// **'{amount}/día para {days, plural, =1{1 día} other{{days} días}}'**
  String goalPerDay(String amount, int days);

  /// No description provided for @goalReached.
  ///
  /// In es, this message translates to:
  /// **'Objetivo logrado'**
  String get goalReached;

  /// No description provided for @goalOverdue.
  ///
  /// In es, this message translates to:
  /// **'Objetivo atrasado'**
  String get goalOverdue;

  /// No description provided for @addGoalLabel.
  ///
  /// In es, this message translates to:
  /// **'Objetivo'**
  String get addGoalLabel;

  /// No description provided for @addGoal.
  ///
  /// In es, this message translates to:
  /// **'Añadir objetivo'**
  String get addGoal;

  /// No description provided for @goalName.
  ///
  /// In es, this message translates to:
  /// **'Nombre del objetivo'**
  String get goalName;

  /// No description provided for @goalNameRequired.
  ///
  /// In es, this message translates to:
  /// **'Escribe un nombre para el objetivo.'**
  String get goalNameRequired;

  /// No description provided for @goalSaving.
  ///
  /// In es, this message translates to:
  /// **'Ahorro'**
  String get goalSaving;

  /// No description provided for @goalSpending.
  ///
  /// In es, this message translates to:
  /// **'Gasto'**
  String get goalSpending;

  /// No description provided for @goalTargetAmount.
  ///
  /// In es, this message translates to:
  /// **'Importe objetivo'**
  String get goalTargetAmount;

  /// No description provided for @goalAmountRequired.
  ///
  /// In es, this message translates to:
  /// **'Introduce un importe mayor que cero.'**
  String get goalAmountRequired;

  /// No description provided for @goalDueDate.
  ///
  /// In es, this message translates to:
  /// **'Fecha límite'**
  String get goalDueDate;

  /// No description provided for @goalNoDueDate.
  ///
  /// In es, this message translates to:
  /// **'Sin fecha límite'**
  String get goalNoDueDate;

  /// No description provided for @goalClearDueDate.
  ///
  /// In es, this message translates to:
  /// **'Quitar fecha límite'**
  String get goalClearDueDate;

  /// No description provided for @addBudgetLabel.
  ///
  /// In es, this message translates to:
  /// **'Presupuesto'**
  String get addBudgetLabel;

  /// No description provided for @budgetAmount.
  ///
  /// In es, this message translates to:
  /// **'Importe'**
  String get budgetAmount;

  /// No description provided for @budgetCategories.
  ///
  /// In es, this message translates to:
  /// **'Categorías incluidas'**
  String get budgetCategories;

  /// No description provided for @budgetAllCategories.
  ///
  /// In es, this message translates to:
  /// **'Todas las categorías de gasto'**
  String get budgetAllCategories;

  /// No description provided for @budgetCategoriesDone.
  ///
  /// In es, this message translates to:
  /// **'Fijar categorías'**
  String get budgetCategoriesDone;

  /// No description provided for @addBudget.
  ///
  /// In es, this message translates to:
  /// **'Añadir presupuesto'**
  String get addBudget;

  /// No description provided for @budgetName.
  ///
  /// In es, this message translates to:
  /// **'Nombre del presupuesto'**
  String get budgetName;

  /// No description provided for @budgetNameRequired.
  ///
  /// In es, this message translates to:
  /// **'Escribe un nombre para el presupuesto.'**
  String get budgetNameRequired;

  /// No description provided for @budgetPeriod.
  ///
  /// In es, this message translates to:
  /// **'Periodo'**
  String get budgetPeriod;

  /// No description provided for @budgetDaily.
  ///
  /// In es, this message translates to:
  /// **'Diario'**
  String get budgetDaily;

  /// No description provided for @budgetWeekly.
  ///
  /// In es, this message translates to:
  /// **'Semanal'**
  String get budgetWeekly;

  /// No description provided for @budgetMonthly.
  ///
  /// In es, this message translates to:
  /// **'Mensual'**
  String get budgetMonthly;

  /// No description provided for @budgetCustom.
  ///
  /// In es, this message translates to:
  /// **'Personalizado'**
  String get budgetCustom;

  /// No description provided for @budgetStartDate.
  ///
  /// In es, this message translates to:
  /// **'Fecha de inicio'**
  String get budgetStartDate;

  /// No description provided for @budgetEndDate.
  ///
  /// In es, this message translates to:
  /// **'Fecha de fin'**
  String get budgetEndDate;

  /// No description provided for @budgetChooseEndDate.
  ///
  /// In es, this message translates to:
  /// **'Seleccionar fecha de fin'**
  String get budgetChooseEndDate;

  /// No description provided for @budgetDatesInvalid.
  ///
  /// In es, this message translates to:
  /// **'La fecha de fin debe ser igual o posterior a la de inicio.'**
  String get budgetDatesInvalid;

  /// No description provided for @budgetSelectedOnly.
  ///
  /// In es, this message translates to:
  /// **'Solo transacciones añadidas'**
  String get budgetSelectedOnly;

  /// No description provided for @budgetSelectedOnlyHint.
  ///
  /// In es, this message translates to:
  /// **'Incluye solo las transacciones asignadas a este presupuesto.'**
  String get budgetSelectedOnlyHint;

  /// No description provided for @editHome.
  ///
  /// In es, this message translates to:
  /// **'Editar'**
  String get editHome;

  /// No description provided for @editHomeTitle.
  ///
  /// In es, this message translates to:
  /// **'Editar Inicio'**
  String get editHomeTitle;

  /// No description provided for @editHomeMinimum.
  ///
  /// In es, this message translates to:
  /// **'Mantén al menos un componente visible.'**
  String get editHomeMinimum;

  /// No description provided for @editHomeReorder.
  ///
  /// In es, this message translates to:
  /// **'Reordenar {component}'**
  String editHomeReorder(String component);

  /// No description provided for @formAddMenuTitle.
  ///
  /// In es, this message translates to:
  /// **'Agregar Transacción'**
  String get formAddMenuTitle;

  /// No description provided for @formEditMenuTitle.
  ///
  /// In es, this message translates to:
  /// **'Editar Transacción'**
  String get formEditMenuTitle;

  /// No description provided for @formSettingTransferTitle.
  ///
  /// In es, this message translates to:
  /// **'Pestaña de transferencia de saldo'**
  String get formSettingTransferTitle;

  /// No description provided for @formSettingTransferSubtitle.
  ///
  /// In es, this message translates to:
  /// **'En la página \'Agregar nueva transacción\''**
  String get formSettingTransferSubtitle;

  /// No description provided for @formSettingAttachmentTitle.
  ///
  /// In es, this message translates to:
  /// **'Botón Agregar archivos adjuntos'**
  String get formSettingAttachmentTitle;

  /// No description provided for @formSettingAttachmentSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Mostrar debajo de la sección de notas'**
  String get formSettingAttachmentSubtitle;

  /// No description provided for @formSettingAutoTitleTitle.
  ///
  /// In es, this message translates to:
  /// **'Agregar títulos automáticamente'**
  String get formSettingAutoTitleTitle;

  /// No description provided for @formSettingAutoTitleSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Cuando se crea una transacción'**
  String get formSettingAutoTitleSubtitle;

  /// No description provided for @formSettingInitialInputTitle.
  ///
  /// In es, this message translates to:
  /// **'Indicaciones iniciales de entrada'**
  String get formSettingInitialInputTitle;

  /// No description provided for @formSettingInitialInputSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Al añadir una transacción por primera vez'**
  String get formSettingInitialInputSubtitle;

  /// No description provided for @formTransfer.
  ///
  /// In es, this message translates to:
  /// **'Transferir'**
  String get formTransfer;

  /// No description provided for @formTypeDefault.
  ///
  /// In es, this message translates to:
  /// **'Predeterminado'**
  String get formTypeDefault;

  /// No description provided for @formTypeUpcoming.
  ///
  /// In es, this message translates to:
  /// **'Próximamente'**
  String get formTypeUpcoming;

  /// No description provided for @formTypeSubscription.
  ///
  /// In es, this message translates to:
  /// **'Suscripción'**
  String get formTypeSubscription;

  /// No description provided for @formTypeRepetitive.
  ///
  /// In es, this message translates to:
  /// **'Repetitivo'**
  String get formTypeRepetitive;

  /// No description provided for @formTypeLend.
  ///
  /// In es, this message translates to:
  /// **'Prestar'**
  String get formTypeLend;

  /// No description provided for @formTypeBorrow.
  ///
  /// In es, this message translates to:
  /// **'Deuda'**
  String get formTypeBorrow;

  /// No description provided for @formTypeInfo.
  ///
  /// In es, this message translates to:
  /// **'Tipos de transacción'**
  String get formTypeInfo;

  /// No description provided for @formAllAccounts.
  ///
  /// In es, this message translates to:
  /// **'Todas las cuentas'**
  String get formAllAccounts;

  /// No description provided for @formAccountSheetTitle.
  ///
  /// In es, this message translates to:
  /// **'Seleccionar Cuenta'**
  String get formAccountSheetTitle;

  /// No description provided for @formNoBudget.
  ///
  /// In es, this message translates to:
  /// **'Sin presupuesto'**
  String get formNoBudget;

  /// No description provided for @formNoGoal.
  ///
  /// In es, this message translates to:
  /// **'Sin objetivo'**
  String get formNoGoal;

  /// No description provided for @formNoLoan.
  ///
  /// In es, this message translates to:
  /// **'Sin préstamo'**
  String get formNoLoan;

  /// No description provided for @formCreateBudget.
  ///
  /// In es, this message translates to:
  /// **'Crear presupuesto'**
  String get formCreateBudget;

  /// No description provided for @formCreateGoal.
  ///
  /// In es, this message translates to:
  /// **'Crear objetivo'**
  String get formCreateGoal;

  /// No description provided for @formTitleHint.
  ///
  /// In es, this message translates to:
  /// **'Título'**
  String get formTitleHint;

  /// No description provided for @formEnterTitle.
  ///
  /// In es, this message translates to:
  /// **'Escribe Un Título'**
  String get formEnterTitle;

  /// No description provided for @formChooseDate.
  ///
  /// In es, this message translates to:
  /// **'Seleccionar fecha'**
  String get formChooseDate;

  /// No description provided for @formNotesHint.
  ///
  /// In es, this message translates to:
  /// **'Notas'**
  String get formNotesHint;

  /// No description provided for @formAddAttachment.
  ///
  /// In es, this message translates to:
  /// **'Añadir un adjunto'**
  String get formAddAttachment;

  /// No description provided for @formMoreOptions.
  ///
  /// In es, this message translates to:
  /// **'Más opciones'**
  String get formMoreOptions;

  /// No description provided for @formIncludeAmount.
  ///
  /// In es, this message translates to:
  /// **'Incluir importe'**
  String get formIncludeAmount;

  /// No description provided for @formExcludeBudget.
  ///
  /// In es, this message translates to:
  /// **'Excluir del presupuesto'**
  String get formExcludeBudget;

  /// No description provided for @formSelectCategory.
  ///
  /// In es, this message translates to:
  /// **'Selecciona una categoría'**
  String get formSelectCategory;

  /// No description provided for @formCategorySheetTitle.
  ///
  /// In es, this message translates to:
  /// **'Selecciona Una Categoría'**
  String get formCategorySheetTitle;

  /// No description provided for @formMenu.
  ///
  /// In es, this message translates to:
  /// **'Más acciones'**
  String get formMenu;

  /// No description provided for @formEditTitle.
  ///
  /// In es, this message translates to:
  /// **'Editar transacción'**
  String get formEditTitle;

  /// No description provided for @formTypeSheetTitle.
  ///
  /// In es, this message translates to:
  /// **'Seleccionar El Tipo De Transacción'**
  String get formTypeSheetTitle;

  /// No description provided for @formTypeUnpaid.
  ///
  /// In es, this message translates to:
  /// **'Una transacción que no está pagada'**
  String get formTypeUnpaid;

  /// No description provided for @formTypeNotInTotal.
  ///
  /// In es, this message translates to:
  /// **'No cuenta para su total a menos que sea marcado como \'Pagado\' o \'Depositado\''**
  String get formTypeNotInTotal;

  /// No description provided for @formTypeSubscriptionDescription.
  ///
  /// In es, this message translates to:
  /// **'Transacción recurrente que se mostrará en la página de suscripciones'**
  String get formTypeSubscriptionDescription;

  /// No description provided for @formTypeNextGenerated.
  ///
  /// In es, this message translates to:
  /// **'Próxima transacción generada cuando la actual está marcada como \"Pagada\" o \"Depositada\"'**
  String get formTypeNextGenerated;

  /// No description provided for @formTypeRepetitiveDescription.
  ///
  /// In es, this message translates to:
  /// **'Transacción recurrente'**
  String get formTypeRepetitiveDescription;

  /// No description provided for @formTypeLendDescription.
  ///
  /// In es, this message translates to:
  /// **'Transacción que prestaste'**
  String get formTypeLendDescription;

  /// No description provided for @formTypeLendCashFlow.
  ///
  /// In es, this message translates to:
  /// **'Flujo de caja negativo hasta que se marque como \'Recolectado\''**
  String get formTypeLendCashFlow;

  /// No description provided for @formTypeBorrowDescription.
  ///
  /// In es, this message translates to:
  /// **'Transacción prestada de alguien'**
  String get formTypeBorrowDescription;

  /// No description provided for @formTypeBorrowCashFlow.
  ///
  /// In es, this message translates to:
  /// **'Flujo de caja positivo hasta que se marque como \'Liquidado\''**
  String get formTypeBorrowCashFlow;

  /// No description provided for @formTypeHelp.
  ///
  /// In es, this message translates to:
  /// **'Marque una transacción especial tocando el botón de acción en la entrada de la transacción'**
  String get formTypeHelp;

  /// No description provided for @formTypeNotice.
  ///
  /// In es, this message translates to:
  /// **'Aún no disponible: se guardará como transacción normal'**
  String get formTypeNotice;

  /// No description provided for @transferBalanceTitle.
  ///
  /// In es, this message translates to:
  /// **'Transferir saldo'**
  String get transferBalanceTitle;

  /// No description provided for @transferBalanceInfo.
  ///
  /// In es, this message translates to:
  /// **'Transfiere un importe de una cuenta a otra. Al realizar una transferencia, se crean dos transacciones de \"Corrección de saldo\": una de \"salida de cuenta\" y otra de \"entrada de cuenta\". Cada una es una transacción independiente y puede editarse en cualquier momento desde la lista de transacciones.'**
  String get transferBalanceInfo;

  /// No description provided for @transferCorrectionCategory.
  ///
  /// In es, this message translates to:
  /// **'Corrección De Saldo'**
  String get transferCorrectionCategory;

  /// No description provided for @transactionResourceReadOnly.
  ///
  /// In es, this message translates to:
  /// **'Solo lectura: esta transacción se edita desde su transferencia o préstamo.'**
  String get transactionResourceReadOnly;

  /// No description provided for @transactionCorrectionLocked.
  ///
  /// In es, this message translates to:
  /// **'El tipo y la categoría de una corrección de saldo no se pueden cambiar.'**
  String get transactionCorrectionLocked;

  /// No description provided for @filterTransactionCategory.
  ///
  /// In es, this message translates to:
  /// **'Filtrar por categoría'**
  String get filterTransactionCategory;

  /// No description provided for @transferConfirm.
  ///
  /// In es, this message translates to:
  /// **'Transferir cantidad'**
  String get transferConfirm;

  /// No description provided for @transferRates.
  ///
  /// In es, this message translates to:
  /// **'Tipos de cambio'**
  String get transferRates;

  /// No description provided for @transferSwap.
  ///
  /// In es, this message translates to:
  /// **'Intercambiar cuentas'**
  String get transferSwap;

  /// No description provided for @transferClear.
  ///
  /// In es, this message translates to:
  /// **'Borrar importe'**
  String get transferClear;

  /// No description provided for @transferArrivalSame.
  ///
  /// In es, this message translates to:
  /// **'Llegada: igual que la salida'**
  String get transferArrivalSame;

  /// No description provided for @transferArrivalLabel.
  ///
  /// In es, this message translates to:
  /// **'Llegada: {date}'**
  String transferArrivalLabel(String date);

  /// No description provided for @transferArrivalReset.
  ///
  /// In es, this message translates to:
  /// **'Igual que la salida'**
  String get transferArrivalReset;

  /// No description provided for @transferInfoLabel.
  ///
  /// In es, this message translates to:
  /// **'Información sobre transferir saldo'**
  String get transferInfoLabel;

  /// No description provided for @transferOk.
  ///
  /// In es, this message translates to:
  /// **'OK'**
  String get transferOk;

  /// No description provided for @transferRateSheetTitle.
  ///
  /// In es, this message translates to:
  /// **'Tipo De Cambio'**
  String get transferRateSheetTitle;

  /// No description provided for @transferRateSuggested.
  ///
  /// In es, this message translates to:
  /// **'Sugerido · tu última compra ({date})'**
  String transferRateSuggested(String date);

  /// No description provided for @transferRateManual.
  ///
  /// In es, this message translates to:
  /// **'Manual'**
  String get transferRateManual;

  /// No description provided for @transferRateInverted.
  ///
  /// In es, this message translates to:
  /// **'Dirección contraria · tasa invertida'**
  String get transferRateInverted;

  /// No description provided for @transferRateLoading.
  ///
  /// In es, this message translates to:
  /// **'Buscando una tasa sugerida…'**
  String get transferRateLoading;

  /// No description provided for @transferRateApply.
  ///
  /// In es, this message translates to:
  /// **'Aplicar'**
  String get transferRateApply;

  /// No description provided for @transferRateUseSuggested.
  ///
  /// In es, this message translates to:
  /// **'Usar sugerido'**
  String get transferRateUseSuggested;

  /// No description provided for @transferRateViewAll.
  ///
  /// In es, this message translates to:
  /// **'Ver todos los tipos de cambio'**
  String get transferRateViewAll;

  /// No description provided for @addAccountLabel.
  ///
  /// In es, this message translates to:
  /// **'Cuenta'**
  String get addAccountLabel;

  /// No description provided for @addAccount.
  ///
  /// In es, this message translates to:
  /// **'Añadir cuenta'**
  String get addAccount;

  /// No description provided for @accountName.
  ///
  /// In es, this message translates to:
  /// **'Nombre'**
  String get accountName;

  /// No description provided for @accountNameRequired.
  ///
  /// In es, this message translates to:
  /// **'Escribe un nombre para la cuenta.'**
  String get accountNameRequired;

  /// No description provided for @accountColor.
  ///
  /// In es, this message translates to:
  /// **'Color'**
  String get accountColor;

  /// No description provided for @accountCurrency.
  ///
  /// In es, this message translates to:
  /// **'Moneda'**
  String get accountCurrency;

  /// No description provided for @accountStartingAt.
  ///
  /// In es, this message translates to:
  /// **'Empieza en'**
  String get accountStartingAt;

  /// No description provided for @accountDuplicateName.
  ///
  /// In es, this message translates to:
  /// **'Ya existe una cuenta con ese nombre. Elige otro nombre.'**
  String get accountDuplicateName;

  /// No description provided for @accountNegativeBalance.
  ///
  /// In es, this message translates to:
  /// **'Saldo negativo'**
  String get accountNegativeBalance;

  /// No description provided for @accountBalanceInvalid.
  ///
  /// In es, this message translates to:
  /// **'Introduce un saldo válido.'**
  String get accountBalanceInvalid;

  /// No description provided for @accountColorOption.
  ///
  /// In es, this message translates to:
  /// **'Color {number}'**
  String accountColorOption(int number);
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'es'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
