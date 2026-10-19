import 'api_dtos.dart';
import '../presentation/exact_decimal.dart';

/// GoalCreate from OpenAPI; PositiveAmount always has two decimal places.
final class GoalCreateDto {
  const GoalCreateDto({
    required this.name,
    required this.kind,
    required this.targetAmount,
    required this.currency,
    required this.color,
    this.dueOn,
  });

  final String name;
  final GoalKind kind;
  final String targetAmount;
  final String currency;
  final String color;
  final String? dueOn;

  Map<String, Object?> toJson() => {
    'name': name,
    'kind': kind.name,
    'target_amount': ExactDecimal.parse(targetAmount).fixed(2),
    'currency': currency,
    if (dueOn != null) 'due_on': dueOn,
    'color': color,
    // TODO(F1): add the goal icon selector.
    'icon': null,
  };
}
