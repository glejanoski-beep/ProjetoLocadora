import os
from typing import Optional


def get_xano_api_url() -> str:
    """Retorna a URL base da API Xano a partir de variável de ambiente.

    Verifica prioritariamente XANO_API_URL e alternativamente XANO_API_BASE_URL.

    Raises:
        RuntimeError: Caso nenhuma variável de ambiente esteja configurada ou esteja vazia.
    """
    url: Optional[str] = os.getenv("XANO_API_URL") or os.getenv("XANO_API_BASE_URL")
    if not url or not url.strip():
        raise RuntimeError("Variável de ambiente XANO_API_URL não configurada.")
    return url.strip().rstrip("/")
