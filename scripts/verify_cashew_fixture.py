#!/usr/bin/env python3
"""Independently verify the synthetic fixture using SQL; never import its generator."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import unittest
import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "services/api/tests/fixtures/cashew_v48"
CENT = Decimal("0.01")
# Any is restricted to decoded JSON and sqlite3.Row at these untyped I/O boundaries.
Manifest = dict[str, Any]
HEADER = [
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


def money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def open_fixture(version: int) -> sqlite3.Connection:
    name = "synthetic_v48.sqlite" if version == 48 else "synthetic_v46_no_tags.sqlite"
    conn = sqlite3.connect((TARGET / name).as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


class FixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected: Manifest = json.loads(
            (TARGET / "expected.json").read_text(encoding="utf-8")
        )
        self.v48 = open_fixture(48)
        self.v46 = open_fixture(46)
        self.addCleanup(self.v48.close)
        self.addCleanup(self.v46.close)

    def test_schema_and_counts(self) -> None:
        """Compare the literal doc DDL, columns, FKs and CHECK/default clauses."""
        doc = (ROOT / "docs/cashew-analysis/03-backup-format.md").read_text(
            encoding="utf-8"
        )
        statements = [
            block.strip()
            for block in re.findall(r"```sql\n(.*?)\n\s*```", doc, re.DOTALL)
            if "CREATE TABLE" in block
        ]
        self.assertEqual(len(statements), 12)
        removed = {
            "wallets": {"archived", "emoji_icon_name"},
            "categories": {"archived"},
            "associated_titles": {"archived"},
            "scanner_templates": {"default_title"},
        }
        for version, conn in [(48, self.v48), (46, self.v46)]:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], version)
            counts = self.expected[f"table_counts_v{version}"]
            actual = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
                )
            }
            self.assertEqual(actual, set(counts))
            reference = sqlite3.connect(":memory:")
            self.addCleanup(reference.close)
            for statement in statements:
                table = statement.split('"')[1]
                if table not in actual:
                    continue
                reference.execute(statement)
                columns = [
                    r[1] for r in reference.execute(f'PRAGMA table_info("{table}")')
                ]
                if version == 46:
                    for col in removed.get(table, set()):
                        statement = re.sub(
                            r'^\s*"' + col + r'"[^\n]*\n',
                            "",
                            statement,
                            flags=re.MULTILINE,
                        )
                    statement = re.sub(r",(\s*\);)", r"\1", statement)
                    reference.execute(f'DROP TABLE "{table}"')
                    reference.execute(statement)
                    columns = [c for c in columns if c not in removed.get(table, set())]
                table_info = [
                    tuple(r) for r in conn.execute(f'PRAGMA table_info("{table}")')
                ]
                self.assertEqual(
                    table_info,
                    reference.execute(f'PRAGMA table_info("{table}")').fetchall(),
                )

                def normalize(sql: str) -> str:
                    return re.sub(r"\s+", "", sql).rstrip(";")

                actual_sql = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name=?", (table,)
                ).fetchone()[0]
                reference_sql = reference.execute(
                    "SELECT sql FROM sqlite_master WHERE name=?", (table,)
                ).fetchone()[0]
                self.assertEqual(normalize(actual_sql), normalize(reference_sql))
                self.assertEqual(
                    conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],
                    counts[table],
                )
                print(
                    f"OK v{version} {table} ({counts[table]} filas): {','.join(columns)}"
                )
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_wallet_balances(self) -> None:
        for conn in [self.v48, self.v46]:
            rows = conn.execute("""
                SELECT w.wallet_pk, w.name, w.currency,
                       COALESCE(SUM(CASE WHEN t.paid=1 THEN t.amount ELSE 0 END),0) AS balance
                FROM wallets w LEFT JOIN transactions t ON t.wallet_fk=w.wallet_pk
                GROUP BY w.wallet_pk,w.name,w.currency
            """).fetchall()
            found = {r["wallet_pk"]: r for r in rows}
            for wallet in self.expected["wallets"]:
                actual = found[wallet["wallet_pk"]]
                self.assertEqual(actual["name"], wallet["name"])
                self.assertEqual(actual["currency"], wallet["currency"])
                self.assertEqual(money(actual["balance"]), money(wallet["balance"]))
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM transactions WHERE (amount>0) != income"
                ).fetchone()[0],
                0,
            )

    def test_loan_cases(self) -> None:
        for conn in [self.v48, self.v46]:
            for case, expected in self.expected["loan_cases"].items():
                obj = conn.execute(
                    "SELECT * FROM objectives WHERE objective_pk=?",
                    (expected["objective_pk"],),
                ).fetchone()
                self.assertEqual(obj["type"], 1)
                self.assertEqual(obj["income"], int(expected["direction"] == "lent"))
                self.assertEqual(money(obj["amount"]), Decimal("0.00"))
                rows = conn.execute(
                    """
                    SELECT t.*,w.currency FROM transactions t JOIN wallets w ON w.wallet_pk=t.wallet_fk
                    WHERE objective_loan_fk=? ORDER BY t.date_created,t.transaction_pk
                """,
                    (obj["objective_pk"],),
                ).fetchall()
                disbursements = [r for r in rows if r["income"] != obj["income"]]
                payments = [r for r in rows if r["income"] == obj["income"]]
                self.assertEqual(len(disbursements), 1)
                for movement in rows:
                    self.assertEqual(
                        movement["income"], int(money(movement["amount"]) > 0)
                    )
                principal = abs(money(disbursements[0]["amount"]))
                payment_nominal = sum(
                    (abs(money(r["amount"])) for r in payments), Decimal("0.00")
                )
                cashew = expected["cashew"]
                self.assertEqual(principal, money(cashew["principal_nominal"]))
                self.assertEqual(payment_nominal, money(cashew["payments_nominal"]))
                self.assertEqual(
                    principal - payment_nominal, money(cashew["nominal_outstanding"])
                )
                self.assertEqual(
                    "settled" if payment_nominal >= principal else "open",
                    cashew["nominal_status"],
                )
                mono = expected["monetae"]
                self.assertEqual(principal, money(mono["principal"]))
                if case == "A":
                    orphan = conn.execute("""
                        SELECT t.* FROM transactions t JOIN categories c ON c.category_pk=t.category_fk
                        WHERE c.name='Intereses' AND t.objective_loan_fk IS NULL
                    """).fetchall()
                    self.assertEqual(len(orphan), 1)
                    interest = abs(money(orphan[0]["amount"]))
                    self.assertEqual(interest, principal * Decimal("0.05"))
                    self.assertEqual(interest, money(mono["interest"]))
                else:
                    interest = Decimal("0.00")
                balance = principal + interest
                self.assertEqual(len(payments), len(mono["payments_in_loan_currency"]))
                for i, payment in enumerate(payments):
                    applied = abs(money(payment["amount"]))
                    if payment["currency"] != expected["currency"]:
                        self.assertEqual(case, "C")
                        self.assertEqual(payment["currency"], "PEN")
                        self.assertEqual(
                            Decimal(mono["fx_rate_applied"]), Decimal("3.800000")
                        )
                        applied = money(applied / Decimal(mono["fx_rate_applied"]))
                    self.assertEqual(
                        applied, money(mono["payments_in_loan_currency"][i])
                    )
                    balance -= applied
                    self.assertEqual(balance, money(mono["balances_after_payments"][i]))
                self.assertEqual(balance, money(mono["outstanding_balance"]))
                self.assertEqual("settled" if balance == 0 else "open", mono["status"])
                if case in {"A", "B"}:
                    self.assertEqual(len({r["wallet_fk"] for r in payments}), 2)
                if case == "D":
                    self.assertTrue(mono["warning_required"])
                    self.assertTrue(mono["import_all_cash_transactions"])
                    self.assertEqual(
                        mono["excess_resolution_selected_by"],
                        "user_during_manual_review",
                    )
                    self.assertEqual(-balance, money(mono["overpayment"]))
                    income = mono["after_confirmed_excess_as_income"]
                    adjustment = mono["after_confirmed_capital_adjustment"]
                    self.assertEqual(income["excess_handling"], "income_expense")
                    self.assertEqual(adjustment["excess_handling"], "adjustment")
                    self.assertEqual(
                        principal - money(income["applied_payment"]),
                        money(income["outstanding_balance"]),
                    )
                    self.assertEqual(
                        principal + money(adjustment["adjustment"]) - payment_nominal,
                        money(adjustment["outstanding_balance"]),
                    )

    def test_special_transactions_and_relationships(self) -> None:
        for conn in [self.v48, self.v46]:
            for loan in self.expected["one_time_loans"]:
                row = conn.execute(
                    "SELECT * FROM transactions WHERE transaction_pk=?",
                    (loan["transaction_pk"],),
                ).fetchone()
                for key in ["type", "paid"]:
                    self.assertEqual(row[key], loan[key])
                self.assertEqual(money(row["amount"]), money(loan["amount"]))
                self.assertIsNone(row["objective_loan_fk"])
            self.assertEqual(
                [
                    tuple(r)
                    for r in conn.execute(
                        "SELECT type,reoccurrence,period_length FROM transactions WHERE type IN (1,2) ORDER BY type"
                    )
                ],
                [(1, 3, 1), (2, 3, 1)],
            )
            pairs = conn.execute("""
                SELECT a.amount AS a_amount,b.amount AS b_amount,a.wallet_fk AS a_wallet,b.wallet_fk AS b_wallet,
                       a.transaction_pk,b.paired_transaction_fk
                FROM transactions a JOIN transactions b ON a.paired_transaction_fk=b.transaction_pk
            """).fetchall()
            self.assertEqual(len(pairs), 2)
            for pair in pairs:
                self.assertEqual(pair["transaction_pk"], pair["paired_transaction_fk"])
                self.assertEqual(money(pair["a_amount"]) + money(pair["b_amount"]), 0)
                self.assertNotEqual(pair["a_wallet"], pair["b_wallet"])
            budget = conn.execute(
                "SELECT b.*,l.amount AS category_limit FROM budgets b JOIN category_budget_limits l ON l.budget_fk=b.budget_pk"
            ).fetchone()
            self.assertEqual((budget["reoccurrence"], budget["period_length"]), (3, 1))
            self.assertEqual(money(budget["amount"]), Decimal("2000.00"))
            self.assertEqual(money(budget["category_limit"]), Decimal("800.00"))
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM categories child JOIN categories parent ON child.main_category_pk=parent.category_pk"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM delete_logs").fetchone()[0], 1
            )
        self.assertEqual(
            self.v48.execute(
                "SELECT COUNT(*) FROM wallets WHERE archived=1"
            ).fetchone()[0],
            1,
        )

    def test_tags(self) -> None:
        actual_tags = [
            dict(r) for r in self.v48.execute('SELECT * FROM tags ORDER BY "order"')
        ]
        self.assertEqual(actual_tags, self.expected["tags"])
        actual_links = sorted(
            (r[0], r[1])
            for r in self.v48.execute(
                "SELECT transaction_pk,tag_pk FROM transaction_to_tag_links"
            )
        )
        self.assertEqual(
            actual_links,
            sorted(
                (r["transaction_pk"], r["tag_pk"]) for r in self.expected["tag_links"]
            ),
        )
        self.assertEqual(
            self.v48.execute("SELECT COUNT(*) FROM tags WHERE archived=1").fetchone()[
                0
            ],
            1,
        )
        self.assertEqual(
            self.v48.execute(
                "SELECT COUNT(*) FROM transaction_to_tag_links WHERE transaction_pk=?",
                (self.expected["row_map"]["G_repetitive"],),
            ).fetchone()[0],
            2,
        )
        self.assertEqual(
            self.v48.execute(
                "SELECT COUNT(*) FROM transaction_to_tag_links WHERE transaction_pk=?",
                (self.expected["untagged_transaction_pk"],),
            ).fetchone()[0],
            0,
        )

    def test_csv_exact_projection(self) -> None:
        with (TARGET / "synthetic_v48.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, HEADER)
            csv_rows = list(reader)
        self.assertEqual(len(HEADER), 17)
        self.assertEqual(len(csv_rows), self.expected["csv"]["paid_rows"])
        sql_rows = self.v48.execute("""
            SELECT t.*,w.name AS account,w.currency,c.name AS category_name,
                   c.colour,c.icon_name,c.emoji_icon_name,sub.name AS subcategory_name,
                   o.name AS objective_name,strftime('%Y-%m-%d %H:%M:%S.000',t.date_created,'unixepoch') AS csv_date
            FROM transactions t JOIN wallets w ON w.wallet_pk=t.wallet_fk
            JOIN categories c ON c.category_pk=t.category_fk
            LEFT JOIN categories sub ON sub.category_pk=t.sub_category_fk
            LEFT JOIN objectives o ON o.objective_pk=t.objective_loan_fk
            WHERE paid=1 ORDER BY t.rowid
        """).fetchall()
        self.assertEqual(len(csv_rows), len(sql_rows))
        type_names = {
            0: "upcoming",
            1: "subscription",
            2: "repetitive",
            3: "credit",
            4: "debt",
        }
        for actual, sql in zip(csv_rows, sql_rows):
            self.assertEqual(set(actual), set(HEADER))
            for csv_key, sql_key in [
                ("account", "account"),
                ("currency", "currency"),
                ("title", "name"),
                ("note", "note"),
                ("category name", "category_name"),
                ("subcategory name", "subcategory_name"),
                ("color", "colour"),
                ("icon", "icon_name"),
                ("emoji", "emoji_icon_name"),
                ("objective", "objective_name"),
                ("date", "csv_date"),
            ]:
                self.assertEqual(actual[csv_key], sql[sql_key] or "")
            self.assertEqual(money(actual["amount"]), money(sql["amount"]))
            self.assertEqual(actual["income"], "true" if sql["income"] else "false")
            self.assertEqual(
                actual["type"],
                "null"
                if sql["type"] is None
                else "TransactionSpecialType." + type_names[sql["type"]],
            )
            budget = self.v48.execute(
                """
                SELECT b.name FROM budgets b WHERE b.wallet_fk=? AND ? BETWEEN b.start_date AND b.end_date
                AND EXISTS (SELECT 1 FROM category_budget_limits l WHERE l.budget_fk=b.budget_pk AND l.category_fk=?)
            """,
                (sql["wallet_fk"], sql["date_created"], sql["category_fk"]),
            ).fetchone()
            self.assertEqual(actual["budget"], budget[0] if budget else "")
            self.assertEqual(actual["amount unpaid"], "")
            self.assertEqual(actual["extra"], "")
        excluded = self.v48.execute(
            "SELECT transaction_pk,name FROM transactions WHERE paid=0"
        ).fetchall()
        self.assertEqual(len(excluded), self.expected["csv"]["excluded_rows"])
        self.assertEqual(
            {r[0] for r in excluded},
            set(self.expected["csv"]["excluded_transaction_pks"]),
        )
        self.assertTrue(
            {r[1] for r in excluded}.isdisjoint({r["title"] for r in csv_rows})
        )

    def test_version_equivalence_and_dates(self) -> None:
        for table in self.expected["table_counts_v46"]:
            cols = [r[1] for r in self.v46.execute(f'PRAGMA table_info("{table}")')]
            projection = ",".join('"' + col + '"' for col in cols)
            sql = f'SELECT {projection} FROM "{table}" ORDER BY rowid'
            self.assertEqual(
                [tuple(r) for r in self.v46.execute(sql)],
                [tuple(r) for r in self.v48.execute(sql)],
            )
        for conn in [self.v48, self.v46]:
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
            ):
                table = row[0]
                cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
                for col in cols:
                    if col.startswith("date_") or col in {
                        "original_date_due",
                        "end_date",
                        "start_date",
                    }:
                        invalid = conn.execute(
                            f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NOT NULL AND (typeof("{col}") != \'integer\' OR "{col}" NOT BETWEEN 1767268800 AND 1800000000 OR "{col}" % 86400 != 43200)'
                        ).fetchone()[0]
                        self.assertEqual(
                            invalid,
                            0,
                            f"{table}.{col}: fecha fuera de segundos UTC a mediodía",
                        )
        namespace = uuid.UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")
        self.assertEqual(self.expected["namespace"], str(namespace))
        for label, pk in self.expected["row_map"].items():
            self.assertEqual(pk, str(uuid.uuid5(namespace, label)))
            row = self.v48.execute(
                "SELECT name,typeof(amount) FROM transactions WHERE transaction_pk=?",
                (pk,),
            ).fetchone()
            self.assertEqual(tuple(row), ("Ejemplo " + label, "real"))
        self.assertTrue(self.expected["synthetic_only"])
        self.assertEqual(
            {r["case"] for r in self.expected["ambiguous_cases"]},
            {"A", "C", "D", "F_settled"},
        )


class ReportResult(unittest.TextTestResult):
    def __init__(self, stream: Any, descriptions: bool, verbosity: int) -> None:
        # unittest passes a private stream wrapper at this framework boundary.
        super().__init__(stream, descriptions, verbosity)

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.stream.writeln("OK " + test.id().split(".")[-1])

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:
        # unittest's exception tuple is an untyped external framework boundary.
        super().addFailure(test, err)
        self.stream.writeln("FAIL " + test.id().split(".")[-1])

    def addError(self, test: unittest.TestCase, err: Any) -> None:
        # unittest's exception tuple is an untyped external framework boundary.
        super().addError(test, err)
        self.stream.writeln("FAIL " + test.id().split(".")[-1])


if __name__ == "__main__":
    result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=0, resultclass=ReportResult
    ).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixtureTests))
    sys.exit(0 if result.wasSuccessful() else 1)
