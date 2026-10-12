import 'package:flutter/widgets.dart';

typedef Now = DateTime Function();

/// Shared presentation clock; production uses the system clock by default.
class PresentationClock extends InheritedWidget {
  const PresentationClock({
    super.key,
    this.now = DateTime.now,
    required super.child,
  });

  final Now now;

  static DateTime of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<PresentationClock>()?.now() ??
      DateTime.now();

  /// Read without subscribing, for a page's initial date in initState.
  static DateTime read(BuildContext context) =>
      (context.getInheritedWidgetOfExactType<PresentationClock>()?.now ??
      DateTime.now)();

  @override
  bool updateShouldNotify(PresentationClock oldWidget) => now != oldWidget.now;
}
