/// Parameters of the two report operations in OpenAPI 0.4.0.
/// Nulls are omitted so the server controls timezone and default ranges.
enum ReportPeriod { daily, weekly, monthly, yearly }

final class ReportQuery {
  const ReportQuery({
    this.dateFrom,
    this.dateTo,
    this.reportCurrency,
    this.accountId,
    this.personId,
    this.period,
  });
  final String? dateFrom;
  final String? dateTo;
  final String? reportCurrency;
  final String? accountId;
  final String? personId;
  final ReportPeriod? period;

  Map<String, String> toQuery({String? cursor, int limit = 100}) => {
    'limit': '$limit',
    'cursor': ?cursor,
    'date_from': ?dateFrom,
    'date_to': ?dateTo,
    'report_currency': ?reportCurrency,
    'account_id': ?accountId,
    'person_id': ?personId,
    'period': ?period?.name,
  };
}
