import unittest
from unittest.mock import AsyncMock, patch

import httpx

from ProjetoLocadora.xano_client import (
    XanoExemplarAuditError,
    XanoExemplarError,
    create_exemplar_xano,
    list_exemplares_xano,
)


EXEMPLAR = {
    "id": 8,
    "identificador": "A-01",
    "filme_id": 42,
    "filme_titulo": "Filme de teste",
}


class TestExemplarClient(unittest.IsolatedAsyncioTestCase):
    async def test_lists_empty_and_populated_responses(self):
        responses = [
            httpx.Response(200, json=[]),
            httpx.Response(200, json=[EXEMPLAR]),
        ]
        with patch(
            "ProjetoLocadora.xano_client._exemplar_request",
            side_effect=responses,
        ) as request:
            self.assertEqual(await list_exemplares_xano("token"), [])
            self.assertEqual(
                await list_exemplares_xano("token"),
                [EXEMPLAR],
            )
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.args, ("GET", "", "token"))

    async def test_rejects_malformed_listing_response(self):
        with patch(
            "ProjetoLocadora.xano_client._exemplar_request",
            return_value=httpx.Response(200, json=[{"id": 8}]),
        ):
            with self.assertRaisesRegex(XanoExemplarError, "lista de exemplares inválida"):
                await list_exemplares_xano("token")

    async def test_create_uses_own_route_and_payload_and_requires_audit_success(self):
        success = httpx.Response(
            200,
            json={"exemplar": EXEMPLAR, "audit_succeeded": True},
        )
        with patch(
            "ProjetoLocadora.xano_client._exemplar_request",
            return_value=success,
        ) as request:
            result = await create_exemplar_xano(
                "token",
                {"identificador": "A-01", "filme_id": 42},
            )
        self.assertEqual(result, EXEMPLAR)
        request.assert_awaited_once_with(
            "POST",
            "",
            "token",
            json_body={"identificador": "A-01", "filme_id": 42},
        )

        partial = httpx.Response(
            200,
            json={"exemplar": EXEMPLAR, "audit_succeeded": False},
        )
        with patch(
            "ProjetoLocadora.xano_client._exemplar_request",
            return_value=partial,
        ):
            with self.assertRaisesRegex(XanoExemplarAuditError, "Não repita"):
                await create_exemplar_xano(
                    "token",
                    {"identificador": "A-01", "filme_id": 42},
                )

    async def test_create_maps_conflict_forbidden_and_missing_film(self):
        cases = (
            (409, "Já existe um exemplar"),
            (403, "permissão"),
            (404, "Filme não encontrado"),
            (
                400,
                "Já existe um exemplar",
            ),
        )
        bodies = (
            {},
            {},
            {},
            {"message": "Já existe um exemplar com este identificador."},
        )
        for (status, message), body in zip(cases, bodies):
            with self.subTest(status=status), patch(
                "ProjetoLocadora.xano_client._exemplar_request",
                return_value=httpx.Response(status, json=body),
            ):
                with self.assertRaisesRegex(XanoExemplarError, message):
                    await create_exemplar_xano(
                        "token",
                        {"identificador": "A-01", "filme_id": 999},
                    )

    async def test_requests_use_separate_exemplar_group_and_hide_token(self):
        real_async_client = httpx.AsyncClient
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=[])

        def client_factory(**kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real_async_client(**kwargs)

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=client_factory,
        ), patch(
            "ProjetoLocadora.xano_client.get_xano_exemplar_api_url",
            return_value="https://exemplars.test/api:exemplar-group",
        ), patch(
            "ProjetoLocadora.xano_client._WINDOWS",
            False,
        ):
            await list_exemplares_xano("private-token")

        self.assertEqual(
            requests[0].url.path,
            "/api:exemplar-group/exemplares",
        )
        self.assertEqual(
            requests[0].headers["Authorization"],
            "Bearer private-token",
        )


if __name__ == "__main__":
    unittest.main()


class TestExemplarRateLimit(unittest.IsolatedAsyncioTestCase):
    async def test_429_reports_plan_limit_and_default_retry_after(self):
        from ProjetoLocadora.xano_client import XanoExemplarError as _Err, list_exemplares_xano as _list

        with patch(
            "ProjetoLocadora.xano_client._exemplar_request",
            new=AsyncMock(return_value=httpx.Response(429, json={})),
        ):
            with self.assertRaises(_Err) as error:
                await _list("token")
        self.assertEqual(error.exception.retry_after, 20)
        self.assertIn("limite de requisições", error.exception.user_message)
