import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from monetae import domain
from monetae.db.models import Account, Loan, LoanMovement, Person, Transaction, User
from monetae.services.loans import LoanService, balances_query


def seed(db: Session, user: User) -> tuple[Person, Loan, Transaction]:
    person = Person(user_id=user.id, name="Synthetic person")
    account = Account(user_id=user.id, name="Synthetic account", type="cash", currency="PEN")
    db.add_all([person, account])
    db.flush()
    loan = Loan(
        user_id=user.id,
        person_id=person.id,
        direction="lent",
        currency="PEN",
        principal=Decimal("200.00"),
        opened_on=date(2026, 10, 1),
    )
    txn = Transaction(
        user_id=user.id,
        account_id=account.id,
        currency="PEN",
        kind="loan",
        amount=Decimal("-200.00"),
        occurred_at=datetime(2026, 10, 1, tzinfo=UTC),
        status="posted",
        title="Synthetic disbursement",
        fx_rate_to_base=Decimal(1),
        fx_rate_source="manual",
        source="web",
    )
    db.add_all([loan, txn])
    db.flush()
    return person, loan, txn


def test_compound_foreign_keys_and_unique_transaction(
    db_session: Session, users: tuple[User, User]
) -> None:
    person, loan, transaction = seed(db_session, users[0])
    foreign_person, foreign_loan, foreign_transaction = seed(db_session, users[1])
    insert_loan = text(
        "INSERT INTO loans (user_id, person_id, direction, currency, principal,"
        " opened_on) VALUES (:user, :person, 'lent', 'PEN', 200, current_date)"
    )
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(insert_loan, {"user": users[0].id, "person": foreign_person.id})
    insert = text(
        "INSERT INTO loan_movements (user_id, loan_id, kind, "
        "amount_in_loan_currency, transaction_id, occurred_at, sequence) VALUES"
        " (:user, :loan, 'disbursement', 200, :transaction, now(), :sequence)"
    )
    params = {"user": users[0].id, "loan": loan.id, "transaction": transaction.id, "sequence": 1}
    for change in ({"loan": foreign_loan.id}, {"transaction": foreign_transaction.id}):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(insert, {**params, **change})
    db_session.execute(insert, params)
    new_id = uuid4()
    db_session.execute(
        text(
            "INSERT INTO loans (id, user_id, person_id, direction, currency, "
            "principal, opened_on) VALUES (:id, :user, :person, 'lent', 'PEN', 200,"
            " current_date)"
        ),
        {"id": new_id, "user": users[0].id, "person": person.id},
    )
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(insert, {**params, "loan": new_id})
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(insert, {**params, "sequence": 2, "transaction": None})
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO loan_movements (user_id, loan_id, kind, amount_in_loan_currency, "
                "occurred_at, sequence) VALUES (:user, :loan, 'interest', 10, now(), 1)"
            ),
            {"user": users[0].id, "loan": loan.id},
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "unknown"},
        {"amount": 0},
        {"amount": -1},
        {"kind": "adjustment", "amount": 0},
        {"kind": "payment", "interest": None, "principal": None},
        {"kind": "payment", "interest": -1, "principal": 11},
        {"kind": "payment", "interest": 1, "principal": 1},
        {"kind": "interest", "interest": 0, "principal": 10},
        {"kind": "write_off", "interest": 0, "principal": None},
        {"rate": -1},
        {"sequence": -1},
    ],
)
def test_checks_reject_incoherent_movements(
    db_session: Session, users: tuple[User, User], changes: dict[str, object]
) -> None:
    _, loan, _ = seed(db_session, users[0])
    params: dict[str, object] = {
        "user": users[0].id,
        "loan": loan.id,
        "kind": "interest",
        "amount": 10,
        "interest": None,
        "principal": None,
        "transaction": None,
        "rate": None,
        "sequence": 1,
        **changes,
    }
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO loan_movements (user_id, loan_id, kind, "
                "amount_in_loan_currency, interest_part, principal_part, "
                "transaction_id, fx_rate_applied, occurred_at, sequence) VALUES (:user,"
                " :loan, :kind, :amount, :interest, :principal, :transaction, :rate, "
                "now(), :sequence)"
            ),
            params,
        )


def test_non_cash_cannot_reference_transaction(
    db_session: Session, users: tuple[User, User]
) -> None:
    _, loan, transaction = seed(db_session, users[0])
    for kind in ("interest", "adjustment", "write_off"):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(
                text(
                    "INSERT INTO loan_movements (user_id, loan_id, kind, "
                    "amount_in_loan_currency, transaction_id, occurred_at, sequence) VALUES"
                    " (:user, :loan, :kind, 10, :transaction, now(), 1)"
                ),
                {"user": users[0].id, "loan": loan.id, "kind": kind, "transaction": transaction.id},
            )


def test_sql_balance_equals_domain_replay_random_ledgers(
    db_session: Session, users: tuple[User, User]
) -> None:
    rng = random.Random(302)
    person = Person(user_id=users[0].id, name="Random synthetic")
    db_session.add(person)
    db_session.flush()
    service = LoanService(db_session, "test")
    for index in range(40):
        currency = domain.Currency("USD" if index % 2 else "PEN")
        principal = domain.Money(rng.randrange(1, 10000), currency)
        loan = Loan(
            id=uuid4(),
            user_id=users[0].id,
            person_id=person.id,
            direction="lent" if index % 2 else "borrowed",
            currency=currency.code,
            principal=principal.amount,
            opened_on=date(2026, 10, 1),
        )
        db_session.add(loan)
        db_session.flush()
        occurred = datetime(2026, 10, 1, tzinfo=UTC)
        ledger = [domain.Movement(domain.MovementKind.DISBURSEMENT, principal, occurred, 0)]
        for sequence in range(1, 30):
            state = domain.replay(principal, ledger)
            kind = rng.choice(list(domain.MovementKind)[1:])
            interest_part = principal_part = None
            if kind in {domain.MovementKind.PAYMENT, domain.MovementKind.WRITE_OFF}:
                if state.outstanding.is_zero():
                    kind = domain.MovementKind.INTEREST
                    amount = domain.Money(1, currency)
                else:
                    cents = int(state.outstanding.amount * 100)
                    amount = domain.Money(Decimal(rng.randint(1, cents)) / 100, currency)
                    split = domain.split_payment(amount, state)
                    interest_part, principal_part = split.interest_part, split.principal_part
            elif kind == domain.MovementKind.ADJUSTMENT:
                amount = domain.Money(
                    1
                    if state.principal_outstanding.is_zero()
                    else rng.choice([1, -1]) * min(Decimal(1), state.principal_outstanding.amount),
                    currency,
                )
            else:
                amount = domain.Money(rng.randint(1, 200), currency)
            # Fechas empatadas ejercitan el desempate por sequence.
            ledger.append(
                domain.Movement(
                    kind,
                    amount,
                    occurred + timedelta(days=sequence // 3),
                    sequence,
                    interest_part,
                    principal_part,
                )
            )
        expected = domain.replay(principal, ledger)
        for movement in ledger:
            db_session.add(
                LoanMovement(
                    user_id=loan.user_id,
                    loan_id=loan.id,
                    kind=movement.kind.value,
                    amount_in_loan_currency=movement.amount.amount,
                    occurred_at=movement.occurred_at,
                    sequence=movement.sequence,
                    interest_part=movement.interest_part.amount if movement.interest_part else None,
                    principal_part=movement.principal_part.amount
                    if movement.principal_part
                    else None,
                )
            )
        # Una fila borrada nunca contribuye al cálculo SQL ni a replay.
        db_session.add(
            LoanMovement(
                user_id=loan.user_id,
                loan_id=loan.id,
                kind="interest",
                amount_in_loan_currency=Decimal(999),
                occurred_at=occurred,
                sequence=100,
                deleted_at=occurred,
            )
        )
        db_session.flush()
        actual = service.balance(loan)
        assert actual.outstanding == expected.outstanding.format()
        assert actual.status == expected.status
        for name in ("interest_total", "adjustment_total", "payment_total", "write_off_total"):
            assert getattr(actual, name) == getattr(expected, name).format()
    # El agregado no incluye al segundo usuario.
    q = balances_query(users[1].id)
    assert not db_session.execute(select(q)).all()
