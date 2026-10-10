// Derived from Cashew budget/lib/pages/homePage/{homePageBudgets,
// homePageObjectives}.dart and pages/{budgetsListPage,objectivesListPage}.dart.
// Copyright (C) 2023 James Kokoska, GPL-3.0.
// Modified for Monetae on 2026-10-09: controlled typed lists, native scrolling,
// intrinsic heights, translated empty states and optional creation callbacks.
import 'dart:typed_data';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../data/api_dtos.dart';
import '../l10n/app_localizations.dart';
import '../theme/monetae_theme.dart';
import 'budget_card.dart';
import 'goal_card.dart';

class BudgetCardList extends StatelessWidget {
  const BudgetCardList({
    super.key,
    required this.budgets,
    this.axis = Axis.horizontal,
    this.today,
    this.onSelected,
    this.onCreate,
  });
  final List<BudgetDto> budgets;
  final Axis axis;
  final DateTime? today;
  final ValueChanged<BudgetDto>? onSelected;
  final VoidCallback? onCreate;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return _CardStrip(
      axis: axis,
      desktopWidth: HomeTokens.budgetDesktopWidth,
      emptyLabel: l.emptyBudgets,
      createLabel: l.addBudgetLabel,
      onCreate: onCreate,
      cards: [
        for (final budget in budgets)
          BudgetCard(
            key: ValueKey(budget.id),
            budget: budget,
            today: today,
            onTap: onSelected == null ? null : () => onSelected!(budget),
          ),
      ],
    );
  }
}

class GoalCardList extends StatelessWidget {
  const GoalCardList({
    super.key,
    required this.goals,
    this.axis = Axis.horizontal,
    this.customIcons = const {},
    this.tintCustomIcons = false,
    this.onSelected,
    this.onCreate,
  });
  final List<GoalDto> goals;
  final Axis axis;
  final Map<String, Uint8List> customIcons;
  final bool tintCustomIcons;
  final ValueChanged<GoalDto>? onSelected;
  final VoidCallback? onCreate;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return _CardStrip(
      axis: axis,
      desktopWidth: HomeTokens.goalDesktopWidth,
      emptyLabel: l.emptyGoals,
      createLabel: l.addGoalLabel,
      onCreate: onCreate,
      cards: [
        for (final goal in goals)
          GoalCard(
            key: ValueKey(goal.id),
            goal: goal,
            customIcons: customIcons,
            tintCustomIcon: tintCustomIcons,
            onTap: onSelected == null ? null : () => onSelected!(goal),
          ),
      ],
    );
  }
}

class _CardStrip extends StatelessWidget {
  const _CardStrip({
    required this.axis,
    required this.desktopWidth,
    required this.cards,
    required this.emptyLabel,
    required this.createLabel,
    required this.onCreate,
  });
  final Axis axis;
  final double desktopWidth;
  final List<Widget> cards;
  final String emptyLabel;
  final String createLabel;
  final VoidCallback? onCreate;

  Widget _empty(BuildContext context, {required bool empty}) => Material(
    color: MonetaeColors.of(context).card,
    borderRadius: BorderRadius.circular(15),
    child: InkWell(
      onTap: onCreate,
      borderRadius: BorderRadius.circular(15),
      child: Container(
        constraints: const BoxConstraints(minHeight: 160),
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              onCreate == null
                  ? Icons.format_list_bulleted_rounded
                  : Icons.format_list_bulleted_add,
              size: 36,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 8),
            Text(empty ? emptyLabel : createLabel, textAlign: TextAlign.center),
            if (empty && onCreate != null) ...[
              const SizedBox(height: 8),
              Text(createLabel),
            ],
          ],
        ),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    if (axis == Axis.vertical && cards.isEmpty) {
      return _empty(context, empty: true);
    }
    final items = [
      ...cards,
      if (axis == Axis.horizontal)
        HomeAddCard(label: createLabel, onTap: onCreate)
      else if (onCreate != null)
        _empty(context, empty: false),
    ];
    if (axis == Axis.vertical) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < items.length; i++) ...[
            if (i > 0) const SizedBox(height: 16),
            items[i],
          ],
        ],
      );
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth >= HomeTokens.desktopBreakpoint
            ? desktopWidth
            : constraints.maxWidth * HomeTokens.mobileCardFraction;
        return ScrollConfiguration(
          behavior: ScrollConfiguration.of(context).copyWith(
            dragDevices: {
              PointerDeviceKind.touch,
              PointerDeviceKind.mouse,
              PointerDeviceKind.trackpad,
            },
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: _EqualHeightRow(
              children: [
                for (var i = 0; i < items.length; i++) ...[
                  if (i > 0) const SizedBox(width: HomeTokens.carouselGap),
                  SizedBox(
                    width: width,
                    child: cards.isEmpty
                        ? SizedBox(
                            height: HomeTokens.emptyCardHeight,
                            child: items[i],
                          )
                        : items[i],
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}

/// Cashew pages/addButton.dart: transparent list-plus card, placed last.
class HomeAddCard extends StatelessWidget {
  const HomeAddCard({super.key, required this.label, this.onTap});
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = MonetaeColors.of(context);
    final radius = BorderRadius.circular(HomeTokens.cardRadius);
    return Material(
      color: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: BorderSide(
          width: HomeTokens.addBorderWidth,
          color: Theme.of(context).colorScheme.onSurface
              .withValues(alpha: HomeTokens.addBorderOpacity),
        ),
      ),
      child: InkWell(
        borderRadius: radius,
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.format_list_bulleted_add,
              size: HomeTokens.addIconSize,
              color: colors.muted,
            ),
            const SizedBox(height: HomeTokens.addLabelGap),
            Text(
              label,
              style: TextStyle(
                fontSize: HomeTokens.addLabelSize,
                color: colors.muted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Lay out real card content first, then match every tile to the tallest card.
/// Unlike IntrinsicHeight this supports the progress bar's LayoutBuilder.
class _EqualHeightRow extends MultiChildRenderObjectWidget {
  const _EqualHeightRow({required super.children});

  @override
  RenderObject createRenderObject(BuildContext context) =>
      _EqualHeightFlex(Directionality.of(context));

  @override
  void updateRenderObject(BuildContext context, _EqualHeightFlex renderObject) {
    renderObject.textDirection = Directionality.of(context);
  }
}

class _EqualHeightFlex extends RenderFlex {
  _EqualHeightFlex(TextDirection textDirection)
    : super(
        direction: Axis.horizontal,
        crossAxisAlignment: CrossAxisAlignment.start,
        textDirection: textDirection,
      );

  @override
  void performLayout() {
    super.performLayout();
    var child = firstChild;
    while (child != null) {
      child.layout(
        BoxConstraints.tightFor(width: child.size.width, height: size.height),
      );
      child = childAfter(child);
    }
  }
}
