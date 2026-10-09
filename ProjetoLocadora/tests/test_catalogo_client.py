import unittest
from unittest.mock import patch

import httpx

from ProjetoLocadora.xano_client import (
    XanoAuditError,
    XanoCatalogError,
    create_film_xano,
    get_film_xano,
    list_films_xano,
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
            return real_async_client(
                transport=httpx.MockTransport(handler),
                **kwargs,
            )

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_api_url",
            return_value="https://xano.test/api",
        ):
            result = await operation
        return result, requests

    async def test_lists_with_server_filters_and_private_bearer_token(self):
        result, requests = await self.request_with_response(
            list_films_xano("secret-token", titulo=" Nome ", genero="Drama"),
            httpx.Response(200, json=[FILM]),
        )
        self.assertEqual(result, [FILM])
        self.assertEqual(requests[0].url.path, "/api/catalogo-filmes/filmes")
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
        self.assertEqual(requests[0].url.path, "/api/catalogo-filmes/filmes/42")

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
        self.assertEqual(requests[0].url.path, "/api/catalogo-filmes/filmes/42")

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
