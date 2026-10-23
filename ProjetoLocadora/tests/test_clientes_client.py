import unittest
from unittest.mock import AsyncMock, patch

import httpx

from ProjetoLocadora.xano_client import (
    XanoCustomerAuditError,
    XanoCustomerError,
    create_customer_xano,
    get_customer_xano,
    list_customers_xano,
    set_customer_manual_block_xano,
    update_customer_xano,
)


CUSTOMER = {
    "id": 7,
    "created_at": 1700000000000,
    "updated_at": 1700000000000,
    "nome": "Maria da Silva",
    "cpf": "01234567890",
    "email": "maria@example.test",
    "telefone": None,
    "status": "active",
    "bloqueio_manual_ativo": False,
    "motivo_bloqueio_manual": None,
    "bloqueado_em": None,
    "bloqueado_por": None,
}

SUMMARY = {
    "id": 7,
    "nome": "Maria da Silva",
    "cpf_mascarado": "***.***.***-90",
    "status": "active",
    "bloqueio_manual_ativo": False,
}


class TestCustomerClient(unittest.IsolatedAsyncioTestCase):
    async def test_list_validates_paginated_minimal_contract_and_caps_page_size(self):
        response = httpx.Response(
            200,
            json={"items": [SUMMARY], "page": 2, "per_page": 50, "total": 51},
        )
        with patch(
            "ProjetoLocadora.xano_client._customer_request",
            new=AsyncMock(return_value=response),
        ) as request:
            result = await list_customers_xano(
                "token", nome=" Maria ", cpf="012.345.678-90", page=2, per_page=500
            )
        self.assertEqual(result["items"], [SUMMARY])
        request.assert_awaited_once_with(
            "GET",
            "",
            "token",
            params={
                "page": "2",
                "per_page": "50",
                "nome": "Maria",
                "cpf": "012.345.678-90",
            },
        )

    async def test_list_rejects_full_cpf_or_contact_in_summary(self):
        leaked = {**SUMMARY, "cpf": "01234567890"}
        with patch(
            "ProjetoLocadora.xano_client._customer_request",
            new=AsyncMock(
                return_value=httpx.Response(
                    200,
                    json={"items": [leaked], "page": 1, "per_page": 20, "total": 1},
                )
            ),
        ):
            with self.assertRaises(XanoCustomerError):
                await list_customers_xano("token")

    async def test_detail_and_writes_use_separate_routes_and_payloads(self):
        success = httpx.Response(200, json=CUSTOMER)
        write_success = httpx.Response(
            200, json={"customer": CUSTOMER, "audit_succeeded": True}
        )
        request = AsyncMock(side_effect=[success, write_success, write_success, write_success])
        with patch("ProjetoLocadora.xano_client._customer_request", new=request):
            self.assertEqual((await get_customer_xano("token", 7))["id"], 7)
            await create_customer_xano("token", {"nome": "Maria"})
            await update_customer_xano("token", 7, {"status": "inactive"})
            await set_customer_manual_block_xano(
                "token", 7, bloqueado=True, motivo="Análise interna"
            )
        self.assertEqual(request.await_args_list[0].args, ("GET", "/7", "token"))
        self.assertEqual(request.await_args_list[1].args, ("POST", "", "token"))
        self.assertEqual(request.await_args_list[2].args, ("PATCH", "/7", "token"))
        self.assertEqual(
            request.await_args_list[3].args,
            ("PATCH", "/7/bloqueio-manual", "token"),
        )
        self.assertEqual(
            request.await_args_list[3].kwargs["json_body"],
            {"bloqueado": True, "motivo": "Análise interna"},
        )

    async def test_maps_conflict_not_found_forbidden_and_invalid_input(self):
        calls = (
            (create_customer_xano("token", {}), 409, "Já existe"),
            (get_customer_xano("token", 99), 404, "não encontrado"),
            (create_customer_xano("token", {}), 403, "permissão"),
            (create_customer_xano("token", {}), 422, "não foram aceitos"),
        )
        for coroutine, status, message in calls:
            with self.subTest(status=status), patch(
                "ProjetoLocadora.xano_client._customer_request",
                new=AsyncMock(return_value=httpx.Response(status, json={})),
            ):
                with self.assertRaisesRegex(XanoCustomerError, message):
                    await coroutine

        with patch(
            "ProjetoLocadora.xano_client._customer_request",
            new=AsyncMock(
                return_value=httpx.Response(
                    400,
                    json={
                        "message": "Já existe um cliente cadastrado com este CPF."
                    },
                )
            ),
        ):
            with self.assertRaisesRegex(XanoCustomerError, "Já existe"):
                await create_customer_xano("token", {})

    async def test_429_reports_plan_limit_and_retry_after(self):
        cases = (
            (httpx.Response(429, json={}), 20),  # transporte curl não repassa o cabeçalho
            (httpx.Response(429, headers={"Retry-After": "7"}, json={}), 7),
        )
        for response, wait in cases:
            with self.subTest(wait=wait), patch(
                "ProjetoLocadora.xano_client._customer_request",
                new=AsyncMock(return_value=response),
            ):
                with self.assertRaises(XanoCustomerError) as error:
                    await list_customers_xano("token")
            self.assertEqual(error.exception.retry_after, wait)
            self.assertIn("limite de requisições", error.exception.user_message)

    async def test_reports_customer_audit_partial_success(self):
        with patch(
            "ProjetoLocadora.xano_client._customer_request",
            new=AsyncMock(
                return_value=httpx.Response(
                    200, json={"customer": CUSTOMER, "audit_succeeded": False}
                )
            ),
        ):
            with self.assertRaisesRegex(XanoCustomerAuditError, "Não repita"):
                await update_customer_xano("token", 7, {"status": "inactive"})

    async def test_rejects_invalid_success_contracts(self):
        for payload in (
            {"items": [], "page": 1, "per_page": 51, "total": 0},
            {"items": "not-a-list", "page": 1, "per_page": 20, "total": 0},
        ):
            with self.subTest(payload=payload), patch(
                "ProjetoLocadora.xano_client._customer_request",
                new=AsyncMock(return_value=httpx.Response(200, json=payload)),
            ):
                with self.assertRaises(XanoCustomerError):
                    await list_customers_xano("token")


if __name__ == "__main__":
    unittest.main()
