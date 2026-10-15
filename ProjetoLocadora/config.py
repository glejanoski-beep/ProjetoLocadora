
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _load_project_environment(dotenv_path: Path = PROJECT_ENV_PATH) -> None:
    """Carrega a configuração local como fonte de verdade da aplicação."""
    load_dotenv(dotenv_path=dotenv_path, override=True)


def _required_url(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value or not value.strip():
        raise RuntimeError(f"Variável {variable_name} não configurada.")
    return value.strip().rstrip("/")


_load_project_environment()


def get_xano_auth_api_url() -> str:
    return _required_url("XANO_AUTH_API_URL")


def get_xano_catalog_api_url() -> str:
    catalog_url = _required_url("XANO_CATALOG_API_URL")
    if catalog_url == get_xano_auth_api_url():
        raise RuntimeError(
            "XANO_CATALOG_API_URL deve apontar para o grupo Catálogo de Filmes, "
            "não para o grupo Authentication."
        )
    return catalog_url


def get_xano_customer_api_url() -> str:
    customer_url = _required_url("XANO_CUSTOMER_API_URL")
    reserved_urls = {
        get_xano_auth_api_url(): "Authentication",
        get_xano_catalog_api_url(): "Catálogo de Filmes",
    }
    if customer_url in reserved_urls:
        raise RuntimeError(
            "XANO_CUSTOMER_API_URL deve apontar para o grupo Clientes, "
            f"não para o grupo {reserved_urls[customer_url]}."
        )
    return customer_url


def get_frontend_base_url() -> str:
    return (
        os.getenv("FRONTEND_BASE_URL") or "http://localhost:3000"
    ).strip().rstrip("/")
