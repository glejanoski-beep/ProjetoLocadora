import logging
from typing import Any, Dict, Optional
import httpx

from ProjetoLocadora.config import get_xano_api_url

logger = logging.getLogger(__name__)

GENERIC_AUTH_ERROR = "Credenciais inválidas ou conta sem acesso."
ALLOWED_ROLES = {"member", "admin"}


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
