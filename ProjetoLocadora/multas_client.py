"""Transporte de multas e pagamentos (grupo Xano "Locações"), sem retries de escrita."""

import json
from uuid import UUID

import httpx

from ProjetoLocadora.config import get_xano_rental_api_url, rental_writes_enabled
from ProjetoLocadora.multas import (
    PAYMENT_METHODS, Fine, Payment, Policy, validar_fine, validar_payment, validar_policy,
)
from ProjetoLocadora.xano_client import retry_after_seconds


MESSAGES = {
    "authentication": "Entre novamente para acessar multas.",
    "authorization": "Sua conta não tem permissão para esta operação.",
    "configuration": "O módulo de multas ainda não está configurado.",
    "disabled": "O registro de pagamentos aguarda habilitação do serviço.",
    "unavailable": "Não foi possível consultar o serviço de multas.",
    "invalid": "O serviço retornou uma resposta inválida.",
    "input": "Confira os dados informados; a operação foi recusada.",
    "conflict": "A multa foi alterada por outra operação. Confira os dados atualizados.",
    "notfound": "Multa não encontrada.",
    "unknown": "Resultado ainda desconhecido. Consulte a multa antes de tentar novamente.",
    "ratelimited": "O Xano atingiu o limite de requisições do plano. Aguarde alguns segundos e tente novamente.",
}
# Recusas de negócio do backend, exibidas como vieram (texto controlado pelo projeto).
BUSINESS_CONFLICTS = frozenset({
    "Multa não está em aberto.", "Valor acima do saldo da multa.", "Pagamento já estornado.",
    "Multa abonada: estorno não permitido.", "Chave já utilizada para outra operação.",
})
NOT_FOUND = frozenset({"Multa não encontrada.", "Pagamento não encontrado."})
FINE_STATUSES = ("", "open", "paid", "waived")


class FineError(Exception):
    def __init__(self, category: str, retry_after: int | None = None, detail: str = ""):
        self.category = category
        self.retry_after = retry_after
        self.detail = detail
        super().__init__(detail or MESSAGES[category])


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError


async def _request(token: str, method: str, path: str, *, payload=None, params=None, gated: bool = True, business=BUSINESS_CONFLICTS):
    """`gated`: escrita depende de XANO_RENTAL_WRITES_ENABLED; `business`: recusas exibidas como vieram."""
    if not token:
        raise FineError("authentication")
    writing = method != "GET"
    if writing and gated and not rental_writes_enabled():
        raise FineError("disabled")
    try:
        base = get_xano_rental_api_url()
    except (RuntimeError, ValueError):
        raise FineError("configuration") from None
    failure = None
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.request(
                method, f"{base}/{path}", headers={"Authorization": f"Bearer {token}"},
                json=payload, params=params,
            )
    except (httpx.HTTPError, ValueError):
        failure = "unknown" if writing else "unavailable"
    if failure:
        raise FineError(failure)
    try:
        data = json.loads(response.content.decode("utf-8"), object_pairs_hook=_object, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        data = None
    status = response.status_code
    message = data.get("message") if type(data) is dict else None
    if status == 429 and not writing:
        raise FineError("ratelimited", retry_after=retry_after_seconds(response))
    if status in (401, 403):
        raise FineError("authentication" if status == 401 else "authorization")
    if status == 404:
        # Rota ausente em escrita não prova inexistência: só a mensagem do endpoint.
        if not writing or message in NOT_FOUND:
            raise FineError("notfound", detail=message if message in NOT_FOUND else "")
        raise FineError("unknown")
    if status >= 400 and message in business:
        raise FineError("conflict", detail=message)
    if status in (400, 422):
        raise FineError("input")
    if status not in (200, 201):
        raise FineError("unknown" if writing else "unavailable")
    if data is None:
        raise FineError("unknown" if writing else "invalid")
    return data


def _id(value):
    if type(value) is not int or value < 1:
        raise FineError("input")
    return value


def _key(value: str) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise FineError("input") from None


def _reason(value: str) -> str:
    clean = value.strip() if isinstance(value, str) else ""
    if not clean or len(clean) > 500:
        raise FineError("input")
    return clean


def _page(data, page: int, per_page: int, validate) -> dict:
    if type(data) is not dict or set(data) != {"items", "page", "per_page", "total"}:
        raise ValueError
    if any(type(data[k]) is not int for k in ("page", "per_page", "total")):
        raise ValueError
    if data["page"] != page or data["per_page"] != per_page or type(data["items"]) is not list or len(data["items"]) > per_page:
        raise ValueError
    if data["total"] < len(data["items"]):
        raise ValueError
    items = [validate(item) for item in data["items"]]
    if len({item["id"] for item in items}) != len(items):
        raise ValueError
    return {"items": items, "page": page, "per_page": per_page, "total": data["total"]}


async def list_fines(token: str, page: int = 1, per_page: int = 10, *, status: str = "", customer_id: int = 0, rental_id: int = 0) -> dict:
    if status not in FINE_STATUSES or type(customer_id) is not int or customer_id < 0 or type(rental_id) is not int or rental_id < 0:
        raise FineError("input")
    params = {"page": _id(page), "per_page": _id(per_page)}
    if status:
        params["status"] = status
    if customer_id:
        params["customer_id"] = customer_id
    if rental_id:
        params["rental_id"] = rental_id
    data = await _request(token, "GET", "multas", params=params)
    try:
        result = _page(data, page, per_page, validar_fine)
        # Filtro ignorado pelo serviço não pode misturar abas ou clientes.
        for item in result["items"]:
            if (status and item["status"] != status) or (customer_id and item["customer_id"] != customer_id) or (rental_id and item["rental_id"] != rental_id):
                raise ValueError
        return result
    except (ValueError, TypeError, KeyError):
        raise FineError("invalid") from None


def _detail(data, fine_id: int) -> tuple[Fine, list[Payment]]:
    if type(data) is not dict or set(data) != {"fine", "payments"} or type(data["payments"]) is not list:
        raise ValueError
    fine = validar_fine(data["fine"])
    payments = [validar_payment(item) for item in data["payments"]]
    if fine["id"] != fine_id or any(item["fine_id"] != fine_id for item in payments):
        raise ValueError
    # O total pago da multa deve bater com os pagamentos confirmados.
    if sum(item["amount_cents"] for item in payments if item["status"] == "confirmed") != fine["paid_cents"]:
        raise ValueError
    return fine, payments


async def get_fine(token: str, fine_id: int) -> tuple[Fine, list[Payment]]:
    data = await _request(token, "GET", f"multas/{_id(fine_id)}")
    try:
        return _detail(data, fine_id)
    except (ValueError, TypeError, KeyError):
        raise FineError("invalid") from None


async def fines_summary(token: str) -> dict:
    data = await _request(token, "GET", "multas/resumo")
    try:
        if type(data) is not dict or set(data) != {"open_count", "open_balance_cents"}:
            raise ValueError
        if any(type(data[k]) is not int or data[k] < 0 for k in data):
            raise ValueError
        if (data["open_count"] == 0) != (data["open_balance_cents"] == 0):
            raise ValueError
        return dict(data)
    except (ValueError, TypeError):
        raise FineError("invalid") from None


async def fine_policy(token: str) -> Policy:
    data = await _request(token, "GET", "multas/politica")
    try:
        return validar_policy(data)
    except ValueError:
        raise FineError("invalid") from None


async def list_payments(token: str, page: int = 1, per_page: int = 10, *, customer_id: int = 0) -> dict:
    if type(customer_id) is not int or customer_id < 0:
        raise FineError("input")
    params = {"page": _id(page), "per_page": _id(per_page)}
    if customer_id:
        params["customer_id"] = customer_id
    data = await _request(token, "GET", "pagamentos", params=params)
    try:
        result = _page(data, page, per_page, validar_payment)
        if customer_id and any(item["customer_id"] != customer_id for item in result["items"]):
            raise ValueError
        return result
    except (ValueError, TypeError, KeyError):
        raise FineError("invalid") from None


def _write_result(result, keys: set) -> None:
    if type(result) is not dict or set(result) != keys or type(result["audit_succeeded"]) is not bool:
        raise ValueError


async def pay_fine(token: str, fine_id: int, amount_cents: int, method: str, operation_key: str) -> tuple[Payment, Fine, bool]:
    """Registra pagamento; sem retry automático. Repetir usa a mesma chave."""
    _id(fine_id)
    if type(amount_cents) is not int or amount_cents < 1 or method not in PAYMENT_METHODS:
        raise FineError("input")
    payload = {"amount_cents": amount_cents, "method": method, "operation_key": _key(operation_key)}
    result = await _request(token, "POST", f"multas/{fine_id}/pagamentos", payload=payload)
    try:
        _write_result(result, {"payment", "fine", "audit_succeeded"})
        payment, fine = validar_payment(result["payment"]), validar_fine(result["fine"])
        if payment["fine_id"] != fine_id or fine["id"] != fine_id or payment["amount_cents"] != amount_cents or payment["method"] != method:
            raise ValueError
        # A multa devolvida precisa refletir o pagamento confirmado.
        if payment["status"] != "confirmed" or fine["paid_cents"] < amount_cents:
            raise ValueError
        return payment, fine, result["audit_succeeded"]
    except (ValueError, TypeError, KeyError):
        raise FineError("unknown") from None


async def waive_fine(token: str, fine_id: int, reason: str, operation_key: str) -> tuple[Fine, bool]:
    _id(fine_id)
    payload = {"reason": _reason(reason), "operation_key": _key(operation_key)}
    result = await _request(token, "POST", f"multas/{fine_id}/abono", payload=payload)
    try:
        _write_result(result, {"fine", "audit_succeeded"})
        fine = validar_fine(result["fine"])
        if fine["id"] != fine_id or fine["status"] != "waived":
            raise ValueError
        return fine, result["audit_succeeded"]
    except (ValueError, TypeError, KeyError):
        raise FineError("unknown") from None


async def reverse_payment(token: str, payment_id: int, reason: str, operation_key: str) -> tuple[Payment, Fine, bool]:
    _id(payment_id)
    payload = {"reason": _reason(reason), "operation_key": _key(operation_key)}
    result = await _request(token, "POST", f"pagamentos/{payment_id}/estorno", payload=payload)
    try:
        _write_result(result, {"payment", "fine", "audit_succeeded"})
        payment, fine = validar_payment(result["payment"]), validar_fine(result["fine"])
        if payment["id"] != payment_id or payment["status"] != "reversed" or fine["id"] != payment["fine_id"]:
            raise ValueError
        return payment, fine, result["audit_succeeded"]
    except (ValueError, TypeError, KeyError):
        raise FineError("unknown") from None
