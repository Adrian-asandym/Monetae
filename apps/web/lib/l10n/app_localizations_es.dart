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
    return '$value%';
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

  @override
  String get more => 'Más';

  @override
  String get accounts => 'Cuentas';

  @override
  String get emptyAccounts => 'Todavía no hay cuentas.';

  @override
  String get defaultAccount => 'Cuenta por defecto';

  @override
  String get homeGreeting => '¡Hola!';

  @override
  String get goodMorning => 'Buenos días';

  @override
  String get goodAfternoon => 'Buenas tardes';

  @override
  String get goodEvening => 'Buenas noches';

  @override
  String get viewAllTransactions => 'Ver todas las transacciones';

  @override
  String get latestTransactions => 'Últimas transacciones';

  @override
  String get cumulativeCashFlow => 'Evolución acumulada';

  @override
  String get addTransaction => 'Agregar transacción';

  @override
  String get comingSoon => 'Próximamente';

  @override
  String get theme => 'Tema';

  @override
  String get systemTheme => 'Tema del sistema';

  @override
  String accountTransactionCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count transacciones',
      one: '1 transacción',
    );
    return '$_temp0';
  }

  @override
  String get transactionAmount => 'Importe';

  @override
  String get formEnterAmount => 'Introduce El Importe';

  @override
  String get formSetAmount => 'Fijar importe';

  @override
  String get formDivide => 'Dividir';

  @override
  String get formMultiply => 'Multiplicar';

  @override
  String get formSubtract => 'Restar';

  @override
  String get formAdd => 'Sumar';

  @override
  String get transactionCategory => 'Categoría (opcional)';

  @override
  String get transactionAccount => 'Cuenta';

  @override
  String get transactionTitle => 'Título (opcional)';

  @override
  String get transactionNote => 'Nota (opcional)';

  @override
  String get transactionPosted => 'Publicada';

  @override
  String get transactionScheduled => 'Programada · fecha futura';

  @override
  String get limaTimezone => 'Hora de Lima · UTC−5';

  @override
  String get exchangeRate => 'Tipo de cambio manual';

  @override
  String manualRateHint(String fromSymbol, String baseSymbol) {
    return 'Por 1 $fromSymbol, ¿cuánto en $baseSymbol?';
  }

  @override
  String get positiveAmountRequired =>
      'Escribe un importe mayor que 0 (hasta 2 decimales).';

  @override
  String get accountRequired => 'Elige una cuenta activa.';

  @override
  String get positiveRateRequired =>
      'Escribe una tasa mayor que 0 (hasta 6 decimales).';

  @override
  String get saveTransaction => 'Guardar transacción';

  @override
  String get savingTransaction => 'Guardando…';

  @override
  String get transactionSaved => 'Transacción guardada';

  @override
  String get deleteDigit => 'Borrar dígito; mantén pulsado para borrar todo';

  @override
  String get decimalPoint => 'Separador decimal';

  @override
  String budgetCanSpendPerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days días más',
      one: '1 día más',
    );
    return 'Puedes gastar $amount/día para $_temp0';
  }

  @override
  String budgetMustSavePerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days días más',
      one: '1 día más',
    );
    return 'Tienes que ahorrar $amount/día para $_temp0';
  }

  @override
  String goalPerDay(String amount, int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days días',
      one: '1 día',
    );
    return '$amount/día para $_temp0';
  }

  @override
  String get goalReached => 'Objetivo logrado';

  @override
  String get goalOverdue => 'Objetivo atrasado';

  @override
  String get addGoalLabel => 'Objetivo';

  @override
  String get addBudgetLabel => 'Presupuesto';

  @override
  String get editHome => 'Editar';

  @override
  String get formAddMenuTitle => 'Agregar Transacción';

  @override
  String get formEditMenuTitle => 'Editar Transacción';

  @override
  String get formSettingTransferTitle => 'Pestaña de transferencia de saldo';

  @override
  String get formSettingTransferSubtitle =>
      'En la página \'Agregar nueva transacción\'';

  @override
  String get formSettingAttachmentTitle => 'Botón Agregar archivos adjuntos';

  @override
  String get formSettingAttachmentSubtitle =>
      'Mostrar debajo de la sección de notas';

  @override
  String get formSettingAutoTitleTitle => 'Agregar títulos automáticamente';

  @override
  String get formSettingAutoTitleSubtitle => 'Cuando se crea una transacción';

  @override
  String get formSettingInitialInputTitle =>
      'Indicaciones iniciales de entrada';

  @override
  String get formSettingInitialInputSubtitle =>
      'Al añadir una transacción por primera vez';

  @override
  String get formTransfer => 'Transferir';

  @override
  String get formTypeDefault => 'Predeterminado';

  @override
  String get formTypeUpcoming => 'Próximamente';

  @override
  String get formTypeSubscription => 'Suscripción';

  @override
  String get formTypeRepetitive => 'Repetitivo';

  @override
  String get formTypeLend => 'Prestar';

  @override
  String get formTypeBorrow => 'Deuda';

  @override
  String get formTypeInfo => 'Tipos de transacción';

  @override
  String get formAllAccounts => 'Todas las cuentas';

  @override
  String get formAccountSheetTitle => 'Seleccionar Cuenta';

  @override
  String get formNoBudget => 'Sin presupuesto';

  @override
  String get formNoGoal => 'Sin objetivo';

  @override
  String get formNoLoan => 'Sin préstamo';

  @override
  String get formCreateBudget => 'Crear presupuesto';

  @override
  String get formCreateGoal => 'Crear objetivo';

  @override
  String get formTitleHint => 'Título';

  @override
  String get formEnterTitle => 'Escribe Un Título';

  @override
  String get formChooseDate => 'Seleccionar fecha';

  @override
  String get formNotesHint => 'Notas';

  @override
  String get formAddAttachment => 'Añadir un adjunto';

  @override
  String get formMoreOptions => 'Más opciones';

  @override
  String get formIncludeAmount => 'Incluir importe';

  @override
  String get formExcludeBudget => 'Excluir del presupuesto';

  @override
  String get formSelectCategory => 'Selecciona una categoría';

  @override
  String get formCategorySheetTitle => 'Selecciona Una Categoría';

  @override
  String get formMenu => 'Más acciones';

  @override
  String get formEditTitle => 'Editar transacción';

  @override
  String get formTypeSheetTitle => 'Seleccionar El Tipo De Transacción';

  @override
  String get formTypeUnpaid => 'Una transacción que no está pagada';

  @override
  String get formTypeNotInTotal =>
      'No cuenta para su total a menos que sea marcado como \'Pagado\' o \'Depositado\'';

  @override
  String get formTypeSubscriptionDescription =>
      'Transacción recurrente que se mostrará en la página de suscripciones';

  @override
  String get formTypeNextGenerated =>
      'Próxima transacción generada cuando la actual está marcada como \"Pagada\" o \"Depositada\"';

  @override
  String get formTypeRepetitiveDescription => 'Transacción recurrente';

  @override
  String get formTypeLendDescription => 'Transacción que prestaste';

  @override
  String get formTypeLendCashFlow =>
      'Flujo de caja negativo hasta que se marque como \'Recolectado\'';

  @override
  String get formTypeBorrowDescription => 'Transacción prestada de alguien';

  @override
  String get formTypeBorrowCashFlow =>
      'Flujo de caja positivo hasta que se marque como \'Liquidado\'';

  @override
  String get formTypeHelp =>
      'Marque una transacción especial tocando el botón de acción en la entrada de la transacción';

  @override
  String get formTypeNotice =>
      'Aún no disponible: se guardará como transacción normal';

  @override
  String get transferBalanceTitle => 'Transferir saldo';

  @override
  String get transferBalanceInfo =>
      'Transfiere un importe de una cuenta a otra. Al realizar una transferencia, se crean dos transacciones de \"Corrección de saldo\": una de \"salida de cuenta\" y otra de \"entrada de cuenta\". Cada una es una transacción independiente y puede editarse en cualquier momento desde la lista de transacciones.';

  @override
  String get transferCorrectionCategory => 'Corrección De Saldo';

  @override
  String get transferConfirm => 'Transferir cantidad';

  @override
  String get transferRates => 'Tipos de cambio';

  @override
  String get transferSwap => 'Intercambiar cuentas';

  @override
  String get transferClear => 'Borrar importe';

  @override
  String get transferArrivalSame => 'Llegada: igual que la salida';

  @override
  String transferArrivalLabel(String date) {
    return 'Llegada: $date';
  }

  @override
  String get transferArrivalReset => 'Igual que la salida';

  @override
  String get transferInfoLabel => 'Información sobre transferir saldo';

  @override
  String get transferOk => 'OK';
}
