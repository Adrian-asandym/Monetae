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
  /// **'{value} %'**
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
