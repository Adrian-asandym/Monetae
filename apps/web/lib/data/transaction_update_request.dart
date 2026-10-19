import '../presentation/decimal_input.dart';
import 'api_dtos.dart';

/// Sparse PATCH body: omission preserves a value; explicit null clears it.
/// The generated contract currently has no TransactionUpdate DTO.
final class TransactionUpdateRequest {
  TransactionUpdateRequest.between(
    TransactionDto original,
    TransactionCreateDto current,
  ) {
    final before = original.toJson();
    final after = current.toJson();
    for (final key in const [
      'account_id',
      'kind',
      'category_id',
      'amount',
      'occurred_at',
      'status',
      'title',
      'note',
      'fx_rate_to_base',
      'fx_rate_source',
    ]) {
      var oldValue = before[key];
      var newValue = after[key];
      if (key == 'occurred_at') {
        oldValue = DateTime.parse(original.occurredAt).toUtc();
        newValue = DateTime.parse(current.occurredAt).toUtc();
      } else if (key == 'amount' || key == 'fx_rate_to_base') {
        final decimals = key == 'amount' ? 2 : 6;
        oldValue = decimalWireText(before[key]! as String, decimals);
        newValue = decimalWireText(after[key]! as String, decimals);
      } else if (key == 'note') {
        oldValue = original.note ?? '';
        newValue = current.note ?? '';
      }
      if (oldValue != newValue) _changes[key] = after[key];
    }
  }

  final _changes = <String, Object?>{};
  bool get isEmpty => _changes.isEmpty;
  Map<String, Object?> toJson() => Map.unmodifiable(_changes);
}
