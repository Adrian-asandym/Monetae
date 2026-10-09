"""Una transacción, savepoint financiero y auditoría durable al confirmar el caller."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from monetae.db.models import (
    Account,
    Category,
    ImportReviewItem,
    ImportRun,
    Tag,
    Transaction,
    TransactionTag,
    User,
)
from monetae.importers.cashew import loans, subscriptions
from monetae.importers.cashew.mapping import (
    ImportFailure,
    ImportOptions,
    ImportPlan,
    TransactionPlan,
    build_plan,
    external_id,
    transaction_tag_map,
)
from monetae.importers.cashew.reader import Snapshot, TransactionRow
from monetae.importers.cashew.report import AccountBalance, ImportReport, ReviewItem


class ImportExecutionError(ImportFailure):
    def __init__(self, report: ImportReport, message: str) -> None:
        super().__init__(message)
        self.report = report


@dataclass
class ImportContext:
    """Interfaz compartida de pasos. T-402/T-403 implementan solo su módulo run(context).

    insert_transaction conserva etiquetas al crear, incluidas las archivadas.
    defer registra importe bruto y cuenta para el cuadre, sin escribir efectivo.
    Los pasos pueden usar session, plan, snapshot y opciones en la misma transacción.
    """

    session: Session
    user_id: UUID
    snapshot: Snapshot
    options: ImportOptions
    plan: ImportPlan
    report: ImportReport
    accounts: dict[str, Account] = field(default_factory=dict)
    categories: dict[str, Category] = field(default_factory=dict)
    tags: dict[str, Tag] = field(default_factory=dict)
    transactions: dict[str, Transaction] = field(default_factory=dict)
    before: dict[str, Decimal] = field(default_factory=dict)
    deferred_amounts: dict[str, Decimal] = field(default_factory=dict)
    tag_links: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def defer(self, rows: tuple[TransactionRow, ...], entity: str) -> None:
        self.report.entity(entity).deferred += len(rows)
        for row in rows:
            if row.paid:
                self.deferred_amounts[row.wallet_pk] = (
                    self.deferred_amounts.get(row.wallet_pk, Decimal("0.00")) + row.amount
                )

    def insert_transaction(
        self,
        mapped: TransactionPlan,
        *,
        kind: str | None = None,
        transfer_group_id: UUID | None = None,
        external_id_override: str | None = None,
    ) -> Transaction:
        source = mapped.source
        identity = external_id_override or external_id(source.pk)
        existing = self.session.scalar(
            select(Transaction).where(
                Transaction.user_id == self.user_id, Transaction.import_external_id == identity
            )
        )
        if existing is not None:
            self.report.entity("transactions").already_imported += 1
            self.transactions[source.pk] = existing
            return existing
        account = self.accounts[source.wallet_pk]
        if account.deleted_at is not None or account.currency != mapped.currency:
            raise ImportFailure("Cuenta importada borrada o con moneda incompatible.")
        category = self.categories.get(mapped.category_pk or "")
        if mapped.category_pk is not None and category is None:
            self.report.warnings.append(f"missing_category:{source.pk}")
        row = Transaction(
            user_id=self.user_id,
            account_id=account.id,
            currency=mapped.currency,
            kind=kind or mapped.kind,
            amount=mapped.amount,
            category_id=category.id if category and kind != "transfer" else None,
            occurred_at=source.occurred_at,
            status=mapped.status,
            title=source.name,
            note=source.note,
            fx_rate_to_base=mapped.fx_rate_to_base,
            fx_rate_source=mapped.fx_rate_source,
            transfer_group_id=transfer_group_id,
            source="import",
            categorization_source="manual",
            is_initial_data=mapped.is_initial_data,
            import_external_id=identity,
        )
        self.session.add(row)
        self.session.flush()
        self.report.entity("transactions").created += 1
        if mapped.fx_rate_source != "manual":
            self.report.provisional_fx += 1
        self.transactions[source.pk] = row
        for tag_pk in self.tag_links.get(source.pk, ()):
            tag = self.tags.get(tag_pk)
            if tag is None or tag.deleted_at is not None:
                self.report.warnings.append(f"missing_tag:{source.pk}:{tag_pk}")
                continue
            self.session.add(
                TransactionTag(user_id=self.user_id, transaction_id=row.id, tag_id=tag.id)
            )
            self.report.entity("transaction_tags").created += 1
        self.session.flush()
        return row


def _balance(session: Session, user_id: UUID, account: Account) -> Decimal:
    total = session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account.id,
            Transaction.status == "posted",
            Transaction.deleted_at.is_(None),
        )
    )
    return account.initial_balance + Decimal(str(total))


def _unique_name(name: str, occupied: set[str], report: ImportReport, code: str) -> str:
    result = name
    counter = 1
    while result.lower() in occupied:
        suffix = " (Cashew)" if counter == 1 else f" (Cashew {counter})"
        result = name + suffix
        counter += 1
    if result != name:
        report.warnings.append(code)
    occupied.add(result.lower())
    return result


def _accounts(ctx: ImportContext) -> None:
    existing_rows = list(ctx.session.scalars(select(Account).where(Account.user_id == ctx.user_id)))
    existing = {row.import_external_id: row for row in existing_rows if row.import_external_id}
    occupied = {row.name.lower() for row in existing_rows if row.deleted_at is None}
    for mapped in ctx.plan.accounts:
        source = mapped.source
        row = existing.get(external_id(source.pk))
        if row is None:
            row = Account(
                user_id=ctx.user_id,
                import_external_id=external_id(source.pk),
                name=_unique_name(
                    source.name, occupied, ctx.report, f"account_name_collision:{source.pk}"
                ),
                type="other",
                currency=mapped.currency,
                initial_balance=Decimal("0.00"),
                color=source.color,
                icon=source.icon,
                sort_order=source.sort_order,
                archived_at=(source.modified_at or source.created_at) if source.archived else None,
                created_at=source.created_at,
                updated_at=source.modified_at or source.created_at,
            )
            ctx.session.add(row)
            ctx.session.flush()
            ctx.report.entity("accounts").created += 1
            before = Decimal("0.00")
        else:
            ctx.report.entity("accounts").already_imported += 1
            before = _balance(ctx.session, ctx.user_id, row)
        ctx.accounts[source.pk] = row
        ctx.before[source.pk] = before


def _categories(ctx: ImportContext) -> None:
    existing = {
        row.import_external_id: row
        for row in ctx.session.scalars(select(Category).where(Category.user_id == ctx.user_id))
        if row.import_external_id
    }
    pending = {source.pk: source for source in ctx.snapshot.categories}
    # Dos fases: resolver identidades existentes y luego insertar padres antes que hijos.
    for pk in list(pending):
        row = existing.get(external_id(pk))
        if row is not None:
            ctx.categories[pk] = row
            ctx.report.entity("categories").already_imported += 1
            del pending[pk]
    while pending:
        progressed = False
        for pk, source in list(pending.items()):
            if source.parent_pk and source.parent_pk not in ctx.categories:
                if source.parent_pk in pending:
                    continue
                raise ImportFailure("Categoría con padre inexistente.")
            parent = ctx.categories.get(source.parent_pk or "")
            row = Category(
                user_id=ctx.user_id,
                import_external_id=external_id(pk),
                name=source.name,
                kind="income" if source.income else "expense",
                color=source.color,
                icon=source.icon,
                parent_id=parent.id if parent else None,
                is_system=False,
                created_at=source.created_at,
                updated_at=source.modified_at or source.created_at,
            )
            ctx.session.add(row)
            ctx.session.flush()
            ctx.categories[pk] = row
            ctx.report.entity("categories").created += 1
            if source.name.casefold() == "intereses":
                ctx.report.warnings.append(f"interest_category_not_merged:{pk}")
            del pending[pk]
            progressed = True
        if not progressed:
            raise ImportFailure("Ciclo en la jerarquía de categorías.")
    ctx.report.unmapped_fields["categories"] = ["archived", "emoji_icon_name"]


def _tags(ctx: ImportContext) -> None:
    existing_rows = list(ctx.session.scalars(select(Tag).where(Tag.user_id == ctx.user_id)))
    existing = {row.import_external_id: row for row in existing_rows if row.import_external_id}
    occupied = {row.name.lower() for row in existing_rows if row.deleted_at is None}
    for source in ctx.snapshot.tags:
        row = existing.get(external_id(source.pk))
        if row is None:
            row = Tag(
                user_id=ctx.user_id,
                import_external_id=external_id(source.pk),
                name=_unique_name(
                    source.name, occupied, ctx.report, f"tag_name_collision:{source.pk}"
                ),
                color=source.color,
                icon=source.icon,
                emoji=source.emoji,
                sort_order=source.sort_order,
                archived_at=(source.modified_at or source.created_at) if source.archived else None,
                created_at=source.created_at,
                updated_at=source.modified_at or source.created_at,
            )
            ctx.session.add(row)
            ctx.session.flush()
            ctx.report.entity("tags").created += 1
        else:
            ctx.report.entity("tags").already_imported += 1
        ctx.tags[source.pk] = row


def _transfers(ctx: ImportContext) -> None:
    for left, right in ctx.plan.transfers:
        rows = list(
            ctx.session.scalars(
                select(Transaction).where(
                    Transaction.user_id == ctx.user_id,
                    Transaction.import_external_id.in_(
                        [external_id(left.source.pk), external_id(right.source.pk)]
                    ),
                )
            )
        )
        if len(rows) == 2:
            # Incluso tras edición manual, las identidades existentes nunca se tocan.
            ctx.report.entity("transfers").already_imported += 1
            for mapped in (left, right):
                ctx.insert_transaction(mapped)
            continue
        if rows:
            # No reparar una pata previamente editada/borrada creando un grupo incompleto.
            ctx.report.review_items.append(
                ReviewItem(
                    kind="unpaired_transfer",
                    payload={
                        "transaction_pk": left.source.pk,
                        "paired_pk": right.source.pk,
                        "reason": "partially_imported",
                    },
                )
            )
            for mapped in (left, right):
                ctx.insert_transaction(mapped)
            ctx.report.entity("transfers").skipped += 1
            continue
        group_id = uuid4()
        for mapped in (left, right):
            ctx.insert_transaction(mapped, kind="transfer", transfer_group_id=group_id)
        ctx.report.entity("transfers").created += 1


def _balances(ctx: ImportContext) -> None:
    cashew: dict[str, Decimal] = {}
    for row in ctx.snapshot.transactions:
        if row.paid:
            cashew[row.wallet_pk] = cashew.get(row.wallet_pk, Decimal("0.00")) + row.amount
    for pk, account in ctx.accounts.items():
        actual = _balance(ctx.session, ctx.user_id, account)
        source = cashew.get(pk, Decimal("0.00"))
        deferred = ctx.deferred_amounts.get(pk, Decimal("0.00"))
        ctx.report.balances.append(
            AccountBalance(
                source_wallet_pk=pk,
                account_id=account.id,
                currency=account.currency,
                before=ctx.before[pk],
                cashew_balance=source,
                monetae_balance=actual,
                deferred_amount=deferred,
                unexplained=source - actual - deferred,
            )
        )


def _persist_report(session: Session, user_id: UUID, run: ImportRun, report: ImportReport) -> None:
    run.finished_at = datetime.now(UTC)
    run.report = report.model_dump(mode="json")
    for item in report.review_items:
        session.add(
            ImportReviewItem(
                user_id=user_id,
                import_run_id=run.id,
                kind=item.kind,
                payload=item.model_dump(mode="json")["payload"],
            )
        )
    session.flush()


def run_import(
    session: Session, user_id: UUID, snapshot: Snapshot, options: ImportOptions
) -> ImportReport:
    """El caller confirma incluso ImportExecutionError para guardar la auditoría.

    La operación financiera es atómica dentro de un savepoint. Dry-run y errores
    lo revierten, conservando auditoría en la transacción exterior del caller.
    """
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"cashew-import:{user_id}"},
    )
    session.execute(
        text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key, 0))"),
        {"key": f"transaction-history:{user_id}"},
    )
    base = session.scalar(
        select(User.base_currency).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if base is None:
        raise ImportFailure("El usuario no existe; créelo con create-user.")
    report = ImportReport(
        file_sha256=snapshot.file_sha256,
        source_schema_version=snapshot.schema_version,
        tables=dict(snapshot.tables),
        unknown_tables=list(snapshot.unknown_tables),
        unknown_columns={name: list(cols) for name, cols in snapshot.unknown_columns},
        warnings=list(snapshot.warnings),
    )
    for entity in (
        "accounts",
        "categories",
        "tags",
        "transactions",
        "transaction_tags",
        "transfers",
    ):
        report.entity(entity)
    run = ImportRun(
        user_id=user_id,
        source_kind="sqlite",
        source_schema_version=snapshot.schema_version,
        file_sha256=snapshot.file_sha256,
        mode="dry_run" if options.dry_run else "apply",
        started_at=datetime.now(UTC),
        report={},
    )
    session.add(run)
    session.flush()
    try:
        plan = build_plan(snapshot, base, options)
        report.warnings.extend(plan.warnings)
        report.review_items.extend(plan.review_items)
        ctx = ImportContext(
            session,
            user_id,
            snapshot,
            options,
            plan,
            report,
            tag_links=transaction_tag_map(snapshot),
        )
        with session.begin_nested() as financial:
            _accounts(ctx)
            _categories(ctx)
            _tags(ctx)
            for mapped in plan.normal_transactions:
                ctx.insert_transaction(mapped)
            _transfers(ctx)
            report.steps["loans"] = loans.run(ctx)
            report.steps["subscriptions"] = subscriptions.run(ctx)
            imported_pks = set(ctx.transactions)
            for link in snapshot.tag_links:
                if link.transaction_pk not in imported_pks:
                    report.entity("transaction_tags").deferred += 1
            for table in (
                "budgets",
                "category_budget_limits",
                "associated_titles",
                "scanner_templates",
                "app_settings",
            ):
                report.entity(table).deferred = report.tables.get(table, 0)
            report.entity("goals").deferred = sum(row.type == 0 for row in snapshot.objectives)
            report.steps["phase_6"] = {"code": "pending_phase_6"}
            _balances(ctx)
            session.flush()
            if options.dry_run:
                financial.rollback()
    except Exception as exc:
        # Nunca guardar SQLAlchemy str(exc): podría incluir parámetros privados.
        report.outcome = "failed"
        report.warnings.append("import_failed")
        for counts in report.counts.values():
            counts.created = 0
        report.balances.clear()
        _persist_report(session, user_id, run, report)
        message = (
            str(exc)
            if isinstance(exc, ImportFailure)
            else "Error de importación; datos financieros revertidos."
        )
        raise ImportExecutionError(report, message) from exc
    _persist_report(session, user_id, run, report)
    return report
