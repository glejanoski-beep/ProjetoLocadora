
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def get_xano_auth_api_url() -> str:
    url = os.getenv("XANO_AUTH_API_URL")
    if not url or not url.strip():
        raise RuntimeError("Variável XANO_AUTH_API_URL não configurada.")
    return url.strip().rstrip("/")


def get_xano_catalog_api_url() -> str:
    url = os.getenv("XANO_CATALOG_API_URL")
    if not url or not url.strip():
        raise RuntimeError("Variável XANO_CATALOG_API_URL não configurada.")
    return url.strip().rstrip("/")


def get_frontend_base_url() -> str:
    return (
        os.getenv("FRONTEND_BASE_URL") or "http://localhost:3000"
    ).strip().rstrip("/")
