import 'dart:convert';

import 'package:http/http.dart' as http;

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import 'browser_environment.dart';
import 'report_query.dart';

enum ApiErrorKind {
  unauthorized,
  forbidden,
  conflict,
  validation,
  rateLimit,
  unavailable,
}

final class ApiException implements Exception {
  const ApiException(this.kind, {this.problem, this.statusCode});
  final int? statusCode;
  final ApiErrorKind kind;
  final ProblemDto? problem;

  String message(AppLocalizations l) => switch (kind) {
    ApiErrorKind.unauthorized => l.sessionRequired,
    ApiErrorKind.forbidden => l.requestForbidden,
    ApiErrorKind.conflict => l.requestConflict,
    ApiErrorKind.validation => l.requestInvalid,
    ApiErrorKind.rateLimit => l.tooManyAttempts,
    ApiErrorKind.unavailable => l.connectionError,
  };
}

String? csrfFromCookies(String cookies) {
  for (final part in cookies.split(';')) {
    final split = part.indexOf('=');
    if (split >= 0 && part.substring(0, split).trim() == 'monetae_csrf') {
      final value = part.substring(split + 1).trim();
      return value.isEmpty ? null : value;
    }
  }
  return null;
}

/// Same-origin only. Session cookies remain under the browser's control;
/// the readable CSRF cookie is read anew after every server rotation.
final class ApiClient {
  ApiClient({http.Client? client, String Function()? cookies})
    : _client = client ?? createBrowserClient(),
      _cookies = cookies ?? readBrowserCookies;

  final http.Client _client;
  final String Function() _cookies;
  void Function()? onUnauthorized;
  int _sessionRevision = 0;

  Future<Map<String, Object?>> _request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, Object?>? body,
  }) async {
    final revision = _sessionRevision;
    final uri = Uri(path: '/api/v1/$path', queryParameters: query);
    final headers = <String, String>{'Accept': 'application/json'};
    if (method != 'GET') {
      final csrf = csrfFromCookies(_cookies());
      if (csrf != null) headers['X-CSRF-Token'] = csrf;
    }
    if (body != null) headers['Content-Type'] = 'application/json';
    http.Response response;
    try {
      final request = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      response = await http.Response.fromStream(await _client.send(request));
    } on http.ClientException {
      throw const ApiException(ApiErrorKind.unavailable);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      ProblemDto? problem;
      try {
        problem = ProblemDto.fromJson(
          jsonDecode(response.body) as Map<String, Object?>,
        );
      } on Object {
        // A proxy's HTML error is still a typed HTTP failure, never UI content.
      }
      final kind = switch (response.statusCode) {
        401 => ApiErrorKind.unauthorized,
        403 => ApiErrorKind.forbidden,
        409 => ApiErrorKind.conflict,
        422 => ApiErrorKind.validation,
        429 => ApiErrorKind.rateLimit,
        _ => ApiErrorKind.unavailable,
      };
      // Ignore an old session's late failure after a successful login/logout.
      if (kind == ApiErrorKind.unauthorized && revision == _sessionRevision) {
        onUnauthorized?.call();
      }
      throw ApiException(
        kind,
        problem: problem,
        statusCode: response.statusCode,
      );
    }
    try {
      return jsonDecode(response.body) as Map<String, Object?>;
    } on Object {
      throw const ApiException(ApiErrorKind.unavailable);
    }
  }

  Future<CurrentUserDto> currentUser() async =>
      CurrentUserDto.fromJson(await _request('GET', 'users/me'));

  Future<AuthenticatedSessionDto> login(String email, String password) async {
    final result = AuthenticatedSessionDto.fromJson(
      await _request(
        'POST',
        'auth/login',
        body: PasswordLoginDto(
          method: 'password',
          email: email,
          password: password,
        ).toJson(),
      ),
    );
    _sessionRevision++;
    return result;
  }

  Future<ActionResultDto> logout() async {
    final result = ActionResultDto.fromJson(
      await _request('POST', 'auth/logout'),
    );
    _sessionRevision++;
    return result;
  }

  /// PATCH replaces preferences: send the complete existing object with the
  /// changed card, retaining theme, accent and ordered home widgets.
  Future<CurrentUserDto> updateCard(
    UserPreferencesDto preferences,
    TransactionCardPreferencesDto card,
  ) async => CurrentUserDto.fromJson(
    await _request(
      'PATCH',
      'users/me',
      body: UserUpdateDto(
        preferences: preferences.copyWith(transactionCard: card),
      ).toJson(),
    ),
  );

  Map<String, String> _pageQuery(String? cursor) => {
    'limit': '50',
    'cursor': ?cursor,
  };

  Future<AccountPageDto> accounts({String? cursor}) async =>
      AccountPageDto.fromJson(
        await _request(
          'GET',
          'accounts',
          query: {..._pageQuery(cursor), 'include_archived': 'true'},
        ),
      );
  Future<CategoryPageDto> categories({String? cursor}) async =>
      CategoryPageDto.fromJson(
        await _request('GET', 'categories', query: _pageQuery(cursor)),
      );
  Future<TagPageDto> tags({String? cursor}) async => TagPageDto.fromJson(
    await _request(
      'GET',
      'tags',
      query: {..._pageQuery(cursor), 'include_archived': 'true'},
    ),
  );
  Future<TransactionPageDto> transactions({String? cursor}) async =>
      TransactionPageDto.fromJson(
        await _request('GET', 'transactions', query: _pageQuery(cursor)),
      );
  Future<AccountDto> account(String id) async =>
      AccountDto.fromJson(await _request('GET', 'accounts/$id'));
  Future<CategoryDto> category(String id) async =>
      CategoryDto.fromJson(await _request('GET', 'categories/$id'));
  Future<TagDto> tag(String id) async =>
      TagDto.fromJson(await _request('GET', 'tags/$id'));

  Future<CashFlowRowPageDto> cashFlow({
    ReportQuery query = const ReportQuery(),
    String? cursor,
    int limit = 100,
  }) async => CashFlowRowPageDto.fromJson(
    await _request(
      'GET',
      'reports/cash-flow',
      query: query.toQuery(cursor: cursor, limit: limit),
    ),
  );

  Future<CategoryReportRowPageDto> categoryReport({
    ReportQuery query = const ReportQuery(),
    String? cursor,
    int limit = 100,
  }) async => CategoryReportRowPageDto.fromJson(
    await _request(
      'GET',
      'reports/categories',
      query: query.toQuery(cursor: cursor, limit: limit),
    ),
  );

  void close() => _client.close();
}
