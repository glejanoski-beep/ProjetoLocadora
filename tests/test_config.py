import os
import unittest
from unittest.mock import patch

from ProjetoLocadora.config import get_xano_api_url


class TestConfig(unittest.TestCase):
    def test_get_xano_api_url_success(self):
        with patch.dict(os.environ, {"XANO_API_URL": "https://example.com/api/"}):
            self.assertEqual(get_xano_api_url(), "https://example.com/api")

    def test_get_xano_api_url_fallback(self):
        with patch.dict(os.environ, {"XANO_API_URL": "", "XANO_API_BASE_URL": "https://fallback.com/api"}):
            self.assertEqual(get_xano_api_url(), "https://fallback.com/api")

    def test_get_xano_api_url_missing_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_xano_api_url()
            self.assertIn("XANO_API_URL não configurada", str(ctx.exception))

    def test_get_xano_api_url_whitespace_raises_error(self):
        with patch.dict(os.environ, {"XANO_API_URL": "   ", "XANO_API_BASE_URL": ""}):
            with self.assertRaises(RuntimeError) as ctx:
                get_xano_api_url()
            self.assertIn("XANO_API_URL não configurada", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
