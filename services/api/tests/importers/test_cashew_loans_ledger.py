"""Contrato ADR-008 con la fixture pública sintética y PostgreSQL real."""

from dataclasses import replace
from decimal import Decimal
from typing import cast

import pytest
from pydantic import JsonValue, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import (
    Account,
    ImportReviewItem,
    Loan,
    LoanMovement,
    Person,
    Transaction,
    TransactionTag,
    User,
)
from monetae.domain.currency import Currency
from monetae.domain.loans import Movement, MovementKind, replay
from monetae.domain.money import Money
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import Snapshot, TagLinkRow
from monetae.importers.cashew.runner import run_import

from .conftest import FIXTURES

EXPECTED = TypeAdapter(dict[str, JsonValue]).validate_json(
    (FIXTURES / "expected.json").read_bytes()
)
ROW_MAP = cast(dict[str, str], EXPECTED["row_map"])
CASES = cast(dict[str, dict[str, JsonValue]], EXPECTED["loan_cases"])


def loan_for(session: Session, user: User, case: str) -> Loan:
    identity = (
        external_id("objective:" + cast(str, CASES[case]["objective_pk"]))
        if case in CASES
        else external_id("tx:" + ROW_MAP[case])
    )
    loan = session.scalar(
        select(Loan).where(Loan.user_id == user.id, Loan.import_external_id == identity)
    )
    assert loan is not None
    return loan


def movements(session: Session, loan: Loan) -> list[Movement]:
    currency = Currency(loan.currency)
    return [
        Movement(
            MovementKind(row.kind),
            Money(row.amount_in_loan_currency, currency),
            row.occurred_at,
            row.sequence,
            Money(row.interest_part, currency) if row.interest_part is not None else None,
            Money(row.principal_part, currency) if row.principal_part is not None else None,
        )
        for row in session.scalars(
            select(LoanMovement)
            .where(LoanMovement.user_id == loan.user_id, LoanMovement.loan_id == loan.id)
            .order_by(LoanMovement.occurred_at, LoanMovement.sequence)
        )
    ]


def financial_rows(session: Session, user: User) -> dict[str, list[dict[str, object]]]:
    return {
        model.__tablename__: [
            {c.name: getattr(row, c.name) for c in model.__table__.columns}
            for row in session.scalars(
                select(model).where(model.user_id == user.id).order_by(model.id)
            )
        ]
        for model in (Account, Person, Loan, LoanMovement, Transaction, TransactionTag)
    }


def tx_for(session: Session, user: User, name: str, suffix: str = "") -> Transaction:
    tx = session.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.import_external_id == external_id(ROW_MAP[name]) + suffix,
        )
    )
    assert tx is not None
    return tx


def test_adr_fixture_books_cash_and_p1_p2_p3(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.steps["loans"]["created"] == 7
    assert report.steps["loans"]["deferred"] == 0
    assert report.steps["loans"]["invalid"] == 0
    assert report.steps["loans"]["movements"] == {
        "disbursement": 7,
        "payment": 10,
        "interest": 0,
        "adjustment": 0,
        "write_off": 0,
    }
    assert all(b.unexplained == Decimal("0.00") for b in report.balances)
    wallets = cast(list[dict[str, JsonValue]], EXPECTED["wallets"])
    for balance in report.balances:
        expected = next(w for w in wallets if w["wallet_pk"] == balance.source_wallet_pk)
        assert balance.monetae_balance + balance.deferred_amount == Decimal(
            cast(str, expected["balance"])
        )
    for case, amounts, running, status in [
        ("A", [100, 100], [200, 100, 0], "settled"),
        ("B", [300, 200], [500, 200, 0], "settled"),
        ("C", [], [100], "open"),
        ("D", [50], [50, 0], "settled"),
        ("E", [50, 120, 30, 800], [1000, 950, 830, 800, 0], "settled"),
        ("F_settled", [150], [150, 0], "settled"),
        ("F_open", [], [80], "open"),
    ]:
        loan = loan_for(db_session, import_user, case)
        ledger = movements(db_session, loan)
        state = replay(Money(loan.principal, Currency(loan.currency)), ledger)
        assert state.status == status
        assert [m.amount.amount for m in ledger if m.kind == MovementKind.PAYMENT] == amounts
        assert [m.amount for m in state.running] == running
        assert loan.deleted_at is None
        assert (
            "outstanding" not in Loan.__table__.columns and "status" not in Loan.__table__.columns
        )
        assert [m.sequence for m in ledger] == list(range(len(ledger)))
        for index, movement in enumerate(ledger):
            if movement.kind == MovementKind.PAYMENT:
                assert movement.interest_part is not None and movement.principal_part is not None
                assert movement.interest_part + movement.principal_part == movement.amount
            assert replay(
                Money(loan.principal, Currency(loan.currency)), ledger[: index + 1]
            ).status == ("settled" if state.running[index].is_zero() else "open")
    assert loan_for(db_session, import_user, "A").direction == "borrowed"
    assert loan_for(db_session, import_user, "F_open").direction == "borrowed"
    for case, expected_amount, expected_kind in [
        ("A_payment_2", Decimal("-10"), "expense"),
        ("D_payment_1", Decimal("10"), "income"),
    ]:
        original = next(r for r in snapshot.transactions if r.pk == ROW_MAP[case])
        payment = tx_for(db_session, import_user, case)
        excess = tx_for(db_session, import_user, case, ":excess")
        assert payment.kind == "loan" and payment.category_id is None
        assert (
            excess.kind == expected_kind
            and excess.amount == expected_amount
            and excess.category_id is None
        )
        assert payment.amount + excess.amount == original.amount
    assert (
        tx_for(db_session, import_user, "B_payment_1").account_id
        != tx_for(db_session, import_user, "B_payment_2").account_id
    )
    assert tx_for(db_session, import_user, "A_interest").kind == "expense"
    assert tx_for(db_session, import_user, "C_payment_1").kind == "income"
    assert (
        tx_for(db_session, import_user, "F_settled").amount
        + tx_for(db_session, import_user, "F_settled", ":synthesized_payment").amount
        == 0
    )
    assert {item.kind for item in report.review_items} >= {
        "synthesized_payment",
        "overpayment_detected",
        "orphan_interest",
        "fx_rate_required",
        "provisional_person",
    }


def test_fx_second_pass_then_idempotence_and_dry_run(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    loan = loan_for(db_session, import_user, "C")
    transaction = tx_for(db_session, import_user, "C_payment_1")
    before = financial_rows(db_session, import_user)
    conversion = replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.800000")})
    dry = run_import(db_session, import_user.id, snapshot, replace(conversion, dry_run=True))
    assert dry.steps["loans"]["resolved_fx"] == 1
    assert financial_rows(db_session, import_user) == before
    reviews = list(
        db_session.scalars(
            select(ImportReviewItem).where(
                ImportReviewItem.user_id == import_user.id,
                ImportReviewItem.kind == "fx_rate_required",
            )
        )
    )
    assert reviews and all(r.resolved_at is None for r in reviews)
    report = run_import(db_session, import_user.id, snapshot, conversion)
    assert report.steps["loans"]["created"] == 0 and report.steps["loans"]["resolved_fx"] == 1
    assert report.counts["transactions"].created == 0
    assert tx_for(db_session, import_user, "C_payment_1").id == transaction.id
    assert transaction.kind == "loan" and transaction.amount == Decimal("380")
    assert (
        replay(Money(loan.principal, Currency(loan.currency)), movements(db_session, loan)).status
        == "settled"
    )
    payment = db_session.scalar(
        select(LoanMovement).where(
            LoanMovement.user_id == import_user.id, LoanMovement.transaction_id == transaction.id
        )
    )
    assert payment is not None and payment.fx_rate_applied == Decimal("3.800000")
    assert payment.amount_in_loan_currency == Decimal("100")
    assert all(r.resolved_at is not None for r in reviews)
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, conversion)
    assert all(c.created == 0 for c in second.counts.values())
    assert second.steps["loans"]["modified"] == 0
    assert financial_rows(db_session, import_user) == before
    assert all(b.unexplained == 0 for b in second.balances)


def test_first_pass_with_explicit_fx(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    report = run_import(
        db_session,
        import_user.id,
        snapshot,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.8")}),
    )
    loan = loan_for(db_session, import_user, "C")
    assert (
        replay(Money(loan.principal, Currency(loan.currency)), movements(db_session, loan)).status
        == "settled"
    )
    assert not any(i.kind == "fx_rate_required" for i in report.review_items)
    assert all(b.unexplained == 0 for b in report.balances)


def test_invalid_objective_keeps_cash_and_other_books(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    changed = replace(
        snapshot,
        transactions=tuple(r for r in snapshot.transactions if r.pk != ROW_MAP["B_disbursement"]),
    )
    report = run_import(db_session, import_user.id, changed, options)
    assert report.steps["loans"]["created"] == 6 and report.steps["loans"]["invalid"] == 1
    assert any(
        i.kind == "ledger_invalid" and i.payload["objective_pk"] == CASES["B"]["objective_pk"]
        for i in report.review_items
    )
    assert tx_for(db_session, import_user, "B_payment_1").kind == "income"
    assert tx_for(db_session, import_user, "B_payment_2").kind == "income"
    assert all(b.unexplained == 0 for b in report.balances)
    assert (
        db_session.scalar(
            select(Loan.id).where(
                Loan.user_id == import_user.id,
                Loan.import_external_id
                == external_id("objective:" + cast(str, CASES["B"]["objective_pk"])),
            )
        )
        is None
    )


def test_people_alias_normalization_and_shared_person(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    person = Person(
        user_id=import_user.id, name="Otra persona sintética", aliases=["PÉRSONA EJEMPLO B"]
    )
    db_session.add(person)
    db_session.flush()
    same = replace(
        snapshot,
        objectives=tuple(
            replace(o, name=" persona Ejemplo B ") if o.pk == CASES["E"]["objective_pk"] else o
            for o in snapshot.objectives
        ),
    )
    run_import(db_session, import_user.id, same, options)
    assert loan_for(db_session, import_user, "B").person_id == person.id
    assert loan_for(db_session, import_user, "E").person_id == person.id
    created = db_session.get(Person, loan_for(db_session, import_user, "A").person_id)
    assert created is not None and created.note == "Creada por la importación de Cashew; revisar"
    assert created.import_external_id == "cashew:sqlite:person:persona ejemplo a"


def test_imported_books_are_isolated_between_users(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    second_user = User(email="loans-other@example.test", base_currency="PEN", report_currency="PEN")
    db_session.add(second_user)
    db_session.flush()
    run_import(db_session, import_user.id, snapshot, options)
    before = financial_rows(db_session, import_user)
    run_import(
        db_session,
        second_user.id,
        snapshot,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.8")}),
    )
    assert financial_rows(db_session, import_user) == before
    for model in (Loan, LoanMovement, Person):
        first = set(db_session.scalars(select(model.id).where(model.user_id == import_user.id)))
        other = set(db_session.scalars(select(model.id).where(model.user_id == second_user.id)))
        assert first and other and first.isdisjoint(other)
    assert (
        replay(
            Money(100, Currency("USD")),
            movements(db_session, loan_for(db_session, import_user, "C")),
        ).status
        == "open"
    )


def test_loan_tags_including_synthetic_and_excess(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    tag = snapshot.tags[2]
    changed = replace(
        snapshot,
        tag_links=snapshot.tag_links
        + (TagLinkRow(ROW_MAP["D_payment_1"], tag.pk), TagLinkRow(ROW_MAP["F_settled"], tag.pk)),
    )
    run_import(db_session, import_user.id, changed, options)
    for name, suffix in [
        ("D_payment_1", ""),
        ("D_payment_1", ":excess"),
        ("F_settled", ""),
        ("F_settled", ":synthesized_payment"),
    ]:
        transaction = tx_for(db_session, import_user, name, suffix)
        assert (
            db_session.scalar(
                select(TransactionTag).where(
                    TransactionTag.user_id == import_user.id,
                    TransactionTag.transaction_id == transaction.id,
                )
            )
            is not None
        )


def test_new_import_dry_run_and_plain_reimport_preserve_edits(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    empty = financial_rows(db_session, import_user)
    dry = run_import(db_session, import_user.id, snapshot, replace(options, dry_run=True))
    assert dry.steps["loans"]["created"] == 7
    assert financial_rows(db_session, import_user) == empty
    run_import(db_session, import_user.id, snapshot, options)
    loan = loan_for(db_session, import_user, "B")
    loan.note = "Nota sintética editada"
    tx_for(db_session, import_user, "B_payment_1").amount = Decimal("299")
    db_session.flush()
    before = financial_rows(db_session, import_user)
    report = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in report.counts.values())
    assert report.steps["loans"]["modified"] == 0 and report.steps["loans"]["already_imported"] == 7
    assert financial_rows(db_session, import_user) == before


@pytest.mark.parametrize("missing_date", [False, True])
def test_synthesized_payment_date_and_account(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    missing_date: bool,
) -> None:
    source = next(r for r in snapshot.transactions if r.pk == ROW_MAP["F_settled"])
    if missing_date:
        source = replace(source, modified_at=None)
    changed = replace(
        snapshot,
        transactions=tuple(source if r.pk == source.pk else r for r in snapshot.transactions),
    )
    run_import(db_session, import_user.id, changed, options)
    original = tx_for(db_session, import_user, "F_settled")
    payment = tx_for(db_session, import_user, "F_settled", ":synthesized_payment")
    assert payment.occurred_at == (source.modified_at or source.occurred_at)
    assert payment.account_id == original.account_id
    assert (
        original.occurred_at == source.occurred_at and original.status == payment.status == "posted"
    )


@pytest.mark.parametrize(
    "rate,applied,excess", [("1.900000", "200.00", "190.00"), ("3.810000", "99.74", "0.00")]
)
def test_fx_conversion_preserves_cash_with_rounding_and_excess(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    rate: str,
    applied: str,
    excess: str,
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    loan = loan_for(db_session, import_user, "C")
    old_movements = movements(db_session, loan)
    report = run_import(
        db_session,
        import_user.id,
        snapshot,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal(rate)}),
    )
    assert report.steps["loans"]["resolved_fx"] == 1
    ledger = movements(db_session, loan)
    assert ledger[0] == old_movements[0]
    payment = ledger[1]
    assert payment.amount.amount == min(Decimal(applied), Decimal("100"))
    transaction = tx_for(db_session, import_user, "C_payment_1")
    if Decimal(excess):
        ordinary = tx_for(db_session, import_user, "C_payment_1", ":excess")
        assert ordinary.kind == "income" and ordinary.amount == Decimal(excess)
        assert transaction.amount + ordinary.amount == Decimal("380")
    else:
        assert transaction.amount == Decimal("380")
    assert all(b.unexplained == 0 for b in report.balances)
