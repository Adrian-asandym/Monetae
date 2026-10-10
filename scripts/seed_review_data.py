"""Seed SYNTHETIC October-2026 data for visual review of Home (never real data).

Usage (the user must already exist, created with `python -m monetae.cli create-user`):
    uv run --project services/api python -I scripts/seed_review_data.py \
        --base http://localhost:8080 --email review@example.test --password-file <file>

Talks only to the HTTP API (same origin, CSRF, Idempotency-Key): it doubles as a smoke test.
"""

import argparse
import sys
import uuid
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password-file", required=True, type=Path)
    parser.add_argument("--display-name", default=None, help="requires contract 0.6.0 (T-603)")
    args = parser.parse_args()
    base: str = args.base.rstrip("/")
    password = args.password_file.read_text().strip()

    with httpx.Client(base_url=base, timeout=10) as client:

        def ok(response: httpx.Response, code: int) -> dict:
            if response.status_code != code:
                request = response.request
                sys.exit(
                    f"{request.method} {request.url} -> {response.status_code}: {response.text[:300]}"
                )
            return response.json() if response.content else {}

        ok(client.get("/api/v1/health"), 200)
        headers = {"Origin": base, "X-CSRF-Token": client.cookies["monetae_csrf"]}
        login = {"method": "password", "email": args.email, "password": password}
        ok(client.post("/api/v1/auth/login", json=login, headers=headers), 200)
        headers = {"Origin": base, "X-CSRF-Token": client.cookies["monetae_csrf"]}

        def post(path: str, body: dict) -> dict:
            extra = {"Idempotency-Key": str(uuid.uuid4())} if path == "/api/v1/transactions" else {}
            return ok(client.post(path, json=body, headers={**headers, **extra}), 201)

        def account(name: str, kind: str, currency: str, initial: str, color: str) -> dict:
            body = {
                "name": name,
                "type": kind,
                "currency": currency,
                "initial_balance": initial,
                "color": color,
            }
            return post("/api/v1/accounts", body)

        def category(name: str, kind: str, icon: str, color: str) -> dict:
            return post(
                "/api/v1/categories", {"name": name, "kind": kind, "icon": icon, "color": color}
            )

        cash = account("Efectivo", "cash", "PEN", "800.00", "#4CAF50")
        bank = account("Banco", "bank", "PEN", "2500.00", "#2196F3")
        usd = account("Dólares", "bank", "USD", "300.00", "#FF9800")
        food = category("Alimentación", "expense", "restaurant", "#F4A261")
        transport = category("Transporte", "expense", "transport", "#2A9D8F")
        home = category("Hogar", "expense", "home", "#9C6ADE")
        salary = category("Sueldo", "income", "work", "#43AA8B")

        def tx(
            acc: dict,
            cat: dict | None,
            kind: str,
            amount: str,
            day: int,
            hour: int,
            title: str,
            currency: str = "PEN",
            fx: str = "1.000000",
            note: str | None = None,
        ) -> dict:
            return post(
                "/api/v1/transactions",
                {
                    "account_id": acc["id"],
                    "category_id": cat["id"] if cat else None,
                    "kind": kind,
                    "amount": amount,
                    "currency": currency,
                    "occurred_at": f"2026-10-{day:02d}T{hour:02d}:00:00Z",
                    "status": "posted",
                    "title": title,
                    "note": note,
                    "fx_rate_to_base": fx,
                    "fx_rate_source": "manual",
                },
            )

        pay = tx(bank, salary, "income", "3200.00", 1, 14, "Sueldo octubre")
        for day, hour, amount, title in [
            (2, 15, "-145.30", "Mercado"),
            (4, 13, "-38.90", "Panadería"),
            (6, 22, "-212.75", "Supermercado"),
            (9, 18, "-56.40", "Almuerzo"),
            (10, 14, "-12.50", "Café"),
        ]:
            tx(cash, food, "expense", amount, day, hour, title)
        tx(cash, transport, "expense", "-24.00", 3, 23, "Taxi", note="Regreso a casa")
        tx(bank, transport, "expense", "-80.00", 7, 12, "Recarga tarjeta metro")
        rent = tx(bank, home, "expense", "-950.00", 5, 16, "Alquiler")
        tx(
            usd,
            home,
            "expense",
            "-25.00",
            8,
            20,
            "Suscripción en dólares",
            currency="USD",
            fx="3.800000",
        )

        def budget(name: str, amount: str, cat: dict, color: str) -> dict:
            return post(
                "/api/v1/budgets",
                {
                    "name": name,
                    "period": "monthly",
                    "start_on": "2026-10-01",
                    "end_on": None,
                    "amount": amount,
                    "currency": "PEN",
                    "scope": "all",
                    "category_limits": [{"category_id": cat["id"], "limit_amount": amount}],
                    "color": color,
                },
            )

        budget("Comida del mes", "600.00", food, "#E76F51")
        budget("Transporte", "90.00", transport, "#2A9D8F")

        def goal(
            name: str,
            kind: str,
            target: str,
            due: str | None,
            color: str,
            icon: str,
            linked: list[dict],
        ) -> None:
            created = post(
                "/api/v1/goals",
                {
                    "name": name,
                    "kind": kind,
                    "target_amount": target,
                    "currency": "PEN",
                    "due_on": due,
                    "color": color,
                    "icon": icon,
                },
            )
            ids = {"transaction_ids": [item["id"] for item in linked]}
            ok(
                client.put(
                    f"/api/v1/goals/{created['id']}/transactions", json=ids, headers=headers
                ),
                200,
            )

        goal("Fondo de emergencia", "save", "5000.00", "2027-03-31", "#264653", "wallet", [pay])
        goal("Gasto en hogar", "spend", "1200.00", None, "#9C6ADE", "home", [rent])

        me = ok(client.get("/api/v1/users/me"), 200)
        update: dict = {"preferences": {**me["preferences"], "default_account_id": cash["id"]}}
        if args.display_name:
            update["display_name"] = args.display_name
        ok(client.patch("/api/v1/users/me", json=update, headers=headers), 200)
    print("seeded synthetic review data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
