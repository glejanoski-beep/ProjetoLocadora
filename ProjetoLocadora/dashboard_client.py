"""Contrato e transporte servidor–Xano da Dashboard, independentes do Reflex."""

from datetime import datetime
from enum import Enum
import json
import re
from typing import TypedDict

import httpx

from ProjetoLocadora.config import get_xano_dashboard_api_url


class DashboardSummary(TypedDict):
    total_filmes: int
    total_exemplares: int
    generated_at: str


class DashboardErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    SERVICE = "service"
    INVALID_RESPONSE = "invalid_response"
    UNEXPECTED_STATUS = "unexpected_status"
    CONFIGURATION = "configuration"


_MESSAGES = {
    DashboardErrorCategory.AUTHENTICATION: "Sessão necessária para consultar o resumo do acervo.",
    DashboardErrorCategory.AUTHORIZATION: "Sem permissão para consultar o resumo do acervo.",
    DashboardErrorCategory.CONNECTION: "Não foi possível conectar ao serviço de resumo do acervo.",
    DashboardErrorCategory.TIMEOUT: "O serviço de resumo do acervo não respondeu a tempo.",
    DashboardErrorCategory.SERVICE: "O serviço de resumo do acervo está indisponível.",
    DashboardErrorCategory.INVALID_RESPONSE: "O serviço retornou um resumo do acervo inválido.",
    DashboardErrorCategory.UNEXPECTED_STATUS: "O serviço retornou um status inesperado ao consultar o acervo.",
    DashboardErrorCategory.CONFIGURATION: "A integração com o resumo do acervo não está configurada corretamente.",
}


class XanoDashboardError(Exception):
    """Erro com categoria e mensagem fixas, sem anexar objetos HTTP ou payloads."""

    def __init__(self, category: DashboardErrorCategory):
        self.category = category
        super().__init__(_MESSAGES[category])


_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z"
)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Campo duplicado")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Constante JSON inválida")


def _validated_summary(content: bytes) -> DashboardSummary | None:
    """Valida integralmente sem coerção; erros de parsing não saem desta função."""
    try:
        payload = json.loads(
            content.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if type(payload) is not dict or set(payload) != {
            "total_filmes", "total_exemplares", "generated_at",
        }:
            return None
        for key in ("total_filmes", "total_exemplares"):
            if type(payload[key]) is not int or payload[key] < 0:
                return None
        timestamp = payload["generated_at"]
        if not isinstance(timestamp, str) or not _TIMESTAMP.fullmatch(timestamp):
            return None
        # Verifica calendário e limites reais de hora/minuto/segundo, sem
        # converter nem truncar a fração de segundo recebida no contrato.
        datetime.strptime(timestamp[:19], "%Y-%m-%dT%H:%M:%S")
        return DashboardSummary(
            total_filmes=payload["total_filmes"],
            total_exemplares=payload["total_exemplares"],
            generated_at=timestamp,
        )
    except (ValueError, UnicodeError, RecursionError):
        return None


async def get_dashboard_summary_xano(auth_token: str) -> DashboardSummary:
    """Consulta e retorna somente um resumo integralmente validado, no servidor.

    Não persiste credenciais/respostas, não segue redirects e não faz retry.
    Nenhuma falha é convertida em totais presumidos ou resultado parcial.
    """
    if not auth_token:
        raise XanoDashboardError(DashboardErrorCategory.AUTHENTICATION)

    category = None
    try:
        base_url = get_xano_dashboard_api_url()
    except (RuntimeError, ValueError):
        category = DashboardErrorCategory.CONFIGURATION
    if category is not None:
        raise XanoDashboardError(category)

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(
                f"{base_url}/dashboard/resumo-acervo",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
    except httpx.TimeoutException:
        category = DashboardErrorCategory.TIMEOUT
    except httpx.RequestError:
        category = DashboardErrorCategory.CONNECTION
    except (httpx.HTTPError, ValueError):
        category = DashboardErrorCategory.CONNECTION
    # Fora dos except para não manter a exceção original como contexto.
    if category is not None:
        raise XanoDashboardError(category)

    status = response.status_code
    if status == 401:
        raise XanoDashboardError(DashboardErrorCategory.AUTHENTICATION)
    if status == 403:
        raise XanoDashboardError(DashboardErrorCategory.AUTHORIZATION)
    if 500 <= status <= 599:
        raise XanoDashboardError(DashboardErrorCategory.SERVICE)
    if status != 200:
        raise XanoDashboardError(DashboardErrorCategory.UNEXPECTED_STATUS)

    summary = _validated_summary(response.content)
    if summary is None:
        raise XanoDashboardError(DashboardErrorCategory.INVALID_RESPONSE)
    return summary
