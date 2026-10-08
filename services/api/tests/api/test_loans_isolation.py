from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import (
    create_account,
    create_loan,
    create_person,
    csrf_headers,
    loan_payload,
    login,
    payment_payload,
)


def test_each_loan_operation_is_user_scoped(client: TestClient, application: FastAPI) -> None:
    login(client)
    account = create_account(client)
    person = create_person(client)
    loan = create_loan(client, person, account)
    movement = client.get(f"/api/v1/loans/{loan}/movements").json()["items"][0]["id"]
    base = f"/api/v1/loans/{loan}"
    with TestClient(application, base_url="https://testserver") as second:
        login(second, "second@example.test")
        own_account = create_account(second)
        own_person = create_person(second)
        for method, path, payload in [
            ("GET", base, None),
            ("GET", base + "?include_deleted=true", None),
            ("PATCH", base, {"note": "foreign"}),
            ("DELETE", base, None),
            ("POST", base + "/restore", None),
            ("GET", base + "/balance", None),
            ("GET", base + "/movements", None),
            ("POST", base + "/movements", payment_payload(own_account, "10.00")),
            (
                "PUT",
                base + f"/movements/{movement}",
                {**payment_payload(own_account, "200.00"), "kind": "disbursement"},
            ),
            ("DELETE", base + f"/movements/{movement}", None),
            ("POST", base + f"/movements/{movement}/restore", None),
            ("POST", base + "/payment-proposal", {"amount_in_loan_currency": "10.00"}),
            ("POST", base + "/interest-proposal", {"percentage": "5.000000"}),
        ]:
            result = second.request(method, path, json=payload, headers=csrf_headers(second))
            assert result.status_code == 404, (method, path, result.text)
        assert not second.get("/api/v1/loans").json()["items"]
        assert not second.get("/api/v1/loans/summary").json()["items"]
        for payload in (loan_payload(person, own_account), loan_payload(own_person, account)):
            assert (
                second.post("/api/v1/loans", json=payload, headers=csrf_headers(second)).status_code
                == 404
            )
        own_loan = create_loan(second, own_person, own_account)
        assert (
            second.patch(
                f"/api/v1/loans/{own_loan}",
                json={"person_id": person},
                headers=csrf_headers(second),
            ).status_code
            == 404
        )
        assert (
            second.post(
                f"/api/v1/loans/{own_loan}/movements",
                json=payment_payload(account, "10.00"),
                headers=csrf_headers(second),
            ).status_code
            == 404
        )
        assert (
            second.delete(
                f"/api/v1/loans/{own_loan}/movements/{movement}", headers=csrf_headers(second)
            ).status_code
            == 404
        )
        assert not second.get("/api/v1/loans", params={"person_id": person}).json()["items"]
        assert not second.get("/api/v1/loans/summary", params={"person_id": person}).json()["items"]
    assert client.get(base).json()["outstanding"] == "200.00"
