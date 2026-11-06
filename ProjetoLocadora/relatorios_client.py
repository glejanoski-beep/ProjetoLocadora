"""Transporte do relatório consolidado (grupo Xano "Locações"); somente leitura."""

from ProjetoLocadora.multas_client import FineError, _request
from ProjetoLocadora.relatorios import validar_relatorio

MESSAGES = {
    "authentication": "Entre novamente para consultar relatórios.",
    "authorization": "Relatórios disponíveis apenas para administradores.",
    "configuration": "O módulo de relatórios ainda não está configurado.",
    "unavailable": "Não foi possível consultar o serviço de relatórios.",
    "invalid": "O serviço retornou um relatório inválido.",
    "input": "Período recusado pelo serviço. Confira as datas.",
    "notfound": "O relatório ainda não está disponível no serviço.",
    "ratelimited": "O Xano atingiu o limite de requisições do plano. Aguarde alguns segundos e tente novamente.",
}


class ReportError(Exception):
    def __init__(self, category: str, retry_after: int | None = None):
        self.category = category if category in MESSAGES else "unavailable"
        self.retry_after = retry_after
        super().__init__(MESSAGES[self.category])


async def operational_report(token: str, from_ms: int, to_ms: int) -> dict:
    """Uma única leitura, sem retry automático; resposta validada antes do uso."""
    if type(from_ms) is not int or type(to_ms) is not int or not 0 < from_ms < to_ms:
        raise ReportError("input")
    try:
        data = await _request(token, "GET", "relatorios/operacional", params={"from": from_ms, "to": to_ms})
    except FineError as error:
        raise ReportError(error.category, error.retry_after) from None
    try:
        return validar_relatorio(data, from_ms, to_ms)
    except (ValueError, TypeError, KeyError):
        raise ReportError("invalid") from None
