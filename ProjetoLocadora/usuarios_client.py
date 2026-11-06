"""Transporte da gestão de contas (grupo Xano "Locações"), sem retries de escrita."""

from ProjetoLocadora.multas_client import FineError, _request
from ProjetoLocadora.usuarios import ROLES, Usuario, validar_lista, validar_motivo, validar_usuario

MESSAGES = {
    "authentication": "Entre novamente para gerenciar usuários.",
    "authorization": "Gestão de usuários disponível apenas para administradores.",
    "configuration": "O módulo de usuários ainda não está configurado.",
    "unavailable": "Não foi possível consultar o serviço de usuários.",
    "invalid": "O serviço retornou uma resposta inválida.",
    "input": "Confira os dados informados; a alteração foi recusada.",
    "notfound": "Usuário não encontrado.",
    "unknown": "Resultado ainda desconhecido. Recarregue a lista antes de tentar novamente.",
    "ratelimited": "O Xano atingiu o limite de requisições do plano. Aguarde alguns segundos e tente novamente.",
}
# Recusas de negócio do backend, exibidas como vieram.
NO_CHANGE = "Nenhuma alteração informada."
BUSINESS = frozenset({
    "Você não pode alterar a própria conta.", NO_CHANGE, "Usuário não encontrado.",
    "Informe o motivo da alteração (até 500 caracteres).",
})


class UserError(Exception):
    def __init__(self, category: str, retry_after: int | None = None, detail: str = ""):
        self.category = category if category in MESSAGES or category == "conflict" else "unavailable"
        self.retry_after = retry_after
        self.detail = detail
        super().__init__(detail or MESSAGES.get(self.category, MESSAGES["unavailable"]))


async def list_users(token: str) -> list[Usuario]:
    try:
        data = await _request(token, "GET", "usuarios")
    except FineError as error:
        raise UserError(error.category, error.retry_after, error.detail) from None
    try:
        return validar_lista(data)
    except (ValueError, TypeError, KeyError):
        raise UserError("invalid") from None


async def update_user(token: str, user_id: int, role: str, is_active: bool, reason: str) -> Usuario:
    if type(user_id) is not int or user_id < 1 or role not in ROLES or type(is_active) is not bool:
        raise UserError("input")
    try:
        clean = validar_motivo(reason)
    except ValueError:
        raise UserError("input") from None
    try:
        data = await _request(
            token, "PATCH", f"usuarios/{user_id}",
            payload={"role": role, "is_active": is_active, "reason": clean},
            gated=False, business=BUSINESS,
        )
    except FineError as error:
        raise UserError(error.category, error.retry_after, error.detail) from None
    try:
        if type(data) is not dict or set(data) != {"user", "audit_succeeded"}:
            raise ValueError
        user = validar_usuario(data["user"])
        if user["id"] != user_id or user["role"] != role or user["is_active"] is not is_active:
            raise ValueError
        return user
    except (ValueError, TypeError, KeyError):
        raise UserError("unknown") from None
