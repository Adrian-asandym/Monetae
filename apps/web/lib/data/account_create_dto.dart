import 'api_dtos.dart';

/// AccountCreate from OpenAPI 0.7.0; money is exact decimal wire text.
final class AccountCreateDto {
  const AccountCreateDto({
    required this.name,
    required this.currency,
    required this.initialBalance,
    required this.color,
  });

  final String name;
  final String currency;
  final String initialBalance;
  final String color;

  Map<String, Object?> toJson() => {
    'name': name,
    'type': AccountType.other.name,
    'currency': currency,
    'initial_balance': initialBalance,
    'color': color,
  };
}
