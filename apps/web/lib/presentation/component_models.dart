import 'package:flutter/material.dart';

import '../data/api_dtos.dart';
import 'category_icon_source.dart';

enum AmountTone { income, expense, neutral, upcoming }

/// All labels, amounts and financial states are provided by the caller.
/// Widgets never convert currency or infer a loan's balance/state.
@immutable
class TransactionCardModel {
  const TransactionCardModel({
    required this.transaction,
    required this.category,
    required this.account,
    required this.amountLabel,
    required this.subtitle,
    required this.dateKey,
    required this.dateLabel,
    required this.timeLabel,
    required this.icon,
    required this.categoryColor,
    required this.tone,
    required this.typeLabel,
    this.secondaryAmountLabel,
    this.tags = const [],
  });

  final TransactionDto transaction;
  final CategoryDto? category;
  final AccountDto account;
  final String amountLabel;
  final String? secondaryAmountLabel;
  final String subtitle;
  final String dateKey;
  final String dateLabel;
  final String timeLabel;
  final CategoryIconSource icon;
  final Color categoryColor;
  final AmountTone tone;
  final String typeLabel;
  final List<String> tags;
}

/// Nonfinancial, normalized chart geometry and already formatted labels.
@immutable
class CategorySlice {
  const CategorySlice({
    required this.id,
    required this.label,
    required this.weight,
    required this.percentLabel,
    required this.amountLabel,
    required this.color,
    required this.icon,
  }) : assert(weight >= 0 && weight <= 1);

  final String id;
  final String label;
  final double weight;
  final String percentLabel;
  final String amountLabel;
  final Color color;
  final CategoryIconSource icon;
}
