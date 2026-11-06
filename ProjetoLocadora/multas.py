"""Contratos de multas e pagamentos, formatação em reais e estimativa da multa.

Valores sempre em centavos inteiros. O valor que vale é o calculado pelo backend
na devolução; `estimar_multa` só alimenta a estimativa exibida antes de confirmar.
"""

import math
import re
from typing import TypedDict

from ProjetoLocadora.locacoes import data_brasilia

DAY_MS = 24 * 60 * 60 * 1000
FINE_STATUS = {"open": "Em aberto", "paid": "Quitada", "waived": "Abonada"}
PAYMENT_STATUS = {"confirmed": "Confirmado", "reversed": "Estornado"}
PAYMENT_METHODS = {"cash": "Dinheiro", "pix": "Pix", "debit_card": "Cartão de débito", "credit_card": "Cartão de crédito"}


class Fine(TypedDict):
    id: int
    rental_id: int
    customer_id: int
    customer_name: str
    film_title: str
    exemplar_identifier: str
    due_at: int
    returned_at: int
    late_days: int
    daily_cents: int
    grace_minutes: int
    cap_cents: int
    amount_cents: int
    paid_cents: int
    waived_cents: int
    status: str
    created_at: int
    created_by: int
    waived_at: int | None
    waived_by: int | None
    waive_reason: str | None


class Payment(TypedDict):
    id: int
    fine_id: int
    customer_id: int
    amount_cents: int
    method: str
    paid_at: int
    registered_by: int
    status: str
    reversed_at: int | None
    reversed_by: int | None
    reversal_reason: str | None


class Policy(TypedDict):
    daily_cents: int
    grace_minutes: int
    cap_cents: int


FINE_FIELDS = frozenset(Fine.__annotations__)
PAYMENT_FIELDS = frozenset(Payment.__annotations__)
POLICY_FIELDS = frozenset(Policy.__annotations__)


def reais(cents: int) -> str:
    """`R$ 1.234,56` a partir de centavos inteiros."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}R$ {whole:,}".replace(",", ".") + f",{frac:02d}"


def centavos(texto: str) -> int | None:
    """Converte `9`, `9,5`, `9,50`, `9.50` ou `1.234,56` em centavos; None se inválido."""
    value = texto.strip().replace("R$", "").strip()
    if re.fullmatch(r"\d+\.\d{1,2}", value):
        # Sem vírgula, ponto com 1–2 casas é decimal (9.50), não milhar.
        value = value.replace(".", ",")
    match = re.fullmatch(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?", value)
    if not match:
        return None
    whole, frac = match.group(1).replace(".", ""), match.group(2) or ""
    if len(whole) > 7:
        return None
    return int(whole) * 100 + int(frac.ljust(2, "0"))


def saldo(fine: Fine) -> int:
    return fine["amount_cents"] - fine["paid_cents"] - fine["waived_cents"]


def dias(n: int) -> str:
    return f"{n} dia" if n == 1 else f"{n} dias"


def estimar_multa(due_at: int, returned_at: int, policy: Policy) -> tuple[int, int]:
    """(dias, centavos) pela mesma regra de `Locacoes/calculate_late_fine`."""
    late_ms = returned_at - due_at
    if late_ms <= policy["grace_minutes"] * 60_000:
        return 0, 0
    days = math.ceil(late_ms / DAY_MS)
    return days, min(days * policy["daily_cents"], policy["cap_cents"])


def _positive(value: object) -> bool:
    return type(value) is int and value > 0


def _date_ok(value: object) -> bool:
    return _positive(value) and data_brasilia(value) != "Data indisponível"


def validar_policy(value: object) -> Policy:
    if type(value) is not dict or set(value) != POLICY_FIELDS:
        raise ValueError("Política de multa inválida")
    if not _positive(value["daily_cents"]) or type(value["grace_minutes"]) is not int or value["grace_minutes"] < 0:
        raise ValueError("Política de multa inválida")
    if type(value["cap_cents"]) is not int or value["cap_cents"] < value["daily_cents"]:
        raise ValueError("Política de multa inválida")
    return value.copy()


def validar_fine(value: object) -> Fine:
    """Multa coerente: inteiros em centavos, saldo >= 0 e status compatível."""
    if type(value) is not dict or set(value) != FINE_FIELDS:
        raise ValueError("Resposta de multa inválida")
    for key in ("id", "rental_id", "customer_id", "created_by", "late_days", "daily_cents", "cap_cents", "amount_cents"):
        if not _positive(value[key]):
            raise ValueError("Resposta de multa inválida")
    for key in ("grace_minutes", "paid_cents", "waived_cents"):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError("Resposta de multa inválida")
    for key in ("due_at", "returned_at", "created_at"):
        if not _date_ok(value[key]):
            raise ValueError("Resposta de multa inválida")
    if value["returned_at"] <= value["due_at"] or value["amount_cents"] > value["cap_cents"]:
        raise ValueError("Resposta de multa inválida")
    for key in ("customer_name", "film_title"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError("Resposta de multa inválida")
    if not isinstance(value["exemplar_identifier"], str) or value["exemplar_identifier"] == "":
        raise ValueError("Resposta de multa inválida")
    balance = value["amount_cents"] - value["paid_cents"] - value["waived_cents"]
    if balance < 0:
        raise ValueError("Resposta de multa inválida")
    status = value["status"]
    waived = (value["waived_at"], value["waived_by"], value["waive_reason"])
    if status == "waived":
        if not _date_ok(waived[0]) or not _positive(waived[1]) or not isinstance(waived[2], str) or not waived[2].strip() or balance != 0:
            raise ValueError("Resposta de multa inválida")
    elif status in ("open", "paid"):
        if any(item is not None for item in waived) or value["waived_cents"] != 0:
            raise ValueError("Resposta de multa inválida")
        if (status == "paid") != (balance == 0):
            raise ValueError("Resposta de multa inválida")
    else:
        raise ValueError("Resposta de multa inválida")
    return value.copy()


def validar_payment(value: object) -> Payment:
    if type(value) is not dict or set(value) != PAYMENT_FIELDS:
        raise ValueError("Resposta de pagamento inválida")
    for key in ("id", "fine_id", "customer_id", "amount_cents", "registered_by"):
        if not _positive(value[key]):
            raise ValueError("Resposta de pagamento inválida")
    if value["method"] not in PAYMENT_METHODS or not _date_ok(value["paid_at"]):
        raise ValueError("Resposta de pagamento inválida")
    reversal = (value["reversed_at"], value["reversed_by"], value["reversal_reason"])
    if value["status"] == "reversed":
        if not _date_ok(reversal[0]) or not _positive(reversal[1]) or not isinstance(reversal[2], str) or not reversal[2].strip():
            raise ValueError("Resposta de pagamento inválida")
    elif value["status"] == "confirmed":
        if any(item is not None for item in reversal):
            raise ValueError("Resposta de pagamento inválida")
    else:
        raise ValueError("Resposta de pagamento inválida")
    return value.copy()
