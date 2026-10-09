import os
import unittest
from unittest.mock import patch

from ProjetoLocadora.config import (
    get_frontend_base_url,
    get_xano_auth_api_url,
    get_xano_catalog_api_url,
)


class TestConfig(unittest.TestCase):
    def test_get_xano_auth_api_url_uses_auth_setting(self):
        with patch.dict(
            os.environ,
            {
                "XANO_AUTH_API_URL": "https://auth.example/api/",
                "XANO_CATALOG_API_URL": "https://catalog.example/api",
            },
        ):
            self.assertEqual(
                get_xano_auth_api_url(),
                "https://auth.example/api",
            )

    def test_get_xano_catalog_api_url_uses_catalog_setting(self):
        with patch.dict(
            os.environ,
            {
                "XANO_AUTH_API_URL": "https://auth.example/api",
                "XANO_CATALOG_API_URL": "https://catalog.example/api/",
            },
        ):
            self.assertEqual(
                get_xano_catalog_api_url(),
                "https://catalog.example/api",
            )

    def test_get_xano_auth_api_url_missing_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_xano_auth_api_url()
            self.assertIn("XANO_AUTH_API_URL não configurada", str(ctx.exception))

    def test_get_xano_catalog_api_url_missing_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_xano_catalog_api_url()
            self.assertIn("XANO_CATALOG_API_URL não configurada", str(ctx.exception))

    def test_xano_auth_and_catalog_settings_are_independent(self):
        with patch.dict(
            os.environ,
            {
                "XANO_AUTH_API_URL": "https://auth.example/api",
                "XANO_CATALOG_API_URL": "",
            },
        ):
            self.assertEqual(
                get_xano_auth_api_url(),
                "https://auth.example/api",
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "XANO_CATALOG_API_URL não configurada",
            ):
                get_xano_catalog_api_url()

    def test_get_frontend_base_url_defaults_to_localhost(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_frontend_base_url(), "http://localhost:3000")

    def test_get_frontend_base_url_uses_environment(self):
        with patch.dict(os.environ, {"FRONTEND_BASE_URL": "https://app.example/"}):
            self.assertEqual(get_frontend_base_url(), "https://app.example")


if __name__ == "__main__":
    unittest.main()
