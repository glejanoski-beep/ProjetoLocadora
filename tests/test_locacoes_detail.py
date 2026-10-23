"""Consulta do detalhe de locação (C1 consultar-locacao); transporte substituído por doubles."""

import os
import re
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State, dashboard_topbar
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.locacoes_state import LocacoesState
from ProjetoLocadora.locacoes_ui import detail, registration
from ProjetoLocadora.xano_client import XanoSessionUnavailable
from tests.test_locacoes_client import RENTAL

ME = {"id": 9, "role": "member", "is_active": True}


async def consume(event):
    async for _ in event:
        pass


def _text(component) -> str:
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), str(component))


class TestRentalDetailState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(LocacoesState)
        self.session = await self.root.get_state(State)
        self.session._user_id = "9"
        self.session._user_role = "member"
        self.session._xano_auth_token = "private-session-token"
        env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.me = patch("ProjetoLocadora.locacoes_state.get_me_xano", new=AsyncMock(return_value=ME)).start()
        self.get = patch("ProjetoLocadora.locacoes_state.get_rental", new=AsyncMock(return_value=RENTAL)).start()
        self.addCleanup(patch.stopall)

    async def open(self, raw: str):
        with patch.object(LocacoesState, "_route_rental_id", return_value=raw):
            await consume(self.state.load_detail())

    async def test_existing_rental_is_loaded_with_readable_fields(self):
        await self.open(str(RENTAL["id"]))
        self.get.assert_awaited_once_with("private-session-token", RENTAL["id"])
        self.assertEqual(self.state.detail_state, "ready")
        self.assertEqual(self.state.message, "")
        view = self.state.rental_view
        self.assertEqual(view["title"], f"Locação #{RENTAL['id']}")
        self.assertEqual(view["status"], "Ativa")
        self.assertEqual(view["customer_href"], f"/clientes/{RENTAL['customer_id']}")
        self.assertRegex(view["rented_at"], r"^\d{2}/\d{2}/\d{4} às \d{2}:\d{2}$")
        self.assertRegex(view["due_at"], r"^\d{2}/\d{2}/\d{4} às \d{2}:\d{2}$")
        self.assertEqual(view["registered_by"], str(RENTAL["registered_by"]))
        self.assertFalse(self.state.loading)

    async def test_invalid_identifiers_never_reach_the_backend(self):
        for raw in ("", "abc", "0", "-1", "1.5", "01", "1 2", "12345678901"):
            with self.subTest(raw=raw):
                await self.open(raw)
                self.assertEqual(self.state.detail_state, "invalid")
                self.assertIn("Número de locação inválido", self.state.message)
                self.assertFalse(self.state.has_rental)
        self.get.assert_not_awaited()
        self.me.assert_not_awaited()

    async def test_missing_rental_names_the_number(self):
        self.get.side_effect = RentalError("notfound")
        await self.open("999")
        self.assertEqual(self.state.detail_state, "notfound")
        self.assertEqual(self.state.message, "A locação nº 999 não foi encontrada.")
        self.assertFalse(self.state.has_rental)

    async def test_connection_failure_is_an_error_with_retry(self):
        self.get.side_effect = RentalError("unavailable")
        await self.open("1")
        self.assertEqual(self.state.detail_state, "error")
        self.assertIn("Não foi possível consultar", self.state.message)
        self.get.side_effect = None
        await self.open("1")
        self.assertEqual(self.state.detail_state, "ready")

    async def test_401_ends_the_session(self):
        self.get.side_effect = RentalError("authentication")
        await self.open("1")
        self.assertEqual(self.state.detail_state, "error")
        self.assertIn("Entre novamente", self.state.message)
        self.assertFalse(self.session.is_authenticated)

    async def test_403_reports_missing_permission_and_keeps_no_data(self):
        self.get.side_effect = RentalError("authorization")
        await self.open("1")
        self.assertEqual(self.state.detail_state, "error")
        self.assertIn("permissão", self.state.message)
        self.assertFalse(self.state.has_rental)

    async def test_429_waits_before_the_next_request(self):
        self.get.side_effect = RentalError("ratelimited", retry_after=20)
        with patch("ProjetoLocadora.locacoes_state.time.monotonic", return_value=500.0):
            await self.open("1")
        self.assertIn("limite de requisições", self.state.message)
        self.get.side_effect = None
        with patch("ProjetoLocadora.locacoes_state.time.monotonic", return_value=505.0):
            await self.open("1")  # “Tentar novamente” antes do prazo
        self.assertEqual(self.get.await_count, 1)
        self.assertEqual(self.state.detail_state, "error")
        self.assertIn("aguarde mais 15 s", self.state.message)

    async def test_session_check_429_does_not_log_out(self):
        self.me.side_effect = XanoSessionUnavailable("limite", retry_after=20)
        await self.open("1")
        self.assertIn("limite de requisições", self.state.message)
        self.assertEqual(self.session._user_id, "9")
        self.get.assert_not_awaited()

    async def test_late_response_after_logout_is_discarded(self):
        async def late(token, rental_id):
            await self.session.logout()
            return RENTAL

        self.get.side_effect = late
        await self.open("1")
        self.assertFalse(self.state.has_rental)

    async def test_overdue_flag_compares_due_date_with_now(self):
        await self.open("1")
        with patch("ProjetoLocadora.locacoes_state.time.time", return_value=RENTAL["due_at"] / 1000 + 60):
            self.state._rental = dict(self.state._rental)  # força recálculo
            self.assertEqual(self.state.rental_view["overdue"], "1")
        with patch("ProjetoLocadora.locacoes_state.time.time", return_value=RENTAL["due_at"] / 1000 - 60):
            self.state._rental = dict(self.state._rental)
            self.assertEqual(self.state.rental_view["overdue"], "")

    def test_open_rental_validates_before_navigating(self):
        state = LocacoesState(_reflex_internal_init=True)
        for raw in ("", "abc", "0", "-3"):
            with self.subTest(raw=raw):
                self.assertIsNone(state.open_rental({"rental_number": raw}))
                self.assertIn("inteiro positivo", state.lookup_error)
        redirect = state.open_rental({"rental_number": " 25 "})
        self.assertEqual(state.lookup_error, "")
        self.assertIn("/locacoes/25", str(redirect))


class TestRentalDetailInterface(unittest.TestCase):
    def setUp(self):
        self.detail = _text(detail(dashboard_topbar("/locacoes/nova")))
        self.form = _text(registration(State.user_role == "admin", dashboard_topbar("/locacoes/nova")))

    def test_lookup_is_on_both_pages(self):
        for page in (self.form, self.detail):
            self.assertIn("Abrir locação pelo número", page)
            self.assertIn('name:"rental_number"', page)
            self.assertIn("lookup_error", page)

    def test_detail_handles_each_state(self):
        for text in ("Consultar locação", "detail_state", "Tentar novamente", "Atualizar detalhes",
                     "Vencimento ultrapassado", "Ver cadastro do cliente", "Voltar a locações"):
            with self.subTest(text=text):
                self.assertIn(text, self.detail)

    def test_detail_offers_only_the_return_action(self):
        # Registro de locação e conferência de condição não pertencem ao detalhe.
        for forbidden in ("Confirmar locação", "Confirmar condição"):
            self.assertNotIn(forbidden, self.detail)
        for text in ("Registrar devolução", "Confirmar devolução", "Repetir a mesma tentativa",
                     "is_active_rental", "can_return", "return_pending_here", "return_confirming",
                     "O registro de devoluções está bloqueado neste ambiente",
                     "Locação encerrada; nenhuma ação disponível.", "Devolvida com atraso", "Devolvida no prazo"):
            with self.subTest(text=text):
                self.assertIn(text, self.detail)


if __name__ == "__main__":
    unittest.main()
