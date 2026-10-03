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
