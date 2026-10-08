from fastapi.testclient import TestClient

from .conftest import (
    add_movement,
    create_account,
    create_loan,
    create_person,
    csrf_headers,
    login,
    payment_payload,
)


def test_summary_by_person_currency_counts_and_soft_deletion(client: TestClient) -> None:
    login(client)
    pen = create_account(client)
    usd = create_account(client, name="USD", currency="USD")
    person = create_person(client)
    other = create_person(client, "Other")
    first = create_loan(client, person, pen, principal="50.00")
    create_loan(client, person, pen, principal="100.00", direction="borrowed")
    create_loan(
        client,
        person,
        usd,
        principal="10.00",
        currency="USD",
        disbursement={
            **payment_payload(
                usd,
                "10.00",
                account_currency="USD",
                fx_rate_to_base="3.800000",
                occurred_at="2026-10-01T00:00:00Z",
            ),
            "kind": "disbursement",
        },
    )
    create_loan(client, other, pen, principal="20.00")
    add_movement(client, first, payment_payload(pen, "50.00"))
    page = client.get("/api/v1/loans/summary", params={"person_id": person}).json()
    assert len(page["items"]) == 2
    grouped = {row["currency"]: row for row in page["items"]}
    assert grouped["PEN"] == {
        "person_id": person,
        "currency": "PEN",
        "lent_outstanding": "0.00",
        "borrowed_outstanding": "100.00",
        "open_count": 1,
        "settled_count": 1,
    }
    assert grouped["USD"]["lent_outstanding"] == "10.00"
    assert client.get("/api/v1/loans/summary", params={"currency": "PEN"}).json()["items"] == [
        row
        for row in client.get("/api/v1/loans/summary").json()["items"]
        if row["currency"] == "PEN"
    ]
    assert client.delete(f"/api/v1/loans/{first}", headers=csrf_headers(client)).status_code == 200
    grouped = {
        row["currency"]: row
        for row in client.get("/api/v1/loans/summary", params={"person_id": person}).json()["items"]
    }
    assert grouped["PEN"]["settled_count"] == 0


def test_all_pagination_cursors_are_stable_and_bound_to_filters(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    person = create_person(client)
    loans = {create_loan(client, person, account) for _ in range(5)}
    create_loan(client, create_person(client, "Other"), account)
    collected: list[str] = []
    cursor = None
    while True:
        query: dict[str, str] = {"limit": "2", "person_id": person}
        if cursor:
            query["cursor"] = cursor
        response = client.get("/api/v1/loans", params=query)
        assert response.status_code == 200, response.text
        page = response.json()
        collected.extend(row["id"] for row in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert set(collected) == loans and collected == sorted(loans)
    first_cursor = client.get("/api/v1/loans", params={"limit": 1}).json()["next_cursor"]
    assert (
        client.get("/api/v1/loans", params={"cursor": first_cursor, "status": "open"}).status_code
        == 400
    )
    summary_cursor = client.get("/api/v1/loans/summary?limit=1").json()["next_cursor"]
    assert (
        client.get(
            "/api/v1/loans/summary", params={"cursor": summary_cursor, "person_id": person}
        ).status_code
        == 400
    )
    loan = next(iter(loans))
    path = f"/api/v1/loans/{loan}/movements"
    for _ in range(5):
        add_movement(
            client,
            loan,
            {
                "kind": "interest",
                "amount_in_loan_currency": "1.00",
                "occurred_at": "2026-10-02T00:00:00Z",
            },
        )
    seen: list[str] = []
    cursor = None
    while True:
        query = {"limit": "2"}
        if cursor:
            query["cursor"] = cursor
        page = client.get(path, params=query).json()
        seen.extend(row["id"] for row in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == 6
    cursor = client.get(path, params={"limit": 1}).json()["next_cursor"]
    assert client.get(path, params={"cursor": cursor, "include_deleted": "true"}).status_code == 400
    assert client.get(path, params={"cursor": cursor + "tampered"}).status_code == 400
