#!/usr/bin/env python3
"""Generate synthetic Cashew fixtures, deterministically, with Python 3.9+."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Union

SqlValue = Union[str, int, None]  # noqa: UP007 -- alias evaluated by Python 3.9
Row = dict[str, SqlValue]
# Any is confined to the heterogeneous JSON manifest serialization boundary.
Manifest = dict[str, Any]
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "services/api/tests/fixtures/cashew_v48"
NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")
BASE_DATE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
CSV_HEADER = [
    "account",
    "amount",
    "amount unpaid",
    "currency",
    "title",
    "note",
    "date",
    "income",
    "type",
    "category name",
    "subcategory name",
    "color",
    "icon",
    "emoji",
    "budget",
    "objective",
    "extra",
]
V48_ONLY = {
    "wallets": {"archived", "emoji_icon_name"},
    "categories": {"archived"},
    "associated_titles": {"archived"},
    "scanner_templates": {"default_title"},
}
# Literal CREATE TABLE statements from 03-backup-format.md §3.3, including
# its actual column counts (wallets=13 and categories=12).
DDL = (
    """  CREATE TABLE "wallets" (
    "wallet_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "currency" TEXT NULL,
    "currency_format" TEXT NULL,
    "decimals" INTEGER NOT NULL DEFAULT 2,
    "home_page_widget_display" TEXT NULL DEFAULT NULL,
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1)),
    "emoji_icon_name" TEXT NULL
  );""",
    """  CREATE TABLE "categories" (
    "category_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "method_added" INTEGER NULL,
    "main_category_pk" TEXT NULL DEFAULT NULL REFERENCES categories (category_pk),
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1))
  );""",
    """  CREATE TABLE "objectives" (
    "objective_pk" TEXT NOT NULL PRIMARY KEY,
    "type" INTEGER NOT NULL DEFAULT 0,
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "order" INTEGER NOT NULL,
    "colour" TEXT NULL,
    "date_created" INTEGER NOT NULL,
    "end_date" INTEGER NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "pinned" INTEGER NOT NULL DEFAULT 1 CHECK ("pinned" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk)
  );""",
    """  CREATE TABLE "transactions" (
    "transaction_pk" TEXT NOT NULL PRIMARY KEY,
    "paired_transaction_fk" TEXT NULL DEFAULT NULL REFERENCES transactions (transaction_pk),
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "note" TEXT NOT NULL,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "sub_category_fk" TEXT NULL DEFAULT NULL REFERENCES categories (category_pk),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "original_date_due" INTEGER NULL DEFAULT 1753912320,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "period_length" INTEGER NULL,
    "reoccurrence" INTEGER NULL,
    "end_date" INTEGER NULL,
    "upcoming_transaction_notification" INTEGER NULL DEFAULT 1 CHECK ("upcoming_transaction_notification" IN (0, 1)),
    "type" INTEGER NULL,
    "paid" INTEGER NOT NULL DEFAULT 0 CHECK ("paid" IN (0, 1)),
    "created_another_future_transaction" INTEGER NULL DEFAULT 0 CHECK ("created_another_future_transaction" IN (0, 1)),
    "skip_paid" INTEGER NOT NULL DEFAULT 0 CHECK ("skip_paid" IN (0, 1)),
    "method_added" INTEGER NULL,
    "transaction_owner_email" TEXT NULL,
    "transaction_original_owner_email" TEXT NULL,
    "shared_key" TEXT NULL,
    "shared_old_key" TEXT NULL,
    "shared_status" INTEGER NULL,
    "shared_date_updated" INTEGER NULL,
    "shared_reference_budget_pk" TEXT NULL,
    "objective_fk" TEXT NULL REFERENCES objectives (objective_pk),
    "objective_loan_fk" TEXT NULL REFERENCES objectives (objective_pk),
    "budget_fks_exclude" TEXT NULL
  );""",
    """  CREATE TABLE "budgets" (
    "budget_pk" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "colour" TEXT NULL,
    "start_date" INTEGER NOT NULL,
    "end_date" INTEGER NOT NULL,
    "wallet_fks" TEXT NULL,
    "category_fks" TEXT NULL,
    "category_fks_exclude" TEXT NULL,
    "income" INTEGER NOT NULL DEFAULT 0 CHECK ("income" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "added_transactions_only" INTEGER NOT NULL DEFAULT 0 CHECK ("added_transactions_only" IN (0, 1)),
    "period_length" INTEGER NOT NULL,
    "reoccurrence" INTEGER NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "pinned" INTEGER NOT NULL DEFAULT 0 CHECK ("pinned" IN (0, 1)),
    "order" INTEGER NOT NULL,
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "budget_transaction_filters" TEXT NULL DEFAULT NULL,
    "member_transaction_filters" TEXT NULL DEFAULT NULL,
    "shared_key" TEXT NULL,
    "shared_owner_member" INTEGER NULL,
    "shared_date_updated" INTEGER NULL,
    "shared_members" TEXT NULL,
    "shared_all_members_ever" TEXT NULL,
    "is_absolute_spending_limit" INTEGER NOT NULL DEFAULT 0 CHECK ("is_absolute_spending_limit" IN (0, 1))
  );""",
    """  CREATE TABLE "category_budget_limits" (
    "category_limit_pk" TEXT NOT NULL PRIMARY KEY,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "budget_fk" TEXT NOT NULL REFERENCES budgets (budget_pk),
    "amount" REAL NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk)
  );""",
    """  CREATE TABLE "associated_titles" (
    "associated_title_pk" TEXT NOT NULL PRIMARY KEY,
    "category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "title" TEXT NOT NULL,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "order" INTEGER NOT NULL,
    "is_exact_match" INTEGER NOT NULL DEFAULT 0 CHECK ("is_exact_match" IN (0, 1)),
    "archived" INTEGER NOT NULL DEFAULT (0) CHECK ("archived" IN (0, 1))
  );""",
    """  CREATE TABLE "app_settings" (
    "settings_pk" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "settings_j_s_o_n" TEXT NOT NULL,
    "date_updated" INTEGER NOT NULL
  );""",
    """  CREATE TABLE "scanner_templates" (
    "scanner_template_pk" TEXT NOT NULL PRIMARY KEY,
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL DEFAULT 1753912320,
    "template_name" TEXT NOT NULL,
    "contains" TEXT NOT NULL,
    "title_transaction_before" TEXT NOT NULL,
    "title_transaction_after" TEXT NOT NULL,
    "amount_transaction_before" TEXT NOT NULL,
    "amount_transaction_after" TEXT NOT NULL,
    "default_category_fk" TEXT NOT NULL REFERENCES categories (category_pk),
    "wallet_fk" TEXT NOT NULL DEFAULT '0' REFERENCES wallets (wallet_pk),
    "ignore" INTEGER NOT NULL DEFAULT 0 CHECK ("ignore" IN (0, 1)),
    "default_title" TEXT NULL DEFAULT (NULL)
  );""",
    """  CREATE TABLE "delete_logs" (
    "delete_log_pk" TEXT NOT NULL PRIMARY KEY,
    "entry_pk" TEXT NOT NULL,
    "type" INTEGER NOT NULL,
    "date_time_modified" INTEGER NOT NULL DEFAULT 1753912320
  );""",
    """  CREATE TABLE "tags" (
    "date_created" INTEGER NOT NULL,
    "date_time_modified" INTEGER NULL,
    "order" INTEGER NOT NULL,
    "archived" INTEGER NOT NULL DEFAULT 0 CHECK ("archived" IN (0, 1)),
    "name" TEXT NOT NULL,
    "colour" TEXT NULL,
    "icon_name" TEXT NULL,
    "emoji_icon_name" TEXT NULL,
    "tag_pk" TEXT NOT NULL PRIMARY KEY
  );""",
    """  CREATE TABLE "transaction_to_tag_links" (
    "transaction_pk" TEXT NULL REFERENCES transactions (transaction_pk),
    "tag_pk" TEXT NULL REFERENCES tags (tag_pk),
    PRIMARY KEY ("transaction_pk", "tag_pk")
  );""",
)


def uid(label: str) -> str:
    """Stable UUID v5: labels are the readable fixture row map."""
    return str(uuid.uuid5(NAMESPACE, label))


def timestamp(day: int = 0) -> int:
    return int((BASE_DATE + timedelta(days=day)).timestamp())


def build_data() -> dict[str, list[Row]]:
    data: dict[str, list[Row]] = {statement.split('"')[1]: [] for statement in DDL}
    for index, (label, name, currency, archived) in enumerate(
        [
            ("soles", "Cuenta Soles", "PEN", 0),
            ("dollars", "Cuenta Dolares", "USD", 0),
            ("cash", "Efectivo", "PEN", 0),
            ("archived", "Cuenta Archivada Ejemplo", "PEN", 1),
        ]
    ):
        data["wallets"].append(
            {
                "wallet_pk": uid(label),
                "name": name,
                "currency": currency,
                "order": index,
                "date_created": timestamp(),
                "date_time_modified": timestamp(),
                "archived": archived,
                "colour": "#336699",
                "icon_name": "wallet",
                "emoji_icon_name": "💰" if archived else None,
            }
        )
    for index, (label, name, income, parent) in enumerate(
        [
            ("food", "Alimentación", 0, None),
            ("restaurant", "Restaurantes", 0, "food"),
            ("interest", "Intereses", 0, None),
            ("services", "Servicios", 0, None),
            ("salary", "Salario", 1, None),
            ("loans", "Préstamos", 0, None),
            ("transfers", "Transferencias", 0, None),
        ]
    ):
        data["categories"].append(
            {
                "category_pk": uid(label),
                "name": name,
                "order": index,
                "date_created": timestamp(),
                "date_time_modified": timestamp(),
                "income": income,
                "main_category_pk": uid(parent) if parent else None,
                "colour": "#336699",
                "icon_name": "category",
                "archived": 0,
            }
        )
    for index, (case, wallet) in enumerate(
        [
            ("A", "cash"),
            ("B", "soles"),
            ("C", "dollars"),
            ("D", "dollars"),
            ("E", "soles"),
        ]
    ):
        data["objectives"].append(
            {
                "objective_pk": uid("loan_" + case),
                "type": 1,
                "name": "Persona Ejemplo " + case,
                "amount": "0.00",
                "order": index,
                "income": int(case != "A"),
                "wallet_fk": uid(wallet),
                "date_created": timestamp(),
                "date_time_modified": timestamp(),
            }
        )

    def tx(
        label: str,
        amount: str,
        wallet: str,
        day: int,
        case: str | None = None,
        category: str = "loans",
        **extra: SqlValue,
    ) -> None:
        row: Row = {
            "transaction_pk": uid(label),
            "name": "Ejemplo " + label,
            "amount": amount,
            "income": int(Decimal(amount) > 0),
            "paid": 1,
            "wallet_fk": uid(wallet),
            "category_fk": uid(category),
            "date_created": timestamp(day),
            "date_time_modified": timestamp(day),
            "original_date_due": timestamp(day),
            "note": "Datos sintéticos; caso " + (case or label),
            "objective_loan_fk": uid("loan_" + case) if case else None,
        }
        row.update(extra)
        data["transactions"].append(row)

    tx("A_disbursement", "200.00", "cash", 0, "A")
    tx("A_interest", "-10.00", "cash", 1, category="interest")
    tx("A_payment_1", "-100.00", "soles", 2, "A")
    tx("A_payment_2", "-110.00", "cash", 3, "A")
    tx("B_disbursement", "-500.00", "soles", 0, "B")
    tx("B_payment_1", "300.00", "cash", 4, "B")
    tx("B_payment_2", "200.00", "soles", 5, "B")
    tx("C_disbursement", "-100.00", "dollars", 0, "C")
    tx("C_payment_1", "380.00", "soles", 6, "C")
    tx("D_disbursement", "-50.00", "dollars", 0, "D")
    tx("D_payment_1", "60.00", "dollars", 7, "D")
    tx("E_disbursement", "-1000.00", "soles", 0, "E")
    for index, amount in enumerate(["50.00", "120.00", "30.00", "800.00"], 1):
        tx("E_payment_" + str(index), amount, "soles", 8 + index, "E")
    tx("F_settled", "-150.00", "soles", 0, type=3, paid=0)
    tx("F_open", "80.00", "cash", 1, type=4)
    tx(
        "G_subscription",
        "-44.90",
        "soles",
        10,
        category="services",
        type=1,
        reoccurrence=3,
        period_length=1,
    )
    tx(
        "G_repetitive",
        "2500.00",
        "soles",
        10,
        category="salary",
        type=2,
        reoccurrence=3,
        period_length=1,
    )
    tx(
        "H_out",
        "-200.00",
        "soles",
        11,
        category="transfers",
        paired_transaction_fk=uid("H_in"),
    )
    tx(
        "H_in",
        "200.00",
        "cash",
        11,
        category="transfers",
        paired_transaction_fk=uid("H_out"),
    )
    tx(
        "I_food",
        "-25.50",
        "soles",
        12,
        category="food",
        sub_category_fk=uid("restaurant"),
    )
    tx("K_future", "-35.00", "soles", 40, category="services", type=0, paid=0)
    tx("K_archived_wallet", "-12.00", "archived", 13, category="food")
    data["budgets"].append(
        {
            "budget_pk": uid("budget"),
            "name": "Presupuesto Mensual Ejemplo",
            "amount": "2000.00",
            "start_date": timestamp(),
            "end_date": timestamp(30),
            "date_created": timestamp(),
            "date_time_modified": timestamp(),
            "order": 0,
            "period_length": 1,
            "reoccurrence": 3,
            "wallet_fk": uid("soles"),
            "wallet_fks": json.dumps([uid("soles")]),
            "category_fks": json.dumps([uid("food")]),
        }
    )
    data["category_budget_limits"].append(
        {
            "category_limit_pk": uid("limit"),
            "budget_fk": uid("budget"),
            "category_fk": uid("food"),
            "amount": "800.00",
            "wallet_fk": uid("soles"),
            "date_time_modified": timestamp(),
        }
    )
    data["associated_titles"].append(
        {
            "associated_title_pk": uid("title_rule"),
            "category_fk": uid("restaurant"),
            "title": "Restaurante Ejemplo",
            "date_created": timestamp(),
            "date_time_modified": timestamp(),
            "order": 0,
            "archived": 1,
        }
    )
    data["app_settings"].append(
        {
            "settings_pk": 1,
            "date_updated": timestamp(),
            "settings_j_s_o_n": json.dumps({"selectedWalletPk": uid("soles")}),
        }
    )
    data["scanner_templates"].append(
        {
            "scanner_template_pk": uid("scanner"),
            "date_created": timestamp(),
            "date_time_modified": timestamp(),
            "template_name": "Plantilla Ejemplo",
            "contains": "Restaurante Ejemplo",
            "title_transaction_before": "",
            "title_transaction_after": "",
            "amount_transaction_before": "",
            "amount_transaction_after": "",
            "default_category_fk": uid("food"),
            "wallet_fk": uid("soles"),
            "default_title": "Compra Ejemplo",
        }
    )
    data["delete_logs"].append(
        {
            "delete_log_pk": uid("deletion"),
            "entry_pk": uid("deleted_transaction"),
            "type": 0,
            "date_time_modified": timestamp(14),
        }
    )
    for index, name in enumerate(
        ["Trabajo Ejemplo", "Viaje Ejemplo", "Antigua Ejemplo"]
    ):
        data["tags"].append(
            {
                "tag_pk": uid("tag_" + str(index)),
                "name": name,
                "order": index,
                "archived": int(index == 2),
                "colour": "#336699",
                "icon_name": "label",
                "emoji_icon_name": "🏷",
                "date_created": timestamp(),
                "date_time_modified": timestamp(),
            }
        )
    for label, tag in [("G_repetitive", 0), ("G_repetitive", 1), ("G_subscription", 2)]:
        data["transaction_to_tag_links"].append(
            {
                "transaction_pk": uid(label),
                "tag_pk": uid("tag_" + str(tag)),
            }
        )
    return data


def create_database(data: dict[str, list[Row]], version: int) -> Path:
    path = TARGET / (
        "synthetic_v48.sqlite" if version == 48 else "synthetic_v46_no_tags.sqlite"
    )
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA defer_foreign_keys = ON")
        for statement in DDL:
            table = statement.split('"')[1]
            if version == 46 and table in {"tags", "transaction_to_tag_links"}:
                continue
            removed = V48_ONLY.get(table, set()) if version == 46 else set()
            if removed:
                lines = [
                    line
                    for line in statement.splitlines()
                    if not any(
                        line.strip().startswith('"' + col + '"') for col in removed
                    )
                ]
                lines[-2] = lines[-2].rstrip(",")
                statement = "\n".join(lines)
            conn.execute(statement)
        conn.execute("PRAGMA user_version = " + str(version))
        conn.execute("BEGIN")
        conn.execute("PRAGMA defer_foreign_keys = ON")
        for table, rows in data.items():
            if version == 46 and table in {"tags", "transaction_to_tag_links"}:
                continue
            removed = V48_ONLY.get(table, set()) if version == 46 else set()
            for row in rows:
                filtered = {
                    key: value for key, value in row.items() if key not in removed
                }
                # Identifiers are internal constants; every inserted value is parameterized.
                columns = ",".join('"' + col + '"' for col in filtered)
                placeholders = ",".join("?" for _ in filtered)
                conn.execute(
                    f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
                    tuple(filtered.values()),
                )
        conn.commit()
    return path


def write_csv(data: dict[str, list[Row]]) -> Path:
    path = TARGET / "synthetic_v48.csv"
    wallets = {row["wallet_pk"]: row for row in data["wallets"]}
    categories = {row["category_pk"]: row for row in data["categories"]}
    objectives = {row["objective_pk"]: row for row in data["objectives"]}
    types = ["upcoming", "subscription", "repetitive", "credit", "debt"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for tx in data["transactions"]:
            if tx["paid"] != 1:
                continue
            wallet = wallets[tx["wallet_fk"]]
            cat = categories[tx["category_fk"]]
            subcat = categories.get(tx.get("sub_category_fk"), {})
            objective = objectives.get(tx.get("objective_loan_fk"), {})
            kind = tx.get("type")
            assert kind is None or isinstance(kind, int)
            date = tx["date_created"]
            assert isinstance(date, int)
            budget = (
                "Presupuesto Mensual Ejemplo" if tx["name"] == "Ejemplo I_food" else ""
            )
            writer.writerow(
                [
                    wallet["name"],
                    tx["amount"],
                    "",
                    wallet["currency"],
                    tx["name"],
                    tx["note"],
                    datetime.fromtimestamp(date, timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S.000"
                    ),
                    "true" if tx["income"] else "false",
                    "null" if kind is None else "TransactionSpecialType." + types[kind],
                    cat["name"],
                    subcat.get("name", ""),
                    cat["colour"],
                    cat["icon_name"],
                    cat.get("emoji_icon_name") or "",
                    budget,
                    objective.get("name", ""),
                    "",
                ]
            )
    return path


def expected_manifest(data: dict[str, list[Row]]) -> Manifest:
    """Literal expectations: do not calculate balances from generated transactions."""
    cases: Manifest = {}
    definitions = [
        ("A", "PEN", "200.00", "10.00", ["100.00", "110.00"], ["110.00", "0.00"]),
        ("B", "PEN", "500.00", "0.00", ["300.00", "200.00"], ["200.00", "0.00"]),
        ("C", "USD", "100.00", "0.00", ["100.00"], ["0.00"]),
        ("D", "USD", "50.00", "0.00", ["60.00"], ["-10.00"]),
        (
            "E",
            "PEN",
            "1000.00",
            "0.00",
            ["50.00", "120.00", "30.00", "800.00"],
            ["950.00", "830.00", "800.00", "0.00"],
        ),
    ]
    for case, currency, principal, interest, payments, balances in definitions:
        cases[case] = {
            "objective_pk": uid("loan_" + case),
            "currency": currency,
            "direction": "borrowed" if case == "A" else "lent",
            "monetae": {
                "principal": principal,
                "interest": interest,
                "payments_in_loan_currency": payments,
                "balances_after_payments": balances,
                "outstanding_balance": balances[-1],
                "status": "open" if case == "D" else "settled",
                "requires_review": case in {"A", "C", "D"},
            },
            "cashew": {
                "principal_nominal": principal,
                "payments_nominal": {
                    "A": "210.00",
                    "B": "500.00",
                    "C": "380.00",
                    "D": "60.00",
                    "E": "1000.00",
                }[case],
                "nominal_outstanding": {
                    "A": "-10.00",
                    "B": "0.00",
                    "C": "-280.00",
                    "D": "-10.00",
                    "E": "0.00",
                }[case],
                "nominal_status": "settled",
            },
        }
    cases["A"]["monetae"]["interpretation"] = (
        "Tras confirmar asociación del interés huérfano como cargo de 10 al préstamo; "
        "no crear otro débito en cuenta. El gasto Cashew -10 y pagos -210 suman "
        "una salida adicional de 10 respecto al ejemplo Monetae; revisar doble conteo."
    )
    cases["C"]["monetae"]["fx_rate_applied"] = "3.800000"
    cases["C"]["monetae"]["fx_convention"] = "PEN por USD; 380 / 3.800000 = 100.00 USD"
    cases["C"]["cashew"]["interpretation"] = (
        "Agregación nominal ilustrativa de §6.2, no suma válida de monedas. "
        "Las consultas de 02-loans §4.1 filtran por wallet: USD capital 100/pagos 0; "
        "PEN capital 0/pagos 380. Sin tasa histórica no se reconstruye estado económico."
    )
    cases["D"]["monetae"].update(
        {
            "overpayment": "10.00",
            "warning_required": True,
            "import_all_cash_transactions": True,
            "excess_resolution_selected_by": "user_during_manual_review",
            "import_note": "Importar la transacción completa +60 USD y conservar saldos Cashew; solo la representación del exceso en el libro del préstamo queda pendiente (RF-40c/d).",
            "outstanding_balance": "-10.00",
            "status": "open",
            "interpretation": "Saldo bruto diagnóstico: no persistir exceso sin confirmación atómica RF-22.",
            "after_confirmed_excess_as_income": {
                "excess_handling": "income_expense",
                "applied_payment": "50.00",
                "excess_income": "10.00",
                "outstanding_balance": "0.00",
                "status": "settled",
            },
            "after_confirmed_capital_adjustment": {
                "excess_handling": "adjustment",
                "adjustment": "10.00",
                "applied_payment": "60.00",
                "outstanding_balance": "0.00",
                "status": "settled",
            },
        }
    )
    counts = {
        "wallets": 4,
        "categories": 7,
        "objectives": 5,
        "transactions": 25,
        "budgets": 1,
        "category_budget_limits": 1,
        "associated_titles": 1,
        "app_settings": 1,
        "scanner_templates": 1,
        "delete_logs": 1,
        "tags": 3,
        "transaction_to_tag_links": 3,
    }
    return {
        "synthetic_only": True,
        "namespace": str(NAMESPACE),
        "table_counts_v48": counts,
        "table_counts_v46": {
            k: v
            for k, v in counts.items()
            if k not in {"tags", "transaction_to_tag_links"}
        },
        "wallets": [
            {
                "wallet_pk": uid(label),
                "name": name,
                "currency": currency,
                "balance": balance,
                "archived_v48": archived,
            }
            for label, name, currency, balance, archived in [
                ("soles", "Cuenta Soles", "PEN", "2209.60", 0),
                ("dollars", "Cuenta Dolares", "USD", "-90.00", 0),
                ("cash", "Efectivo", "PEN", "660.00", 0),
                ("archived", "Cuenta Archivada Ejemplo", "PEN", "-12.00", 1),
            ]
        ],
        "loan_cases": cases,
        "row_map": {
            str(row["name"]).removeprefix("Ejemplo "): row["transaction_pk"]
            for row in data["transactions"]
        },
        "one_time_loans": [
            {
                "transaction_pk": uid("F_settled"),
                "type": 3,
                "paid": 0,
                "amount": "-150.00",
                "cashew_status": "settled",
                "requires_review": True,
            },
            {
                "transaction_pk": uid("F_open"),
                "type": 4,
                "paid": 1,
                "amount": "80.00",
                "cashew_status": "open",
                "requires_review": False,
            },
        ],
        "ambiguous_cases": [
            {
                "case": "A",
                "reason": "Interés huérfano sin objective_loan_fk; pagos 210 > capital 200; posible doble conteo de gasto.",
            },
            {
                "case": "C",
                "reason": "Desembolso USD y pago PEN; sin tasa histórica en Cashew; confirmar 3.800000 PEN/USD.",
            },
            {
                "case": "D",
                "reason": "Pago 60 > capital 50 USD: aviso obligatorio y confirmación de ingreso o ajuste por 10.",
            },
            {
                "case": "F_settled",
                "reason": "paid=0 sin contraparte: faltan fecha y cuenta de pago; no sintetizar sin confirmar.",
            },
        ],
        "tags": data["tags"],
        "tag_links": data["transaction_to_tag_links"],
        "untagged_transaction_pk": uid("I_food"),
        "csv": {
            "header": CSV_HEADER,
            "paid_rows": 23,
            "excluded_rows": 2,
            "excluded_transaction_pks": [uid("F_settled"), uid("K_future")],
            "unknown_columns_left_empty": ["amount unpaid", "extra"],
            "import_note": "Semántica v48 desconocida (03 §2.4): el importador debe ignorar amount unpaid y extra; nunca usarlas para calcular saldos.",
        },
    }


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    data = build_data()
    paths = [create_database(data, 48), create_database(data, 46), write_csv(data)]
    expected = TARGET / "expected.json"
    expected.write_text(
        json.dumps(expected_manifest(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for path in paths + [expected]:
        print(f"{path.name}: sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
