import logging
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from ProjetoLocadora.catalogo_filmes import Filme
from ProjetoLocadora.config import get_xano_api_url

logger = logging.getLogger(__name__)

GENERIC_AUTH_ERROR = "Credenciais inválidas ou conta sem acesso."
ALLOWED_ROLES = {"member", "admin"}


class XanoCatalogError(Exception):
    """Falha explícita em uma operação do catálogo no Xano."""

    def __init__(self, message: str):
        super().__init__(message)
        self.user_message = message


class XanoAuditError(XanoCatalogError):
    """O Xano persistiu o filme, mas não confirmou o evento de auditoria."""


def _catalog_endpoint(path: str) -> str:
    try:
        base_url = get_xano_api_url().rstrip("/")
    except RuntimeError as err:
        raise XanoCatalogError("A integração com o catálogo não está configurada.") from err
    return f"{base_url}/catalogo-filmes/filmes{path}"


def _catalog_headers(auth_token: str) -> dict[str, str]:
    if not auth_token:
        raise XanoCatalogError("Sua sessão expirou. Entre novamente.")
    return {"Authorization": f"Bearer {auth_token}"}


def _raise_catalog_http_error(response: httpx.Response) -> None:
    if response.is_success:
        return

    if response.status_code in (401, 403):
        message = "Você não tem permissão para realizar esta operação."
    elif response.status_code == 404:
        message = "Filme não encontrado."
    elif response.status_code in (400, 422):
        message = "Os dados enviados não foram aceitos pelo catálogo."
    else:
        message = "Não foi possível concluir a operação no catálogo."
    logger.warning("Operação do catálogo recusada pelo Xano (HTTP %s)", response.status_code)
    raise XanoCatalogError(message)


def _is_film(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("id"), int)
        and isinstance(value.get("titulo"), str)
        and isinstance(value.get("genero"), str)
        and isinstance(value.get("ano_lancamento"), int)
        and isinstance(value.get("classificacao"), str)
        and isinstance(value.get("valor_locacao_centavos"), int)
        and isinstance(value.get("status"), str)
    )


def _film_response(response: httpx.Response) -> Filme:
    try:
        film = response.json()
    except ValueError as err:
        raise XanoCatalogError("O Xano retornou uma resposta inválida para o filme.") from err
    if not _is_film(film):
        raise XanoCatalogError("O Xano retornou uma resposta inválida para o filme.")
    return film


def _write_film_response(response: httpx.Response) -> Filme:
    try:
        result = response.json()
    except ValueError as err:
        raise XanoCatalogError("O Xano retornou uma resposta inválida para o filme.") from err

    if (
        isinstance(result, dict)
        and result.get("audit_succeeded") is False
        and _is_film(result.get("film"))
    ):
        raise XanoAuditError(
            "O filme foi gravado, mas a auditoria não foi concluída. "
            "Não repita a operação; confirme o estado do catálogo antes de tentar novamente."
        )
    if (
        not isinstance(result, dict)
        or result.get("audit_succeeded") is not True
        or not _is_film(result.get("film"))
    ):
        raise XanoCatalogError("O Xano retornou uma resposta inválida para a gravação do filme.")
    return result["film"]


async def list_films_xano(
    auth_token: str,
    *,
    titulo: str = "",
    genero: str = "",
) -> list[Filme]:
    params = {}
    if titulo.strip():
        params["titulo"] = titulo.strip()
    if genero.strip():
        params["genero"] = genero.strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                _catalog_endpoint(""),
                headers=_catalog_headers(auth_token),
                params=params,
            )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consultar o catálogo: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível consultar os filmes no Xano.") from err

    _raise_catalog_http_error(response)
    try:
        films = response.json()
    except ValueError as err:
        raise XanoCatalogError("O Xano retornou uma lista de filmes inválida.") from err
    if not isinstance(films, list) or any(
        not _is_film(film)
        for film in films
    ):
        raise XanoCatalogError("O Xano retornou uma lista de filmes inválida.")
    return films


async def get_film_xano(auth_token: str, film_id: int) -> Filme:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                _catalog_endpoint(f"/{quote(str(film_id), safe='')}"),
                headers=_catalog_headers(auth_token),
            )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consultar um filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível carregar o filme no Xano.") from err

    _raise_catalog_http_error(response)
    return _film_response(response)


async def create_film_xano(auth_token: str, data: dict[str, Any]) -> Filme:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _catalog_endpoint(""),
                headers=_catalog_headers(auth_token),
                json=data,
            )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao cadastrar filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível cadastrar o filme no Xano.") from err

    _raise_catalog_http_error(response)
    return _write_film_response(response)


async def update_film_xano(
    auth_token: str, film_id: int, data: dict[str, Any]
) -> Filme:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                _catalog_endpoint(f"/{quote(str(film_id), safe='')}"),
                headers=_catalog_headers(auth_token),
                json=data,
            )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao editar filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível editar o filme no Xano.") from err

    _raise_catalog_http_error(response)
    return _write_film_response(response)


def is_authorized_employee(me_data: Optional[Dict[str, Any]]) -> bool:
    """Verifica se os dados do usuário correspondem a um funcionário ativo com papel permitido."""
    if not me_data or not isinstance(me_data, dict):
        return False
    
    is_active = me_data.get("is_active")
    # Caso is_active seja explicitamente False, nega o acesso
    if is_active is False:
        return False
        
    role = me_data.get("role")
    if role not in ALLOWED_ROLES:
        return False

    return True


async def login_xano(
    email: str, password: str, base_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Envia credenciais ao endpoint POST /auth/login do Xano.

    Retorna o payload JSON com 'authToken' e 'user_id' em caso de sucesso, ou None se falhar.
    """
    if not email or not password:
        return None

    try:
        url = (base_url or get_xano_api_url()).rstrip("/")
    except RuntimeError as err:
        logger.error("Erro ao obter URL da API Xano: %s", err)
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{url}/auth/login",
                json={"email": email.strip(), "password": password},
            )
            if response.status_code == 200:
                data = response.json()
                if "authToken" in data:
                    return data
            return None
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao conectar à API Xano no login: %s", type(err).__name__)
        return None
    except Exception as err:
        logger.error("Erro inesperado na chamada de login Xano: %s", type(err).__name__)
        return None


async def get_me_xano(
    auth_token: str, base_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Consulta a identidade autenticada no endpoint GET /auth/me do Xano.

    Retorna o dicionário com os dados do usuário ou None se a requisição falhar/expirar.
    """
    if not auth_token:
        return None

    try:
        url = (base_url or get_xano_api_url()).rstrip("/")
    except RuntimeError as err:
        logger.error("Erro ao obter URL da API Xano: %s", err)
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{url}/auth/me",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            if response.status_code == 200:
                return response.json()
            return None
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consultar auth/me no Xano: %s", type(err).__name__)
        return None
    except Exception as err:
        logger.error("Erro inesperado ao consultar auth/me no Xano: %s", type(err).__name__)
        return None


async def request_password_reset(email: str, base_url: Optional[str] = None) -> bool:
    """Solicita um magic link sem revelar se o e-mail existe."""
    if not email:
        return False

    try:
        url = (base_url or get_xano_api_url()).rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{url}/reset/request-reset-link",
                params={"email": email.strip()},
            )
        return response.status_code == 200
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao solicitar recuperação: %s", type(err).__name__)
        return False
    except Exception as err:
        logger.error("Erro inesperado ao solicitar recuperação: %s", type(err).__name__)
        return False


async def consume_password_reset_token(
    magic_token: str, email: str, base_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Consome o magic link e retorna apenas o payload necessário ao fluxo privado."""
    if not magic_token or not email:
        return None

    try:
        url = (base_url or get_xano_api_url()).rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{url}/reset/magic-link-login",
                json={"magic_token": magic_token, "email": email.strip()},
            )
        if response.status_code == 200:
            payload = response.json()
            if payload.get("authToken"):
                return payload
        return None
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consumir magic link: %s", type(err).__name__)
        return None
    except Exception as err:
        logger.error("Erro inesperado ao consumir magic link: %s", type(err).__name__)
        return None


async def update_password_xano(
    auth_token: str,
    password: str,
    confirm_password: str,
    base_url: Optional[str] = None,
) -> bool:
    """Atualiza a senha usando o token privado retornado pelo magic link."""
    if not auth_token or not password or password != confirm_password:
        return False

    try:
        url = (base_url or get_xano_api_url()).rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{url}/reset/update_password",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"password": password, "confirm_password": confirm_password},
            )
        return response.status_code == 200
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao atualizar senha: %s", type(err).__name__)
        return False
    except Exception as err:
        logger.error("Erro inesperado ao atualizar senha: %s", type(err).__name__)
        return False
