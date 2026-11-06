"""Gestão de usuários (gerenciar-usuarios): regras, transporte, estado e contrato Xano.

HTTP simulado localmente; NÃO consulta nem grava no Xano.
"""

import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import reflex as rx

from ProjetoLocadora import usuarios_client as client
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.usuarios import filtrar, validar_lista, validar_motivo, validar_usuario
from ProjetoLocadora.usuarios_state import UNCERTAIN, UsuariosState
from tests.test_locacoes_xano_contract import ROOT, body, calls, flatten, predicate_exists, unique_assignment

ME = {"id": 3, "name": "Gustavo Admin", "email": "gu@locadora.test", "role": "admin", "is_active": True, "created_at": 1_760_000_000_000}
ANA = {"id": 5, "name": "Ana Júlia", "email": "ana@locadora.test", "role": "member", "is_active": True, "created_at": 1_761_000_000_000}
BRUNO = {"id": 7, "name": "Bruno", "email": "bruno@locadora.test", "role": "member", "is_active": False, "created_at": 1_762_000_000_000}
USERS = [ANA, BRUNO, ME]


async def consume(event):
    async for _ in event:
        pass


class TestUserRules(unittest.TestCase):
    def test_item_contract_is_exact(self):
        self.assertEqual(validar_usuario(ANA), ANA)
        for bad in ({**ANA, "password": "x"}, {**ANA, "role": "owner"}, {**ANA, "is_active": "true"}, {k: v for k, v in ANA.items() if k != "email"}, {**ANA, "id": 0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validar_usuario(bad)
        with self.assertRaises(ValueError):
            validar_lista({"items": [ANA], "total": 1})

    def test_search_ignores_accents_and_case_and_filters_status(self):
        self.assertEqual(filtrar(USERS, "JULIA", "all"), [ANA])
        self.assertEqual(filtrar(USERS, "locadora.test", "inactive"), [BRUNO])
        self.assertEqual(filtrar(USERS, "", "active"), [ANA, ME])

    def test_reason_is_required(self):
        self.assertEqual(validar_motivo("  Saiu da loja "), "Saiu da loja")
        for bad in ("", "   ", "x" * 501):
            with self.subTest(n=len(bad)), self.assertRaises(ValueError):
                validar_motivo(bad)


class TestUserTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Sem XANO_RENTAL_WRITES_ENABLED: a escrita de usuário não depende da flag de locação.
        env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.requests = []

    async def call(self, response, coro_factory):
        def handler(request):
            self.requests.append(request)
            return response

        real = httpx.AsyncClient

        def fake(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real(*args, **kwargs)

        with patch("ProjetoLocadora.multas_client.httpx.AsyncClient", side_effect=fake):
            return await coro_factory()

    async def test_list_reads_once(self):
        result = await self.call(httpx.Response(200, json={"items": USERS}), lambda: client.list_users("tok"))
        self.assertEqual(result, USERS)
        self.assertEqual(self.requests[0].url.path, "/api:rentals/usuarios")

    async def test_update_sends_full_target_state_without_rental_flag(self):
        updated = {**ANA, "role": "admin"}
        result = await self.call(
            httpx.Response(200, json={"user": updated, "audit_succeeded": True}),
            lambda: client.update_user("tok", 5, "admin", True, " Gerente "),
        )
        self.assertEqual(result, updated)
        request = self.requests[0]
        self.assertEqual((request.method, request.url.path), ("PATCH", "/api:rentals/usuarios/5"))
        self.assertEqual(json.loads(request.content), {"role": "admin", "is_active": True, "reason": "Gerente"})

    async def test_business_refusals_are_shown_as_returned(self):
        for message in ("Você não pode alterar a própria conta.", "Nenhuma alteração informada."):
            with self.subTest(message=message), self.assertRaises(client.UserError) as error:
                await self.call(httpx.Response(400, json={"message": message}), lambda: client.update_user("tok", 5, "admin", True, "x"))
            self.assertEqual((error.exception.category, str(error.exception)), ("conflict", message))

    async def test_mismatched_write_response_is_uncertain(self):
        with self.assertRaises(client.UserError) as error:
            await self.call(
                httpx.Response(200, json={"user": ANA, "audit_succeeded": True}),
                lambda: client.update_user("tok", 5, "admin", True, "x"),
            )
        self.assertEqual(error.exception.category, "unknown")

    async def test_invalid_input_is_not_sent(self):
        for args in ((0, "admin", True, "x"), (5, "owner", True, "x"), (5, "admin", True, "  ")):
            with self.subTest(args=args), self.assertRaises(client.UserError):
                await client.update_user("tok", *args)
        self.assertEqual(self.requests, [])


class TestUserState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(UsuariosState)
        self.session = await self.root.get_state(State)
        self.session._user_id, self.session._user_role, self.session._xano_auth_token = "3", "admin", "private-token"
        patch("ProjetoLocadora.multas_state.get_me_xano", new=AsyncMock(return_value={"id": 3, "role": "admin", "is_active": True})).start()
        self.list = patch("ProjetoLocadora.usuarios_state.list_users", new=AsyncMock(return_value=USERS)).start()
        self.update = patch("ProjetoLocadora.usuarios_state.update_user", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)

    async def test_member_never_queries(self):
        self.session._user_role = "member"
        await consume(self.state.open_page())
        self.assertEqual(self.state.state, "forbidden")
        self.list.assert_not_awaited()

    async def test_own_account_is_marked_and_cannot_be_opened(self):
        await consume(self.state.open_page())
        own = next(r for r in self.state.rows if r["id"] == 3)
        self.assertTrue(own["is_self"])
        self.state.open_edit(3)
        self.assertFalse(self.state.edit_open)
        self.assertEqual(self.state.summary, "3 contas · 2 ativas")

    async def test_promotion_updates_the_row(self):
        await consume(self.state.open_page())
        self.state.open_edit(5)
        self.state.capture_role("Administrador")
        self.state.capture_reason("Nova gerente")
        self.update.return_value = {**ANA, "role": "admin"}
        await consume(self.state.submit_edit())
        self.update.assert_awaited_once_with("private-token", 5, "admin", True, "Nova gerente")
        self.assertFalse(self.state.edit_open)
        self.assertEqual(next(r for r in self.state.rows if r["id"] == 5)["role_label"], "Administrador")

    async def test_deactivation_asks_confirmation_first(self):
        await consume(self.state.open_page())
        self.state.open_edit(5)
        self.state.capture_active(False)
        self.state.capture_reason("Saiu da loja")
        await consume(self.state.submit_edit())
        self.assertTrue(self.state.confirming)
        self.update.assert_not_awaited()
        self.update.return_value = {**ANA, "is_active": False}
        await consume(self.state.submit_edit())
        self.update.assert_awaited_once()
        self.assertFalse(next(r for r in self.state.rows if r["id"] == 5)["active"])

    async def test_no_change_and_missing_reason_are_not_sent(self):
        await consume(self.state.open_page())
        self.state.open_edit(5)
        self.state.capture_reason("x")
        await consume(self.state.submit_edit())
        self.assertEqual(self.state.edit_error, "Nenhuma alteração informada.")
        self.state.capture_role("Administrador")
        self.state.capture_reason("")
        await consume(self.state.submit_edit())
        self.assertIn("motivo", self.state.edit_error)
        self.update.assert_not_awaited()

    async def test_backend_refusal_keeps_dialog_open(self):
        await consume(self.state.open_page())
        self.state.open_edit(7)
        self.state.capture_active(True)
        self.state.capture_reason("Voltou")
        message = "Você não pode alterar a própria conta."
        self.update.side_effect = client.UserError("conflict", detail=message)
        await consume(self.state.submit_edit())
        self.assertTrue(self.state.edit_open)
        self.assertEqual(self.state.edit_error, message)

    async def test_uncertain_result_reloads_instead_of_retrying(self):
        await consume(self.state.open_page())
        self.state.open_edit(7)
        self.state.capture_active(True)
        self.state.capture_reason("Voltou")
        self.update.side_effect = client.UserError("unknown")
        await consume(self.state.submit_edit())
        self.assertEqual(self.update.await_count, 1)
        self.assertEqual(self.list.await_count, 2)
        self.assertFalse(self.state.edit_open)
        self.assertEqual(self.state.notice, UNCERTAIN)

    async def test_logout_discards_the_list(self):
        await consume(self.state.open_page())
        await self.session.logout()
        self.assertEqual(self.state.rows, [])
        self.assertEqual(self.state.state, "idle")


def stack_of(relative: str):
    source = (ROOT / relative).read_text(encoding="utf-8")
    return source, next(calls(body(source), "stack"))[1]


class TestUserXanoContract(unittest.TestCase):
    def test_list_is_admin_only_and_never_reads_secrets(self):
        source, stack = stack_of("api/locacoes/usuarios_GET.xs")
        self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
        self.assertIn('"admin"', list(flatten(stack[2][1])))
        self.assertIn('output = ["id", "name", "email", "role", "is_active", "created_at"]', source)
        for secret in ("password", "password_reset"):
            self.assertNotIn(secret, source.split("query", 1)[1])
        for statement in ("db.add", "db.edit", "db.del", "db.transaction"):
            self.assertEqual(list(calls(stack, statement)), [], statement)

    def test_update_refuses_self_locks_in_id_order_and_never_deletes(self):
        source, stack = stack_of("api/locacoes/usuarios_id_PATCH.xs")
        self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
        self.assertIn('"admin"', list(flatten(stack[2][1])))
        self.assertTrue(predicate_exists(stack, "$input.id != $auth.id"))
        transaction = next(calls(stack, "db.transaction"))[1]
        locks = [op for args, op in calls(transaction, "db.get") if args == ("user",)]
        self.assertEqual([unique_assignment(op, "field_value") for op in locks], ["$low_id", "$high_id"])
        for op in locks:
            self.assertEqual(unique_assignment(op, "lock"), "true")
        self.assertTrue(predicate_exists(transaction, '$actor != null && $actor.is_active != false && $actor.role == "admin"'))
        self.assertTrue(predicate_exists(transaction, "$target.role != $input.role || $previous_active != $input.is_active"))
        self.assertIn("data = {role: $input.role, is_active: $input.is_active}", source)
        self.assertIn('action: "update_user"', source)
        self.assertNotIn("password", source)
        self.assertEqual(list(calls(stack, "db.del")), [])
        self.assertEqual(list(calls(stack, "db.add")), [])


if __name__ == "__main__":
    unittest.main()
