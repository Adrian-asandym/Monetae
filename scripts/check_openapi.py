#!/usr/bin/env python3
"""Valida invariantes de Monetae y ejemplos sintéticos, sin dependencias externas."""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Union, cast

# Union es necesario: este alias se evalúa en Python 3.9 (no admite X | Y).
Json = Union[None, bool, int, float, str, list["Json"], dict[str, "Json"]]  # noqa: UP007
Object = dict[str, Json]
ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "api" / "openapi.json"
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
PUBLIC = {
    ("/api/v1/auth/login", "post"),
    ("/api/v1/auth/google/callback", "get"),
    ("/api/v1/health", "get"),
}
CENT = Decimal("0.01")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def mapping(value: Json) -> Object:
    require(isinstance(value, dict), "Se esperaba objeto JSON")
    return cast(Object, value)


def sequence(value: Json) -> list[Json]:
    require(isinstance(value, list), "Se esperaba lista JSON")
    return cast(list[Json], value)


def text(value: Json) -> str:
    require(isinstance(value, str), "Se esperaba cadena JSON")
    return cast(str, value)


def walk(value: Json, path: str = "") -> Iterator[tuple[str, Object]]:
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from walk(child, path + "/" + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + "/" + str(index))


def resolve(document: Object, value: Json) -> Object:
    node = mapping(value)
    visited: set[str] = set()
    while "$ref" in node:
        pointer = text(node["$ref"])
        require(pointer.startswith("#/"), "Referencia externa no permitida: " + pointer)
        require(pointer not in visited, "Ciclo de referencias: " + pointer)
        visited.add(pointer)
        target: Json = document
        for part in pointer[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(target, list):
                target = target[int(part)]
            else:
                target = mapping(target)[part]
        node = mapping(target)
    return node


def load_contract() -> Object:
    # Borde JSON no tipado de la biblioteca estándar: cast tras parsear, luego
    # mapping/sequence/text validan las formas antes de consumir cada valor.
    return mapping(cast(Json, json.loads(CONTRACT.read_text(encoding="utf-8"))))


def properties(document: Object, schema: Json) -> Object:
    return mapping(resolve(document, schema).get("properties", {}))


def validate_example(document: Object, schema: Json, value: Json) -> None:
    """Subconjunto de JSON Schema para ejemplos; no sustituye Redocly."""
    node = resolve(document, schema)
    for keyword in ("oneOf", "anyOf"):
        if keyword in node:
            matches = 0
            for branch in sequence(node[keyword]):
                try:
                    validate_example(document, branch, value)
                    matches += 1
                except ValueError:
                    pass
            require(
                matches == 1 if keyword == "oneOf" else matches > 0,
                "Ejemplo no satisface " + keyword,
            )
            return
    kind = node.get("type")
    if kind == "null":
        require(value is None, "Ejemplo debe ser null")
    elif kind == "string":
        item = text(value)
        if "pattern" in node:
            require(
                re.fullmatch(text(node["pattern"]), item) is not None,
                "Ejemplo decimal/patrón inválido: " + item,
            )
        if node.get("format") == "uuid":
            require(
                re.fullmatch(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", item)
                is not None,
                "UUID inválido",
            )
    elif kind == "integer":
        require(
            isinstance(value, int) and not isinstance(value, bool), "Entero inválido"
        )
    elif kind == "boolean":
        require(isinstance(value, bool), "Booleano inválido")
    elif kind == "array":
        for child in sequence(value):
            validate_example(document, node["items"], child)
    elif kind == "object":
        item_object = mapping(value)
        props = mapping(node.get("properties", {}))
        require(
            set(map(text, sequence(node.get("required", [])))) <= set(item_object),
            "Faltan campos requeridos en ejemplo",
        )
        if node.get("additionalProperties") is False:
            require(set(item_object) <= set(props), "Campos inesperados en ejemplo")
        for key, child in item_object.items():
            if key in props:
                validate_example(document, props[key], child)
    if "const" in node:
        require(value == node["const"], "Constante inválida en ejemplo")
    if "enum" in node:
        require(value in sequence(node["enum"]), "Enum inválido en ejemplo")


def check_request(document: Object, schema: Json, seen: set[str]) -> None:
    node = mapping(schema)
    pointer = node.get("$ref")
    if pointer is not None:
        key = text(pointer)
        if key in seen:
            return
        seen.add(key)
        check_request(document, resolve(document, node), seen)
        return
    props = mapping(node.get("properties", {}))
    require("user_id" not in props, "user_id en cuerpo de petición")
    for child in props.values():
        check_request(document, child, seen)
    for keyword in ("oneOf", "anyOf", "allOf"):
        for child in sequence(node.get(keyword, [])):
            check_request(document, child, seen)
    if "items" in node:
        check_request(document, node["items"], seen)


def decimal_field(value: Object, name: str) -> Decimal:
    amount = text(value[name])
    require(
        re.fullmatch(r"-?(0|[1-9][0-9]*)\.[0-9]{2}", amount) is not None,
        "Importe debe tener dos decimales: " + name,
    )
    return Decimal(amount)


def check_loans(document: Object) -> None:
    components = mapping(document["components"])
    examples = mapping(components["examples"])
    schemas = mapping(components["schemas"])
    scenarios = mapping(document["x-loan-scenarios"])
    require(set(scenarios) == set("ABCDE"), "Deben estar los ejemplos A–E")
    expected_steps = {
        "A": ["200.00", "210.00", "110.00", "0.00"],
        "B": ["500.00", "200.00", "0.00"],
        "C": ["100.00", "0.00"],
        "D": ["50.00"],
        "E": ["1000.00", "950.00", "830.00", "800.00", "0.00"],
    }
    cash = "00000000-0000-4000-8000-000000000010"
    bcp = "00000000-0000-4000-8000-000000000011"
    yape = "00000000-0000-4000-8000-000000000012"
    usd = "00000000-0000-4000-8000-000000000013"
    pen = "00000000-0000-4000-8000-000000000014"
    expected_accounts = {
        "A": {cash: Decimal("90.00"), bcp: Decimal("-100.00")},
        "B": {
            yape: Decimal("-500.00"),
            cash: Decimal("300.00"),
            bcp: Decimal("200.00"),
        },
        "C": {usd: Decimal("-100.00"), pen: Decimal("380.00")},
        "D": {usd: Decimal("-50.00")},
        "E": {cash: Decimal("0.00")},
    }
    expected_principals = dict(
        zip("ABCDE", ["200.00", "500.00", "100.00", "50.00", "1000.00"])
    )
    expected_kinds = {
        "A": ["disbursement", "interest", "payment", "payment"],
        "B": ["disbursement", "payment", "payment"],
        "C": ["disbursement", "payment"],
        "D": ["disbursement"],
        "E": ["disbursement"] + ["payment"] * 4,
    }
    proposal = mapping(mapping(examples["A_interest_proposal_response"])["value"])
    percentage = Decimal(text(proposal["percentage"]))
    require(percentage == Decimal("5.000000"), "Ejemplo A debe usar interés 5 %")
    require(
        (decimal_field(proposal, "outstanding") * percentage / 100).quantize(
            CENT, ROUND_HALF_UP
        )
        == decimal_field(proposal, "amount_in_loan_currency")
        == Decimal("10.00"),
        "Propuesta de interés A incorrecta",
    )
    for letter, raw in scenarios.items():
        scenario = mapping(raw)
        principal = decimal_field(scenario, "principal")
        require(
            str(principal) == expected_principals[letter], "Principal SPEC " + letter
        )
        balance = principal
        interest_pending = Decimal(0)
        paid_interest = Decimal(0)
        totals = {
            kind: Decimal(0)
            for kind in ("interest", "adjustment", "payment", "write_off")
        }
        accounts: dict[str, Decimal] = {}
        computed_steps: list[Json] = []
        kinds: list[str] = []
        for name in sequence(scenario["movement_examples"]):
            movement = mapping(mapping(examples[text(name)])["value"])
            validate_example(document, schemas["MovementCreate"], movement)
            kind = text(movement["kind"])
            kinds.append(kind)
            amount = decimal_field(movement, "amount_in_loan_currency")
            if kind == "disbursement":
                require(amount == principal, "Desembolso distinto al principal")
            else:
                totals[kind] += amount
                balance += amount if kind in ("interest", "adjustment") else -amount
            if kind == "interest":
                interest_pending += amount
            if kind == "payment":
                interest = decimal_field(movement, "interest_part")
                capital = decimal_field(movement, "principal_part")
                require(interest + capital == amount, "Reparto no suma pago")
                require(
                    interest == min(amount, interest_pending),
                    "Ejemplo no asigna interés primero",
                )
                interest_pending -= interest
                paid_interest += interest
            if kind in ("disbursement", "payment"):
                account_amount = decimal_field(movement, "account_amount")
                if movement["account_currency"] != scenario["currency"]:
                    rate = Decimal(text(movement["fx_rate_applied"]))
                    require(
                        (account_amount / rate).quantize(CENT, ROUND_HALF_UP) == amount,
                        "Conversión aplicada incorrecta",
                    )
                else:
                    require(
                        account_amount == amount, "Misma moneda con importes distintos"
                    )
                outgoing = (
                    kind == "disbursement" and scenario["direction"] == "lent"
                ) or (kind == "payment" and scenario["direction"] == "borrowed")
                account = text(movement["account_id"])
                accounts[account] = accounts.get(account, Decimal(0)) + (
                    -account_amount if outgoing else account_amount
                )
            require(balance >= 0, "Saldo negativo silencioso en ejemplo " + letter)
            computed_steps.append(format(balance, ".2f"))
        require(
            kinds == expected_kinds[letter], "Movimientos no reproducen SPEC " + letter
        )
        require(
            computed_steps == expected_steps[letter] == scenario["balances_after_each"],
            "Saldos intermedios incorrectos: " + letter,
        )
        require(accounts == expected_accounts[letter], "Cuentas incorrectas: " + letter)
        require(
            paid_interest == (Decimal("10.00") if letter == "A" else Decimal(0)),
            "Interés reconocido incorrecto: " + letter,
        )
        result = mapping(mapping(examples[text(scenario["balance_example"])])["value"])
        validate_example(document, schemas["LoanBalance"], result)
        require(
            result["currency"] == scenario["currency"], "Moneda de saldo incorrecta"
        )
        require(
            decimal_field(result, "principal") == principal,
            "Principal de respuesta incorrecto",
        )
        for kind, total in totals.items():
            require(
                decimal_field(result, kind + "_total") == total,
                "Total incorrecto: " + kind,
            )
        require(
            decimal_field(result, "outstanding") == balance, "Saldo final incorrecto"
        )
        require(
            result["status"] == ("settled" if balance == 0 else "open"),
            "Estado no derivado",
        )
        if letter == "D":
            rejected = mapping(
                mapping(examples[text(scenario["rejected_payment_example"])])["value"]
            )
            problem = mapping(
                mapping(examples[text(scenario["problem_example"])])["value"]
            )
            validate_example(document, schemas["MovementCreate"], rejected)
            validate_example(document, schemas["Problem"], problem)
            require(
                decimal_field(rejected, "account_amount") == Decimal("60.00"),
                "Pago D != 60",
            )
            excess = decimal_field(rejected, "amount_in_loan_currency") - balance
            require(
                excess == Decimal("10.00") == decimal_field(problem, "excess_amount"),
                "Exceso D",
            )
            require(
                decimal_field(problem, "outstanding") == balance, "Saldo D en Problem"
            )
            require(
                problem["status"] == 422 and problem["code"] == "loan_overpayment",
                "Exceso sin Problem de conflicto",
            )
            require(
                {text(mapping(item)["action"]) for item in sequence(problem["options"])}
                == {"adjustment", "income_expense"},
                "Faltan salidas RF-22",
            )


def check_architecture_v02(document: Object) -> None:
    """Comprueba contrato, efectos atómicos RF-22 y reglas resueltas en v0.2."""
    components = mapping(document["components"])
    schemas = mapping(components["schemas"])
    examples = mapping(components["examples"])
    paths = mapping(document["paths"])

    def example(name: Json) -> Object:
        return mapping(mapping(examples[text(name)])["value"])

    payment = resolve(document, schemas["PaymentRequest"])
    props = properties(document, payment)
    require(
        mapping(props["excess_handling"])["enum"] == ["adjustment", "income_expense"],
        "Falta excess_handling con ambas opciones",
    )
    require(
        "excess_handling" not in sequence(payment["required"]),
        "excess_handling debe ser opcional",
    )
    require(
        not {"interest_part", "principal_part"}
        & set(map(text, sequence(payment["required"]))),
        "Reparto de pago debe permitir cálculo por servidor",
    )
    require(
        payment.get("dependentRequired")
        == {"interest_part": ["principal_part"], "principal_part": ["interest_part"]},
        "Reparto opcional debe enviarse completo",
    )
    write_off = resolve(document, schemas["WriteOffRequest"])
    require(
        {"interest_part", "principal_part"}
        <= set(map(text, sequence(write_off["required"]))),
        "Condonación sin reparto obligatorio",
    )
    require(
        "account_id" not in properties(document, write_off), "Condonación mueve dinero"
    )
    require(
        "account_id" not in properties(document, schemas["AdjustmentRequest"]),
        "Ajuste mueve dinero",
    )
    side = properties(document, schemas["LoanMovement"])["side_effects"]
    require(mapping(side).get("readOnly") is True, "side_effects debe ser solo lectura")
    options = properties(document, schemas["OverpaymentOption"])
    require("applied_amount" in options, "Opciones RF-22 sin applied_amount")
    require(example("D_overpayment")["status"] == 422, "RF-22 debe devolver 422")
    for raw_option in sequence(example("D_overpayment")["options"]):
        option = mapping(raw_option)
        expected_applied = (
            Decimal("60.00") if option["action"] == "adjustment" else Decimal("50.00")
        )
        require(
            decimal_field(option, "applied_amount") == expected_applied,
            "Problem RF-22 informa applied_amount incorrecto",
        )

    operation = mapping(mapping(paths["/api/v1/loans/{id}/movements"])["post"])
    error = resolve(document, mapping(operation["responses"])["422"])
    error_examples = mapping(
        mapping(mapping(error["content"])["application/problem+json"])["examples"]
    )
    require(
        mapping(error_examples["D"]).get("$ref")
        == "#/components/examples/D_overpayment",
        "Ejemplo D debe enlazarse a 422",
    )
    require(
        "NUEVA" in text(operation["description"]), "Reintento RF-22 sin clave NUEVA"
    )
    parameters = mapping(components["parameters"])
    require(
        mapping(parameters["IdempotencyKey"]).get("x-retention-hours") == 24,
        "Retención idempotente debe ser 24 h",
    )

    overpayments = sequence(document["x-overpayment-scenarios"])
    modes: set[str] = set()
    foreign = False
    for raw in overpayments:
        scenario = mapping(raw)
        request = example(scenario["request_example"])
        response = example(scenario["response_example"])
        balance = example(scenario["balance_example"])
        validate_example(document, schemas["PaymentRequest"], request)
        validate_example(document, schemas["LoanMovement"], response)
        validate_example(document, schemas["LoanBalance"], balance)
        handling = text(request["excess_handling"])
        modes.add(handling)
        total = decimal_field(request, "amount_in_loan_currency")
        before = decimal_field(scenario, "outstanding_before")
        applied = total if handling == "adjustment" else before
        excess = total - before
        require(
            total == Decimal("60.00") and before == Decimal("50.00"),
            "Exceso no reproduce D",
        )
        require(
            decimal_field(response, "amount_in_loan_currency") == applied,
            "Pago aplicado RF-22",
        )
        require(
            decimal_field(response, "interest_part")
            + decimal_field(response, "principal_part")
            == applied,
            "Reparto de respuesta no suma pago aplicado",
        )
        require(
            decimal_field(response, "interest_part")
            == min(applied, decimal_field(scenario, "interest_pending_before")),
            "Respuesta RF-22 no asigna interés primero",
        )
        if "interest_part" in request:
            require(
                decimal_field(request, "interest_part")
                + decimal_field(request, "principal_part")
                == applied,
                "Reparto de petición no refiere al pago aplicado",
            )
        effects = sequence(response["side_effects"])
        require(len(effects) == 1, "RF-22 requiere un efecto adicional")
        effect = mapping(effects[0])
        require(
            response["account_id"] == request["account_id"]
            and response["account_currency"] == request["account_currency"],
            "Pago aplicado debe usar la misma cuenta y moneda físicas",
        )
        physical = decimal_field(request, "account_amount")
        cash_payment = decimal_field(response, "account_amount")
        rate = Decimal(1)
        if request["account_currency"] != balance["currency"]:
            foreign = True
            rate = Decimal(text(request["fx_rate_applied"]))
            require(
                (abs(physical) / rate).quantize(CENT, ROUND_HALF_UP) == total,
                "Conversión del importe físico RF-22",
            )
        if handling == "adjustment":
            adjustment = excess
            require(
                effect["kind"] == "adjustment" and effect["adjustment_id"] is not None,
                "Falta referencia al ajuste atómico",
            )
            require(
                effect["transaction_id"] is None and effect["account_id"] is None,
                "Ajuste no debe mover dinero",
            )
            require(
                effect["currency"] == balance["currency"], "Moneda del ajuste RF-22"
            )
            require(
                decimal_field(effect, "amount") == excess, "Importe del ajuste RF-22"
            )
            extra_cash = Decimal(0)
        else:
            adjustment = Decimal(0)
            require(
                effect["kind"] == "income" and effect["transaction_id"] is not None,
                "Lent debe crear ingreso adicional",
            )
            require(
                effect["adjustment_id"] is None
                and effect["account_id"] == request["account_id"],
                "Exceso en otra cuenta",
            )
            require(
                effect["currency"] == request["account_currency"], "Moneda del exceso"
            )
            extra_cash = decimal_field(effect, "amount")
            require(
                cash_payment == (applied * rate).quantize(CENT, ROUND_HALF_UP),
                "Pago de préstamo mal convertido",
            )
            require(
                extra_cash == physical - cash_payment,
                "Exceso debe ser RESTO del importe físico",
            )
        require(
            cash_payment + extra_cash == physical,
            "Pago más exceso pierde dinero/céntimos",
        )
        require(
            before + adjustment - applied
            == Decimal(0)
            == decimal_field(balance, "outstanding"),
            "Saldo RF-22 no llega a cero",
        )
        require(
            decimal_field(balance, "adjustment_total") == adjustment
            and decimal_field(balance, "payment_total") == applied
            and balance["status"] == "settled",
            "Totales/estado RF-22 incorrectos",
        )
    require(
        modes == {"adjustment", "income_expense"} and foreign,
        "Faltan ambas salidas RF-22 o variante multimoneda",
    )

    scenario = mapping(document["x-write-off-scenario"])
    capital = decimal_field(scenario, "principal")
    interest = Decimal(0)
    for name in sequence(scenario["movement_examples"]):
        movement = example(name)
        validate_example(document, schemas["MovementCreate"], movement)
        amount = decimal_field(movement, "amount_in_loan_currency")
        require("account_id" not in movement, "Condonación/ajuste produce dinero")
        if movement["kind"] == "interest":
            interest += amount
        elif movement["kind"] == "adjustment":
            require(amount != 0, "Ajuste debe ser distinto de cero")
            capital += amount
            require(capital >= 0, "Ajuste deja capital negativo")
        elif movement["kind"] == "write_off":
            interest_part = decimal_field(movement, "interest_part")
            principal_part = decimal_field(movement, "principal_part")
            require(
                interest_part == min(amount, interest)
                and interest_part + principal_part == amount,
                "Condonación no asigna interés primero",
            )
            interest -= interest_part
            capital -= principal_part
            require(capital >= 0, "Condonación excede capital")
    require(
        capital == decimal_field(scenario, "capital_after")
        and interest == decimal_field(scenario, "interest_after")
        and capital + interest == decimal_field(scenario, "outstanding_after"),
        "Saldo condonación/ajuste incorrecto",
    )
    require(
        decimal_field(scenario, "recognized_interest") == 0
        and decimal_field(scenario, "account_change") == 0,
        "Condonación reconoce interés o mueve dinero",
    )

    factors = {
        "daily": Decimal("30.4375"),
        "weekly": Decimal("4.348125"),
        "monthly": Decimal(1),
        "yearly": Decimal(1) / 12,
    }
    for raw in sequence(document["x-subscription-scenarios"]):
        scenario = mapping(raw)
        total_response = mapping(
            sequence(example(scenario["total_example"])["items"])[0]
        )
        validate_example(document, schemas["SubscriptionTotal"], total_response)
        interval = scenario["interval_count"]
        require(isinstance(interval, int) and interval > 0, "Intervalo inválido")
        monthly = (
            decimal_field(scenario, "amount")
            * factors[text(scenario["period"])]
            / cast(int, interval)
        )
        yearly = monthly * 12
        require(
            monthly.quantize(CENT, ROUND_HALF_UP)
            == decimal_field(total_response, "monthly_amount")
            and yearly.quantize(CENT, ROUND_HALF_UP)
            == decimal_field(total_response, "yearly_amount"),
            "Equivalente mensual/anual incorrecto; redondear solo al final",
        )
    report = resolve(document, schemas["ReportTotal"])
    require(
        "unconverted_count" in sequence(report["required"])
        and mapping(properties(document, report)["unconverted_count"]).get("minimum")
        == 0,
        "Total convertido sin unconverted_count obligatorio",
    )
    for raw_schema in schemas.values():
        for _, node in walk(raw_schema):
            if node.get("$ref") == "#/components/schemas/ReportTotal":
                require(
                    "unconverted_count" in properties(document, node),
                    "Total sin aviso de tasa faltante",
                )
    current = properties(document, schemas["CurrentUser"])
    update = properties(document, schemas["UserUpdate"])
    require(
        {"report_currency", "preferences", "base_currency"} <= set(current)
        and {"report_currency", "preferences", "base_currency"} <= set(update),
        "Perfil incompleto",
    )
    require(
        mapping(current["base_currency"]).get("readOnly") is True,
        "Base no es solo lectura en respuesta",
    )
    require(
        "409"
        in mapping(mapping(mapping(paths["/api/v1/users/me"])["patch"])["responses"]),
        "Cambio de base sin conflicto",
    )
    require(
        mapping(properties(document, schemas["UserPreferences"])["home_widgets"]).get(
            "type"
        )
        == "array",
        "Widgets deben conservar orden",
    )
    for path, methods in [
        ("/api/v1/category-rules", {"get", "post"}),
        ("/api/v1/category-rules/{id}", {"get", "patch", "delete"}),
        ("/api/v1/transactions/{id}/attachments", {"get", "post"}),
        ("/api/v1/transactions/{id}/attachments/{attachment_id}", {"delete"}),
        ("/api/v1/transactions/{id}/attachments/{attachment_id}/download", {"get"}),
    ]:
        require(
            path in paths and methods <= set(mapping(paths[path])),
            "Falta recurso/operación: " + path,
        )
    rule = properties(document, schemas["CategoryRule"])
    require(
        mapping(rule["hits"]).get("readOnly") is True
        and mapping(rule["source"]).get("readOnly") is True,
        "hits/source deben ser solo lectura",
    )
    require(
        mapping(rule["match_type"])["enum"] == ["exact", "contains"],
        "Tipos de regla inválidos",
    )
    upload = resolve(document, schemas["AttachmentUpload"])
    file = mapping(properties(document, upload)["file"])
    require(
        file.get("x-max-size-bytes") == 10485760
        and upload.get("x-max-attachments-per-transaction") == 5,
        "Límites de adjuntos incorrectos",
    )
    require(
        set(map(text, sequence(file["x-allowed-content-types"])))
        == {"image/jpeg", "image/png", "image/webp", "application/pdf"},
        "MIME adjuntos incorrectos",
    )
    attachment_post = mapping(
        mapping(paths["/api/v1/transactions/{id}/attachments"])["post"]
    )
    for code in ("413", "415"):
        error = resolve(document, mapping(attachment_post["responses"])[code])
        error_schema = mapping(
            mapping(mapping(error["content"])["application/problem+json"])["schema"]
        )
        require(
            error_schema.get("$ref") == "#/components/schemas/Problem",
            "Adjuntos sin Problem " + code,
        )
    require(
        "schema_version"
        in sequence(resolve(document, schemas["FullExport"])["required"]),
        "Exportación sin schema_version obligatorio",
    )


def check(document: Object) -> tuple[int, int, int]:
    require(document.get("openapi") == "3.1.0", "Contrato debe ser OpenAPI 3.1.0")
    for location, node in walk(document):
        if "$ref" in node:
            resolve(document, node)
        require(node.get("type") != "number", "Tipo number no permitido: " + location)
        # Valida los ejemplos conectados a los media types de requests/responses.
        if "schema" in node and isinstance(node.get("examples"), dict):
            for raw_example in mapping(node["examples"]).values():
                example = resolve(document, raw_example)
                if "value" in example:
                    validate_example(document, node["schema"], example["value"])

    components = mapping(document["components"])
    schemas = mapping(components["schemas"])
    for name in (
        "MoneyAmount",
        "PositiveAmount",
        "NonNegativeAmount",
        "ExchangeRate",
        "Currency",
    ):
        schema = mapping(schemas[name])
        require(
            schema.get("type") == "string" and "pattern" in schema,
            "Dinero/tasa/moneda requiere cadena y pattern: " + name,
        )
    require(
        mapping(schemas["Currency"])["pattern"] == "^[A-Z]{3}$",
        "Patrón de moneda incorrecto",
    )
    require(
        mapping(schemas["Uuid"]).get("format") == "uuid", "Identificadores sin UUID"
    )
    cookie = mapping(mapping(components["securitySchemes"])["SessionCookie"])
    require(
        cookie.get("type") == "apiKey" and cookie.get("in") == "cookie",
        "Seguridad sin cookie",
    )
    limit = mapping(
        resolve(document, {"$ref": "#/components/parameters/Limit"})["schema"]
    )
    require(
        limit.get("minimum") == 1
        and limit.get("maximum") == 200
        and limit.get("default") == 50,
        "Limit debe ser 1–200, defecto 50",
    )
    paths = mapping(document["paths"])
    operation_ids: set[str] = set()
    for path, raw_path in paths.items():
        require(path.startswith("/api/v1/"), "Path fuera de /api/v1")
        require(
            "settle" not in path.lower() and "liquidar" not in path.lower(),
            "Operación de liquidar",
        )
        for method, raw_operation in mapping(raw_path).items():
            if method not in METHODS:
                continue
            operation = mapping(raw_operation)
            operation_id = text(operation["operationId"])
            require(
                re.fullmatch(r"[a-z][a-z0-9_]*", operation_id) is not None,
                "operationId sin snake_case",
            )
            require(
                operation_id not in operation_ids,
                "operationId duplicado: " + operation_id,
            )
            operation_ids.add(operation_id)
            require(
                bool(operation.get("summary"))
                and bool(operation.get("description"))
                and bool(operation.get("tags")),
                "Falta documentación de operación",
            )
            security = operation.get("security", document.get("security"))
            require(
                security
                == ([] if (path, method) in PUBLIC else [{"SessionCookie": []}]),
                "Seguridad incorrecta: " + operation_id,
            )
            responses = mapping(operation["responses"])
            require(
                any(str(code).startswith("2") for code in responses),
                "Sin respuesta exitosa",
            )
            for code in ("400", "401", "403", "404", "409", "422"):
                require(
                    code in responses, "Falta Problem " + code + ": " + operation_id
                )
                response = resolve(document, responses[code])
                content = mapping(response["content"])
                problem_schema = mapping(
                    mapping(content["application/problem+json"])["schema"]
                )
                require(
                    problem_schema.get("$ref") == "#/components/schemas/Problem",
                    "Error sin Problem",
                )
            parameters = [
                resolve(document, item)
                for item in sequence(operation.get("parameters", []))
            ]
            names = {text(item["name"]) for item in parameters}
            if method in ("post", "put", "patch", "delete"):
                require(
                    "X-CSRF-Token" in names
                    and "Origin" in text(operation["description"]),
                    "Mutación sin CSRF/Origin: " + operation_id,
                )
            if operation_id in ("create_transaction", "create_loan_movement"):
                require("Idempotency-Key" in names, "Creación sin idempotencia")
            if "requestBody" in operation:
                body = resolve(document, operation["requestBody"])
                for media in mapping(body["content"]).values():
                    check_request(document, mapping(media)["schema"], set())
            success = resolve(
                document,
                responses[next(code for code in responses if code.startswith("2"))],
            )
            for media in mapping(success.get("content", {})).values():
                schema = resolve(document, mapping(media)["schema"])
                props = mapping(schema.get("properties", {}))
                is_list = (
                    "items" in props
                    or operation_id.startswith("list_")
                    or operation.get("x-paginated") is True
                )
                if is_list:
                    require(
                        method == "get" and {"limit", "cursor"} <= names,
                        "Listado sin paginación",
                    )
                    require(
                        set(props) == {"items", "next_cursor"},
                        "Listado sin envelope común",
                    )
                    require(
                        mapping(props["items"]).get("type") == "array",
                        "items no es array",
                    )
                    require(
                        {"items", "next_cursor"}
                        <= set(map(text, sequence(schema["required"]))),
                        "Envelope incompleto",
                    )
                    require(
                        mapping(props["next_cursor"]).get("anyOf")
                        == [{"type": "string"}, {"type": "null"}],
                        "next_cursor debe ser string o null",
                    )
            for parameter in parameters:
                if parameter["name"] in ("limit", "cursor"):
                    expected = resolve(
                        document,
                        {
                            "$ref": "#/components/parameters/"
                            + text(parameter["name"]).title()
                        },
                    )
                    require(
                        parameter == expected, "Paginación no usa parámetros comunes"
                    )
    for name in ("Loan", "LoanBalance"):
        for field in ("status", "outstanding"):
            require(
                mapping(properties(document, schemas[name])[field]).get("readOnly")
                is True,
                "Saldo/estado editable: " + name,
            )
    check_loans(document)
    check_architecture_v02(document)
    return len(paths), len(operation_ids), len(schemas)


class CheckerTests(unittest.TestCase):
    """Regresiones para impedir que el verificador acepte contratos rotos."""

    def setUp(self) -> None:
        self.document = copy.deepcopy(load_contract())

    def test_valid_contract(self) -> None:
        check(self.document)

    def test_overpayment_cash_remainder(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        response = mapping(
            mapping(examples["D_income_expense_foreign_response"])["value"]
        )
        mapping(sequence(response["side_effects"])[0])["amount"] = "38.00"
        with self.assertRaises(ValueError):
            check(self.document)

    def test_overpayment_applied_amount(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        request = mapping(mapping(examples["D_income_expense_request"])["value"])
        request["principal_part"] = "60.00"
        with self.assertRaises(ValueError):
            check(self.document)

    def test_write_off_interest_first(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        request = mapping(mapping(examples["Write_off_split"])["value"])
        request.update(interest_part="0.00", principal_part="30.00")
        with self.assertRaises(ValueError):
            check(self.document)

    def test_monthly_rounding(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        response = mapping(mapping(examples["Weekly_subscription_totals"])["value"])
        mapping(sequence(response["items"])[0])["yearly_amount"] = "521.76"
        with self.assertRaises(ValueError):
            check(self.document)

    def test_missing_unconverted_count(self) -> None:
        schemas = mapping(mapping(self.document["components"])["schemas"])
        sequence(mapping(schemas["ReportTotal"])["required"]).remove(
            "unconverted_count"
        )
        with self.assertRaises(ValueError):
            check(self.document)

    def test_missing_attachment_operation(self) -> None:
        paths = mapping(self.document["paths"])
        del paths["/api/v1/transactions/{id}/attachments/{attachment_id}/download"]
        with self.assertRaises(ValueError):
            check(self.document)

    def test_dangling_ref(self) -> None:
        mapping(self.document["components"])["bad_ref"] = {
            "$ref": "#/components/schemas/Missing"
        }
        with self.assertRaises(KeyError):
            check(self.document)

    def test_numeric_money(self) -> None:
        schemas = mapping(mapping(self.document["components"])["schemas"])
        schemas["MoneyAmount"] = {"type": "number"}
        with self.assertRaises(ValueError):
            check(self.document)

    def test_missing_security(self) -> None:
        path = mapping(mapping(self.document["paths"])["/api/v1/accounts"])
        mapping(path["get"])["security"] = []
        with self.assertRaises(ValueError):
            check(self.document)

    def test_request_user_id(self) -> None:
        schemas = mapping(mapping(self.document["components"])["schemas"])
        properties(self.document, schemas["PaymentRequest"])["user_id"] = {
            "type": "string"
        }
        with self.assertRaises(ValueError):
            check(self.document)

    def test_wrong_example_balance(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        mapping(mapping(examples["A_balance"])["value"])["outstanding"] = "1.00"
        with self.assertRaises(ValueError):
            check(self.document)

    def test_wrong_example_account(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        mapping(mapping(examples["A_movement_3"])["value"])["account_id"] = (
            "00000000-0000-4000-8000-000000000010"
        )
        with self.assertRaises(ValueError):
            check(self.document)

    def test_wrong_fx(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        mapping(mapping(examples["C_movement_2"])["value"])["fx_rate_applied"] = (
            "3.700000"
        )
        with self.assertRaises(ValueError):
            check(self.document)

    def test_missing_overpayment_option(self) -> None:
        examples = mapping(mapping(self.document["components"])["examples"])
        mapping(mapping(examples["D_overpayment"])["value"])["options"] = []
        with self.assertRaises(ValueError):
            check(self.document)


def main() -> int:
    try:
        paths, operations, schemas = check(load_contract())
    except (ValueError, KeyError, IndexError, OSError, ArithmeticError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print(
        f"OK: {paths} paths, {operations} operaciones, {schemas} esquemas; "
        "referencias, decimales, Problem, seguridad, CSRF, paginación, aislamiento "
        "y ejemplos A–E verificados; v0.2: exceso atómico/multimoneda, condonación, "
        "equivalentes mensuales/anuales, unconverted_count, category-rules y attachments."
    )
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        sys.exit(main())
