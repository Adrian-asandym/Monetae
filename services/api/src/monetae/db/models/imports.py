"""Auditoría de importaciones, también de simulaciones y fallos atómicos."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from monetae.db.base import UserScopedModel


class ImportRun(UserScopedModel):
    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_import_runs_id_user_id"),
        CheckConstraint("source_kind IN ('sqlite', 'csv')", name="source_kind"),
        CheckConstraint("mode IN ('dry_run', 'apply')", name="mode"),
    )
    source_kind: Mapped[str] = mapped_column(Text)
    source_schema_version: Mapped[int | None]
    file_sha256: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report: Mapped[dict[str, object]] = mapped_column(JSONB)


class ImportReviewItem(UserScopedModel):
    __tablename__ = "import_review_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_run_id", "user_id"],
            ["import_runs.id", "import_runs.user_id"],
            name="fk_import_review_items_run_owner",
        ),
    )
    import_run_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
