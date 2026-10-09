import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';
import '../widgets/brand_logo.dart';

/// Cashew-style rounded surfaces, pastel accent and generous input spacing.
class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.onLogin,
    this.busy = false,
    this.error,
  });
  final Future<void> Function(String, String) onLogin;
  final bool busy;
  final ApiException? error;
  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _form = GlobalKey<FormState>();
  bool _submitted = false;
  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (widget.busy || _submitted || !_form.currentState!.validate()) return;
    setState(() => _submitted = true);
    try {
      await widget.onLogin(_email.text.trim(), _password.text);
    } finally {
      if (mounted) setState(() => _submitted = false);
    }
  }

  InputDecoration _decoration(
    BuildContext context,
    String label,
    IconData icon,
  ) => InputDecoration(
    labelText: label,
    prefixIcon: Icon(icon),
    filled: true,
    fillColor: Theme.of(context).colorScheme.secondaryContainer
        .withValues(alpha: .4),
    contentPadding: const EdgeInsets.all(18),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(15),
      borderSide: BorderSide.none,
    ),
  );

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final busy = widget.busy || _submitted;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                children: [
                  const BrandLogo(size: 110),
                  const SizedBox(height: 24),
                  Text(
                    l.loginTitle,
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(l.loginSubtitle, textAlign: TextAlign.center),
                  const SizedBox(height: 28),
                  Material(
                    color: MonetaeColors.of(context).card,
                    borderRadius: BorderRadius.circular(20),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Form(
                        key: _form,
                        child: AutofillGroup(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              TextFormField(
                                key: const Key('login-email'),
                                controller: _email,
                                enabled: !busy,
                                autofillHints: const [AutofillHints.username],
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                                decoration: _decoration(
                                  context,
                                  l.email,
                                  Icons.mail_outline,
                                ),
                                validator: (value) =>
                                    value == null || value.trim().isEmpty
                                    ? l.requestInvalid
                                    : null,
                              ),
                              const SizedBox(height: 16),
                              TextFormField(
                                key: const Key('login-password'),
                                controller: _password,
                                enabled: !busy,
                                autofillHints: const [AutofillHints.password],
                                obscureText: true,
                                textInputAction: TextInputAction.done,
                                decoration: _decoration(
                                  context,
                                  l.password,
                                  Icons.lock_outline,
                                ),
                                validator: (value) =>
                                    value == null || value.isEmpty
                                    ? l.requestInvalid
                                    : null,
                                onFieldSubmitted: (_) => _submit(),
                              ),
                              if (widget.error != null) ...[
                                const SizedBox(height: 16),
                                Text(
                                  widget.error!.message(l),
                                  key: const Key('login-error'),
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 24),
                              FilledButton(
                                key: const Key('login-submit'),
                                onPressed: busy ? null : _submit,
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: busy
                                      ? const SizedBox(
                                          width: 20,
                                          height: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : Text(l.signIn),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
