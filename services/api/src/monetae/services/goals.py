"""Atomic goal CRUD, reversible selections and bounded page aggregation."""

import json
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas import goals as schema
from monetae.db.models import Goal, GoalTransaction, Transaction, User
from monetae.domain.currency import Currency
from monetae.domain.money import Money
from monetae.reports.goals import goal_progress
from monetae.reports.service import Totals
from monetae.services.auth import AuthError, Clock


class GoalService:
    def __init__(self, db: Session, secret: str, clock: Clock) -> None:
        self.db, self.secret, self.clock = db, secret, clock

    def get(self, user: User, goal_id: UUID, *, lock: bool = False) -> Goal:
        query = (
            select(Goal)
            .where(Goal.id == goal_id, Goal.user_id == user.id, Goal.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        row = self.db.scalar(query)
        if row is None:
            raise AuthError(404, "not_found", "Goal not found.")
        return row

    def create(self, user: User, payload: schema.GoalCreate) -> Goal:
        row = Goal(
            id=uuid4(),
            user_id=user.id,
            name=payload.name,
            kind=payload.kind,
            target_amount=Decimal(payload.target_amount),
            currency=payload.currency,
            due_on=payload.due_on,
            color=payload.color,
            icon=payload.icon,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def update(self, user: User, goal_id: UUID, payload: schema.GoalUpdate) -> Goal:
        row = self.get(user, goal_id, lock=True)
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            setattr(row, field, Decimal(value) if field == "target_amount" else value)
        row.updated_at = self.clock.now()
        self.db.flush()
        return row

    def delete(self, user: User, goal_id: UUID) -> None:
        row = self.get(user, goal_id, lock=True)
        row.deleted_at = self.clock.now()
        self.db.flush()

    def assign(self, user: User, goal_id: UUID, ids: list[UUID]) -> Goal:
        row = self.get(user, goal_id, lock=True)
        desired = set(ids)
        transactions = (
            list(
                self.db.scalars(
                    select(Transaction)
                    .where(
                        Transaction.user_id == user.id,
                        Transaction.id.in_(desired),
                        Transaction.deleted_at.is_(None),
                    )
                    .with_for_update()
                )
            )
            if desired
            else []
        )
        if {transaction.id for transaction in transactions} != desired:
            raise AuthError(404, "not_found", "A requested transaction was not found.")
        if any(transaction.kind == "loan" for transaction in transactions):
            raise AuthError(
                422, "loan_transaction_not_allowed", "Goals cannot link loan transactions."
            )
        links = list(
            self.db.scalars(
                select(GoalTransaction).where(
                    GoalTransaction.user_id == user.id, GoalTransaction.goal_id == row.id
                )
            )
        )
        existing = {link.transaction_id for link in links}
        for link in links:
            link.deleted_at = None if link.transaction_id in desired else self.clock.now()
        for transaction_id in desired - existing:
            self.db.add(
                GoalTransaction(user_id=user.id, goal_id=row.id, transaction_id=transaction_id)
            )
        row.updated_at = self.clock.now()
        self.db.flush()
        return row

    def representations(self, user: User, rows: list[Goal]) -> list[schema.Goal]:
        if not rows:
            return []
        progress = goal_progress(self.db, user, [row.id for row in rows])
        result = []
        for row in rows:
            totals = Totals()
            for entry in progress.get(row.id, []):
                totals.add(entry)
            report = totals.representation(row.currency)
            amount = Money.parse(report.report_amount, Currency(row.currency))
            result.append(
                schema.Goal(
                    id=row.id,
                    name=row.name,
                    kind=cast(schema.Kind, row.kind),
                    target_amount=f"{row.target_amount:.2f}",
                    currency=row.currency,
                    due_on=row.due_on,
                    color=row.color,
                    icon=row.icon,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    deleted_at=row.deleted_at,
                    progress_amount=amount.format(),
                    report_total=report,
                )
            )
        return result

    def representation(self, user: User, row: Goal) -> schema.Goal:
        return self.representations(user, [row])[0]

    def list(self, user: User, limit: int, cursor: str | None) -> schema.GoalPage:
        filters = json.dumps([str(user.id)])
        key = decode_cursor(cursor, "goals", filters, self.secret)
        query = select(Goal).where(Goal.user_id == user.id, Goal.deleted_at.is_(None))
        if key is not None:
            try:
                if len(key) != 2:
                    raise ValueError
                created, entity_id = datetime.fromisoformat(key[0]), UUID(key[1])
                if created.tzinfo is None:
                    raise ValueError
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
            query = query.where(tuple_(Goal.created_at, Goal.id) > tuple_(created, entity_id))
        rows = list(self.db.scalars(query.order_by(Goal.created_at, Goal.id).limit(limit + 1)))
        page = rows[:limit]
        next_cursor = (
            encode_cursor(
                "goals", filters, [page[-1].created_at.isoformat(), str(page[-1].id)], self.secret
            )
            if len(rows) > limit
            else None
        )
        return schema.GoalPage(items=self.representations(user, page), next_cursor=next_cursor)
