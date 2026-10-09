import 'package:flutter_test/flutter_test.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';

void main() {
  test('DTO preserves decimal precision, nulls, enums and UTC wire values', () {
    final dto = TransactionDto.fromJson(
      mockTransactionJson(amount: '-9999999999999999.99'),
    );
    expect(dto.amount, '-9999999999999999.99');
    expect(dto.fxRateToBase, '1.000000');
    expect(dto.status, TransactionStatus.posted);
    expect(dto.note, isNull);
    expect(dto.occurredAt, '2026-10-09T15:00:00Z');
    expect(() => dto.tagIds.add('x'), throwsUnsupportedError);
  });
  test(
    'DTO rejects implicit numeric conversion, unknown enum and field mismatch',
    () {
      expect(
        () => TransactionDto.fromJson({
          ...mockTransactionJson(),
          'amount': -48.5,
        }),
        throwsFormatException,
      );
      expect(
        () => TransactionDto.fromJson({
          ...mockTransactionJson(),
          'kind': 'unknown',
        }),
        throwsFormatException,
      );
      expect(
        () => TransactionDto.fromJson({
          ...mockTransactionJson(),
          'unknown': true,
        }),
        throwsFormatException,
      );
      final missing = mockTransactionJson()..remove('note');
      expect(() => TransactionDto.fromJson(missing), throwsFormatException);
    },
  );
}
