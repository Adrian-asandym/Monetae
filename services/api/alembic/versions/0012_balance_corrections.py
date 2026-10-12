"""System categories and independent linked correction legs."""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_categories_system_key"), "categories", type_="check")
    op.create_check_constraint(
        op.f("ck_categories_system_key"),
        "categories",
        "system_key IN ('interest_income', 'interest_expense', "
        "'balance_correction_income', 'balance_correction_expense')",
    )
    op.execute(
        sa.text("""
        INSERT INTO categories (user_id, kind, name, is_system, system_key, icon, color)
        SELECT u.id, kinds.kind, 'Corrección de saldo', true,
               'balance_correction_' || kinds.kind, 'swap_horiz', '#808080'
        FROM users u CROSS JOIN (VALUES ('income'), ('expense')) AS kinds(kind)
        ON CONFLICT (user_id, system_key)
            WHERE deleted_at IS NULL AND system_key IS NOT NULL DO NOTHING
    """)
    )
    op.drop_constraint(op.f("ck_transactions_transfer_group"), "transactions", type_="check")
    op.create_check_constraint(
        op.f("ck_transactions_transfer_group"),
        "transactions",
        "(kind = 'transfer' AND transfer_group_id IS NOT NULL) OR "
        "(kind IN ('income', 'expense')) OR (kind = 'loan' AND transfer_group_id IS NULL)",
    )
    for direction, kind in (("outgoing", "expense"), ("incoming", "income")):
        op.create_index(
            f"uq_transactions_correction_{direction}",
            "transactions",
            ["transfer_group_id"],
            unique=True,
            postgresql_where=sa.text(
                f"kind = '{kind}' AND transfer_group_id IS NOT NULL AND deleted_at IS NULL"
            ),
        )


def downgrade() -> None:
    # Preserve the ledger, selections, tags and category references when reverting:
    # only the new link and category system semantics disappear.
    op.execute(
        sa.text("""
        UPDATE transactions SET transfer_group_id = NULL
        WHERE kind IN ('income', 'expense') AND transfer_group_id IS NOT NULL
    """)
    )
    op.execute(
        sa.text("""
        UPDATE categories SET is_system = false, system_key = NULL
        WHERE system_key IN ('balance_correction_income', 'balance_correction_expense')
    """)
    )
    for direction in ("incoming", "outgoing"):
        op.drop_index(f"uq_transactions_correction_{direction}", table_name="transactions")
    op.drop_constraint(op.f("ck_transactions_transfer_group"), "transactions", type_="check")
    op.create_check_constraint(
        op.f("ck_transactions_transfer_group"),
        "transactions",
        "(kind = 'transfer') = (transfer_group_id IS NOT NULL)",
    )
    op.drop_constraint(op.f("ck_categories_system_key"), "categories", type_="check")
    op.create_check_constraint(
        op.f("ck_categories_system_key"),
        "categories",
        "system_key IN ('interest_income', 'interest_expense')",
    )
