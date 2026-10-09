import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:monetae_web/api/api_client.dart';
import 'package:monetae_web/api/transaction_feed.dart';
import 'package:monetae_web/data/api_dtos.dart';
import 'package:monetae_web/data/mock_data.dart';
import 'package:monetae_web/l10n/app_localizations_es.dart';
import 'package:monetae_web/main.dart';
import 'package:monetae_web/pages/login_page.dart';
import 'package:monetae_web/presentation/transaction_presenter.dart';
import 'package:monetae_web/session/session_controller.dart';
import 'package:monetae_web/widgets/transaction_card.dart';
import 'package:monetae_web/widgets/transaction_card_list.dart';

import 'components_test.dart' as harness;

final l = AppLocalizationsEs();
const all = TransactionCardPreferencesDto(
  showDate: true,
  showTime: true,
  showNote: true,
  showTags: true,
  showAccount: true,
  showActions: true,
);
const none = TransactionCardPreferencesDto(
  showDate: false,
  showTime: false,
  showNote: false,
  showTags: false,
  showAccount: false,
  showActions: false,
);

Map<String, Object?> profile({TransactionCardPreferencesDto card = all}) => {
  'id': '00000000-0000-4000-8000-000000000999',
  'email': 'sample@example.test',
  'preferences': {
    'theme': 'dark',
    'accent_color': '#BA7DBD',
    'home_widgets': ['accounts', 'transactions'],
    'transaction_card': card.toJson(),
  },
  'pin_configured': false,
  'locked': false,
  'webauthn_enabled': false,
  'timezone': 'America/Lima',
  'base_currency': 'PEN',
  'locale': 'es',
  'lock_after_minutes': null,
  'report_currency': 'USD',
};
http.Response ok(Object body) => http.Response(
  jsonEncode(body),
  200,
  headers: {'content-type': 'application/json'},
);
http.Response problem(int status) => http.Response(
  jsonEncode({
    'type': 'about:blank',
    'title': 'Error',
    'status': status,
    'detail': 'Synthetic server error',
    'code': 'synthetic_error',
  }),
  status,
  headers: {'content-type': 'application/problem+json'},
);

final tag = TagDto.fromJson({
  'id': '00000000-0000-4000-8000-000000000033',
  'name': 'Etiqueta sintética',
  'color': null,
  'icon': null,
  'emoji': null,
  'sort_order': 0,
  'created_at': '2026-10-09T15:00:00Z',
  'updated_at': '2026-10-09T15:00:00Z',
  'deleted_at': null,
  'archived_at': null,
});
Map<String, Object?> transaction({
  String id = '00000000-0000-4000-8000-000000000100',
  String time = '2026-10-09T03:30:00Z',
}) => {
  ...mockTransactionJson(
    id: id,
    occurredAt: time,
    title: 'Compra sintética',
    note: 'Nota de prueba',
  ),
  'tag_ids': [tag.id],
};
http.Response catalogs(http.Request request) => switch (request.url.path) {
  '/api/v1/accounts' => ok({
    'items': [mockAccount(l).toJson()],
    'next_cursor': null,
  }),
  '/api/v1/categories' => ok({
    'items': [mockCategory(l, custom: true).toJson()],
    'next_cursor': null,
  }),
  '/api/v1/tags' => ok({
    'items': [tag.toJson()],
    'next_cursor': null,
  }),
  '/api/v1/transactions' => ok({
    'items': [transaction()],
    'next_cursor': null,
  }),
  _ => throw StateError('Unexpected request: ${request.method} ${request.url}'),
};

void main() {
  harness.loadGoldenFonts();

  test(
    'same-origin reads omit CSRF; every write uses the rotated cookie',
    () async {
      var cookie = 'irrelevant=a; monetae_csrf=pre.token; second=z';
      final requests = <http.Request>[];
      final api = ApiClient(
        cookies: () => cookie,
        client: MockClient((request) async {
          requests.add(request);
          expect(request.url.hasScheme, isFalse);
          expect(request.url.hasAuthority, isFalse);
          if (request.url.path == '/api/v1/auth/login') {
            expect(jsonDecode(request.body), {
              'method': 'password',
              'email': 'sample@example.test',
              'password': 'synthetic-password',
            });
            cookie = 'monetae_csrf=after.token';
            return ok({
              'user': profile(),
              'csrf_token': 'after.token',
              'expires_at': '2026-11-01T00:00:00Z',
            });
          }
          if (request.url.path == '/api/v1/auth/logout') {
            return ok({'success': true, 'affected_count': 1});
          }
          return ok(profile());
        }),
      );
      addTearDown(api.close);
      await api.currentUser();
      await api.login('sample@example.test', 'synthetic-password');
      await api.updateCard(
        CurrentUserDto.fromJson(profile()).preferences,
        none,
      );
      await api.logout();
      expect(requests.map((r) => r.headers['X-CSRF-Token']), [
        null,
        'pre.token',
        'after.token',
        'after.token',
      ]);
      expect(
        csrfFromCookies('monetae_csrf_extra=bad; monetae_csrf=a=b'),
        'a=b',
      );
      expect(csrfFromCookies('monetae_session=opaque'), isNull);
    },
  );

  test(
    'PATCH sends the entire preferences object and retains optional nulls',
    () async {
      final prefs = CurrentUserDto.fromJson(profile()).preferences;
      final api = ApiClient(
        cookies: () => 'monetae_csrf=token',
        client: MockClient((request) async {
          expect(request.method, 'PATCH');
          expect(jsonDecode(request.body), {
            'preferences': {
              'theme': 'dark',
              'accent_color': '#BA7DBD',
              'home_widgets': ['accounts', 'transactions'],
              'transaction_card': none.toJson(),
            },
          });
          return ok(profile(card: none));
        }),
      );
      addTearDown(api.close);
      expect(
        (await api.updateCard(
          prefs,
          none,
        )).preferences.transactionCard.showDate,
        false,
      );
      expect(UserPreferencesDto.fromJson({}).toJson(), {
        'theme': 'system',
        'accent_color': null,
        'home_widgets': <String>[],
        'transaction_card': const TransactionCardPreferencesDto().toJson(),
      });
    },
  );

  for (final (status, kind) in [
    (401, ApiErrorKind.unauthorized),
    (403, ApiErrorKind.forbidden),
    (409, ApiErrorKind.conflict),
    (422, ApiErrorKind.validation),
  ]) {
    test('Problem $status retains code and maps to a typed error', () async {
      final api = ApiClient(client: MockClient((_) async => problem(status)));
      addTearDown(api.close);
      await expectLater(
        api.currentUser(),
        throwsA(
          isA<ApiException>()
              .having((e) => e.kind, 'kind', kind)
              .having((e) => e.problem?.code, 'code', 'synthetic_error'),
        ),
      );
    });
  }

  test('pre-login bootstrap, restore and logout transition session', () async {
    var signedIn = false;
    final api = ApiClient(
      cookies: () => 'monetae_csrf=token',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/auth/login') {
          signedIn = true;
          return ok({
            'user': profile(),
            'csrf_token': 'token',
            'expires_at': '2026-11-01T00:00:00Z',
          });
        }
        if (request.url.path == '/api/v1/auth/logout') {
          signedIn = false;
          return ok({'success': true, 'affected_count': 1});
        }
        return signedIn ? ok(profile()) : problem(401);
      }),
    );
    final session = SessionController(api);
    addTearDown(() {
      session.dispose();
      api.close();
    });
    await session.restore();
    expect(session.loading, false);
    expect(session.user, isNull);
    expect(session.error, isNull);
    await session.login('sample@example.test', 'synthetic-password');
    expect(session.user?.email, 'sample@example.test');
    await session.logout();
    expect(session.user, isNull);
    expect(signedIn, false);
  });

  testWidgets('401 on a later authenticated read returns to login', (
    tester,
  ) async {
    var expired = false;
    final api = ApiClient(
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/users/me') return ok(profile());
        if (expired) return problem(401);
        return catalogs(request);
      }),
    );
    addTearDown(api.close);
    await tester.pumpWidget(MonetaeApp(api: api));
    await tester.pumpAndSettle();
    if (find.byKey(const Key('home-transactions')).evaluate().isNotEmpty) {
      await tester.tap(find.byKey(const Key('home-transactions')));
      await tester.pumpAndSettle();
    }
    await tester.pumpAndSettle();
    expect(find.byType(TransactionCard), findsOneWidget);
    expired = true;
    await tester.tap(find.byTooltip('Actualizar'));
    await tester.pumpAndSettle();
    expect(find.byType(LoginPage), findsOneWidget);
    expect(find.byType(TransactionCard), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Problem 422 on login displays the localized validation message',
    (tester) async {
      final api = ApiClient(
        cookies: () => 'monetae_csrf=token',
        client: MockClient(
          (request) async =>
              request.method == 'POST' ? problem(422) : problem(401),
        ),
      );
      addTearDown(api.close);
      await tester.pumpWidget(MonetaeApp(api: api));
      await tester.pumpAndSettle();
      if (find.byKey(const Key('home-transactions')).evaluate().isNotEmpty) {
        await tester.tap(find.byKey(const Key('home-transactions')));
        await tester.pumpAndSettle();
      }
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('login-email')),
        'sample@example.test',
      );
      await tester.enterText(
        find.byKey(const Key('login-password')),
        'synthetic-password',
      );
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pumpAndSettle();
      expect(find.text(l.requestInvalid), findsOneWidget);
      expect(find.text('Synthetic server error'), findsNothing);
    },
  );

  test('catalog and transaction cursors resolve archived catalogs and retain exact decimals', () async {
    final api = ApiClient(
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/accounts') {
          expect(request.url.queryParameters['include_archived'], 'true');
          return request.url.queryParameters['cursor'] == null
              ? ok({'items': <Object?>[], 'next_cursor': 'account cursor/+='})
              : ok({
                  'items': [mockAccount(l).toJson()],
                  'next_cursor': null,
                });
        }
        if (request.url.path == '/api/v1/transactions') {
          return request.url.queryParameters['cursor'] == null
              ? ok({
                  'items': [transaction()],
                  'next_cursor': 'tx cursor/+=',
                })
              : ok({
                  'items': [
                    {
                      ...transaction(
                        id: '00000000-0000-4000-8000-000000000101',
                        time: '2026-10-08T01:00:00Z',
                      ),
                      'amount': '-9999999999999999.99',
                    },
                  ],
                  'next_cursor': null,
                });
        }
        return catalogs(request);
      }),
    );
    addTearDown(api.close);
    final feed = TransactionFeed(api);
    await feed.load();
    await feed.loadMore();
    final models = presentTransactions(feed, l);
    expect(models.map((m) => m.dateKey), ['2026-10-08', '2026-10-07']);
    expect(models.first.timeLabel, '22:30');
    expect(models.last.amountLabel, contains('9,999,999,999,999,999.99'));
    expect(models.first.icon.materialIcon, Icons.category_rounded);
    expect(models.first.tags, ['Etiqueta sintética']);
  });

  testWidgets(
    'real feed groups across pages and honors each of the six preferences',
    (tester) async {
      final api = ApiClient(
        client: MockClient((request) async {
          if (request.url.path == '/api/v1/transactions') {
            return ok({
              'items': [
                transaction(),
                transaction(id: 'second'),
                transaction(id: 'third', time: '2026-10-08T01:00:00Z'),
              ],
              'next_cursor': null,
            });
          }
          return catalogs(request);
        }),
      );
      addTearDown(api.close);
      final feed = TransactionFeed(api);
      await feed.load();
      for (final (field, prefs) in [
        ('all', all),
        ('date', all.copyWith(showDate: false)),
        ('time', all.copyWith(showTime: false)),
        ('note', all.copyWith(showNote: false)),
        ('tags', all.copyWith(showTags: false)),
        ('account', all.copyWith(showAccount: false)),
        ('actions', all.copyWith(showActions: false)),
        ('none', none),
      ]) {
        await harness.mount(
          tester,
          Brightness.light,
          (_, loc) => SingleChildScrollView(
            child: TransactionCardList(
              models: presentTransactions(feed, loc),
              preferences: prefs,
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(TransactionCard), findsNWidgets(3), reason: field);
        expect(
          find.byKey(const ValueKey('date-2026-10-08')),
          prefs.showDate ? findsOneWidget : findsNothing,
          reason: field,
        );
        expect(
          find.byKey(const ValueKey('date-2026-10-07')),
          prefs.showDate ? findsOneWidget : findsNothing,
          reason: field,
        );
        expect(
          find.byKey(const Key('transaction-time')),
          prefs.showTime ? findsNWidgets(3) : findsNothing,
          reason: field,
        );
        expect(
          find.text('Nota de prueba'),
          prefs.showNote ? findsNWidgets(3) : findsNothing,
          reason: field,
        );
        expect(
          find.text('Etiqueta sintética'),
          prefs.showTags ? findsNWidgets(3) : findsNothing,
          reason: field,
        );
        expect(
          find.byKey(const Key('transaction-account')),
          prefs.showAccount ? findsNWidgets(3) : findsNothing,
          reason: field,
        );
        expect(
          find.byTooltip(l.editTransaction),
          prefs.showActions ? findsNWidgets(3) : findsNothing,
          reason: field,
        );
      }
    },
  );

  testWidgets('settings save to server and a new app session restores them', (
    tester,
  ) async {
    var card = all;
    final api = ApiClient(
      cookies: () => 'monetae_csrf=token',
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/users/me') {
          if (request.method == 'PATCH') {
            final body = jsonDecode(request.body) as Map<String, Object?>;
            final preferences = body['preferences'] as Map<String, Object?>;
            expect(preferences['theme'], 'dark');
            expect(preferences['accent_color'], '#BA7DBD');
            expect(preferences['home_widgets'], ['accounts', 'transactions']);
            card = TransactionCardPreferencesDto.fromJson(
              preferences['transaction_card'] as Map<String, Object?>,
            );
          }
          return ok(profile(card: card));
        }
        return catalogs(request);
      }),
    );
    addTearDown(api.close);
    await tester.pumpWidget(MonetaeApp(api: api));
    await tester.pumpAndSettle();
    if (find.byKey(const Key('home-transactions')).evaluate().isNotEmpty) {
      await tester.tap(find.byKey(const Key('home-transactions')));
      await tester.pumpAndSettle();
    }
    await tester.pumpAndSettle();
    await tester.tap(find.text(l.cardSettings));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('show-date')));
    await tester.pumpAndSettle();
    expect(card.showDate, false);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpWidget(MonetaeApp(api: api));
    await tester.pumpAndSettle();
    if (find.byKey(const Key('home-transactions')).evaluate().isNotEmpty) {
      await tester.tap(find.byKey(const Key('home-transactions')));
      await tester.pumpAndSettle();
    }
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('date-2026-10-08')), findsNothing);
    expect(find.byType(TransactionCard), findsOneWidget);
  });

  test(
    'a late 401 from a previous session cannot clear a successful login',
    () async {
      final delayed = Completer<http.Response>();
      final started = Completer<void>();
      final api = ApiClient(
        cookies: () => 'monetae_csrf=token',
        client: MockClient((request) async {
          if (request.url.path == '/api/v1/transactions') {
            started.complete();
            return delayed.future;
          }
          if (request.url.path == '/api/v1/auth/login') {
            return ok({
              'user': profile(),
              'csrf_token': 'token',
              'expires_at': '2026-11-01T00:00:00Z',
            });
          }
          return ok(profile());
        }),
      );
      final session = SessionController(api);
      addTearDown(() {
        session.dispose();
        api.close();
      });
      await session.restore();
      final request = expectLater(
        api.transactions(),
        throwsA(isA<ApiException>()),
      );
      await started.future;
      await session.login('sample@example.test', 'synthetic-password');
      delayed.complete(problem(401));
      await request;
      expect(session.user?.email, 'sample@example.test');
      expect(session.error, isNull);
    },
  );

  test(
    'a rejected preference update retains the confirmed server preferences',
    () async {
      final api = ApiClient(
        cookies: () => 'monetae_csrf=token',
        client: MockClient(
          (request) async =>
              request.method == 'PATCH' ? problem(422) : ok(profile()),
        ),
      );
      final session = SessionController(api);
      addTearDown(() {
        session.dispose();
        api.close();
      });
      await session.restore();
      await session.updateCard(none);
      expect(session.user?.preferences.transactionCard.toJson(), all.toJson());
      expect(session.saving, false);
      expect(session.error?.kind, ApiErrorKind.validation);
      expect(
        () => UserPreferencesDto.fromJson({'theme': null}),
        throwsFormatException,
      );
      expect(
        () => UserPreferencesDto.fromJson({'transaction_card': null}),
        throwsFormatException,
      );
    },
  );

  test('soft-deleted display catalogs retain their transactions with fallback labels', () async {
    final api = ApiClient(
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/transactions') {
          return ok({
            'items': [transaction()],
            'next_cursor': null,
          });
        }
        if ([
          '/api/v1/accounts',
          '/api/v1/categories',
          '/api/v1/tags',
        ].contains(request.url.path)) {
          return ok({'items': <Object?>[], 'next_cursor': null});
        }
        return problem(404);
      }),
    );
    addTearDown(api.close);
    final feed = TransactionFeed(api);
    await feed.load();
    final model = presentTransactions(feed, l).single;
    expect(model.account, isNull);
    expect(model.category, isNull);
    expect(model.transaction.title, 'Compra sintética');
    expect(model.tags, [l.unavailableTag]);
  });

  testWidgets('load more uses the cursor and merges a repeated day header', (
    tester,
  ) async {
    final api = ApiClient(
      client: MockClient((request) async {
        if (request.url.path == '/api/v1/users/me') {
          return ok(profile(card: const TransactionCardPreferencesDto()));
        }
        if (request.url.path == '/api/v1/transactions') {
          final cursor = request.url.queryParameters['cursor'];
          expect(cursor == null || cursor == 'cursor/+', true);
          return ok({
            'items': [transaction(id: cursor == null ? 'first' : 'second')],
            'next_cursor': cursor == null ? 'cursor/+' : null,
          });
        }
        return catalogs(request);
      }),
    );
    addTearDown(api.close);
    await tester.pumpWidget(MonetaeApp(api: api));
    await tester.pumpAndSettle();
    if (find.byKey(const Key('home-transactions')).evaluate().isNotEmpty) {
      await tester.tap(find.byKey(const Key('home-transactions')));
      await tester.pumpAndSettle();
    }
    await tester.pumpAndSettle();
    expect(find.byType(TransactionCard), findsOneWidget);
    await tester.tap(find.byKey(const Key('load-more')));
    await tester.pumpAndSettle();
    expect(find.byType(TransactionCard), findsNWidgets(2));
    expect(find.byKey(const ValueKey('date-2026-10-08')), findsOneWidget);
    expect(find.byKey(const Key('load-more')), findsNothing);
  });

  for (final brightness in Brightness.values) {
    testWidgets('login golden ${brightness.name}', (tester) async {
      await harness.mount(
        tester,
        brightness,
        (_, _) => LoginPage(onLogin: (_, _) async {}),
        captureSize: const Size(600, 640),
      );
      await tester.pumpAndSettle();
      await expectLater(
        find.byKey(const Key('capture')),
        matchesGoldenFile('goldens/login_${brightness.name}.png'),
      );
    });
  }
}
