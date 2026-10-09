"""L1-A: principal supuesto sin efectivo, tasas y conservación del historial."""

import sqlite3
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from monetae.cli import main
from monetae.db.models import ImportReviewItem, ImportRun, Loan, LoanMovement, User
from monetae.domain.currency import Currency
from monetae.domain.loans import replay
from monetae.domain.money import Money
from monetae.importers.cashew.mapping import ImportOptions, external_id
from monetae.importers.cashew.reader import Snapshot
from monetae.importers.cashew.runner import run_import

from .test_cashew_loans_ledger import CASES, ROW_MAP, financial_rows, loan_for, movements, tx_for


def without_disbursement(snapshot: Snapshot, case: str = "B") -> Snapshot:
    return replace(
        snapshot,
        transactions=tuple(
            r for r in snapshot.transactions if r.pk != ROW_MAP[case + "_disbursement"]
        ),
    )


def stored_movements(session: Session, loan: Loan) -> list[LoanMovement]:
    return list(
        session.scalars(
            select(LoanMovement)
            .where(LoanMovement.user_id == loan.user_id, LoanMovement.loan_id == loan.id)
            .order_by(LoanMovement.sequence)
        )
    )


def assert_settled(session: Session, loan: Loan) -> None:
    state = replay(Money(loan.principal, Currency(loan.currency)), movements(session, loan))
    assert state.status == "settled" and state.outstanding.amount == 0
    assert "outstanding" not in Loan.__table__.columns and "status" not in Loan.__table__.columns


@pytest.mark.parametrize("case", ["A", "B"])
@pytest.mark.parametrize("same_timestamp", [False, True])
def test_synthetic_disbursement_order_idempotence_and_dry_run(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    case: str,
    same_timestamp: bool,
) -> None:
    changed = without_disbursement(snapshot, case)
    first = next(r for r in changed.transactions if r.pk == ROW_MAP[case + "_payment_1"])
    if same_timestamp:
        changed = replace(
            changed,
            transactions=tuple(
                replace(r, occurred_at=first.occurred_at)
                if r.objective_loan_pk == first.objective_loan_pk
                else r
                for r in changed.transactions
            ),
        )
    empty = financial_rows(db_session, import_user)
    dry = run_import(db_session, import_user.id, changed, replace(options, dry_run=True))
    assert dry.steps["loans"]["created"] == 7
    assert financial_rows(db_session, import_user) == empty
    report = run_import(db_session, import_user.id, changed, options)
    assert all(b.unexplained == 0 for b in report.balances)
    loan = loan_for(db_session, import_user, case)
    assert loan.direction == ("borrowed" if case == "A" else "lent")
    assert loan.principal == (Decimal("210") if case == "A" else Decimal("500"))
    ledger = stored_movements(db_session, loan)
    assert [r.sequence for r in ledger] == [0, 1, 2]
    assert ledger[0].kind == "disbursement"
    assert ledger[0].transaction_id is None and ledger[0].fx_rate_applied is None
    assert ledger[0].note is None
    earliest = min(
        r.occurred_at
        for r in changed.transactions
        if r.objective_loan_pk == first.objective_loan_pk and r.paid
    )
    assert ledger[0].occurred_at == earliest - timedelta(seconds=1)
    assert loan.opened_on == ledger[0].occurred_at.astimezone(ZoneInfo("America/Lima")).date()
    assert_settled(db_session, loan)
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, changed, options)
    assert all(c.created == 0 for c in second.counts.values())
    assert second.steps["loans"]["modified"] == 0
    assert financial_rows(db_session, import_user) == before
    assert len(stored_movements(db_session, loan)) == 3


@pytest.mark.parametrize("empty", [False, True])
def test_no_paid_rows_remains_invalid(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    empty: bool,
) -> None:
    objective_pk = CASES["B"]["objective_pk"]
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, paid=False) if r.objective_loan_pk == objective_pk else r
            for r in snapshot.transactions
            if not (empty and r.objective_loan_pk == objective_pk)
        ),
    )
    report = run_import(db_session, import_user.id, changed, options)
    assert report.steps["loans"]["created"] == 6 and report.steps["loans"]["invalid"] == 1
    assert any(
        i.kind == "ledger_invalid" and i.payload["reason"] == "MissingDisbursementError"
        for i in report.review_items
    )
    assert (
        db_session.scalar(
            select(Loan.id).where(
                Loan.user_id == import_user.id,
                Loan.import_external_id == external_id("objective:" + str(objective_pk)),
            )
        )
        is None
    )
    assert all(b.unexplained == 0 for b in report.balances)


def mixed_currency(snapshot: Snapshot) -> Snapshot:
    changed = without_disbursement(snapshot)
    usd = next(w for w in snapshot.wallets if w.currency == "USD")
    return replace(
        changed,
        transactions=tuple(
            replace(r, wallet_pk=usd.pk, amount=Decimal("80"))
            if r.pk == ROW_MAP["B_payment_2"]
            else r
            for r in changed.transactions
        ),
    )


@pytest.mark.parametrize("with_rate", [False, True])
def test_foreign_payment_first_pass_and_second_pass_conflict(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    with_rate: bool,
) -> None:
    changed = mixed_currency(snapshot)
    conversion = replace(options, loan_fx_rates={ROW_MAP["B_payment_2"]: Decimal("0.250000")})
    report = run_import(db_session, import_user.id, changed, conversion if with_rate else options)
    loan = loan_for(db_session, import_user, "B")
    assert loan.principal == (Decimal("620") if with_rate else Decimal("300"))
    assert_settled(db_session, loan)
    transaction = tx_for(db_session, import_user, "B_payment_2")
    assert transaction.kind == ("loan" if with_rate else "income")
    ledger = stored_movements(db_session, loan)
    assert len(ledger) == (3 if with_rate else 2)
    if with_rate:
        assert ledger[2].fx_rate_applied == Decimal("0.250000")
        assert ledger[2].amount_in_loan_currency == Decimal("320")
        assert ledger[2].transaction_id == transaction.id
    assumed = next(i for i in report.review_items if i.kind == "principal_assumed")
    assert assumed.payload["payments"] == (2 if with_rate else 1)
    assert assumed.payload["assumed_principal"] == ("620.00" if with_rate else "300.00")
    pending = list(
        db_session.scalars(
            select(ImportReviewItem).where(
                ImportReviewItem.user_id == import_user.id,
                ImportReviewItem.kind == "fx_rate_required",
                ImportReviewItem.payload["loan_external_id"].astext == loan.import_external_id,
            )
        )
    )
    assert len(pending) == (0 if with_rate else 1)
    before = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, changed, conversion)
    assert second.steps["loans"]["modified"] == 0
    assert financial_rows(db_session, import_user) == before
    if not with_rate:
        assert any(
            i.kind == "ambiguous_loan" and i.payload["reason"] == "second_pass_conflict"
            for i in second.review_items
        )
        assert pending[0].resolved_at is None
        assert transaction.kind == "income"
    assert all(b.unexplained == 0 for b in report.balances)


def test_all_foreign_payments_without_rates_remain_ordinary(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    changed = without_disbursement(snapshot, "C")
    report = run_import(db_session, import_user.id, changed, options)
    assert report.steps["loans"]["created"] == 6 and report.steps["loans"]["invalid"] == 1
    assert tx_for(db_session, import_user, "C_payment_1").kind == "income"
    assert any(
        i.kind == "ledger_invalid" and i.payload["objective_pk"] == CASES["C"]["objective_pk"]
        for i in report.review_items
    )
    assert all(b.unexplained == 0 for b in report.balances)


@pytest.mark.parametrize("amount", ["0", "-300", "0.001"])
def test_anomalous_payment_never_aborts_other_books(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    amount: str,
) -> None:
    changed = without_disbursement(snapshot)
    changed = replace(
        changed,
        transactions=tuple(
            replace(r, amount=Decimal(amount)) if r.pk == ROW_MAP["B_payment_1"] else r
            for r in changed.transactions
        ),
    )
    report = run_import(db_session, import_user.id, changed, options, allow_balance_diff=True)
    assert report.steps["loans"]["created"] == 6 and report.steps["loans"]["invalid"] == 1
    assert tx_for(db_session, import_user, "B_payment_2").kind == "income"
    if amount != "0.001":
        assert any(
            i.kind == "ledger_invalid" and i.payload["reason"] == "invalid_cash_polarity_or_amount"
            for i in report.review_items
        )


def test_assumed_principal_is_isolated_between_users(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    changed = mixed_currency(snapshot)
    other = User(email="longterm-other@example.test", base_currency="PEN", report_currency="PEN")
    db_session.add(other)
    db_session.flush()
    run_import(db_session, import_user.id, changed, options)
    before = financial_rows(db_session, import_user)
    run_import(
        db_session,
        other.id,
        changed,
        replace(options, loan_fx_rates={ROW_MAP["B_payment_2"]: Decimal("0.25")}),
    )
    assert financial_rows(db_session, import_user) == before
    assert loan_for(db_session, import_user, "B").principal == 300
    assert loan_for(db_session, other, "B").principal == 620
    assert loan_for(db_session, import_user, "B").id != loan_for(db_session, other, "B").id


def test_cli_assumed_principal_is_private_and_dry_run_preserves_finances(
    database_url: str,
    db_engine: Engine,
    source_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with sqlite3.connect(source_path) as source:
        source.execute(
            "DELETE FROM transactions WHERE transaction_pk = ?", (ROW_MAP["B_disbursement"],)
        )
        source.execute(
            "UPDATE transactions SET amount = ? WHERE transaction_pk = ?",
            ("123.45", ROW_MAP["B_payment_1"]),
        )
        source.execute(
            "UPDATE transactions SET amount = ? WHERE transaction_pk = ?",
            ("234.56", ROW_MAP["B_payment_2"]),
        )
    monkeypatch.setenv("MONETAE_DATABASE_URL", database_url)
    with Session(db_engine) as session:
        user = User(
            email=f"longterm-cli-{uuid4().hex}@example.test",
            base_currency="PEN",
            report_currency="PEN",
        )
        session.add(user)
        session.commit()
        user_id, email = user.id, user.email
    try:
        assert (
            main(
                [
                    "import-cashew",
                    "--file",
                    str(source_path),
                    "--user-email",
                    email,
                    "--fx-rate",
                    "USD=3.8",
                    "--dry-run",
                ]
            )
            == 0
        )
        output = capsys.readouterr()
        assert not output.err
        assert all(
            text not in output.out
            for text in ("358.01", "Persona", "Ejemplo", "Nota", '"title":', '"note":', '"name":')
        )
        with Session(db_engine) as session:
            persisted = session.get(User, user_id)
            assert persisted is not None
            assert all(not rows for rows in financial_rows(session, persisted).values())
    finally:
        with Session(db_engine) as session:
            for model in (ImportReviewItem, ImportRun):
                session.execute(delete(model).where(model.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
            session.commit()


def test_unpaid_disbursement_is_excluded_from_assumed_principal(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
) -> None:
    changed = replace(
        snapshot,
        transactions=tuple(
            replace(r, paid=False) if r.pk == ROW_MAP["B_disbursement"] else r
            for r in snapshot.transactions
        ),
    )
    report = run_import(db_session, import_user.id, changed, options)
    loan = loan_for(db_session, import_user, "B")
    assert loan.principal == 500
    assert_settled(db_session, loan)
    assert any(
        i.kind == "unpaid_loan_transaction"
        and i.payload["transaction_pk"] == ROW_MAP["B_disbursement"]
        for i in report.review_items
    )
    assert all(b.unexplained == 0 for b in report.balances)


def test_second_pass_rebuilds_assumption_with_prior_rates(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monetae.domain.fx import ExchangeRate
    from monetae.importers.cashew import loans
    from monetae.importers.cashew.reader import TransactionRow

    changed = mixed_currency(snapshot)
    foreign = next(r for r in changed.transactions if r.pk == ROW_MAP["B_payment_2"])
    pending_source = replace(
        foreign, pk="longterm-pending-rate", occurred_at=foreign.occurred_at + timedelta(days=1)
    )
    changed = replace(changed, transactions=changed.transactions + (pending_source,))
    prior = replace(options, loan_fx_rates={foreign.pk: Decimal("0.300000")})
    report = run_import(db_session, import_user.id, changed, prior)
    loan = loan_for(db_session, import_user, "B")
    assert loan.principal == Decimal("566.67")
    assert_settled(db_session, loan)
    assert all(b.unexplained == 0 for b in report.balances)
    before = financial_rows(db_session, import_user)
    original = loans._payment_amount
    calls: list[tuple[str, Decimal | None]] = []

    def capture(
        loan_currency: str, row: TransactionRow, currency: str, rate_value: Decimal | None
    ) -> tuple[Money | None, ExchangeRate | None]:
        calls.append((row.pk, rate_value))
        return original(loan_currency, row, currency, rate_value)

    monkeypatch.setattr(loans, "_payment_amount", capture)
    second = run_import(
        db_session,
        import_user.id,
        changed,
        replace(
            prior,
            loan_fx_rates={
                foreign.pk: Decimal("0.300000"),
                pending_source.pk: Decimal("0.250000"),
            },
        ),
    )
    assert (foreign.pk, Decimal("0.300000")) in calls
    assert (pending_source.pk, None) in calls
    assert (pending_source.pk, Decimal("0.250000")) not in calls
    assert second.steps["loans"]["modified"] == 0
    assert financial_rows(db_session, import_user) == before
    assert any(
        i.kind == "ambiguous_loan" and i.payload["reason"] == "second_pass_conflict"
        for i in second.review_items
    )
    stored_review = db_session.scalar(
        select(ImportReviewItem).where(
            ImportReviewItem.user_id == import_user.id,
            ImportReviewItem.kind == "principal_assumed",
        )
    )
    assert stored_review is not None and stored_review.payload == {
        "loan_external_id": loan.import_external_id,
        "objective_pk": CASES["B"]["objective_pk"],
        "payments": 2,
        "assumed_principal": "566.67",
        "currency": "PEN",
    }
