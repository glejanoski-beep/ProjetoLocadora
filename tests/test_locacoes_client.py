"""HTTP simulado localmente; não consulta nem grava dados no Xano."""

from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch

import httpx

from ProjetoLocadora.config import get_xano_rental_api_url, rental_writes_enabled
from ProjetoLocadora.locacoes import data_brasilia, validar_rental, vencimento_utc
from ProjetoLocadora import locacoes_client as client

KEY = "c14508ef-538b-44d1-97c9-89bcc0692398"
PAYLOAD = {"customer_id": 1, "exemplar_id": 2, "due_at": "2030-01-02T15:00:00Z", "operation_key": KEY}
RENTAL = {
    "id": 3, "customer_id": 1, "exemplar_id": 2, "registered_by": 9,
    "rented_at": 1893506400000, "due_at": 1893596400000, "status": "active",
    "customer_name": "Cliente do teste local", "exemplar_identifier": "LOCAL-2",
    "film_id": 4, "film_title": "Filme do teste local",
}
# Contrato com devolução: 13 campos.
ACTIVE_13 = {**RENTAL, "returned_at": None, "returned_by": None}
RETURNED = {**RENTAL, "status": "returned", "returned_at": 1893600000000, "returned_by": 9}
RETURN_KEY = "5d0c2f7e-9a4b-4c1e-8f3d-2b6a7c9e1f40"


class TestRentalDomain(unittest.TestCase):
    def test_brasilia_local_becomes_explicit_utc(self):
        self.assertEqual(vencimento_utc("2030-01-02T12:00"), PAYLOAD["due_at"])
        self.assertEqual(data_brasilia(RENTAL["due_at"]), "02/01/2030 às 12:00")

    def test_rejects_impossible_missing_relative_or_ambiguous_dates(self):
        for value in ("", "amanhã", "2030-02-30T12:00", "2030-01-02", "2030-01-02T12:00Z", "2018-11-04T00:30", "2019-02-16T23:30"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                vencimento_utc(value)

    def test_rental_projection_rejects_personal_data_and_coercion(self):
        self.assertEqual(validar_rental(RENTAL), RENTAL)
        self.assertEqual(validar_rental({**RENTAL, "exemplar_identifier": "   "})["exemplar_identifier"], "   ")
        variants = [
            {**RENTAL, "cpf": "must-not-pass"}, {**RENTAL, "id": True},
            {**RENTAL, "due_at": str(RENTAL["due_at"])},
            {**RENTAL, "due_at": RENTAL["rented_at"]},
            {**RENTAL, "status": "returned"}, {**RENTAL, "due_at": 10**30},
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validar_rental(value)

    def test_return_contract_with_13_fields_is_accepted_and_kept_coherent(self):
        self.assertEqual(validar_rental(ACTIVE_13), ACTIVE_13)
        self.assertEqual(validar_rental(RETURNED), RETURNED)
        incoherent = [
            {**ACTIVE_13, "returned_at": RETURNED["returned_at"]},          # ativa com data de devolução
            {**ACTIVE_13, "returned_by": 9},
            {**RETURNED, "returned_at": None},                              # devolvida sem data
            {**RETURNED, "returned_by": None},
            {**RETURNED, "returned_at": RENTAL["rented_at"] - 1},           # devolvida antes da retirada
            {**RETURNED, "returned_at": str(RETURNED["returned_at"])},      # coerção de tipo
            {**RETURNED, "returned_by": True},
            {**RETURNED, "returned_at": 10**30},
            {**RETURNED, "status": "cancelled"},
            {**RENTAL, "returned_at": None},                                # 12 campos
            {**RETURNED, "cpf": "must-not-pass"},
        ]
        for value in incoherent:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validar_rental(value)


class TestRentalConfiguration(unittest.TestCase):
    def test_group_url_has_no_fallback_and_requires_https(self):
        for url in ("", "http://api.test/api:rentals", "https://name:secret@api.test/api:r", "https://api.test/api:r?token=x", "https://api.test/api:r#x", "https://api.test/api:r/locacoes", "https://api.test:0/api:r", "https://bad_host/api:r"):
            with self.subTest(url=url), patch.dict(os.environ, {"XANO_RENTAL_API_URL": url}, clear=True), self.assertRaises(RuntimeError):
                get_xano_rental_api_url()
        with patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals"}, clear=True):
            self.assertEqual(get_xano_rental_api_url(), "https://api.test/api:rentals")

    def test_group_cannot_alias_existing_api_and_writes_default_off(self):
        with patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:auth", "XANO_AUTH_API_URL": "https://api.test/api:auth"}, clear=True), self.assertRaises(RuntimeError):
            get_xano_rental_api_url()
        for value in ("", "false", "1", "True"):
            with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": value}, clear=True):
                self.assertFalse(rental_writes_enabled())


class TestRentalTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.environment = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.real_client = httpx.AsyncClient
        self.requests = []

    async def call(self, operation, response):
        def transport(request):
            self.requests.append(request)
            if isinstance(response, Exception):
                raise response
            return response

        def factory(**kwargs):
            self.assertFalse(kwargs["follow_redirects"])
            return self.real_client(**kwargs, transport=httpx.MockTransport(transport))

        with patch.object(client.httpx, "AsyncClient", side_effect=factory):
            return await operation()

    async def test_create_uses_private_bearer_and_exact_payload_once(self):
        result = await self.call(lambda: client.create_rental("private-secret", PAYLOAD), httpx.Response(200, json={"rental": RENTAL, "audit_succeeded": False}))
        self.assertEqual(result, (RENTAL, False))
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.url.path, "/api:rentals/locacoes")
        self.assertEqual(json.loads(request.content), PAYLOAD)
        self.assertEqual(request.headers["Authorization"], "Bearer private-secret")
        self.assertNotIn("private-secret", str(request.url))

    async def test_gate_and_missing_config_do_not_send_requests(self):
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}), self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.create_rental("token", PAYLOAD), httpx.Response(200, json={}))
        self.assertEqual(error.exception.category, "disabled")
        self.assertEqual(self.requests, [])
        with patch.dict(os.environ, {"XANO_RENTAL_API_URL": ""}), self.assertRaises(client.RentalError) as error:
            await client.get_rental("token", 3)
        self.assertEqual(error.exception.category, "configuration")

    async def test_timeout_and_server_errors_are_unknown_without_retry(self):
        for response in (httpx.ReadTimeout("secret-body"), httpx.ConnectError("secret-body"), httpx.Response(500, text="secret-body"), httpx.Response(302, headers={"Location": "https://other.test"})):
            before = len(self.requests)
            with self.subTest(response=response), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.create_rental("token", PAYLOAD), response)
            self.assertEqual(error.exception.category, "unknown")
            self.assertNotIn("secret-body", str(error.exception))
            self.assertEqual(len(self.requests), before + 1)

    async def test_error_categories_and_safe_messages(self):
        for status, category in ((401, "authentication"), (403, "authorization"), (409, "conflict"), (400, "input"), (422, "input")):
            with self.subTest(status=status), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.create_rental("token", PAYLOAD), httpx.Response(status, json={"message": "private database detail"}))
            self.assertEqual(error.exception.category, category)
            self.assertNotIn("database", str(error.exception))

    async def test_read_429_is_rate_limited_with_retry_after_and_no_retry(self):
        body = {"code": "ERROR_CODE_TOO_MANY_REQUESTS", "message": "Your plan only supports 10 requests per 20 seconds."}
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.available_exemplars("token", 1, 10), httpx.Response(429, headers={"Retry-After": "20"}, json=body))
        self.assertEqual(error.exception.category, "ratelimited")
        self.assertEqual(error.exception.retry_after, 20)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].url.params["per_page"], "10")

    async def test_write_429_stays_unknown_to_force_reconciliation(self):
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.create_rental("token", PAYLOAD), httpx.Response(429, headers={"Retry-After": "20"}))
        self.assertEqual(error.exception.category, "unknown")

    async def test_xano_named_conflict_is_recognized_without_exposing_body(self):
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.create_rental("token", PAYLOAD), httpx.Response(500, json={"message": "Exemplar já possui locação ativa."}))
        self.assertEqual(error.exception.category, "conflict")

    async def test_malformed_or_mismatched_success_does_not_confirm_write(self):
        responses = [
            httpx.Response(200, text="not-json"),
            httpx.Response(200, text='{"rental":{},"rental":{},"audit_succeeded":true}'),
            httpx.Response(200, json={"rental": RENTAL, "audit_succeeded": "true"}),
            httpx.Response(200, json={"rental": {**RENTAL, "exemplar_id": 99}, "audit_succeeded": True}),
            httpx.Response(200, json={"rental": {**RENTAL, "due_at": RENTAL["due_at"] + 1000}, "audit_succeeded": True}),
        ]
        for response in responses:
            with self.subTest(response=response), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.create_rental("token", PAYLOAD), response)
            self.assertEqual(error.exception.category, "unknown")

    async def test_reconciliation_uses_same_key_and_private_identity(self):
        result = await self.call(lambda: client.reconcile_rental("token", KEY), httpx.Response(200, json=RENTAL))
        self.assertEqual(result, RENTAL)
        self.assertEqual(self.requests[-1].method, "GET")
        self.assertTrue(self.requests[-1].url.path.endswith(KEY))

    async def test_returned_rental_is_accepted_by_replay_detail_and_reconciliation(self):
        created = await self.call(lambda: client.create_rental("token", PAYLOAD), httpx.Response(200, json={"rental": {**RETURNED, "due_at": 1893596400000}, "audit_succeeded": True}))
        self.assertEqual(created[0]["status"], "returned")
        self.assertEqual(await self.call(lambda: client.get_rental("token", 3), httpx.Response(200, json=RETURNED)), RETURNED)
        self.assertEqual(await self.call(lambda: client.get_rental("token", 3), httpx.Response(200, json=ACTIVE_13)), ACTIVE_13)
        self.assertEqual(await self.call(lambda: client.reconcile_rental("token", KEY), httpx.Response(200, json=RETURNED)), RETURNED)

    async def test_return_posts_only_the_key_once_and_validates_the_result(self):
        result = await self.call(lambda: client.return_rental("private-secret", 3, RETURN_KEY), httpx.Response(200, json={"rental": RETURNED, "audit_succeeded": True}))
        self.assertEqual(result, (RETURNED, True))
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.path, "/api:rentals/locacoes/3/devolucao")
        self.assertEqual(json.loads(request.content), {"operation_key": RETURN_KEY})
        self.assertEqual(request.headers["Authorization"], "Bearer private-secret")

    async def test_return_gate_and_input_send_nothing(self):
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}), self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.return_rental("token", 3, RETURN_KEY), httpx.Response(200, json={}))
        self.assertEqual(error.exception.category, "disabled")
        for rental_id, key in ((0, RETURN_KEY), (3, "not-a-uuid"), (True, RETURN_KEY)):
            with self.subTest(rental_id=rental_id, key=key), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.return_rental("token", rental_id, key), httpx.Response(200, json={}))
            self.assertEqual(error.exception.category, "input")
        self.assertEqual(self.requests, [])

    async def test_return_error_categories(self):
        cases = (
            (httpx.Response(400, json={"message": "Locação já devolvida."}), "conflict"),
            (httpx.Response(400, json={"message": "Chave já utilizada para outra operação."}), "conflict"),
            (httpx.Response(404, json={"message": "Locação não encontrada."}), "notfound"),
            (httpx.Response(404, json={"message": "Unable to locate request."}), "unknown"),  # rota ausente
            (httpx.Response(401), "authentication"), (httpx.Response(403), "authorization"),
            (httpx.Response(400, json={"message": "Locação inválida."}), "input"),
            (httpx.Response(429, headers={"Retry-After": "20"}), "unknown"),
            (httpx.Response(500), "unknown"), (httpx.ReadTimeout("t"), "unknown"),
        )
        for response, category in cases:
            before = len(self.requests)
            with self.subTest(response=response), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.return_rental("token", 3, RETURN_KEY), response)
            self.assertEqual(error.exception.category, category)
            self.assertEqual(len(self.requests), before + 1)  # sem retry automático

    async def test_return_result_must_be_the_same_rental_and_returned(self):
        for rental in ({**RETURNED, "id": 4}, ACTIVE_13, RENTAL, {**RETURNED, "returned_at": None}):
            with self.subTest(rental=rental), self.assertRaises(client.RentalError) as error:
                await self.call(lambda: client.return_rental("token", 3, RETURN_KEY), httpx.Response(200, json={"rental": rental, "audit_succeeded": True}))
            self.assertEqual(error.exception.category, "unknown")

    async def test_detail_does_not_accept_another_id(self):
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.get_rental("token", 4), httpx.Response(200, json=RENTAL))
        self.assertEqual(error.exception.category, "invalid")

    async def test_empty_availability_is_valid_and_network_failure_is_distinct(self):
        page = {"items": [], "page": 1, "per_page": 20, "total": 0}
        self.assertEqual(await self.call(lambda: client.available_exemplars("token"), httpx.Response(200, json=page)), page)
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.available_exemplars("token"), httpx.ConnectError("private"))
        self.assertEqual(error.exception.category, "unavailable")

    async def test_availability_rejects_coercion_duplicates_and_personal_fields(self):
        item = {"id": 1, "identificador": "LOCAL", "filme_id": 2, "filme_titulo": "Local"}
        for data in (
            {"items": [], "page": True, "per_page": 20, "total": 0},
            {"items": [item, item], "page": 1, "per_page": 20, "total": 2},
            {"items": [{**item, "cpf": "private"}], "page": 1, "per_page": 20, "total": 1},
        ):
            with self.subTest(data=data), self.assertRaises(client.RentalError):
                await self.call(lambda: client.available_exemplars("token"), httpx.Response(200, json=data))

    async def test_condition_write_partial_audit_and_bad_response(self):
        item = {"id": 2, "operational_condition": "available", "condition_confirmed_at": 1893506400000, "condition_confirmed_by": 9}
        result = await self.call(lambda: client.confirm_condition("token", 2, "available", "Conferência local de teste"), httpx.Response(200, json={"exemplar": item, "audit_succeeded": False}))
        self.assertFalse(result)
        self.assertNotIn("customer_id", json.loads(self.requests[-1].content))
        with self.assertRaises(client.RentalError) as error:
            await self.call(lambda: client.confirm_condition("token", 2, "available", "Teste"), httpx.Response(200, json={"exemplar": {**item, "id": 99}, "audit_succeeded": True}))
        self.assertEqual(error.exception.category, "unknown")
