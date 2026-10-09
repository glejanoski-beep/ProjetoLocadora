import json
import subprocess
import unittest
from unittest.mock import patch

import httpx

from ProjetoLocadora.xano_client import (
    XanoAuditError,
    XanoCatalogError,
    create_film_xano,
    get_film_xano,
    list_films_xano,
    login_xano,
    update_film_xano,
)


FILM = {
    "id": 42,
    "titulo": "Filme",
    "genero": "Drama",
    "ano_lancamento": 2020,
    "classificacao": "Livre",
    "valor_locacao_centavos": 1234,
    "status": "active",
}


class TestCatalogClient(unittest.IsolatedAsyncioTestCase):
    async def request_with_response(self, operation, response):
        real_async_client = httpx.AsyncClient
        requests = []

        def handler(request):
            requests.append(request)
            return response

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            return_value="https://catalog.test/api:catalog-id",
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            side_effect=AssertionError("Catalog requests must not use auth configuration"),
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ):
            result = await operation
        return result, requests

    async def test_lists_with_server_filters_and_private_bearer_token(self):
        result, requests = await self.request_with_response(
            list_films_xano("secret-token", titulo=" Nome ", genero="Drama"),
            httpx.Response(200, json=[FILM]),
        )
        self.assertEqual(result, [FILM])
        self.assertEqual(
            requests[0].url.path,
            "/api:catalog-id/catalogo-filmes/filmes",
        )
        self.assertEqual(
            dict(requests[0].url.params),
            {"titulo": "Nome", "genero": "Drama"},
        )
        self.assertEqual(
            requests[0].headers["Authorization"],
            "Bearer secret-token",
        )

    async def test_gets_a_film_by_id(self):
        result, requests = await self.request_with_response(
            get_film_xano("token", 42),
            httpx.Response(200, json=FILM),
        )
        self.assertEqual(result, FILM)
        self.assertEqual(
            requests[0].url.path,
            "/api:catalog-id/catalogo-filmes/filmes/42",
        )

    async def test_creates_only_when_audit_is_confirmed(self):
        result, requests = await self.request_with_response(
            create_film_xano("token", {"titulo": "Filme"}),
            httpx.Response(200, json={"film": FILM, "audit_succeeded": True}),
        )
        self.assertEqual(result, FILM)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].read(), b'{"titulo":"Filme"}')

    async def test_updates_only_when_audit_is_confirmed(self):
        result, requests = await self.request_with_response(
            update_film_xano("token", 42, {"status": "inactive"}),
            httpx.Response(200, json={"film": FILM, "audit_succeeded": True}),
        )
        self.assertEqual(result, FILM)
        self.assertEqual(requests[0].method, "PATCH")
        self.assertEqual(
            requests[0].url.path,
            "/api:catalog-id/catalogo-filmes/filmes/42",
        )

    async def test_windows_catalog_list_uses_schannel_declared_route(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'[]\n__XANO_META__200__XANO_REQUEST_ID__test-request-123__XANO_CORRELATION_ID____XANO_CF_RAY__',
            stderr=b"",
        )

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            True,
        ), patch(
            "ProjetoLocadora.xano_client.shutil.which",
            return_value=r"C:\Windows\System32\curl.exe",
        ), patch(
            "ProjetoLocadora.xano_client.subprocess.run",
            return_value=result,
        ) as run, patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            return_value="https://catalog.test/api:catalog-id",
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            side_effect=AssertionError("Catalog must not use auth configuration"),
        ):
            films = await list_films_xano(
                "private-test-token",
                titulo="Nome do teste",
                genero="Drama",
            )

        self.assertEqual(films, [])
        self.assertEqual(
            run.call_args.args[0],
            [r"C:\Windows\System32\curl.exe", "--disable", "--silent", "--show-error",
             "--connect-timeout", "10", "--max-time", "10", "--config", "-",
             "--write-out",
             ("\n__XANO_META__%{http_code}"
              "__XANO_REQUEST_ID__%header{x-request-id}"
              "__XANO_CORRELATION_ID__%header{x-correlation-id}"
              "__XANO_CF_RAY__%header{cf-ray}")],
        )
        config = run.call_args.kwargs["input"].decode("utf-8")
        self.assertIn(
            "https://catalog.test/api:catalog-id/catalogo-filmes/filmes?",
            config,
        )
        self.assertIn("Authorization: Bearer private-test-token", config)
        self.assertNotIn("private-test-token", " ".join(run.call_args.args[0]))
        self.assertIn("titulo=Nome+do+teste", config)

    async def test_windows_catalog_create_sends_invalid_test_payload_without_write(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"message":"invalid input"}\n__XANO_META__400__XANO_REQUEST_ID____XANO_CORRELATION_ID____XANO_CF_RAY__',
            stderr=b"",
        )

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            True,
        ), patch(
            "ProjetoLocadora.xano_client.shutil.which",
            return_value=r"C:\Windows\System32\curl.exe",
        ), patch(
            "ProjetoLocadora.xano_client.subprocess.run",
            return_value=result,
        ) as run, patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            return_value="https://catalog.test/api:catalog-id",
        ), self.assertLogs("ProjetoLocadora.xano_client", level="WARNING") as logs:
            with self.assertRaises(XanoCatalogError):
                await create_film_xano(
                    "private-test-token",
                    {"titulo": ""},
                )

        config = run.call_args.kwargs["input"].decode("utf-8")
        self.assertIn('data = "{\\"titulo\\": \\"\\"}"', config)
        self.assertNotIn("private-test-token", " ".join(run.call_args.args[0]))
        self.assertIn("HTTP 400", "\n".join(logs.output))

    async def test_windows_catalog_preserves_safe_server_request_id(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"message":"internal"}\n__XANO_META__500__XANO_REQUEST_ID__xano-ref-123__XANO_CORRELATION_ID____XANO_CF_RAY__',
            stderr=b"",
        )

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            True,
        ), patch(
            "ProjetoLocadora.xano_client.shutil.which",
            return_value=r"C:\Windows\System32\curl.exe",
        ), patch(
            "ProjetoLocadora.xano_client.subprocess.run",
            return_value=result,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            return_value="https://catalog.test/api:catalog-id",
        ), self.assertLogs("ProjetoLocadora.xano_client", level="ERROR") as logs:
            with self.assertRaises(XanoCatalogError) as error:
                await create_film_xano(
                    "private-test-token",
                    {"titulo": "Film"},
                )

        self.assertIn("HTTP 500", error.exception.user_message)
        self.assertIn("xano-ref-123", error.exception.user_message)
        self.assertIn("xano-ref-123", "\n".join(logs.output))
        self.assertNotIn("private-test-token", "\n".join(logs.output))
        self.assertNotIn('"titulo"', "\n".join(logs.output))

    async def test_catalog_http_500_is_server_error_not_network_error(self):
        real_async_client = httpx.AsyncClient
        response = httpx.Response(
            500,
            json={"message": "private server detail"},
            headers={"x-request-id": "httpx-ref-456"},
        )

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(lambda request: response)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            return_value="https://catalog.test/api:catalog-id",
        ), patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), self.assertLogs("ProjetoLocadora.xano_client", level="ERROR") as logs:
            with self.assertRaises(XanoCatalogError) as error:
                await create_film_xano(
                    "private-test-token",
                    {"titulo": "Film"},
                )

        self.assertIn("POST catalogo-filmes/filmes", error.exception.user_message)
        self.assertIn("HTTP 500", error.exception.user_message)
        self.assertIn("httpx-ref-456", error.exception.user_message)
        self.assertNotIn("private server detail", "\n".join(logs.output))

    async def test_login_uses_auth_api_url_not_catalog_url(self):
        real_async_client = httpx.AsyncClient
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"authToken": "test-token"})

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            side_effect=AssertionError("Login must not use catalog configuration"),
        ):
            result = await login_xano("staff@example.test", "test-password")

        self.assertEqual(result, {"authToken": "test-token"})
        self.assertEqual(
            str(requests[0].url),
            "https://auth.test/api:auth-id/auth/login",
        )

    async def test_windows_login_uses_native_curl_and_stdin_for_credentials(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"authToken":"test-token"}\n200',
            stderr=b"",
        )

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            True,
        ), patch(
            "ProjetoLocadora.xano_client.shutil.which",
            return_value=r"C:\Windows\System32\curl.exe",
        ), patch(
            "ProjetoLocadora.xano_client.subprocess.run",
            return_value=result,
        ) as run, patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            side_effect=AssertionError("Login must not use catalog configuration"),
        ):
            response = await login_xano("private-email", "private-password")

        self.assertEqual(response, {"authToken": "test-token"})
        command = run.call_args.args[0]
        self.assertIn(
            "https://auth.test/api:auth-id/auth/login",
            command,
        )
        self.assertNotIn("private-email", command)
        self.assertNotIn("private-password", command)
        self.assertEqual(
            json.loads(run.call_args.kwargs["input"]),
            {"email": "private-email", "password": "private-password"},
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 11)

    async def test_windows_login_rejects_http_errors_without_logging_response_body(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"message":"private response body"}\n403',
            stderr=b"",
        )

        with patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            True,
        ), patch(
            "ProjetoLocadora.xano_client.shutil.which",
            return_value=r"C:\Windows\System32\curl.exe",
        ), patch(
            "ProjetoLocadora.xano_client.subprocess.run",
            return_value=result,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), self.assertLogs("ProjetoLocadora.xano_client", level="WARNING") as logs:
            response = await login_xano("private-email", "private-password")

        self.assertIsNone(response)
        message = "\n".join(logs.output)
        self.assertIn("HTTP 403", message)
        self.assertNotIn("private response body", message)
        self.assertNotIn("private-email", message)
        self.assertNotIn("private-password", message)

    async def test_login_configures_one_connection_retry(self):
        real_async_client = httpx.AsyncClient
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(400, json={"message": "invalid test payload"})

        transport = httpx.MockTransport(handler)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncHTTPTransport",
            return_value=transport,
        ) as make_transport, patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=lambda **kwargs: real_async_client(**kwargs),
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_catalog_api_url",
            side_effect=AssertionError("Login must not use catalog configuration"),
        ):
            result = await login_xano("test@example.invalid", "test-only-password")

        make_transport.assert_called_once_with(retries=1)
        self.assertIsNone(result)
        self.assertEqual(len(requests), 1)
        self.assertEqual(
            str(requests[0].url),
            "https://auth.test/api:auth-id/auth/login",
        )

    async def test_login_logs_connect_timeout_without_sensitive_data(self):
        real_async_client = httpx.AsyncClient

        def handler(request):
            raise httpx.ConnectTimeout(
                "connection timed out",
                request=request,
            )

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), self.assertLogs("ProjetoLocadora.xano_client", level="WARNING") as logs:
            result = await login_xano("private-email", "private-password")

        self.assertIsNone(result)
        message = "\n".join(logs.output)
        self.assertIn("Timeout na fase de conexão TCP/TLS", message)
        self.assertIn("ConnectTimeout", message)
        self.assertNotIn("private-email", message)
        self.assertNotIn("private-password", message)

    async def test_login_logs_response_timeout_separately(self):
        real_async_client = httpx.AsyncClient

        def handler(request):
            raise httpx.ReadTimeout("response timed out", request=request)

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), self.assertLogs("ProjetoLocadora.xano_client", level="WARNING") as logs:
            result = await login_xano("private-email", "private-password")

        self.assertIsNone(result)
        message = "\n".join(logs.output)
        self.assertIn("Timeout aguardando resposta", message)
        self.assertIn("ReadTimeout", message)
        self.assertNotIn("private-email", message)
        self.assertNotIn("private-password", message)

    async def test_login_logs_http_status_without_response_body(self):
        real_async_client = httpx.AsyncClient

        def handler(request):
            return httpx.Response(
                403,
                json={"message": "diagnostic response body must not be logged"},
            )

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_auth_api_url",
            return_value="https://auth.test/api:auth-id",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ), self.assertLogs("ProjetoLocadora.xano_client", level="WARNING") as logs:
            result = await login_xano("private-email", "private-password")

        self.assertIsNone(result)
        message = "\n".join(logs.output)
        self.assertIn("HTTP 403", message)
        self.assertNotIn("diagnostic response body", message)
        self.assertNotIn("private-email", message)
        self.assertNotIn("private-password", message)

    async def test_reports_audit_failure_as_partial_success(self):
        with self.assertRaises(XanoAuditError) as context:
            await self.request_with_response(
                create_film_xano("token", {"titulo": "Filme"}),
                httpx.Response(200, json={"film": FILM, "audit_succeeded": False}),
            )
        self.assertIn("foi gravado", str(context.exception))

    async def test_does_not_treat_api_errors_as_empty_data(self):
        with self.assertRaises(XanoCatalogError):
            await self.request_with_response(
                list_films_xano("token"),
                httpx.Response(403, json={"message": "forbidden"}),
            )

    async def test_rejects_invalid_success_payload(self):
        with self.assertRaises(XanoCatalogError):
            await self.request_with_response(
                list_films_xano("token"),
                httpx.Response(200, json={"not": "a list"}),
            )


if __name__ == "__main__":
    unittest.main()
