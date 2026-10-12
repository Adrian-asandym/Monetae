import 'api_dtos.dart';

/// Typed wire boundary for OpenAPI 0.7.0 BalanceCorrectionCreate.
/// Kept separate from generated 0.6.0 DTOs until the generator includes RF-03.
final class BalanceCorrectionCreateDto {
  const BalanceCorrectionCreateDto({
    required this.fromAccountId,
    required this.toAccountId,
    required this.fromAmount,
    required this.toAmount,
    required this.fromFxRateToBase,
    required this.toFxRateToBase,
    required this.occurredAt,
    required this.toOccurredAt,
    required this.title,
  });
  final String fromAccountId, toAccountId, fromAmount, toAmount;
  final String fromFxRateToBase, toFxRateToBase;
  final String occurredAt, toOccurredAt, title;
  Map<String, Object?> toJson() => {
    'from_account_id': fromAccountId,
    'to_account_id': toAccountId,
    'from_amount': fromAmount,
    'to_amount': toAmount,
    'from_fx_rate_to_base': fromFxRateToBase,
    'to_fx_rate_to_base': toFxRateToBase,
    'fx_rate_source': 'manual',
    'occurred_at': occurredAt,
    'to_occurred_at': toOccurredAt,
    'title': title,
  };
}

final class BalanceCorrectionDto {
  const BalanceCorrectionDto({
    required this.groupId,
    required this.outgoing,
    required this.incoming,
  });
  final String groupId;
  final TransactionDto outgoing, incoming;
  factory BalanceCorrectionDto.fromJson(
    Map<String, Object?> json,
  ) => BalanceCorrectionDto(
    groupId: json['group_id'] as String,
    outgoing: TransactionDto.fromJson(json['outgoing'] as Map<String, Object?>),
    incoming: TransactionDto.fromJson(json['incoming'] as Map<String, Object?>),
  );
}
