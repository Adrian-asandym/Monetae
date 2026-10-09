"""Salvaguardas aprobadas por coordinación y anomalías del libro sintético."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import ImportReviewItem, LoanMovement, Person, Transaction, User
from monetae.domain.currency import Currency
from monetae.domain.loans import replay
from monetae.domain.money import Money
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import Snapshot
from monetae.importers.cashew.runner import run_import

from .test_cashew_loans_ledger import CASES, ROW_MAP, financial_rows, loan_for, movements, tx_for


def test_difference_only_extra_disbursement_and_unpaid(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    first = next(r for r in snapshot.transactions if r.pk == ROW_MAP["E_disbursement"])
    extra = replace(
        first,
        pk="synthetic-extra-disbursement",
        amount=Decimal("-25"),
        occurred_at=first.occurred_at + timedelta(hours=1),
    )
    unpaid = replace(first, pk="synthetic-unpaid-loan", amount=Decimal("-12"), paid=False)
    changed = replace(
        snapshot,
        objectives=tuple(
            replace(o, amount=Decimal(-1), archived=True) if o.pk == first.objective_loan_pk else o
            for o in snapshot.objectives
        ),
        transactions=snapshot.transactions + (extra, unpaid),
    )
    report = run_import(db_session, import_user.id, changed, options)
    loan = loan_for(db_session, import_user, "E")
    assert loan.principal == Decimal("1000")
    state = replay(Money(loan.principal, Currency(loan.currency)), movements(db_session, loan))
    assert state.outstanding.amount == Decimal("25")
    adjustment = db_session.scalar(
        select(LoanMovement).where(
            LoanMovement.user_id == import_user.id,
            LoanMovement.loan_id == loan.id,
            LoanMovement.kind == "adjustment",
        )
    )
    assert (
        adjustment is not None
        and adjustment.transaction_id is None
        and adjustment.fx_rate_applied is None
    )
    assert (
        db_session.scalar(
            select(LoanMovement).where(
                LoanMovement.user_id == import_user.id,
                LoanMovement.transaction_id
                == db_session.scalar(
                    select(Transaction.id).where(
                        Transaction.user_id == import_user.id,
                        Transaction.import_external_id == external_id(extra.pk),
                    )
                ),
            )
        )
        is None
    )
    assert (
        db_session.scalar(
            select(Transaction.id).where(
                Transaction.user_id == import_user.id,
                Transaction.import_external_id == external_id(unpaid.pk),
            )
        )
        is None
    )
    assert any(i.kind == "extra_disbursement" for i in report.review_items)
    assert any(i.kind == "unpaid_loan_transaction" for i in report.review_items)
    assert all(b.unexplained == 0 for b in report.balances)


def test_multiple_matching_people_never_selects_one(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    people = [
        Person(user_id=import_user.id, name="Persona Ejemplo B", aliases=[]),
        Person(user_id=import_user.id, name="Otra sintética", aliases=["persona ejemplo b"]),
    ]
    db_session.add_all(people)
    db_session.flush()
    report = run_import(db_session, import_user.id, snapshot, options)
    assert report.steps["loans"]["created"] == 6
    item = next(i for i in report.review_items if i.kind == "ambiguous_loan")
    assert item.payload["objective_pk"] == CASES["B"]["objective_pk"]
    candidates = item.payload["candidate_person_ids"]
    assert isinstance(candidates, list)
    assert len(candidates) == len(people) and all(str(p.id) in candidates for p in people)
    assert tx_for(db_session, import_user, "B_disbursement").kind == "expense"
    assert tx_for(db_session, import_user, "B_payment_1").kind == "income"
    assert all(b.unexplained == 0 for b in report.balances)


def test_cross_currency_disbursement_is_not_guessed(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    changed = replace(
        snapshot,
        objectives=tuple(
            replace(o, wallet_pk=snapshot.wallets[0].pk)
            if o.pk == CASES["C"]["objective_pk"]
            else o
            for o in snapshot.objectives
        ),
    )
    # Escoger explícitamente una cuenta PEN aunque cambie el orden de la fixture.
    pen = next(w for w in snapshot.wallets if w.currency == "PEN")
    changed = replace(
        changed,
        objectives=tuple(
            replace(o, wallet_pk=pen.pk) if o.pk == CASES["C"]["objective_pk"] else o
            for o in changed.objectives
        ),
    )
    report = run_import(
        db_session,
        import_user.id,
        changed,
        replace(options, loan_fx_rates={ROW_MAP["C_disbursement"]: Decimal("3.8")}),
    )
    item = next(i for i in report.review_items if i.kind == "ledger_invalid")
    assert item.payload["reason"] == "disbursement_currency_mismatch"
    assert tx_for(db_session, import_user, "C_disbursement").kind == "expense"
    assert tx_for(db_session, import_user, "C_payment_1").kind == "income"
    assert all(b.unexplained == 0 for b in report.balances)


def test_orphan_interest_candidates_are_only_hints(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, note="Interés de PÉRSONA EJEMPLO A") if r.pk == ROW_MAP["A_interest"] else r
            for r in snapshot.transactions
        ),
    )
    report = run_import(db_session, import_user.id, changed, options)
    loan = loan_for(db_session, import_user, "A")
    item = next(i for i in report.review_items if i.kind == "orphan_interest")
    assert item.payload["candidates"] == [str(loan.id)]
    interest = tx_for(db_session, import_user, "A_interest")
    assert interest.amount == Decimal("-10") and interest.kind == "expense"
    assert (
        db_session.scalar(
            select(LoanMovement.id).where(
                LoanMovement.user_id == import_user.id, LoanMovement.transaction_id == interest.id
            )
        )
        is None
    )
    assert (
        replay(
            Money(loan.principal, Currency(loan.currency)), movements(db_session, loan)
        ).interest_total.amount
        == 0
    )


@pytest.mark.parametrize("edit", ["cash", "note", "movement", "loan", "review"])
def test_fx_second_pass_preserves_conflicts(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions, edit: str
) -> None:
    run_import(db_session, import_user.id, snapshot, options)
    loan = loan_for(db_session, import_user, "C")
    if edit == "cash":
        tx_for(db_session, import_user, "C_payment_1").amount += Decimal(1)
    elif edit == "note":
        tx_for(db_session, import_user, "C_payment_1").note = "Nota manual sintética"
    elif edit == "movement":
        stored = db_session.scalar(
            select(LoanMovement).where(
                LoanMovement.user_id == import_user.id, LoanMovement.loan_id == loan.id
            )
        )
        assert stored is not None
        stored.note = "Movimiento editado"
    elif edit == "loan":
        loan.note = "Préstamo editado"
    else:
        pending = db_session.scalar(
            select(ImportReviewItem).where(
                ImportReviewItem.user_id == import_user.id,
                ImportReviewItem.kind == "fx_rate_required",
            )
        )
        assert pending is not None
        pending.kind = "another_review"
    db_session.flush()
    before = financial_rows(db_session, import_user)
    report = run_import(
        db_session,
        import_user.id,
        snapshot,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.8")}),
    )
    assert report.steps["loans"]["resolved_fx"] == 0
    assert any(
        i.kind == "ambiguous_loan" and i.payload["reason"] == "second_pass_conflict"
        for i in report.review_items
    )
    assert financial_rows(db_session, import_user) == before


def test_second_pass_same_timestamp_follows_existing_movement(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    first = next(r for r in snapshot.transactions if r.pk == ROW_MAP["C_disbursement"])
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, occurred_at=first.occurred_at) if r.pk == ROW_MAP["C_payment_1"] else r
            for r in snapshot.transactions
        ),
    )
    run_import(db_session, import_user.id, changed, options)
    loan = loan_for(db_session, import_user, "C")
    original = movements(db_session, loan)
    report = run_import(
        db_session,
        import_user.id,
        changed,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.8")}),
    )
    assert report.steps["loans"]["resolved_fx"] == 1
    converted = movements(db_session, loan)
    assert converted[0] == original[0] and converted[1].sequence == original[0].sequence + 1
    assert converted[0].occurred_at == converted[1].occurred_at
    assert replay(Money(loan.principal, Currency(loan.currency)), converted).status == "settled"


def test_second_pass_rejects_invalidated_later_payment(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions
) -> None:
    first = next(r for r in snapshot.transactions if r.pk == ROW_MAP["C_disbursement"])
    last = replace(
        first,
        pk="synthetic-later-payment",
        income=True,
        amount=Decimal("80"),
        occurred_at=first.occurred_at + timedelta(days=120),
    )
    changed = replace(snapshot, transactions=snapshot.transactions + (last,))
    run_import(db_session, import_user.id, changed, options)
    before = financial_rows(db_session, import_user)
    report = run_import(
        db_session,
        import_user.id,
        changed,
        replace(options, loan_fx_rates={ROW_MAP["C_payment_1"]: Decimal("3.8")}),
    )
    assert report.steps["loans"]["resolved_fx"] == 0
    assert financial_rows(db_session, import_user) == before
    assert any(
        i.kind == "ambiguous_loan" and i.payload["reason"] == "second_pass_conflict"
        for i in report.review_items
    )


@pytest.mark.parametrize("amount", ["0", "0.001", "10000000000000000"])
def test_anomalous_loan_amount_never_aborts_other_books(
    db_session: Session, import_user: User, snapshot: Snapshot, options: ImportOptions, amount: str
) -> None:
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, amount=Decimal(amount)) if r.pk == ROW_MAP["C_disbursement"] else r
            for r in snapshot.transactions
        ),
    )
    report = run_import(db_session, import_user.id, changed, options)
    assert report.outcome == "succeeded" and report.steps["loans"]["created"] == 6
    assert report.steps["loans"]["invalid"] == 1
    assert tx_for(db_session, import_user, "C_payment_1").kind == "income"
