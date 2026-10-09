// Derived from Cashew budget/lib/colors.dart (James Kokoska), GPL-3.0.
// Modified for Monetae on 2026-10-09: typed tokens and explicit theme options.
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
  });

  final Color card;
  final Color background;
  final Color muted;
  final Color income;
  final Color expense;
  final Color upcoming;
  final Color overdue;
  final Color divider;

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
  }) => MonetaeColors(
    card: card ?? this.card,
    background: background ?? this.background,
    muted: muted ?? this.muted,
    income: income ?? this.income,
    expense: expense ?? this.expense,
    upcoming: upcoming ?? this.upcoming,
    overdue: overdue ?? this.overdue,
    divider: divider ?? this.divider,
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
    );
  }
}

ThemeData monetaeTheme({
  required Brightness brightness,
  Color accent = const Color(0xFF5F85C2),
  bool tinted = true,
  bool highContrast = false,
  bool fullDark = false,
}) {
  final light = brightness == Brightness.light;
  final background = light
      ? (tinted ? pastel(accent, brightness, .91) : Colors.white)
      : (fullDark || !tinted ? Colors.black : pastel(accent, brightness, .92));
  final colors = MonetaeColors(
    background: background,
    card: tinted
        ? pastel(accent, brightness, light ? .92 : .8)
        : (light ? Colors.white : const Color(0xFF242424)),
    muted: (light ? Colors.black : Colors.white).withValues(
      alpha: highContrast ? .7 : .55,
    ),
    income: light ? const Color(0xFF59A849) : const Color(0xFF62CA77),
    expense: light ? const Color(0xFFCA5A5A) : const Color(0xFFDA7272),
    upcoming: light ? const Color(0xFF58A4C2) : const Color(0xFF7DB6CC),
    overdue: light ? const Color(0xFF6577E0) : const Color(0xFF8395FF),
    divider: light ? const Color(0x0F000000) : const Color(0x13FFFFFF),
  );
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: accent,
      brightness: brightness,
    ).copyWith(surface: background),
    scaffoldBackgroundColor: background,
    extensions: [colors],
    dividerColor: colors.divider,
  );
}
