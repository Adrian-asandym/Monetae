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
  String get dollarAccount => 'Cuenta USD de prueba';

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
  String penAmount(String amount) {
    return 'S/ $amount';
  }

  @override
  String usdAmount(String amount) {
    return 'US\$ $amount';
  }

  @override
  String percent(String value) {
    return '$value %';
  }

  @override
  String get themeCard => 'Superficie';

  @override
  String get themeBackground => 'Fondo';
}
