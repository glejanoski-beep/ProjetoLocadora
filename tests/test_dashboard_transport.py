"""Testes locais: MockTransport não realiza conexões ao Xano."""

import os
import json
import traceback
import unittest
from unittest.mock import patch

import httpx

from ProjetoLocadora.config import get_xano_dashboard_api_url
from ProjetoLocadora.dashboard_client import (
    DashboardErrorCategory, XanoDashboardError, get_dashboard_summary_xano,
)


INVALID_DASHBOARD_URLS = (
    "http://example.test/api:group", "example.test/api:group",
    "https:///api:group", "https://", "https://bad host/api:group",
    "https://-bad.test/api:group", "https://bad_.test/api:group",
    "https://example..test/api:group", "https://999.999.999.999/api:group",
    "https://[invalid]/api:group", "https://example.test:invalid/api:group",
    "https://example.test:65536/api:group", "https://example.test:/api:group",
    "https://user:password@example.test/api:group", "https://user@example.test/api:group",
    "https://@example.test/api:group", "https://example.test/api:group?",
    "https://example.test/api:group?token=synthetic", "https://example.test/api:group#",
    "https://example.test/api:group#fragment", "https://exam\nple.test/api:group",
    "https://example.test\\other/api:group",
)


class TestDashboardConfig(unittest.TestCase):
    def test_rejects_insecure_or_malformed_urls_without_echoing_them(self):
        for url in INVALID_DASHBOARD_URLS:
            with self.subTest(url=url), patch.dict(os.environ, {"XANO_DASHBOARD_API_URL": url}):
                with self.assertRaises(RuntimeError) as caught:
                    get_xano_dashboard_api_url()
                self.assertNotIn(url, str(caught.exception))

    def test_accepts_https_group_bases_with_valid_hosts(self):
        for url in ("https://example.test/api:group", "https://example.test:443/api:group",
                    "https://127.0.0.1/api:group", "https://[::1]/api:group"):
            with self.subTest(url=url), patch.dict(os.environ, {"XANO_DASHBOARD_API_URL": url + "/"}):
                self.assertEqual(get_xano_dashboard_api_url(), url)

    def test_requires_explicit_group_url_and_normalizes_slash(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "XANO_DASHBOARD_API_URL"):
                get_xano_dashboard_api_url()
        with patch.dict(os.environ, {"XANO_DASHBOARD_API_URL": " https://example.test/api:group/ "}):
            self.assertEqual(get_xano_dashboard_api_url(), "https://example.test/api:group")

    def test_rejects_base_that_would_duplicate_route_prefix(self):
        for suffix in ("/dashboard", "/dashboard/resumo-acervo/"):
            with self.subTest(suffix=suffix), patch.dict(
                os.environ, {"XANO_DASHBOARD_API_URL": "https://example.test/api:group" + suffix},
            ):
                with self.assertRaises(RuntimeError):
                    get_xano_dashboard_api_url()


class TestDashboardTransport(unittest.IsolatedAsyncioTestCase):
    async def request_mocked_response(self, response):
        token = "synthetic-token"
        with patch.dict(os.environ, {
            "XANO_DASHBOARD_API_URL": "https://example.test/api:group",
        }), self.mock_client(lambda request: response):
            return await get_dashboard_summary_xano(token)

    async def assert_safe_error(self, response, category):
        with self.assertNoLogs(level="WARNING"):
            try:
                await self.request_mocked_response(response)
            except XanoDashboardError as error:
                self.assertEqual(error.category, category)
                self.assertIsNone(error.__context__)
                self.assertIsNone(error.__cause__)
                rendered = str(error) + repr(error) + "".join(traceback.format_exception(error))
                for secret in ("synthetic-token", "sensitive-body", "example.test", "Authorization"):
                    self.assertNotIn(secret, rendered)
            else:
                self.fail("Resposta inválida/status de erro não pode retornar resumo")

    async def test_accepts_exact_counts_zero_and_real_utc_dates(self):
        for films, copies in ((3, 5), (1, 0), (0, 0), (10**30, 10**30)):
            for timestamp in ("2026-10-18T15:00:00Z", "2024-02-29T23:59:59.123456789Z"):
                payload = {"total_filmes": films, "total_exemplares": copies, "generated_at": timestamp}
                with self.subTest(payload=payload):
                    self.assertEqual(await self.request_mocked_response(
                        httpx.Response(200, json=payload),
                    ), payload)

    async def test_rejects_invalid_totals_without_coercion(self):
        for key in ("total_filmes", "total_exemplares"):
            for value in (-1, True, False, 1.0, 1.5, "3", None, [], {}):
                payload = {"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-18T15:00:00Z"}
                payload[key] = value
                with self.subTest(key=key, value=value):
                    await self.assert_safe_error(httpx.Response(200, json=payload), DashboardErrorCategory.INVALID_RESPONSE)

    async def test_rejects_invalid_structure_missing_extra_and_duplicate_fields(self):
        valid = {"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-18T15:00:00Z"}
        payloads = [None, [], [valid], True, 3, "sensitive-body", {}, {**valid, "extra": "sensitive-body"}]
        payloads += [{k: v for k, v in valid.items() if k != missing} for missing in valid]
        for payload in payloads:
            with self.subTest(payload=payload):
                await self.assert_safe_error(
                    httpx.Response(200, content=json.dumps(payload).encode()), DashboardErrorCategory.INVALID_RESPONSE,
                )
        for content in (b"", b"sensitive-body", b"{", b"\xff", b'{"total_filmes":NaN}',
                        b'{"total_filmes":Infinity}',
                        b'{"total_filmes":3,"total_filmes":4,"total_exemplares":5,"generated_at":"2026-10-18T15:00:00Z"}'):
            with self.subTest(content=content):
                await self.assert_safe_error(httpx.Response(200, content=content), DashboardErrorCategory.INVALID_RESPONSE)

    async def test_rejects_invalid_or_non_utc_timestamps(self):
        for timestamp in (
            None, 0, True, "", "2026-10-18", "2026-10-18T15:00:00",
            "2026-10-18T15:00:00+00:00", "2026-10-18T15:00:00-03:00",
            "2026-02-29T15:00:00Z", "2026-13-01T15:00:00Z",
            "2026-04-31T15:00:00Z", "2026-10-18T24:00:00Z",
            "2026-10-18T15:60:00Z", "2026-10-18T15:00:61Z",
            "0000-01-01T00:00:00Z", "2026-10-18 15:00:00Z",
            "2026-10-18T15:00:00.Z", "2026-10-18T15:00:00Z\n",
        ):
            with self.subTest(timestamp=timestamp):
                await self.assert_safe_error(httpx.Response(200, json={
                    "total_filmes": 3, "total_exemplares": 5, "generated_at": timestamp,
                }), DashboardErrorCategory.INVALID_RESPONSE)

    async def test_http_status_categories_ignore_error_payloads(self):
        for status, category in (
            (401, DashboardErrorCategory.AUTHENTICATION),
            (403, DashboardErrorCategory.AUTHORIZATION),
            (500, DashboardErrorCategory.SERVICE), (503, DashboardErrorCategory.SERVICE),
            (599, DashboardErrorCategory.SERVICE),
            *[(status, DashboardErrorCategory.UNEXPECTED_STATUS) for status in (201, 204, 301, 302, 400, 404, 429)],
        ):
            with self.subTest(status=status):
                await self.assert_safe_error(httpx.Response(status, text="sensitive-body"), category)

    async def test_connection_and_timeout_have_distinct_sanitized_categories(self):
        for kind, category in (
            (httpx.ConnectError, DashboardErrorCategory.CONNECTION),
            (httpx.RemoteProtocolError, DashboardErrorCategory.CONNECTION),
            (httpx.ConnectTimeout, DashboardErrorCategory.TIMEOUT),
            (httpx.ReadTimeout, DashboardErrorCategory.TIMEOUT),
            (httpx.PoolTimeout, DashboardErrorCategory.TIMEOUT),
        ):
            def handler(request):
                raise kind("sensitive-body synthetic-token", request=request)

            with self.subTest(kind=kind), patch.dict(os.environ, {
                "XANO_DASHBOARD_API_URL": "https://example.test/api:group",
            }), self.mock_client(handler), self.assertNoLogs(level="WARNING"):
                try:
                    await get_dashboard_summary_xano("synthetic-token")
                except XanoDashboardError as error:
                    self.assertEqual(error.category, category)
                    self.assertIsNone(error.__context__)
                    self.assertIsNone(error.__cause__)
                    self.assertNotIn("sensitive-body", "".join(traceback.format_exception(error)))
                    self.assertNotIn("synthetic-token", str(error))
                else:
                    self.fail("Falha de transporte deve interromper a consulta")

    async def test_invalid_url_is_rejected_before_http_client_creation(self):
        for url in INVALID_DASHBOARD_URLS:
            with self.subTest(url=url), patch.dict(
                os.environ, {"XANO_DASHBOARD_API_URL": url},
            ), patch("ProjetoLocadora.dashboard_client.httpx.AsyncClient") as client:
                with self.assertRaises(XanoDashboardError):
                    await get_dashboard_summary_xano("synthetic-token")
                client.assert_not_called()

    def mock_client(self, handler):
        original = httpx.AsyncClient
        return patch(
            "ProjetoLocadora.dashboard_client.httpx.AsyncClient",
            side_effect=lambda **kwargs: original(
                transport=httpx.MockTransport(handler), **kwargs,
            ),
        )

    async def test_get_uses_group_base_bearer_and_ten_second_timeout(self):
        requests = []
        payload = b'{"total_filmes":3,"total_exemplares":5,"generated_at":"2026-10-18T15:00:00Z"}'

        def handler(request):
            requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url), "https://example.test/api:group/dashboard/resumo-acervo")
            self.assertEqual(request.headers["Authorization"], "Bearer private-token")
            self.assertEqual(request.extensions["timeout"], {
                "connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0,
            })
            self.assertEqual(request.content, b"")
            return httpx.Response(200, content=payload)

        with patch.dict(os.environ, {"XANO_DASHBOARD_API_URL": "https://example.test/api:group/"}), self.mock_client(handler):
            result = await get_dashboard_summary_xano("private-token")
        self.assertEqual(result, json.loads(payload))
        self.assertEqual(len(requests), 1)

    async def test_errors_do_not_leak_token_body_or_original_exception(self):
        secret = "private-test-secret"

        def failure(request):
            raise httpx.ReadTimeout(secret, request=request)

        for handler in (failure, lambda request: httpx.Response(403, text=secret)):
            with self.subTest(handler=handler), patch.dict(
                os.environ, {"XANO_DASHBOARD_API_URL": "https://example.test/api:group"},
            ), self.mock_client(handler), self.assertNoLogs(level="WARNING"):
                try:
                    await get_dashboard_summary_xano(secret)
                except XanoDashboardError as error:
                    self.assertNotIn(secret, str(error))
                    self.assertNotIn(secret, repr(error))
                    self.assertNotIn(secret, "".join(traceback.format_exception(error)))
                    self.assertIsNone(error.__cause__)
                    self.assertIsNone(error.__context__)
                else:
                    self.fail("Falha HTTP/rede deve gerar erro, nunca totais zero")

    async def test_redirect_is_not_followed(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={"Location": "https://other.test/"})

        with patch.dict(os.environ, {"XANO_DASHBOARD_API_URL": "https://example.test/api:group"}), self.mock_client(handler):
            with self.assertRaises(XanoDashboardError):
                await get_dashboard_summary_xano("private-token")
        self.assertEqual(len(calls), 1)

    async def test_missing_token_or_config_does_not_send_request(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "ProjetoLocadora.dashboard_client.httpx.AsyncClient",
        ) as client:
            for token in ("", "private-token"):
                with self.subTest(token_present=bool(token)), self.assertRaises(XanoDashboardError):
                    await get_dashboard_summary_xano(token)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
