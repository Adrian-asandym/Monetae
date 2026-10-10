"""Atomic budget CRUD, reversible selections and bounded page aggregation."""

import json
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from monetae.api.pagination import decode_cursor, encode_cursor
from monetae.api.schemas import budgets as schema
from monetae.db.models import Budget, BudgetCategory, BudgetTransaction, Category, Transaction, User
from monetae.domain.budgets import BudgetPeriod, current_cycle, validate_dates
from monetae.domain.currency import Currency
from monetae.domain.money import Money
from monetae.reports.budgets import budget_expenses
from monetae.reports.service import Totals
from monetae.services.auth import AuthError, Clock


class BudgetService:
    def __init__(self, db: Session, secret: str, clock: Clock) -> None:
        self.db, self.secret, self.clock = db, secret, clock

    def get(self, user: User, budget_id: UUID, *, lock: bool = False) -> Budget:
        query = (
            select(Budget)
            .where(Budget.id == budget_id, Budget.user_id == user.id, Budget.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        row = self.db.scalar(query)
        if row is None:
            raise AuthError(404, "not_found", "Budget not found.")
        return row

    def validate_categories(self, user: User, limits: list[schema.BudgetCategoryLimit]) -> None:
        ids = {limit.category_id for limit in limits}
        if (
            ids
            and set(
                self.db.scalars(
                    select(Category.id).where(
                        Category.user_id == user.id,
                        Category.id.in_(ids),
                        Category.deleted_at.is_(None),
                    )
                )
            )
            != ids
        ):
            raise AuthError(404, "not_found", "A requested category was not found.")

    def replace_categories(self, row: Budget, limits: list[schema.BudgetCategoryLimit]) -> None:
        links = list(
            self.db.scalars(
                select(BudgetCategory).where(
                    BudgetCategory.user_id == row.user_id, BudgetCategory.budget_id == row.id
                )
            )
        )
        existing = {link.category_id: link for link in links}
        desired = {limit.category_id: Decimal(limit.limit_amount) for limit in limits}
        for link in links:
            link.deleted_at = None if link.category_id in desired else self.clock.now()
            if link.category_id in desired:
                link.limit_amount = desired[link.category_id]
        for category_id, amount in desired.items():
            if category_id not in existing:
                self.db.add(
                    BudgetCategory(
                        user_id=row.user_id,
                        budget_id=row.id,
                        category_id=category_id,
                        limit_amount=amount,
                    )
                )

    def create(self, user: User, payload: schema.BudgetCreate) -> Budget:
        self.validate_categories(user, payload.category_limits)
        row = Budget(
            id=uuid4(),
            user_id=user.id,
            name=payload.name,
            period=payload.period,
            start_on=payload.start_on,
            end_on=payload.end_on,
            amount=Decimal(payload.amount),
            currency=payload.currency,
            scope=payload.scope,
            color=payload.color,
        )
        self.db.add(row)
        self.db.flush()
        self.replace_categories(row, payload.category_limits)
        self.db.flush()
        return row

    def update(self, user: User, budget_id: UUID, payload: schema.BudgetUpdate) -> Budget:
        row = self.get(user, budget_id, lock=True)
        period = payload.period if payload.period is not None else cast(BudgetPeriod, row.period)
        start = payload.start_on if payload.start_on is not None else row.start_on
        end = payload.end_on if "end_on" in payload.model_fields_set else row.end_on
        try:
            validate_dates(period, start, end)
        except ValueError as exc:
            raise AuthError(422, "validation_error", str(exc)) from exc
        if payload.category_limits is not None:
            self.validate_categories(user, payload.category_limits)
        for field in payload.model_fields_set - {"category_limits"}:
            value = getattr(payload, field)
            setattr(row, field, Decimal(value) if field == "amount" else value)
        if payload.category_limits is not None:
            self.replace_categories(row, payload.category_limits)
        row.updated_at = self.clock.now()
        self.db.flush()
        return row

    def delete(self, user: User, budget_id: UUID) -> None:
        row = self.get(user, budget_id, lock=True)
        row.deleted_at = self.clock.now()
        self.db.flush()

    def assign(self, user: User, budget_id: UUID, ids: list[UUID]) -> Budget:
        row = self.get(user, budget_id, lock=True)
        desired = set(ids)
        if (
            desired
            and set(
                self.db.scalars(
                    select(Transaction.id).where(
                        Transaction.user_id == user.id,
                        Transaction.id.in_(desired),
                        Transaction.deleted_at.is_(None),
                    )
                )
            )
            != desired
        ):
            raise AuthError(404, "not_found", "A requested transaction was not found.")
        links = list(
            self.db.scalars(
                select(BudgetTransaction).where(
                    BudgetTransaction.user_id == user.id, BudgetTransaction.budget_id == row.id
                )
            )
        )
        existing = {link.transaction_id for link in links}
        for link in links:
            link.deleted_at = None if link.transaction_id in desired else self.clock.now()
        for transaction_id in desired - existing:
            self.db.add(
                BudgetTransaction(user_id=user.id, budget_id=row.id, transaction_id=transaction_id)
            )
        row.updated_at = self.clock.now()
        self.db.flush()
        return row

    def representations(self, user: User, rows: list[Budget]) -> list[schema.Budget]:
        if not rows:
            return []
        today = self.clock.now().astimezone(ZoneInfo(user.timezone)).date()
        cycles = {
            row.id: current_cycle(cast(BudgetPeriod, row.period), row.start_on, row.end_on, today)
            for row in rows
        }
        expenses = budget_expenses(self.db, user, cycles)
        categories: dict[UUID, list[schema.BudgetCategoryLimit]] = {}
        for link in self.db.scalars(
            select(BudgetCategory)
            .where(
                BudgetCategory.user_id == user.id,
                BudgetCategory.budget_id.in_(cycles),
                BudgetCategory.deleted_at.is_(None),
            )
            .order_by(BudgetCategory.category_id)
        ):
            categories.setdefault(link.budget_id, []).append(
                schema.BudgetCategoryLimit(
                    category_id=link.category_id, limit_amount=f"{link.limit_amount:.2f}"
                )
            )
        result = []
        for row in rows:
            totals = Totals()
            for entry in expenses.get(row.id, []):
                totals.add(entry)
            report = totals.representation(row.currency)
            currency = Currency(row.currency)
            spent = Money.parse(report.report_amount, currency)
            remaining = Money(row.amount, currency) - spent
            result.append(
                schema.Budget(
                    name=row.name,
                    period=cast(BudgetPeriod, row.period),
                    start_on=row.start_on,
                    end_on=row.end_on,
                    amount=f"{row.amount:.2f}",
                    currency=row.currency,
                    scope=cast(schema.Scope, row.scope),
                    color=row.color,
                    category_limits=categories.get(row.id, []),
                    id=row.id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    deleted_at=row.deleted_at,
                    spent_amount=spent.format(),
                    remaining_amount=remaining.format(),
                    report_total=report,
                )
            )
        return result

    def representation(self, user: User, row: Budget) -> schema.Budget:
        return self.representations(user, [row])[0]

    def list(self, user: User, limit: int, cursor: str | None) -> schema.BudgetPage:
        filters = json.dumps([str(user.id)])
        key = decode_cursor(cursor, "budgets", filters, self.secret)
        query = select(Budget).where(Budget.user_id == user.id, Budget.deleted_at.is_(None))
        if key is not None:
            try:
                if len(key) != 2:
                    raise ValueError
                created, entity_id = datetime.fromisoformat(key[0]), UUID(key[1])
                if created.tzinfo is None:
                    raise ValueError
            except ValueError as exc:
                raise AuthError(400, "invalid_cursor", "The pagination cursor is invalid.") from exc
            query = query.where(tuple_(Budget.created_at, Budget.id) > tuple_(created, entity_id))
        rows = list(self.db.scalars(query.order_by(Budget.created_at, Budget.id).limit(limit + 1)))
        page = rows[:limit]
        next_cursor = (
            encode_cursor(
                "budgets", filters, [page[-1].created_at.isoformat(), str(page[-1].id)], self.secret
            )
            if len(rows) > limit
            else None
        )
        return schema.BudgetPage(items=self.representations(user, page), next_cursor=next_cursor)
