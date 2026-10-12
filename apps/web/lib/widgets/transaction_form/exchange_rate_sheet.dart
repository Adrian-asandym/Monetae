// Derived from Cashew widgets/openBottomSheet.dart (PopupFramework).
// Copyright James Kokoska, GPL-3.0. Modified 2026-10-12 (T-519 piece 11):
// Monetae's manual/suggested rate sheet; capture 24 shows only its entry points.
// Layout reuses the established transaction form sheet, fields and buttons.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../api/transfer_balance_controller.dart';
import '../../l10n/app_localizations.dart';
import '../../presentation/currency_format.dart';
import '../../presentation/decimal_input.dart';
import '../../theme/monetae_theme.dart';
import 'form_controls.dart';
import 'form_sheet.dart';

typedef _T = TransactionFormTokens;

Future<void> showExchangeRateSheet(
  BuildContext context,
  TransferBalanceController controller,
) => showFormSheet<void>(
  context,
  key: const Key('exchange-rate-sheet'),
  title: AppLocalizations.of(context).transferRateSheetTitle,
  builder: (_) => ExchangeRateSheet(controller: controller),
);

class ExchangeRateSheet extends StatefulWidget {
  const ExchangeRateSheet({super.key, required this.controller});
  final TransferBalanceController controller;
  @override
  State<ExchangeRateSheet> createState() => _ExchangeRateSheetState();
}

class _ExchangeRateSheetState extends State<ExchangeRateSheet> {
  TransferBalanceController get form => widget.controller;
  final _input = TextEditingController();
  String? _seenRate;
  bool _typing = false, _attempted = false;
  @override
  void initState() {
    super.initState();
    form.addListener(_changed);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  String _text() {
    final decimalComma =
        form.peruRate ||
        AppLocalizations.of(context).localeName.startsWith('es');
    return decimalComma
        ? form.displayedRate.replaceAll('.', ',')
        : form.displayedRate;
  }

  void _sync({bool force = false}) {
    final value = _text();
    if (!_typing && (force || value != _seenRate)) {
      _input.value = TextEditingValue(
        text: value,
        selection: TextSelection.collapsed(offset: value.length),
      );
    }
    _seenRate = value;
  }

  void _changed() {
    if (!mounted) return;
    _sync();
    setState(() {});
  }

  @override
  void dispose() {
    form.removeListener(_changed);
    _input.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final c = TransactionFormColors.of(context);
    final muted = MonetaeColors.of(context).muted;
    final suggested = form.suggestion;
    final date = suggested == null
        ? ''
        : DateFormat.yMMMd(l.localeName)
              .format(suggested.occurredAt.subtract(const Duration(hours: 5)));
    final source = form.suggestionActive
        ? l.transferRateSuggested(date)
        : l.transferRateManual;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          source,
          key: const Key('exchange-rate-source'),
          style: TextStyle(fontSize: _T.rateSheetCaptionSize, color: muted),
        ),
        if (form.suggestionActive && suggested?.inverted == true)
          Text(
            l.transferRateInverted,
            key: const Key('exchange-rate-inverted'),
            style: TextStyle(fontSize: _T.rateSheetCaptionSize, color: muted),
          ),
        if (form.loadingSuggestion)
          Text(
            l.transferRateLoading,
            key: const Key('exchange-rate-loading'),
            style: TextStyle(fontSize: _T.rateSheetCaptionSize, color: muted),
          ),
        if (form.suggestionError case final error?)
          Row(
            children: [
              Expanded(
                child: Text(
                  error.message(l),
                  key: const Key('exchange-rate-error'),
                  style: TextStyle(
                    fontSize: _T.rateSheetCaptionSize,
                    color: muted,
                  ),
                ),
              ),
              TextButton(onPressed: form.loadSuggestion, child: Text(l.retry)),
            ],
          ),
        const SizedBox(height: _T.rateSheetGap),
        Row(
          children: [
            Text(
              '1 ${form.displayFromCurrency} =',
              style: const TextStyle(fontSize: _T.rateSheetEquationSize),
            ),
            const SizedBox(width: _T.rateSheetEquationGap),
            Expanded(
              child: FormFilledField(
                key: const Key('exchange-rate-input'),
                controller: _input,
                hint: l.exchangeRate,
                icon: Icons.currency_exchange_rounded,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                inputFormatters: [
                  _RateTextFormatter(
                    decimalComma:
                        form.peruRate || l.localeName.startsWith('es'),
                  ),
                ],
                errorText:
                    (_attempted || form.invalidFields.contains('rate')) &&
                        !form.hasRate
                    ? l.requestInvalid
                    : null,
                onChanged: (value) {
                  _typing = true;
                  form.setDisplayedRate(value);
                  _typing = false;
                },
              ),
            ),
            const SizedBox(width: _T.rateSheetEquationGap),
            Text(
              form.displayToCurrency,
              style: const TextStyle(fontSize: _T.rateSheetEquationSize),
            ),
          ],
        ),
        const SizedBox(height: _T.rateSheetCaptionGap),
        Text(
          '× ${form.rateLabel}',
          key: const Key('exchange-rate-equivalent'),
          textAlign: TextAlign.end,
          style: TextStyle(fontSize: _T.rateSheetCaptionSize, color: muted),
        ),
        const SizedBox(height: _T.rateSheetPreviewGap),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Row(
            key: const Key('exchange-rate-preview'),
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                formatTypedAmount(
                  form.fromAmount,
                  form.from!.currency,
                  l.localeName,
                ),
                style: const TextStyle(
                  fontSize: _T.rateSheetPreviewSize,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: _T.rateSheetEquationGap),
              const Icon(
                Icons.arrow_forward_rounded,
                size: _T.rateSheetArrowSize,
              ),
              const SizedBox(width: _T.rateSheetEquationGap),
              Text(
                formatTypedAmount(
                  form.toAmount,
                  form.to!.currency,
                  l.localeName,
                ),
                style: const TextStyle(
                  fontSize: _T.rateSheetPreviewSize,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: _T.rateSheetPreviewGap),
        FormSheetButton(
          key: const Key('exchange-rate-apply'),
          label: l.transferRateApply,
          height: _T.amountSheetButtonHeight,
          onPressed: () {
            if (!form.hasRate) {
              setState(() => _attempted = true);
              return;
            }
            Navigator.of(context).pop();
          },
        ),
        if (form.isManualRate) ...[
          const SizedBox(height: _T.rateSheetCaptionGap),
          FormSheetButton(
            key: const Key('exchange-rate-suggested'),
            label: l.transferRateUseSuggested,
            height: _T.amountSheetButtonHeight,
            color: c.action,
            onPressed: suggested == null
                ? null
                : () {
                    form.useSuggestedRate();
                    _sync(force: true);
                  },
          ),
        ],
        const SizedBox(height: _T.rateSheetCaptionGap),
        TextButton(
          key: const Key('exchange-rate-all'),
          style: TextButton.styleFrom(foregroundColor: muted),
          // TODO(T-519): Monetae does not have an exchange-rate list yet.
          onPressed: () {},
          child: Text(l.transferRateViewAll),
        ),
      ],
    );
  }
}

/// Preserve the Peru-facing comma while using the existing exact input guard.
class _RateTextFormatter extends TextInputFormatter {
  _RateTextFormatter({required this.decimalComma});
  final bool decimalComma;
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final next = const DecimalTextFormatter(6)
        .formatEditUpdate(oldValue, newValue);
    return decimalComma
        ? next.copyWith(text: next.text.replaceAll('.', ','))
        : next;
  }
}
