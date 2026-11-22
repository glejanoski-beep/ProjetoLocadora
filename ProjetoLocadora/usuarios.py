"""Contas internas: rótulos, contrato do item recebido, busca e motivo (gerenciar-usuarios)."""

import re
import unicodedata
from typing import TypedDict

ROLES = {"admin": "Administrador", "member": "Funcionário"}
ROLE_BY_LABEL = {label: role for role, label in ROLES.items()}
STATUS_FILTERS = {"all": "Todas", "active": "Ativas", "inactive": "Desativadas"}
MAX_USERS = 500
USER_KEYS = frozenset({"id", "name", "email", "role", "is_active", "created_at"})


class Usuario(TypedDict):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: int


def validar_usuario(value) -> Usuario:
    """Chaves exatas e tipos estritos: qualquer campo a mais (ex.: senha) é recusado."""
    if type(value) is not dict or set(value) != USER_KEYS:
        raise ValueError("Conta inválida.")
    if type(value["id"]) is not int or value["id"] < 1:
        raise ValueError("Conta inválida.")
    if type(value["name"]) is not str or type(value["email"]) is not str:
        raise ValueError("Conta inválida.")
    if value["role"] not in ROLES or type(value["is_active"]) is not bool:
        raise ValueError("Conta inválida.")
    if type(value["created_at"]) is not int or value["created_at"] < 0:
        raise ValueError("Conta inválida.")
    return Usuario(**value)


def validar_lista(data) -> list[Usuario]:
    if type(data) is not dict or set(data) != {"items"} or type(data["items"]) is not list:
        raise ValueError("Lista inválida.")
    if len(data["items"]) > MAX_USERS:
        raise ValueError("Lista inválida.")
    return [validar_usuario(item) for item in data["items"]]


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold()) if unicodedata.category(c) != "Mn"
    )


def filtrar(usuarios: list[Usuario], busca: str, situacao: str) -> list[Usuario]:
    """Busca por nome ou e-mail, sem acentos e sem diferença de maiúsculas."""
    termo = _sem_acento(busca.strip())
    result = []
    for usuario in usuarios:
        if situacao == "active" and not usuario["is_active"]:
            continue
        if situacao == "inactive" and usuario["is_active"]:
            continue
        if termo and termo not in _sem_acento(usuario["name"]) and termo not in _sem_acento(usuario["email"]):
            continue
        result.append(usuario)
    return result


def validar_motivo(motivo: str) -> str:
    clean = motivo.strip() if isinstance(motivo, str) else ""
    if not clean:
        raise ValueError("Informe o motivo da alteração.")
    if len(clean) > 500:
        raise ValueError("O motivo pode ter no máximo 500 caracteres.")
    return clean


def validar_novo_usuario(name: str, email: str, role: str) -> tuple[str, str]:
    clean_name = name.strip() if isinstance(name, str) else ""
    if not clean_name:
        raise ValueError("Informe o nome da nova conta.")
    if len(clean_name) > 200:
        raise ValueError("O nome pode ter no máximo 200 caracteres.")
    clean_email = email.strip().lower() if isinstance(email, str) else ""
    if not clean_email:
        raise ValueError("Informe o e-mail da nova conta.")
    if len(clean_email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", clean_email):
        raise ValueError("Informe um e-mail válido.")
    if role not in ROLES:
        raise ValueError("Selecione um papel válido.")
    return clean_name, clean_email
