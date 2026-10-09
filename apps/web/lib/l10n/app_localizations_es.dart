// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

  @override
  String get appTitle => 'Monetae';

  @override
  String get spikeTitle => 'Componentes de Monetae';

  @override
  String get syntheticData => 'Vista de prueba · datos sintéticos';

  @override
  String get transactions => 'Transacciones';

  @override
  String get categoryChart => 'Gastos por categoría';

  @override
  String get themePreview => 'Paleta de colores';

  @override
  String get lightTheme => 'Tema claro';

  @override
  String get darkTheme => 'Tema oscuro';

  @override
  String get language => 'Idioma';

  @override
  String get accent => 'Color de acento';

  @override
  String get blueAccent => 'Azul';

  @override
  String get greenAccent => 'Verde';

  @override
  String get purpleAccent => 'Morado';

  @override
  String get income => 'Ingreso';

  @override
  String get expense => 'Gasto';

  @override
  String get scheduled => 'Programada';

  @override
  String get loanMovement => 'Movimiento de préstamo';

  @override
  String get sampleAccount => 'Efectivo de prueba';

  @override
  String get dollarAccount => 'Cuenta en dólares de prueba';

  @override
  String get foodCategory => 'Alimentación';

  @override
  String get workCategory => 'Trabajo';

  @override
  String get transportCategory => 'Transporte';

  @override
  String get homeCategory => 'Hogar';

  @override
  String get sampleLunch => 'Almuerzo de ejemplo';

  @override
  String get sampleNote => 'Nota sintética para revisar el componente.';

  @override
  String get sampleWork => 'Trabajo de ejemplo';

  @override
  String get sampleLoan => 'Cobro de préstamo de ejemplo';

  @override
  String get sampleUpcoming => 'Pago próximo de ejemplo';

  @override
  String get sampleTag => 'Ejemplo';

  @override
  String get emptyChart => 'Sin datos';

  @override
  String get chartTotal => 'Total de ejemplo';

  @override
  String get selectionHint => 'Selecciona una categoría';

  @override
  String get allCategories => 'Todas las categorías';

  @override
  String get fadePreview => 'Entrada animada';

  @override
  String get replayAnimation => 'Repetir animación';

  @override
  String get compact => 'Vista compacta';

  @override
  String cardSubtitle(String category, String account) {
    return '$category · $account';
  }

  @override
  String percent(String value) {
    return '$value %';
  }

  @override
  String get themeCard => 'Superficie';

  @override
  String get themeBackground => 'Fondo';

  @override
  String get cardSettings => 'Detalles de la tarjeta';

  @override
  String get showDate => 'Fecha por día';

  @override
  String get showTime => 'Hora';

  @override
  String get showNote => 'Nota';

  @override
  String get showTags => 'Etiquetas';

  @override
  String get showAccount => 'Cuenta';

  @override
  String get showActions => 'Acciones';

  @override
  String get editTransaction => 'Editar';

  @override
  String get duplicateTransaction => 'Duplicar';

  @override
  String get deleteTransaction => 'Borrar';

  @override
  String get tintCategoryIcons => 'Teñir íconos propios';

  @override
  String actionPreview(String action) {
    return 'Vista de prueba: $action';
  }

  @override
  String get sampleLoanParty => 'Persona de prueba';

  @override
  String get loginTitle => 'Bienvenido a Monetae';

  @override
  String get loginSubtitle => 'Tus finanzas, en un solo lugar.';

  @override
  String get email => 'Correo electrónico';

  @override
  String get password => 'Contraseña';

  @override
  String get signIn => 'Iniciar sesión';

  @override
  String get signOut => 'Cerrar sesión';

  @override
  String get sessionRequired => 'Inicia sesión para continuar.';

  @override
  String get requestForbidden =>
      'No se pudo verificar la solicitud. Recarga e inténtalo de nuevo.';

  @override
  String get requestConflict =>
      'Los datos han cambiado. Recarga e inténtalo de nuevo.';

  @override
  String get requestInvalid => 'Revisa los datos e inténtalo de nuevo.';

  @override
  String get tooManyAttempts =>
      'Demasiados intentos. Espera antes de volver a intentarlo.';

  @override
  String get connectionError => 'No se pudo conectar con el servidor.';

  @override
  String get loadMore => 'Cargar más';

  @override
  String get retry => 'Reintentar';

  @override
  String get refresh => 'Actualizar';

  @override
  String get emptyTransactions => 'Todavía no hay transacciones.';

  @override
  String get demo => 'Ver demostración';

  @override
  String get backToApp => 'Volver a Monetae';

  @override
  String get savingPreferences => 'Guardando preferencias…';

  @override
  String get unavailableAccount => 'Cuenta no disponible';

  @override
  String get unavailableTag => 'Etiqueta no disponible';

  @override
  String get transfer => 'Transferencia';

  @override
  String get home => 'Inicio';

  @override
  String get cashFlow => 'Ingresos y gastos';

  @override
  String get categoryDistribution => 'Categorías';

  @override
  String get uncategorized => 'Sin categoría';

  @override
  String get emptyReports => 'Todavía no hay reportes para este periodo.';

  @override
  String get unconvertedNotice =>
      'Algunos movimientos no tienen tasa histórica y quedan fuera de los totales convertidos.';

  @override
  String get previousMonth => 'Mes anterior';

  @override
  String get nextMonth => 'Mes siguiente';

  @override
  String get periodTotals => 'Totales del periodo';

  @override
  String get budgets => 'Presupuestos';

  @override
  String get goals => 'Objetivos';

  @override
  String get budgetGoalDemo => 'Presupuestos y objetivos';

  @override
  String get emptyBudgets => 'Todavía no hay presupuestos.';

  @override
  String get emptyGoals => 'Todavía no hay objetivos.';

  @override
  String get createBudget => 'Crear presupuesto';

  @override
  String get createGoal => 'Crear objetivo';

  @override
  String get dailyBudget => 'Diario';

  @override
  String get weeklyBudget => 'Semanal';

  @override
  String get monthlyBudget => 'Mensual';

  @override
  String get customBudget => 'Personalizado';

  @override
  String get savingsGoal => 'Objetivo de ahorro';

  @override
  String get spendingGoal => 'Objetivo de gasto';

  @override
  String get goalComplete => 'Completado';

  @override
  String get progress => 'Progreso';

  @override
  String get today => 'Hoy';

  @override
  String get horizontalList => 'Lista horizontal';

  @override
  String get verticalList => 'Lista vertical';

  @override
  String get showEmptyLists => 'Mostrar listas vacías';

  @override
  String get sampleFoodBudget => 'Alimentación';

  @override
  String get sampleTravelBudget => 'Viaje';

  @override
  String get sampleHomeBudget => 'Hogar';

  @override
  String get sampleSavingsGoal => 'Fondo de emergencia';

  @override
  String get sampleSpendingGoal => 'Nueva laptop';

  @override
  String get sampleHolidayGoal => 'Vacaciones';

  @override
  String budgetLeft(String amount, String total) {
    return '$amount restante de $total';
  }

  @override
  String budgetOver(String amount, String total) {
    return '$amount excedido de $total';
  }

  @override
  String budgetSpent(String amount, String total) {
    return 'Gastado: $amount / $total';
  }

  @override
  String goalAmounts(String amount, String total) {
    return '$amount / $total';
  }

  @override
  String goalDue(String date) {
    return 'Hasta $date';
  }

  @override
  String convertedTotal(String amount) {
    return 'Total convertido: $amount';
  }
}
