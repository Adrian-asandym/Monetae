import 'api_dtos.dart';
import '../presentation/exact_decimal.dart';

/// BudgetCreate from OpenAPI; money is serialized with exactly two decimals.
final class BudgetCreateDto {
  const BudgetCreateDto({
    required this.name,
    required this.period,
    required this.startOn,
    required this.amount,
    required this.currency,
    required this.scope,
    required this.color,
    this.endOn,
    this.categoryIds = const [],
  });

  final List<String> categoryIds;
  final String name;
  final BudgetPeriod period;
  final String startOn;
  final String? endOn;
  final String amount;
  final String currency;
  final BudgetScope scope;
  final String color;

  Map<String, Object?> toJson() => {
    'name': name,
    'period': period.name,
    'start_on': startOn,
    if (period == BudgetPeriod.custom && endOn != null) 'end_on': endOn,
    'amount': ExactDecimal.parse(amount).fixed(2),
    'currency': currency,
    'scope': scope.name,
    'color': color,
    // TODO(F1): editable category limits in a dedicated limits screen, as in
    // Cashew editBudgetLimitsPage. The total means no separate category limit.
    'category_limits': [
      for (final id in categoryIds)
        {
          'category_id': id,
          'limit_amount': ExactDecimal.parse(amount).fixed(2),
        },
    ],
  };
}
