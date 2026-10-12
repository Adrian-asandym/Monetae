import 'package:flutter/material.dart';

Color pastel(Color color, Brightness brightness, double amount) =>
    Color.alphaBlend(
      (brightness == Brightness.light ? Colors.white : Colors.black).withValues(
        alpha: amount,
      ),
      color,
    );

@immutable
class MonetaeColors extends ThemeExtension<MonetaeColors> {
  const MonetaeColors({
    required this.card,
    required this.background,
    required this.muted,
    required this.income,
    required this.expense,
    required this.upcoming,
    required this.overdue,
    required this.divider,
    required this.selectedPill,
  });

  final Color card;
  final Color background;
  final Color muted;
  final Color income;
  final Color expense;
  final Color upcoming;
  final Color overdue;
  final Color divider;
  final Color selectedPill;

  static MonetaeColors of(BuildContext context) =>
      Theme.of(context).extension<MonetaeColors>()!;

  @override
  MonetaeColors copyWith({
    Color? card,
    Color? background,
    Color? muted,
    Color? income,
    Color? expense,
    Color? upcoming,
    Color? overdue,
    Color? divider,
    Color? selectedPill,
  }) => MonetaeColors(
    card: card ?? this.card,
    background: background ?? this.background,
    muted: muted ?? this.muted,
    income: income ?? this.income,
    expense: expense ?? this.expense,
    upcoming: upcoming ?? this.upcoming,
    overdue: overdue ?? this.overdue,
    divider: divider ?? this.divider,
    selectedPill: selectedPill ?? this.selectedPill,
  );

  @override
  MonetaeColors lerp(covariant MonetaeColors? other, double t) {
    if (other == null) return this;
    return MonetaeColors(
      card: Color.lerp(card, other.card, t)!,
      background: Color.lerp(background, other.background, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      income: Color.lerp(income, other.income, t)!,
      expense: Color.lerp(expense, other.expense, t)!,
      upcoming: Color.lerp(upcoming, other.upcoming, t)!,
      overdue: Color.lerp(overdue, other.overdue, t)!,
      divider: Color.lerp(divider, other.divider, t)!,
      selectedPill: Color.lerp(selectedPill, other.selectedPill, t)!,
    );
  }
}

ThemeData monetaeTheme({
  required Brightness brightness,
  Color accent = const Color(0xFFE0E0E0), // Neutral accent
}) {
  final light = brightness == Brightness.light;

  // Neutral backgrounds per skill:
  final background = light ? Colors.white : const Color(0xFF121212);
  final card = light ? const Color(0xFFF5F5F5) : const Color(0xFF1E1E1E);
  final selectedPill = light
      ? const Color(0xFFE0E0E0)
      : const Color(0xFF3A3A3A);

  final colors = MonetaeColors(
    background: background,
    card: card,
    muted: (light ? Colors.black : Colors.white).withValues(alpha: 0.60),
    income: light
        ? const Color(0xFF4CAF50)
        : const Color(0xFF4CAF50), // Cashew green
    expense: light
        ? const Color(0xFFE57373)
        : const Color(0xFFE57373), // Cashew red/coral
    upcoming: light ? const Color(0xFF58A4C2) : const Color(0xFF7DB6CC),
    overdue: light ? const Color(0xFF6577E0) : const Color(0xFF8395FF),
    divider: light ? const Color(0x0F000000) : const Color(0x13FFFFFF),
    selectedPill: selectedPill,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    fontFamily: 'DM Sans',
    colorScheme: ColorScheme.fromSeed(
      seedColor: accent,
      brightness: brightness,
    ).copyWith(surface: background),
    scaffoldBackgroundColor: background,
    extensions: [colors],
    dividerColor: colors.divider,
  );
}

/// Presentation tokens calibrated from Cashew's AddButton and Home carousels.
abstract final class HomeTokens {
  static const cardRadius = 20.0;
  static const carouselGap = 13.0;
  static const goalDesktopWidth = 400.0;
  static const budgetDesktopWidth = 500.0;
  static const desktopBreakpoint = 650.0;
  static const mobileCardFraction = .95;
  static const emptyCardHeight = 160.0;
  static const addBorderWidth = 1.5;
  static const addBorderOpacity = .35;
  static const addIconSize = 22.0;
  static const addLabelSize = 14.0;
  static const addLabelGap = 2.0;
  static const categoryCardHeight = 280.0;
  static const categoryPadding = 16.0;
  static const categoryPieSize = 208.0;
  static const emptyRingOpacity = .15;
  static const categoryPieFraction = .65;
  static const categoryPieTop = 12.0;
  static const categoryLegendFraction = .30;
  static const categoryTriangleSize = 32.0;
  static const legendGap = 4.0;
  static const legendDotTop = 3.0;
  static const legendDotSize = 10.0;
  static const legendDotGap = 8.0;
  static const legendFontSize = 12.0;
  static const pageDotGap = 8.0;
  static const pageDotSize = 8.0;
  static const pageDotSpacing = 4.0;
  static const activeDotOpacity = .60;
  static const inactiveDotOpacity = .20;
  static const pageSwitchMilliseconds = 250;
  static const linePlotHeight = 175.0;
  static const lineBottomTitleHeight = 30.0;
  static const lineLabelHeight = 18.0;
  static const lineChartHeight =
      linePlotHeight + lineBottomTitleHeight + lineLabelHeight / 2;
  static const lineAxisWidth = 64.0;
  static const lineAxisGap = 8.0;
  static const lineLeftPadding = 12.0;
  static const lineTopPadding = 18.0;
  static const lineRightPadding = 7.0;
  static const lineBottomPadding = 12.0;
  static const lineDateGap = 8.0;
  static const lineFontSize = 12.0;
  static const lineLabelOpacity = .5;
  static const lineGridOpacity = .12;
  static const lineZeroOpacity = .24;
  static const lineGridWidth = 2.0;
  static const lineZeroWidth = 1.0;
  static const lineStrokeWidth = 2.0;
  static const lineGridDashes = [2, 8];
  static const lineZeroEpsilon = .000001;
  static const lineTooltipRadius = 8.0;
  static const lineAnimationMilliseconds = 1500;
  static const editWidth = 114.0;
  static const editHeight = 45.0;
  static const editRadius = 14.0;
  static const editPadding = 12.0;
  static const editIconSize = 22.0;
  static const editGap = 8.0;
  static const editFontSize = 14.0;
}

/// Transaction form colors sampled from Cashew web (dark, 400×642 at 1.25×)
/// in reference captures 11–19; light values mirror Cashew's light palette.
@immutable
class TransactionFormColors {
  const TransactionFormColors._({
    required this.header,
    required this.headerCategoryName,
    required this.tabIdle,
    required this.emptyCategory,
    required this.dateBox,
    required this.dateIcon,
    required this.timeBox,
    required this.field,
    required this.fieldDivider,
    required this.chipSelected,
    required this.chipBorder,
    required this.pill,
    required this.card,
    required this.sheet,
    required this.keypad,
    required this.action,
    required this.sheetAction,
    required this.onAction,
    required this.onCategory,
    required this.neutralCategory,
    required this.switchTrack,
    required this.switchThumb,
    required this.typeText,
    required this.menuSubtitle,
    required this.transferBackground,
    required this.transferCard,
    required this.transferDialog,
    required this.transferMuted,
    required this.transferAmount,
  });

  final Color header;
  final Color headerCategoryName;
  final Color tabIdle;
  final Color emptyCategory;
  final Color dateBox;
  final Color dateIcon;
  final Color timeBox;
  final Color field;
  final Color fieldDivider;
  final Color chipSelected;
  final Color chipBorder;
  final Color pill;
  final Color card;
  final Color sheet;
  final Color keypad;
  final Color action;
  final Color sheetAction;
  final Color onAction;
  final Color onCategory;
  final Color neutralCategory;
  final Color switchTrack;
  final Color switchThumb;
  final Color typeText;
  final Color menuSubtitle;
  final Color transferBackground,
      transferCard,
      transferDialog,
      transferMuted,
      transferAmount;

  static const _dark = TransactionFormColors._(
    header: Color(0xFF33383A),
    headerCategoryName: Color(0xB3FFFFFF),
    tabIdle: Color(0xFF242729),
    emptyCategory: Color(0xFF242424),
    dateBox: Color(0xFF181818),
    dateIcon: Color(0xFF424242),
    timeBox: Color(0xFF242424),
    field: Color(0xFF424242),
    fieldDivider: Color(0xFF4E4E4E),
    chipSelected: Color(0xFF424242),
    chipBorder: Color(0xFF646464),
    pill: Color(0xFF1F2021),
    card: Color(0xFF323232),
    sheet: Color(0xFF2E2E2E),
    keypad: Color(0xFF424242),
    action: Color(0xFF7B8C94),
    sheetAction: Color(0xFF96A2A8),
    onAction: Color(0xFF000000),
    onCategory: Color(0xFFFFFFFF),
    neutralCategory: Color(0xFF424242),
    switchTrack: Color(0xFF707C81),
    switchThumb: Color(0xFFBAC8CF),
    typeText: Color(0xFFFFFFFF),
    menuSubtitle: Color(0xCCFFFFFF),
    transferBackground: Color(0xFF0F0F0F),
    transferCard: Color(0xFF1A1C1D),
    transferDialog: Color(0xFF212121),
    transferMuted: Color(0xFF666868),
    transferAmount: Color(0xFF2E2F2F),
  );

  static const _light = TransactionFormColors._(
    header: Color(0xFFDDE3E6),
    headerCategoryName: Color(0xB3000000),
    tabIdle: Color(0xFFEEF1F2),
    emptyCategory: Color(0xFFE0E0E0),
    dateBox: Color(0xFFF2F2F2),
    dateIcon: Color(0xFFDDDDDD),
    timeBox: Color(0xFFE6E6E6),
    field: Color(0xFFEBEBEB),
    fieldDivider: Color(0xFFD6D6D6),
    chipSelected: Color(0xFFD5D5D5),
    chipBorder: Color(0xFFB5B5B5),
    pill: Color(0xFFEDEFF0),
    card: Color(0xFFEBEBEB),
    sheet: Color(0xFFF7F7F7),
    keypad: Color(0xFFEBEBEB),
    action: Color(0xFFB0BEC5),
    sheetAction: Color(0xFFB0BEC5),
    onAction: Color(0xFF000000),
    onCategory: Color(0xFFFFFFFF),
    neutralCategory: Color(0xFF757575),
    switchTrack: Color(0xFF78909C),
    switchThumb: Color(0xFFFFFFFF),
    typeText: Color(0xFF121212),
    menuSubtitle: Color(0xCC121212),
    transferBackground: Color(0xFFFFFFFF),
    transferCard: Color(0xFFF2F3F3),
    transferDialog: Color(0xFFF0F0F0),
    transferMuted: Color(0xFF666868),
    transferAmount: Color(0xFFE2E5E5),
  );

  static TransactionFormColors of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? _dark : _light;
}

/// Transaction form sizes in dp, calibrated from Cashew addTransactionPage,
/// selectChips, selectAmount and captures 11–19 (1 dp = 1.25 px).
abstract final class TransactionFormTokens {
  // Captures 24–25, right viewport 500 px / 400 dp = 1.25 px per dp.
  // The local Cashew TransferBalancePopup predates this card-based screen.
  // Piece 11: reuse sheet typography/spacing from captures 11 and 16;
  // capture 24 only shows the multiplicative rate control, not this sheet.
  static const rateSheetGap = 16.0;
  static const rateSheetCaptionGap = 8.0;
  static const rateSheetEquationGap = 8.0;
  static const rateSheetCaptionSize = 14.0;
  static const rateSheetEquationSize = 16.0;
  static const rateSheetPreviewGap = 20.0;
  static const rateSheetArrowSize = 22.0;
  static const rateSheetPreviewSize = 24.0;
  static const transferInset = 13.0;
  static const transferTop = 17.0;
  static const transferCardHeight = 96.0;
  static const transferCardRadius = 15.0;
  static const transferBorder = 2.0;
  static const transferCardPadding = 15.0;
  static const transferNameHeight = 1.0;
  static const transferNameSize = 18.0;
  static const transferBalanceSize = 14.0;
  static const transferAmountMaxWidth = 180.0;
  static const transferDirectionSize = 22.0;
  static const transferAmountSize = 30.0;
  static const transferAmountRadius = 12.0;
  static const transferAmountPadding = 8.0;
  static const transferAmountHeight = 42.0;
  static const transferControlHeight = 60.0;
  static const transferSwapSize = 40.0;
  static const transferClearSize = 34.0;
  static const transferRateWidth = 110.0;
  static const transferRateSize = 18.0;
  static const transferRateHeight = 34.0;
  static const transferDetailsGap = 28.0;
  static const transferDetailInset = 16.0;
  static const transferTitleGap = 12.0;
  static const transferArrivalSize = 12.0;
  static const transferPillTop = 22.0;
  static const transferDialogInset = 20.0;
  static const transferDialogRadius = 28.0;
  static const transferDialogIconSize = 56.0;
  static const transferDialogTitleSize = 24.0;
  static const transferDialogBodySize = 17.0;
  static const transferDialogLineHeight = 1.18;
  static const transferDialogIconGap = 22.0;
  static const transferDialogTextGap = 16.0;
  static const transferDialogButtonGap = 10.0;
  static const transferDialogActionTop = 26.0;
  static const transferDialogButtonHeight = 48.0;
  static const transferDialogPadding = 26.0;

  static const maxWidth = 560.0;
  static const sidePadding = 20.0;
  static const titleSize = 20.0;
  static const tabHeight = 50.0;
  static const tabFontSize = 16.0;
  static const headerHeight = 136.0;
  static const categorySquare = 80.0;
  static const categoryRadius = 15.0;
  static const categoryIconSize = 44.0;
  static const amountFontSize = 36.0;
  static const headerCategoryNameSize = 20.0;
  static const headerCategoryNameHeight = 1.0;
  static const dateHeight = 53.0;
  static const dateRadius = 15.0;
  static const dateIconBox = 35.0;
  static const dateFontSize = 24.0;
  static const timeFontSize = 20.0;
  static const timeBoxWidth = 30.0;
  static const timeBoxRadius = 6.0;
  static const captionSize = 12.0;
  static const chipHeight = 30.0;
  static const chipRadius = 8.0;
  static const chipBorder = 1.5;
  static const chipFontSize = 15.0;
  static const chipGap = 10.0;
  static const chipPadding = 12.0;
  static const rowGap = 15.0;
  static const fieldHeight = 38.0;
  static const fieldRadius = 14.0;
  static const fieldFontSize = 16.0;
  static const notesHeight = 87.0;
  static const attachmentHeight = 41.0;
  static const pillRadius = 12.0;
  static const pillHeight = 38.0;
  static const pillFontSize = 15.0;
  static const actionHeight = 50.0;
  static const actionRadius = 28.0;
  static const actionFontSize = 17.0;
  static const sheetRadius = 28.0;
  static const sheetPadding = 16.0;
  static const sheetTitleSize = 26.0;
  static const sheetButtonHeight = 40.0;
  static const sheetButtonRadius = 20.0;
  static const sheetFieldGap = 20.0;
  static const expandedSheetHeightFraction = .95;
  static const expandedSheetHeadingTop = 20.0;
  static const expandedSheetHeadingGap = 14.0;
  static const categoryGridColumns = 4;
  static const categoryGridSquare = 64.0;
  static const categoryGridRadius = 14.0;
  static const categoryGridIconSize = 40.0;
  static const categoryGridLabelSize = 12.0;
  static const categoryGridLabelHeight = 1.0;
  static const categoryGridInset = 12.0;
  static const categoryGridLabelGap = 4.0;
  static const categoryGridGap = 9.0;
  static const categoryGridTileHeight = 82.0;
  static const categoryGridBorderWidth = 3.0;
  static const keypadRowHeight = 57.0;
  static const keypadRadius = 24.0;
  static const keypadFontSize = 30.0;
  static const keypadPadding = 6.0;
  static const keypadBackspaceSize = 26.0;
  static const amountSheetFontSize = 40.0;
  static const amountSheetLineHeight = 1.2;
  static const amountSheetGap = 12.0;
  static const amountSheetActionGap = 16.0;
  static const amountSheetAccountInset = 4.0;
  static const amountSheetButtonHeight = 48.0;
  static const accountSheetHeightFraction = .65;
  static const accountRowHeight = 48.0;
  static const accountRowRadius = 12.0;
  static const accountRowPadding = 16.0;
  static const accountRowGap = 12.0;
  static const accountNameSize = 20.0;
  static const accountBalanceSize = 18.0;
  static const accountRadioSize = 20.0;
  static const accountRadioBorder = 2.0;
  static const accountRadioFillSize = 10.0;
  static const accountSelectionOpacity = .33;
  static const accountHoverOpacity = .04;
  static const menuListInset = 0.0;
  static const menuHeadingSize = 23.0;
  static const menuHeadingTop = 19.0;
  static const menuHeadingGap = 13.0;
  static const menuBottomPadding = 16.0;
  static const menuRowHorizontalPadding = 16.0;
  static const menuRowVerticalPadding = 12.0;
  static const menuIconSize = 28.0;
  static const menuIconGap = 16.0;
  static const menuTitleSize = 16.0;
  static const menuSubtitleSize = 14.0;
  static const menuTextHeight = 1.2;
  static const menuSubtitleGap = 3.0;
  static const menuTrailingGap = 5.0;
  static const menuChevronWidth = 52.0;
  static const moreDividerHeight = 20.0;
  static const moreDividerLabelGap = 10.0;
  static const moreDividerThickness = 1.0;
  static const optionGap = 12.0;
  static const optionSectionGap = 16.0;
  static const optionLabelGap = 8.0;
  static const optionIconSize = 26.0;
  static const optionLabelSize = 18.0;
  static const optionLabelHeight = 1.2;
  static const formBottomPadding = 24.0;
  static const optionsBottomPadding = 56.0;
  static const optionCardHeight = 62.0;
  static const optionCardRadius = 16.0;
  static const typeSheetInset = 12.0;
  static const typeCardRadius = 16.0;
  static const typeCardBorder = 1.5;
  static const typeCardPadding = 20.0;
  static const typeCardGap = 14.0;
  static const typeCardIconSize = 26.0;
  static const typeCardTitleSize = 22.0;
  static const typeCardTitleHeight = 1.2;
  static const typeCardIconGap = 12.0;
  static const typeBulletSize = 15.0;
  static const typeBulletHeight = 1.25;
  static const typeBulletGap = 2.0;
  static const typeBulletIndent = 14.0;
  static const typeDescriptionGap = 14.0;
  static const typeMenuSize = 26.0;
  static const typeHelpFontSize = 16.0;
  static const typeHelpGap = 18.0;
  static const typeHelpActionSize = 35.0;
  static const typeHelpActionIconSize = 23.0;
  static const typeHelpActionGap = 10.0;
  static const typeExamplePadding = 12.0;
  static const typeExampleAvatarSize = 48.0;
  static const typeExampleHighlightBorder = 2.0;
  static const typeExampleAmountSize = 20.0;
  static const typeExampleNoteSize = 20.0;
  static const typeExampleAccountRadius = 4.0;
  static const typeExampleAccountInset = 4.0;
  static const typeNoticeTop = 6.0;
  static const typeSheetHeightFraction = .985;
  static const typeSheetHeadingTop = 0.0;
}
