import 'package:flutter/material.dart';

Color pastel(Color color, Brightness brightness, double amount) =>
    Color.alphaBlend(
      (brightness == Brightness.light ? Colors.white : Colors.black).withValues(
        alpha: amount,
      ),
      color,
    );

@immutable
class MonetaeColors extends ThemeExtension<MonetaeColors> {
  const MonetaeColors({
    required this.card,
    required this.background,
    required this.muted,
    required this.income,
    required this.expense,
    required this.upcoming,
    required this.overdue,
    required this.divider,
    required this.selectedPill,
  });

  final Color card;
  final Color background;
  final Color muted;
  final Color income;
  final Color expense;
  final Color upcoming;
  final Color overdue;
  final Color divider;
  final Color selectedPill;

  static MonetaeColors of(BuildContext context) =>
      Theme.of(context).extension<MonetaeColors>()!;

  @override
  MonetaeColors copyWith({
    Color? card,
    Color? background,
    Color? muted,
    Color? income,
    Color? expense,
    Color? upcoming,
    Color? overdue,
    Color? divider,
    Color? selectedPill,
  }) => MonetaeColors(
    card: card ?? this.card,
    background: background ?? this.background,
    muted: muted ?? this.muted,
    income: income ?? this.income,
    expense: expense ?? this.expense,
    upcoming: upcoming ?? this.upcoming,
    overdue: overdue ?? this.overdue,
    divider: divider ?? this.divider,
    selectedPill: selectedPill ?? this.selectedPill,
  );

  @override
  MonetaeColors lerp(covariant MonetaeColors? other, double t) {
    if (other == null) return this;
    return MonetaeColors(
      card: Color.lerp(card, other.card, t)!,
      background: Color.lerp(background, other.background, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      income: Color.lerp(income, other.income, t)!,
      expense: Color.lerp(expense, other.expense, t)!,
      upcoming: Color.lerp(upcoming, other.upcoming, t)!,
      overdue: Color.lerp(overdue, other.overdue, t)!,
      divider: Color.lerp(divider, other.divider, t)!,
      selectedPill: Color.lerp(selectedPill, other.selectedPill, t)!,
    );
  }
}

ThemeData monetaeTheme({
  required Brightness brightness,
  Color accent = const Color(0xFFE0E0E0), // Neutral accent
}) {
  final light = brightness == Brightness.light;
  
  // Neutral backgrounds per skill:
  final background = light ? Colors.white : const Color(0xFF121212);
  final card = light ? const Color(0xFFF5F5F5) : const Color(0xFF1E1E1E);
  final selectedPill = light ? const Color(0xFFE0E0E0) : const Color(0xFF3A3A3A);

  final colors = MonetaeColors(
    background: background,
    card: card,
    muted: (light ? Colors.black : Colors.white).withValues(
      alpha: 0.60,
    ),
    income: light ? const Color(0xFF4CAF50) : const Color(0xFF4CAF50), // Cashew green
    expense: light ? const Color(0xFFE57373) : const Color(0xFFE57373), // Cashew red/coral
    upcoming: light ? const Color(0xFF58A4C2) : const Color(0xFF7DB6CC),
    overdue: light ? const Color(0xFF6577E0) : const Color(0xFF8395FF),
    divider: light ? const Color(0x0F000000) : const Color(0x13FFFFFF),
    selectedPill: selectedPill,
  );
  
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    fontFamily: 'DM Sans',
    colorScheme: ColorScheme.fromSeed(
      seedColor: accent,
      brightness: brightness,
    ).copyWith(surface: background),
    scaffoldBackgroundColor: background,
    extensions: [colors],
    dividerColor: colors.divider,
  );
}
