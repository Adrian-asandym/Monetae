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

/// OpenAPI 0.7.0: pairs are linked and ordered newest departure first by API.
final class BalanceCorrectionLegDto {
  const BalanceCorrectionLegDto({
    required this.id,
    required this.accountId,
    required this.currency,
    required this.amount,
    required this.occurredAt,
  });
  final String id, accountId, currency, amount, occurredAt;
  factory BalanceCorrectionLegDto.fromJson(Map<String, Object?> json) =>
      BalanceCorrectionLegDto(
        id: json['id'] as String,
        accountId: json['account_id'] as String,
        currency: json['currency'] as String,
        amount: json['amount'] as String,
        occurredAt: json['occurred_at'] as String,
      );
}

final class BalanceCorrectionSummaryDto {
  const BalanceCorrectionSummaryDto({
    required this.groupId,
    required this.outgoing,
    required this.incoming,
    required this.implicitRate,
  });
  final String groupId, implicitRate;
  final BalanceCorrectionLegDto outgoing, incoming;
  factory BalanceCorrectionSummaryDto.fromJson(Map<String, Object?> json) =>
      BalanceCorrectionSummaryDto(
        groupId: json['group_id'] as String,
        implicitRate: json['implicit_rate'] as String,
        outgoing: BalanceCorrectionLegDto.fromJson(
          json['outgoing'] as Map<String, Object?>,
        ),
        incoming: BalanceCorrectionLegDto.fromJson(
          json['incoming'] as Map<String, Object?>,
        ),
      );
}

final class BalanceCorrectionPageDto {
  const BalanceCorrectionPageDto({
    required this.items,
    required this.nextCursor,
  });
  final List<BalanceCorrectionSummaryDto> items;
  final String? nextCursor;
  factory BalanceCorrectionPageDto.fromJson(Map<String, Object?> json) =>
      BalanceCorrectionPageDto(
        items: List<BalanceCorrectionSummaryDto>.unmodifiable(
          (json['items'] as List<Object?>).map(
            (item) => BalanceCorrectionSummaryDto.fromJson(
              item as Map<String, Object?>,
            ),
          ),
        ),
        nextCursor: json['next_cursor'] as String?,
      );
}
