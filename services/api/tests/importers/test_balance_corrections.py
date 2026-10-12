"""Category 0 corrections retain cash, even without a valid partner."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from monetae.db.models import Category, Transaction, User
from monetae.importers.cashew.mapping import ImportOptions, build_plan
from monetae.importers.cashew.reader import Snapshot, TransactionRow
from monetae.importers.cashew.runner import run_import

from .test_runner import ROW_MAP, financial_rows


def correction_snapshot(snapshot: Snapshot) -> Snapshot:
    rows = tuple(
        replace(r, category_pk="0", subcategory_pk=None)
        for r in snapshot.transactions
        if r.pk in (ROW_MAP["H_out"], ROW_MAP["H_in"])
    )
    category_zero = replace(
        snapshot.categories[0], pk="0", parent_pk=None, name="Corrección de saldo"
    )
    return replace(
        snapshot, transactions=rows, tag_links=(), categories=(*snapshot.categories, category_zero)
    )


@pytest.mark.parametrize(
    "scenario",
    ["paired", "one_way", "unpaired", "missing", "multicurrency", "deferred", "ambiguous"],
)
def test_corrections_import_and_reimport(
    db_session: Session,
    import_user: User,
    snapshot: Snapshot,
    options: ImportOptions,
    scenario: str,
) -> None:
    snapshot = correction_snapshot(snapshot)
    outgoing = next(r for r in snapshot.transactions if r.amount < 0)
    incoming = next(r for r in snapshot.transactions if r.amount > 0)
    expected_pairs = 1
    if scenario == "one_way":
        incoming = replace(incoming, paired_pk=None)
    elif scenario == "unpaired":
        snapshot = replace(snapshot, transactions=(replace(outgoing, paired_pk=None),))
        expected_pairs = 0
    elif scenario == "missing":
        outgoing = replace(outgoing, paired_pk="absent")
        incoming = replace(incoming, paired_pk=None)
        expected_pairs = 0
    elif scenario == "multicurrency":
        incoming = replace(
            incoming,
            wallet_pk=next(w.pk for w in snapshot.wallets if w.currency == "USD"),
            amount=Decimal("52.63"),
        )
    elif scenario == "deferred":
        incoming = replace(
            incoming, occurred_at=incoming.occurred_at + timedelta(days=2), paid=False
        )
    elif scenario == "ambiguous":
        expected_pairs = 0
    if scenario != "unpaired":
        rows: tuple[TransactionRow, ...] = (outgoing, incoming)
        if scenario == "ambiguous":
            rows += (replace(outgoing, pk=str(uuid4())),)
        snapshot = replace(snapshot, transactions=rows)
    plan = build_plan(snapshot, "PEN", options)
    assert len(plan.transfers) == expected_pairs
    assert not [item for item in plan.review_items if item.kind == "unpaired_transfer"]
    before = financial_rows(db_session, import_user)
    dry = run_import(db_session, import_user.id, snapshot, replace(options, dry_run=True))
    assert dry.financial_rolled_back
    assert financial_rows(db_session, import_user) == before
    result = run_import(db_session, import_user.id, snapshot, options)
    assert all(b.unexplained == Decimal("0.00") for b in result.balances)
    rows_db = list(
        db_session.scalars(select(Transaction).where(Transaction.user_id == import_user.id))
    )
    assert len(rows_db) == len(snapshot.transactions)
    categories = {
        c.id: c.system_key
        for c in db_session.scalars(select(Category).where(Category.user_id == import_user.id))
    }
    for row in rows_db:
        assert row.kind in ("income", "expense")
        assert row.category_id is not None
        assert categories[row.category_id] == f"balance_correction_{row.kind}"
        assert (row.transfer_group_id is not None) == bool(expected_pairs)
    assert not db_session.scalar(
        select(Category).where(
            Category.user_id == import_user.id, Category.import_external_id == "cashew:sqlite:0"
        )
    )
    imported = financial_rows(db_session, import_user)
    second = run_import(db_session, import_user.id, snapshot, options)
    assert all(c.created == 0 for c in second.counts.values())
    assert financial_rows(db_session, import_user) == imported
