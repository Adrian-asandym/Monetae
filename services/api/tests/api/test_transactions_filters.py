from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.conftest import (
    create_account,
    create_category,
    create_tag,
    create_transaction,
    csrf_headers,
    login,
)


def ids(client: TestClient, **filters: object) -> set[str]:
    response = client.get("/api/v1/transactions", params=filters)
    assert response.status_code == 200, response.text
    return {row["id"] for row in response.json()["items"]}


def test_date_interval_inclusive_start_exclusive_end_with_offsets(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    first = create_transaction(client, account, occurred_at="2026-10-07T00:00:00-05:00")
    middle = create_transaction(client, account, occurred_at="2026-10-07T12:00:00-05:00")
    create_transaction(client, account, occurred_at="2026-10-08T00:00:00-05:00")
    assert ids(client, date_from="2026-10-07T05:00:00Z", date_to="2026-10-08T05:00:00Z") == {
        first,
        middle,
    }


@pytest.mark.parametrize("parameter", ["date_from", "date_to"])
def test_filter_timestamp_requires_timezone(client: TestClient, parameter: str) -> None:
    login(client)
    assert (
        client.get("/api/v1/transactions", params={parameter: "2026-10-07T12:00:00"}).status_code
        == 422
    )


def test_account_category_currency_kind_status_filters(client: TestClient) -> None:
    login(client)
    first, second = create_account(client), create_account(client, "Dollar")
    client.patch(
        f"/api/v1/accounts/{second}", json={"currency": "USD"}, headers=csrf_headers(client)
    )
    category = create_category(client)
    a = create_transaction(client, first, category_id=category)
    b = create_transaction(
        client,
        second,
        currency="USD",
        kind="income",
        amount="20.00",
        status="scheduled",
        fx_rate_to_base="3.800000",
    )
    for filters in (
        {"account_id": first},
        {"category_id": category},
        {"currency": "PEN"},
        {"kind": "expense"},
        {"status": "posted"},
    ):
        assert ids(client, **filters) == {a}
    assert ids(client, account_id=second, currency="USD", kind="income", status="scheduled") == {b}
    assert ids(client, account_id=first, currency="USD") == set()
    assert ids(client, loan_id=str(uuid4())) == set()
    assert ids(client, person_id=str(uuid4())) == set()


def test_repeated_tag_filters_are_or_and_do_not_duplicate_transactions(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    a, b = create_tag(client, "A"), create_tag(client, "B")
    first = create_transaction(client, account, tag_ids=[a])
    second = create_transaction(client, account, tag_ids=[b])
    both = create_transaction(client, account, tag_ids=[a, b])
    create_transaction(client, account)
    response = client.get("/api/v1/transactions", params=[("tag_ids", a), ("tag_ids", b)])
    assert response.status_code == 200
    assert {row["id"] for row in response.json()["items"]} == {first, second, both}
    assert len(response.json()["items"]) == 3


def test_search_substring_spanish_stemming_and_literal_wildcards(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    a = create_transaction(client, account, title="Compra 50%_off", note="Comidas familiares")
    b = create_transaction(client, account, title="Otra compra", note="CAMISETA")
    assert ids(client, q="COMID") == {a}
    assert ids(client, q="comida familiares") == {a}  # Ambas raíces en tsvector español.
    assert ids(client, q="miset") == {b}
    assert ids(client, q="%_") == {a}
    assert ids(client, q="\\") == set()


def test_keyset_pages_equal_timestamps_and_cursor_filter_binding(client: TestClient) -> None:
    login(client)
    account = create_account(client)
    expected = {create_transaction(client, account) for _ in range(7)}
    collected: list[str] = []
    cursor = None
    while True:
        params = {"limit": "2"}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/api/v1/transactions", params=params)
        assert response.status_code == 200, response.text
        page = response.json()
        collected.extend(row["id"] for row in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert set(collected) == expected and collected == sorted(expected, reverse=True)
    first_cursor = client.get("/api/v1/transactions?limit=2").json()["next_cursor"]
    assert (
        client.get(
            "/api/v1/transactions", params={"cursor": first_cursor, "q": "different"}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/v1/transactions", params={"cursor": first_cursor + "tampered"}).status_code
        == 400
    )
    catalog_cursor = client.get("/api/v1/accounts?limit=1").json()["next_cursor"]
    assert catalog_cursor is None


@pytest.mark.parametrize(
    "filters",
    [
        {"limit": "0"},
        {"limit": "201"},
        {"currency": "pen"},
        {"kind": "invalid"},
        {"status": "invalid"},
        {"tag_ids": "not-a-uuid"},
    ],
)
def test_filter_validation(client: TestClient, filters: dict[str, str]) -> None:
    login(client)
    assert client.get("/api/v1/transactions", params=filters).status_code == 422


def test_loan_and_person_filters_link_each_cash_transaction(client: TestClient) -> None:
    from .conftest import add_movement, create_loan, create_person, payment_payload

    login(client)
    account = create_account(client)
    person = create_person(client)
    other = create_person(client, "Other")
    loan = create_loan(client, person, account)
    second = create_loan(client, other, account)
    add_movement(client, loan, payment_payload(account, "200.00"))
    linked = client.get("/api/v1/transactions", params={"loan_id": loan}).json()["items"]
    assert len(linked) == 2 and all(row["loan_id"] == loan for row in linked)
    assert ids(client, person_id=person) == {row["id"] for row in linked}
    assert not ids(client, loan_id=loan, person_id=other)
    assert len(ids(client, loan_id=second)) == 1
