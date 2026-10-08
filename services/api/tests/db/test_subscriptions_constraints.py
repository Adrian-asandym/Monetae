from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from monetae.db.models import Account, Category, RecurringRule, Subscription, User


def seed(db: Session, user: User) -> tuple[Account, Category, RecurringRule, Subscription]:
    account = Account(user_id=user.id, name="Synthetic", type="cash", currency="PEN")
    category = Category(user_id=user.id, name="Synthetic", kind="expense")
    db.add_all([account, category])
    db.flush()
    rule = RecurringRule(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        kind="expense",
        amount=Decimal("-30.00"),
        currency="PEN",
        title="Synthetic",
        period="monthly",
        interval_count=1,
        anchor_on=date(2026, 11, 1),
        next_run_on=date(2026, 11, 1),
        fx_rate_to_base=Decimal(1),
    )
    db.add(rule)
    db.flush()
    subscription = Subscription(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        amount=Decimal("30.00"),
        currency="PEN",
        title="Synthetic",
        status="active",
        period="monthly",
        interval_count=1,
        anchor_on=date(2026, 11, 1),
        next_due_on=date(2026, 11, 1),
        recurring_rule_id=rule.id,
    )
    db.add(subscription)
    db.flush()
    rule.subscription_id = subscription.id
    db.flush()
    return account, category, rule, subscription


def test_compound_foreign_keys_reject_other_owner_or_currency(
    db_session: Session, users: tuple[User, User]
) -> None:
    account, category, rule, subscription = seed(db_session, users[0])
    foreign_account, foreign_category, foreign_rule, foreign_subscription = seed(
        db_session, users[1]
    )
    cases = [
        (
            "UPDATE subscriptions SET account_id=:value WHERE id=:id",
            foreign_account.id,
            subscription.id,
        ),
        (
            "UPDATE subscriptions SET category_id=:value WHERE id=:id",
            foreign_category.id,
            subscription.id,
        ),
        (
            "UPDATE subscriptions SET recurring_rule_id=:value WHERE id=:id",
            foreign_rule.id,
            subscription.id,
        ),
        ("UPDATE subscriptions SET currency=:value WHERE id=:id", "USD", subscription.id),
        ("UPDATE recurring_rules SET account_id=:value WHERE id=:id", foreign_account.id, rule.id),
        (
            "UPDATE recurring_rules SET category_id=:value WHERE id=:id",
            foreign_category.id,
            rule.id,
        ),
        (
            "UPDATE recurring_rules SET subscription_id=:value WHERE id=:id",
            foreign_subscription.id,
            rule.id,
        ),
        ("UPDATE recurring_rules SET currency=:value WHERE id=:id", "USD", rule.id),
    ]
    for sql, value, entity in cases:
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(text(sql), {"value": value, "id": entity})
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO transactions (user_id, account_id, currency, kind, amount, "
                "occurred_at, status, title, fx_rate_to_base, fx_rate_source, source, "
                "recurring_rule_id) VALUES (:user, :account, 'PEN', 'expense', -30, now(), "
                "'posted', 'Synthetic', 1, 'manual', 'web', :rule)"
            ),
            {"user": users[0].id, "account": account.id, "rule": foreign_rule.id},
        )
    assert category.id != foreign_category.id


@pytest.mark.parametrize(
    "assignment",
    [
        "status='archived'",
        "archived_at=now()",
        "amount=0",
        "interval_count=0",
        "interval_count=367",
        "reminder_days_before=-1",
        "status='invalid'",
        "period='quarterly'",
        "archive_reason=repeat('x', 501)",
    ],
)
def test_subscription_checks(
    db_session: Session, users: tuple[User, User], assignment: str
) -> None:
    _, _, _, subscription = seed(db_session, users[0])
    # Las asignaciones son constantes del test, no entrada de usuario.
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(f"UPDATE subscriptions SET {assignment} WHERE id=:id"), {"id": subscription.id}
        )


@pytest.mark.parametrize(
    "assignment",
    ["amount=0", "amount=30", "kind='unknown'", "interval_count=367", "fx_rate_to_base=0"],
)
def test_rule_checks(db_session: Session, users: tuple[User, User], assignment: str) -> None:
    _, _, rule, _ = seed(db_session, users[0])
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(f"UPDATE recurring_rules SET {assignment} WHERE id=:id"), {"id": rule.id}
        )
