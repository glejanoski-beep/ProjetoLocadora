"""Contratos de locação e apresentação de datas, sem persistência local."""

from datetime import datetime, timezone
import re
from typing import TypedDict
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")


class Rental(TypedDict):
    id: int
    customer_id: int
    exemplar_id: int
    registered_by: int
    rented_at: int
    due_at: int
    status: str
    customer_name: str
    exemplar_identifier: str
    film_id: int
    film_title: str


def vencimento_utc(value: str) -> str:
    """Converte o datetime-local do formulário, explicitamente em Brasília."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?", value):
        raise ValueError("Informe data e hora de vencimento no horário de Brasília.")
    try:
        local = datetime.fromisoformat(value).replace(tzinfo=BRASILIA)
        converted = local.astimezone(timezone.utc)
        if converted.astimezone(BRASILIA).replace(tzinfo=None) != local.replace(tzinfo=None):
            raise ValueError
        if local.utcoffset() != local.replace(fold=1).utcoffset():
            raise ValueError
        return converted.isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        raise ValueError("Data ou hora de vencimento inválida.") from None


def data_brasilia(value: int) -> str:
    try:
        if type(value) is not int:
            raise ValueError
        return datetime.fromtimestamp(value / 1000, timezone.utc).astimezone(BRASILIA).strftime("%d/%m/%Y às %H:%M")
    except (ValueError, OverflowError, OSError):
        return "Data indisponível"


def validar_rental(value: object) -> Rental:
    fields = set(Rental.__annotations__)
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Resposta de locação inválida")
    for key in ("id", "customer_id", "exemplar_id", "registered_by", "film_id", "rented_at", "due_at"):
        if type(value[key]) is not int or value[key] <= 0:
            raise ValueError("Resposta de locação inválida")
    if value["status"] != "active" or value["due_at"] <= value["rented_at"]:
        raise ValueError("Resposta de locação inválida")
    for key in ("customer_name", "film_title"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError("Resposta de locação inválida")
    # O contrato de exemplar compara exatamente o identificador, sem trim.
    if not isinstance(value["exemplar_identifier"], str) or value["exemplar_identifier"] == "":
        raise ValueError("Resposta de locação inválida")
    for key in ("rented_at", "due_at"):
        if data_brasilia(value[key]) == "Data indisponível":
            raise ValueError("Resposta de locação inválida")
    return value.copy()
