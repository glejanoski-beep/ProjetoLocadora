
import os
import ipaddress
import re
from pathlib import Path
from urllib.parse import urlsplit

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


def get_xano_exemplar_api_url() -> str:
    exemplar_url = _required_url("XANO_EXEMPLAR_API_URL")
    reserved_urls = {
        get_xano_auth_api_url(): "Authentication",
        get_xano_catalog_api_url(): "Catálogo de Filmes",
        get_xano_customer_api_url(): "Clientes",
    }
    if exemplar_url in reserved_urls:
        raise RuntimeError(
            "XANO_EXEMPLAR_API_URL deve apontar para o grupo Exemplares, "
            f"não para o grupo {reserved_urls[exemplar_url]}."
        )
    return exemplar_url


def get_xano_dashboard_api_url() -> str:
    """Retorna a base do grupo Dashboard, sem o caminho do endpoint."""
    dashboard_url = _required_url("XANO_DASHBOARD_API_URL")
    valid = False
    try:
        parsed = urlsplit(dashboard_url)
        hostname = parsed.hostname or ""
        port = parsed.port
        if ":" in hostname:
            ipaddress.IPv6Address(hostname)
            host_valid = "%" not in hostname
        else:
            ascii_host = hostname.encode("idna").decode("ascii").rstrip(".")
            labels = ascii_host.split(".")
            host_valid = bool(ascii_host) and len(ascii_host) <= 253 and all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in labels
            )
            if ascii_host and all(c in "0123456789." for c in ascii_host):
                ipaddress.IPv4Address(ascii_host)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.netloc)
            and host_valid
            and parsed.username is None
            and parsed.password is None
            and "?" not in dashboard_url
            and "#" not in dashboard_url
            and "\\" not in dashboard_url
            and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in dashboard_url)
            and (port is None or port > 0)
            and not parsed.netloc.endswith(":")
        )
    except (ValueError, UnicodeError):
        pass
    if not valid:
        raise RuntimeError(
            "XANO_DASHBOARD_API_URL deve ser uma URL HTTPS com hostname válido, "
            "sem credenciais, query string ou fragmento."
        )
    if dashboard_url.endswith(("/dashboard", "/dashboard/resumo-acervo")):
        raise RuntimeError(
            "XANO_DASHBOARD_API_URL deve conter somente a base do grupo, "
            "sem o caminho dashboard/resumo-acervo."
        )
    return dashboard_url


def get_frontend_base_url() -> str:
    return (
        os.getenv("FRONTEND_BASE_URL") or "http://localhost:3000"
    ).strip().rstrip("/")
