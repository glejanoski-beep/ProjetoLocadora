from __future__ import annotations

import re
from typing import NotRequired, TypedDict


STATUS_CLIENTE = ("active", "inactive")
_CPF_ALLOWED = re.compile(r"^[0-9.\-/\s]+$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ClienteResumo(TypedDict):
    id: int
    nome: str
    cpf_mascarado: str
    status: str
    bloqueio_manual_ativo: bool


class ClienteDetalhe(TypedDict):
    id: int
    created_at: NotRequired[int | str | None]
    updated_at: NotRequired[int | str | None]
    nome: str
    cpf: str
    email: str | None
    telefone: str | None
    status: str
    bloqueio_manual_ativo: bool
    motivo_bloqueio_manual: str | None
    bloqueado_em: int | str | None
    bloqueado_por: int | None


class PaginaClientes(TypedDict):
    items: list[ClienteResumo]
    page: int
    per_page: int
    total: int


def normalizar_cpf(value: str) -> str:
    raw = value.strip()
    if not raw or not _CPF_ALLOWED.fullmatch(raw):
        raise ValueError("Informe um CPF válido.")
    return re.sub(r"\D", "", raw)


def cpf_valido(value: str) -> bool:
    try:
        digits = normalizar_cpf(value)
    except ValueError:
        return False
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    numbers = [int(digit) for digit in digits]
    first_sum = sum(number * weight for number, weight in zip(numbers[:9], range(10, 1, -1)))
    first_digit = (first_sum * 10) % 11
    if first_digit == 10:
        first_digit = 0
    if first_digit != numbers[9]:
        return False

    second_sum = sum(number * weight for number, weight in zip(numbers[:10], range(11, 1, -1)))
    second_digit = (second_sum * 10) % 11
    if second_digit == 10:
        second_digit = 0
    return second_digit == numbers[10]


def mascarar_cpf(value: str) -> str:
    if not cpf_valido(value):
        raise ValueError("Informe um CPF válido.")
    digits = normalizar_cpf(value)
    return f"***.***.***-{digits[-2:]}"


def normalizar_telefone(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if not re.fullmatch(r"[0-9()\-\s]+", raw):
        raise ValueError("Informe um telefone brasileiro válido.")
    digits = re.sub(r"\D", "", raw)
    if len(digits) not in (10, 11):
        raise ValueError("Informe um telefone brasileiro com 10 ou 11 dígitos.")
    return digits


def validar_cliente(
    *,
    nome: str,
    cpf: str,
    email: str,
    telefone: str,
    status: str = "active",
) -> tuple[dict[str, str], dict[str, str | None]]:
    errors: dict[str, str] = {}
    clean_name = nome.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        errors["nome"] = "Informe o nome completo."
    elif len(clean_name) > 200:
        errors["nome"] = "O nome deve ter no máximo 200 caracteres."

    try:
        clean_cpf = normalizar_cpf(cpf)
        if not cpf_valido(clean_cpf):
            raise ValueError
    except ValueError:
        clean_cpf = ""
        errors["cpf"] = "Informe um CPF válido."

    if clean_email and (len(clean_email) > 254 or not _EMAIL.fullmatch(clean_email)):
        errors["email"] = "Informe um e-mail válido."

    try:
        clean_phone = normalizar_telefone(telefone)
    except ValueError as err:
        clean_phone = ""
        errors["telefone"] = str(err)

    if not clean_email and not clean_phone:
        errors["contato"] = "Informe ao menos um contato: e-mail ou telefone."

    if status not in STATUS_CLIENTE:
        errors["status"] = "Selecione uma situação cadastral válida."

    return errors, {
        "nome": clean_name,
        "cpf": clean_cpf,
        "email": clean_email or None,
        "telefone": clean_phone or None,
        "status": status,
    }


def validar_bloqueio_manual(
    *, bloqueado: bool, motivo: str
) -> tuple[dict[str, str], dict[str, str | bool | None]]:
    clean_reason = motivo.strip()
    errors: dict[str, str] = {}
    if bloqueado and not clean_reason:
        errors["motivo"] = "Informe o motivo do bloqueio manual."
    elif len(clean_reason) > 500:
        errors["motivo"] = "O motivo deve ter no máximo 500 caracteres."
    return errors, {
        "bloqueado": bloqueado,
        "motivo": clean_reason if bloqueado else None,
    }
