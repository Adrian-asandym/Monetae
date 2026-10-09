import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../data/api_dtos.dart';

final class SessionController extends ChangeNotifier {
  SessionController(this.api) {
    api.onUnauthorized = _expired;
  }
  final ApiClient api;
  CurrentUserDto? user;
  ApiException? error;
  bool loading = true;
  bool busy = false;
  bool saving = false;
  int _revision = 0;
  bool _disposed = false;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _expired() {
    _revision++;
    user = null;
    error = const ApiException(ApiErrorKind.unauthorized);
    _notify();
  }

  Future<void> restore() async {
    final revision = _revision;
    try {
      final profile = await api.currentUser();
      if (_revision == revision) {
        user = profile;
        error = null;
      }
    } on ApiException catch (e) {
      error = e.kind == ApiErrorKind.unauthorized ? null : e;
    } on Object {
      error = const ApiException(ApiErrorKind.unavailable);
    }
    loading = false;
    _notify();
  }

  Future<void> login(String email, String password) async {
    if (busy) return;
    busy = true;
    error = null;
    _notify();
    try {
      // Also bootstraps CSRF when the initial restore failed due to networking.
      try {
        await api.currentUser();
      } on ApiException catch (e) {
        if (e.kind != ApiErrorKind.unauthorized) rethrow;
      }
      final result = await api.login(email, password);
      if (!_disposed) {
        _revision++;
        user = result.user;
        error = null;
      }
    } on ApiException catch (e) {
      error = e;
    } on Object {
      error = const ApiException(ApiErrorKind.unavailable);
    }
    busy = false;
    _notify();
  }

  Future<void> logout() async {
    if (busy) return;
    busy = true;
    error = null;
    _notify();
    try {
      await api.logout();
      _revision++;
      user = null;
    } on ApiException catch (e) {
      error = e;
    } on Object {
      error = const ApiException(ApiErrorKind.unavailable);
    }
    busy = false;
    _notify();
  }

  Future<void> updateCard(TransactionCardPreferencesDto value) async {
    final profile = user;
    if (profile == null || saving) return;
    final revision = _revision;
    saving = true;
    error = null;
    _notify();
    try {
      final updated = await api.updateCard(profile.preferences, value);
      if (_revision == revision) user = updated;
    } on ApiException catch (e) {
      error = e;
    } on Object {
      error = const ApiException(ApiErrorKind.unavailable);
    }
    saving = false;
    _notify();
  }

  @override
  void dispose() {
    _disposed = true;
    api.onUnauthorized = null;
    super.dispose();
  }
}
