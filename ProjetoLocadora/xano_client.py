import asyncio
import json
import logging
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from ProjetoLocadora.catalogo_filmes import Filme
from ProjetoLocadora.config import (
    get_xano_auth_api_url,
    get_xano_catalog_api_url,
)

logger = logging.getLogger(__name__)

GENERIC_AUTH_ERROR = "Credenciais inválidas ou conta sem acesso."
ALLOWED_ROLES = {"member", "admin"}
_WINDOWS = sys.platform == "win32"


class XanoCatalogError(Exception):
    """Falha explícita em uma operação do catálogo no Xano."""

    def __init__(self, message: str):
        super().__init__(message)
        self.user_message = message


class XanoAuditError(XanoCatalogError):
    """O Xano persistiu o filme, mas não confirmou o evento de auditoria."""


def _login_response_data(status_code: int, body: bytes) -> Optional[Dict[str, Any]]:
    if not 200 <= status_code < 300:
        logger.warning("Login Xano respondeu com status HTTP %s", status_code)
        return None

    try:
        data = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Login Xano retornou JSON inválido (HTTP %s)", status_code)
        return None

    if not isinstance(data, dict) or not data.get("authToken"):
        logger.warning(
            "Login Xano retornou payload sem authToken (HTTP %s)",
            status_code,
        )
        return None
    return data


async def _login_with_windows_curl(
    url: str,
    email: str,
    password: str,
) -> Optional[Dict[str, Any]]:
    curl_path = shutil.which("curl.exe")
    if not curl_path:
        logger.error("curl.exe não está disponível para o transporte TLS nativo do Windows.")
        return None

    command = [
        curl_path,
        "--disable",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "10",
        "--max-time",
        "10",
        "--request",
        "POST",
        "--header",
        "Content-Type: application/json",
        "--data-binary",
        "@-",
        "--write-out",
        "\n%{http_code}",
        f"{url}/auth/login",
    ]
    request_body = json.dumps(
        {"email": email.strip(), "password": password}
    ).encode("utf-8")

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            input=request_body,
            capture_output=True,
            timeout=11,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout no transporte TLS nativo do Windows durante o login Xano.")
        return None
    except OSError as err:
        logger.error(
            "Falha ao iniciar o transporte TLS nativo do Windows (%s)",
            type(err).__name__,
        )
        return None

    if result.returncode != 0:
        logger.warning(
            "Transporte TLS nativo do Windows falhou no login Xano (código %s)",
            result.returncode,
        )
        return None

    body, separator, status_text = result.stdout.rpartition(b"\n")
    if not separator or len(status_text) != 3 or not status_text.isdigit():
        logger.warning("Transporte TLS nativo retornou resposta incompleta no login Xano.")
        return None
    return _login_response_data(int(status_text), body)


def _catalog_endpoint(path: str) -> str:
    try:
        base_url = get_xano_catalog_api_url()
    except RuntimeError as err:
        raise XanoCatalogError(
            "A integração com o catálogo não está configurada."
        ) from err

    return f"{base_url}/catalogo-filmes/filmes{path}"


def _catalog_headers(auth_token: str) -> dict[str, str]:
    if not auth_token:
        raise XanoCatalogError("Sua sessão expirou. Entre novamente.")
    return {"Authorization": f"Bearer {auth_token}"}


def _curl_config_value(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


async def _catalog_request(
    method: str,
    path: str,
    auth_token: str,
    *,
    params: Optional[dict[str, str]] = None,
    json_body: Optional[dict[str, Any]] = None,
) -> httpx.Response:
    url = _catalog_endpoint(path)
    headers = _catalog_headers(auth_token)
    if params:
        url = str(httpx.URL(url, params=params))

    if not _WINDOWS:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.request(
                method,
                url,
                headers=headers,
                json=json_body,
            )

    curl_path = shutil.which("curl.exe")
    if not curl_path:
        raise httpx.ConnectError("curl.exe is unavailable for catalog transport.")

    config_lines = [
        f"url = {_curl_config_value(url)}",
        f"request = {_curl_config_value(method)}",
        f"header = {_curl_config_value('Authorization: ' + headers['Authorization'])}",
        f"header = {_curl_config_value('Content-Type: application/json')}",
    ]
    if json_body is not None:
        config_lines.append(
            f"data = {_curl_config_value(json.dumps(json_body, ensure_ascii=False))}"
        )
    config = ("\n".join(config_lines) + "\n").encode("utf-8")
    command = [
        curl_path,
        "--disable",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "10",
        "--max-time",
        "10",
        "--config",
        "-",
        "--write-out",
        (
            "\n__XANO_META__%{http_code}"
            "__XANO_REQUEST_ID__%header{x-request-id}"
            "__XANO_CORRELATION_ID__%header{x-correlation-id}"
            "__XANO_CF_RAY__%header{cf-ray}"
        ),
    ]
    request = httpx.Request(method, url, headers=headers, json=json_body)

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            input=config,
            capture_output=True,
            timeout=11,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        raise httpx.TimeoutException(
            "Catalog request exceeded its transport timeout.",
            request=request,
        ) from err
    except OSError as err:
        raise httpx.ConnectError(
            "Could not start the native Windows catalog transport.",
            request=request,
        ) from err

    body, separator, metadata = result.stdout.rpartition(b"\n__XANO_META__")
    if result.returncode != 0 or not separator:
        logger.warning(
            "Transporte nativo do catálogo falhou (código curl %s)",
            result.returncode,
        )
        raise httpx.ConnectError(
            "Native Windows catalog transport failed.",
            request=request,
        )
    status_text, request_metadata = metadata.split(b"__XANO_REQUEST_ID__", 1)
    if len(status_text) != 3 or not status_text.isdigit():
        raise httpx.ProtocolError(
            "Native Windows catalog transport returned an invalid status.",
            request=request,
        )

    response_headers = {}
    for marker, header_name in (
        (b"__XANO_CORRELATION_ID__", "x-request-id"),
        (b"__XANO_CF_RAY__", "x-correlation-id"),
    ):
        request_id, found, request_metadata = request_metadata.partition(marker)
        if not found:
            raise httpx.ProtocolError(
                "Native Windows catalog transport returned incomplete metadata.",
                request=request,
            )
        value = request_id.decode("ascii", errors="ignore").strip()
        if value and all(char.isalnum() or char in "-_.:" for char in value):
            response_headers[header_name] = value[:128]

    value = request_metadata.decode("ascii", errors="ignore").strip()
    if value and all(char.isalnum() or char in "-_.:" for char in value):
        response_headers["cf-ray"] = value[:128]

    return httpx.Response(
        int(status_text),
        content=body,
        headers=response_headers,
        request=request,
    )


def _raise_catalog_http_error(
    response: httpx.Response,
    *,
    film_not_found: bool = False,
    operation: str = "catalog operation",
) -> None:
    if response.is_success:
        return

    if response.status_code in (401, 403):
        message = "Você não tem permissão para realizar esta operação."
    elif response.status_code == 404 and film_not_found:
        message = "Filme não encontrado."
    elif response.status_code == 404:
        message = "Rota do catálogo não encontrada."
    elif response.status_code in (400, 422):
        message = "Os dados enviados não foram aceitos pelo catálogo."
    elif response.status_code >= 500:
        request_id = (
            response.headers.get("x-request-id")
            or response.headers.get("x-correlation-id")
            or response.headers.get("cf-ray", "")
        )
        message = (
            f"O Xano retornou erro interno ao executar {operation} "
            f"(HTTP {response.status_code})."
        )
        if request_id:
            message += f" Referência: {request_id}."
        logger.error(
            "Erro interno do Xano (operação=%s; HTTP=%s; request_id=%s)",
            operation,
            response.status_code,
            request_id or "unavailable",
        )
        raise XanoCatalogError(message)
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
        response = await _catalog_request(
            "GET",
            "",
            auth_token,
            params=params,
        )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consultar o catálogo: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível consultar os filmes no Xano.") from err

    _raise_catalog_http_error(response, operation="GET catalogo-filmes/filmes")
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
        response = await _catalog_request(
            "GET",
            f"/{quote(str(film_id), safe='')}",
            auth_token,
        )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao consultar um filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível carregar o filme no Xano.") from err

    _raise_catalog_http_error(
        response,
        film_not_found=True,
        operation="GET catalogo-filmes/filmes/{id}",
    )
    return _film_response(response)


async def create_film_xano(auth_token: str, data: dict[str, Any]) -> Filme:
    try:
        response = await _catalog_request(
            "POST",
            "",
            auth_token,
            json_body=data,
        )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao cadastrar filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível cadastrar o filme no Xano.") from err

    _raise_catalog_http_error(response, operation="POST catalogo-filmes/filmes")
    return _write_film_response(response)


async def update_film_xano(
    auth_token: str, film_id: int, data: dict[str, Any]
) -> Filme:
    try:
        response = await _catalog_request(
            "PATCH",
            f"/{quote(str(film_id), safe='')}",
            auth_token,
            json_body=data,
        )
    except httpx.HTTPError as err:
        logger.warning("Falha de rede ao editar filme: %s", type(err).__name__)
        raise XanoCatalogError("Não foi possível editar o filme no Xano.") from err

    _raise_catalog_http_error(
        response,
        film_not_found=True,
        operation="PATCH catalogo-filmes/filmes/{id}",
    )
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
        url = (base_url or get_xano_auth_api_url()).rstrip("/")
    except RuntimeError as err:
        logger.error("Erro ao obter URL da API Xano: %s", err)
        return None

    if _WINDOWS:
        return await _login_with_windows_curl(url, email, password)

    try:
        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(
            timeout=10.0,
            transport=transport,
        ) as client:
            response = await client.post(
                f"{url}/auth/login",
                json={"email": email.strip(), "password": password},
            )
        return _login_response_data(response.status_code, response.content)
    except httpx.ConnectTimeout as err:
        cause_type = type(err.__cause__).__name__ if err.__cause__ else "unknown"
        logger.warning(
            "Timeout na fase de conexão TCP/TLS com a API Xano no login "
            "(ConnectTimeout; causa=%s)",
            cause_type,
        )
        return None
    except httpx.ReadTimeout as err:
        cause_type = type(err.__cause__).__name__ if err.__cause__ else "unknown"
        logger.warning(
            "Timeout aguardando resposta da API Xano no login "
            "(ReadTimeout; causa=%s)",
            cause_type,
        )
        return None
    except httpx.HTTPError as err:
        cause_type = type(err.__cause__).__name__ if err.__cause__ else "unknown"
        logger.warning(
            "Falha HTTP de rede no login Xano (%s; causa=%s)",
            type(err).__name__,
            cause_type,
        )
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
        url = (base_url or get_xano_auth_api_url()).rstrip("/")
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
        url = (base_url or get_xano_auth_api_url()).rstrip("/")
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
        url = (base_url or get_xano_auth_api_url()).rstrip("/")
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
        url = (base_url or get_xano_auth_api_url()).rstrip("/")
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
