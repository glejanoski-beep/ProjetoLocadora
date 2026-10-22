"""Transporte privado de locações, sem retries automáticos de escrita."""

from datetime import datetime
import json
from uuid import UUID

import httpx

from ProjetoLocadora.config import get_xano_rental_api_url, rental_writes_enabled
from ProjetoLocadora.locacoes import Rental, validar_rental


MESSAGES = {
    "authentication": "Entre novamente para acessar locações.",
    "authorization": "Sua conta não tem permissão para esta operação.",
    "configuration": "O módulo de locações ainda não está configurado.",
    "disabled": "O registro de locações aguarda validação e habilitação do serviço.",
    "unavailable": "Não foi possível consultar o serviço de locações.",
    "invalid": "O serviço retornou uma resposta inválida.",
    "input": "Confira cliente, exemplar e vencimento; a operação foi recusada.",
    "conflict": "O exemplar foi ocupado ou a chave já pertence a outra operação. Consulte o resultado antes de tentar novamente.",
    "notfound": "Locação não encontrada.",
    "unknown": "Resultado ainda desconhecido. Consulte a tentativa antes de iniciar outra locação.",
}


class RentalError(Exception):
    def __init__(self, category: str):
        self.category = category
        super().__init__(MESSAGES[category])


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError


async def _request(token: str, method: str, path: str, *, payload=None, params=None):
    if not token:
        raise RentalError("authentication")
    writing = method != "GET"
    if writing and not rental_writes_enabled():
        raise RentalError("disabled")
    try:
        base = get_xano_rental_api_url()
    except (RuntimeError, ValueError):
        raise RentalError("configuration") from None
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
        raise RentalError(failure)
    try:
        data = json.loads(response.content.decode("utf-8"), object_pairs_hook=_object, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        data = None
    status = response.status_code
    if status in (401, 403):
        raise RentalError("authentication" if status == 401 else "authorization")
    if status == 404:
        # A POST em rota ausente não é motivo para usar outro grupo ou repetir.
        raise RentalError("unknown" if writing else "notfound")
    if status == 409 or (type(data) is dict and data.get("message") in {
        "Exemplar já possui locação ativa.", "Chave já utilizada para outra operação.",
    } and status >= 400):
        raise RentalError("conflict")
    if status in (400, 422):
        raise RentalError("input")
    if status not in (200, 201):
        raise RentalError("unknown" if writing else "unavailable")
    if data is None:
        raise RentalError("unknown" if writing else "invalid")
    return data


def _id(value):
    if type(value) is not int or value < 1:
        raise RentalError("input")
    return value


def _key(value: str) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise RentalError("input") from None


async def create_rental(token: str, payload: dict) -> tuple[Rental, bool]:
    if set(payload) != {"customer_id", "exemplar_id", "due_at", "operation_key"}:
        raise RentalError("input")
    _id(payload["customer_id"])
    _id(payload["exemplar_id"])
    _key(payload["operation_key"])
    try:
        due = datetime.fromisoformat(payload["due_at"].replace("Z", "+00:00"))
        if due.tzinfo is None:
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise RentalError("input") from None
    result = await _request(token, "POST", "locacoes", payload=payload)
    try:
        if type(result) is not dict or set(result) != {"rental", "audit_succeeded"} or type(result["audit_succeeded"]) is not bool:
            raise ValueError
        rental = validar_rental(result["rental"])
        expected_due = int(due.timestamp() * 1000)
        if (rental["customer_id"], rental["exemplar_id"], rental["due_at"]) != (payload["customer_id"], payload["exemplar_id"], expected_due):
            raise ValueError
        return rental, result["audit_succeeded"]
    except (ValueError, TypeError, KeyError):
        raise RentalError("unknown") from None


async def get_rental(token: str, rental_id: int) -> Rental:
    data = await _request(token, "GET", f"locacoes/{_id(rental_id)}")
    try:
        rental = validar_rental(data)
        if rental["id"] != rental_id:
            raise ValueError
        return rental
    except ValueError:
        raise RentalError("invalid") from None


async def reconcile_rental(token: str, key: str) -> Rental:
    data = await _request(token, "GET", f"locacoes/operacoes/{_key(key)}")
    try:
        return validar_rental(data)
    except ValueError:
        raise RentalError("invalid") from None


async def available_exemplars(token: str, page: int = 1) -> dict:
    data = await _request(token, "GET", "locacoes/exemplares-disponiveis", params={"page": _id(page), "per_page": 20})
    try:
        if type(data) is not dict or set(data) != {"items", "page", "per_page", "total"}:
            raise ValueError
        if any(type(data[k]) is not int for k in ("page", "per_page", "total")):
            raise ValueError
        if data["page"] != page or data["per_page"] != 20 or data["total"] < 0 or type(data["items"]) is not list or len(data["items"]) > 20:
            raise ValueError
        seen = set()
        for item in data["items"]:
            if type(item) is not dict or set(item) != {"id", "identificador", "filme_id", "filme_titulo"}:
                raise ValueError
            if any(type(item[k]) is not int or item[k] < 1 for k in ("id", "filme_id")):
                raise ValueError
            if not isinstance(item["identificador"], str) or item["identificador"] == "":
                raise ValueError
            if not isinstance(item["filme_titulo"], str) or not item["filme_titulo"].strip() or item["id"] in seen:
                raise ValueError
            seen.add(item["id"])
        return data
    except (ValueError, TypeError, KeyError):
        raise RentalError("invalid") from None


async def confirm_condition(token: str, exemplar_id: int, condition: str, reason: str) -> bool:
    if condition not in {"unverified", "available", "unavailable"} or not reason.strip() or len(reason.strip()) > 500:
        raise RentalError("input")
    result = await _request(token, "PATCH", f"locacoes/exemplares/{_id(exemplar_id)}/condicao", payload={"operational_condition": condition, "reason": reason.strip()})
    try:
        if type(result) is not dict or set(result) != {"exemplar", "audit_succeeded"} or type(result["audit_succeeded"]) is not bool:
            raise ValueError
        item = result["exemplar"]
        if type(item) is not dict or set(item) != {"id", "operational_condition", "condition_confirmed_at", "condition_confirmed_by"}:
            raise ValueError
        if type(item["id"]) is not int or item["id"] != exemplar_id or item["operational_condition"] != condition:
            raise ValueError
        if any(type(item[k]) is not int or item[k] <= 0 for k in ("condition_confirmed_at", "condition_confirmed_by")):
            raise ValueError
        return result["audit_succeeded"]
    except (ValueError, KeyError, TypeError):
        raise RentalError("unknown") from None
