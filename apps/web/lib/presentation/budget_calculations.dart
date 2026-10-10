import 'package:decimal/decimal.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import 'currency_format.dart';

final _zero = Decimal.zero;

/// Cashew port: returns the localized daily breakdown string for a budget.
String? budgetPerDayLabel(
  AppLocalizations l,
  BudgetDto budget,
  Decimal totalAmount,
  DateTime today,
) {
  if (budget.endOn == null) return null;
  final start = DateTime.parse(budget.startOn);
  final end = DateTime.parse(budget.endOn!);
  
  // Date only logic
  final todayDate = DateTime(today.year, today.month, today.day);
  final endDate = DateTime(end.year, end.month, end.day);
  final startDate = DateTime(start.year, start.month, start.day);

  if (todayDate.isAfter(endDate) || todayDate.isBefore(startDate)) {
    return null;
  }

  final remainingDays = endDate.difference(todayDate).inDays + 1;
  if (remainingDays <= 0) return null;

  final budgetAmount = Decimal.parse(budget.amount);
  final diff = totalAmount - budgetAmount;
  final polarity = Decimal.fromInt(-1);
  
  final amountPerDayRational = diff.toRational() / Decimal.fromInt(remainingDays).toRational() * polarity.toRational();
  
  final scaled = (amountPerDayRational * Decimal.fromInt(100).toRational()).ceil();
  final roundedAmount = (Decimal.fromBigInt(scaled) / Decimal.fromInt(100)).toDecimal(scaleOnInfinitePrecision: 2);

  final isOverBudget = roundedAmount < _zero;

  if (isOverBudget) {
    return l.budgetOver(
      formatCurrency(totalAmount.toStringAsFixed(2), budget.currency, l.localeName),
      formatCurrency(budgetAmount.toStringAsFixed(2), budget.currency, l.localeName),
    );
  }

  final absAmount = roundedAmount.abs().toStringAsFixed(2);
  final moneyStr = formatCurrency(absAmount, budget.currency, l.localeName);

  if (roundedAmount < _zero) {
    return l.budgetMustSavePerDay(moneyStr, remainingDays);
  } else {
    return l.budgetCanSpendPerDay(moneyStr, remainingDays);
  }
}

/// Cashew port: returns the localized daily breakdown string for a goal.
String? goalPerDayLabel(
  AppLocalizations l,
  GoalDto goal,
  DateTime today,
) {
  if (goal.dueOn == null) return null;

  final totalAmount = Decimal.parse(goal.progressAmount);
  final targetAmount = Decimal.parse(goal.targetAmount);

  if (totalAmount >= targetAmount) {
    return l.goalReached;
  }

  final end = DateTime.parse(goal.dueOn!);
  final todayDate = DateTime(today.year, today.month, today.day);
  final endDate = DateTime(end.year, end.month, end.day);

  final remainingDays = endDate.difference(todayDate).inDays + 1;
  if (remainingDays <= 0) {
    return l.goalOverdue;
  }

  final diff = totalAmount - targetAmount;
  final amountRational = diff.toRational() / Decimal.fromInt(remainingDays).toRational() * Decimal.fromInt(-1).toRational();
  
  final scaled = (amountRational * Decimal.fromInt(100).toRational()).ceil();
  final roundedAmount = (Decimal.fromBigInt(scaled) / Decimal.fromInt(100)).toDecimal(scaleOnInfinitePrecision: 2);

  final absAmount = roundedAmount.abs().toStringAsFixed(2);
  final moneyStr = formatCurrency(absAmount, goal.currency, l.localeName);

  return l.goalPerDay(moneyStr, remainingDays);
}
