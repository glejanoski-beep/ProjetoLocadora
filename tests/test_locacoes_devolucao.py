"""Estado da devolução (registrar-devolucao); transporte substituído por doubles locais."""

import os
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.locacoes_state import LocacoesState
from ProjetoLocadora.multas_client import FineError
from tests.test_locacoes_client import ACTIVE_13, RETURNED

ME = {"id": 9, "role": "member", "is_active": True}
POLICY = {"daily_cents": 300, "grace_minutes": 120, "cap_cents": 9000}


def fine_for(rental: dict, fine_id: int = 7) -> dict:
    """Multa coerente com a locação devolvida, pela política padrão."""
    late_days = -(-(rental["returned_at"] - rental["due_at"]) // (24 * 3600 * 1000))
    return {
        "id": fine_id, "rental_id": rental["id"], "customer_id": rental["customer_id"],
        "customer_name": rental["customer_name"], "film_title": rental["film_title"],
        "exemplar_identifier": rental["exemplar_identifier"], "due_at": rental["due_at"],
        "returned_at": rental["returned_at"], "late_days": late_days, "daily_cents": 300,
        "grace_minutes": 120, "cap_cents": 9000, "amount_cents": min(late_days * 300, 9000),
        "paid_cents": 0, "waived_cents": 0, "status": "open", "created_at": rental["returned_at"],
        "created_by": rental["returned_by"], "waived_at": None, "waived_by": None, "waive_reason": None,
    }


async def consume(event):
    async for _ in event:
        pass


class TestRentalReturnState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(LocacoesState)
        self.session = await self.root.get_state(State)
        self.session._user_id = "9"
        self.session._user_role = "member"
        self.session._xano_auth_token = "private-session-token"
        self.env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.me = patch("ProjetoLocadora.locacoes_state.get_me_xano", new=AsyncMock(return_value=ME)).start()
        self.get = patch("ProjetoLocadora.locacoes_state.get_rental", new=AsyncMock(return_value=ACTIVE_13)).start()
        self.ret = patch("ProjetoLocadora.locacoes_state.return_rental", new=AsyncMock(return_value=(RETURNED, True, None))).start()
        self.fines = patch("ProjetoLocadora.locacoes_state.list_fines", new=AsyncMock(return_value={"items": [], "page": 1, "per_page": 1, "total": 0})).start()
        self.policy = patch("ProjetoLocadora.locacoes_state.fine_policy", new=AsyncMock(return_value=POLICY)).start()
        self.addCleanup(patch.stopall)

    async def open(self, raw="3"):
        with patch.object(LocacoesState, "_route_rental_id", return_value=raw):
            await consume(self.state.load_detail())

    async def confirm(self):
        self.state.ask_return()
        await consume(self.state.submit_return())

    async def test_active_rental_offers_return_only_after_explicit_confirmation(self):
        await self.open()
        self.assertTrue(self.state.can_return)
        self.assertFalse(self.state.writes_blocked)
        self.assertFalse(self.state.return_confirming)
        self.state.ask_return()
        self.assertTrue(self.state.return_confirming)
        self.state.cancel_return()
        self.assertFalse(self.state.return_confirming)
        self.ret.assert_not_awaited()

    async def test_success_shows_the_persisted_return_and_checks_session_now(self):
        await self.open()
        me_before = self.me.await_count
        await self.confirm()
        self.assertEqual(self.me.await_count, me_before + 1)  # escrita: auth/me atual
        token, rental_id, key = self.ret.await_args.args
        self.assertEqual((token, rental_id), ("private-session-token", 3))
        self.assertRegex(key, r"^[0-9a-f-]{36}$")
        self.assertEqual(self.state.rental_view["status"], "Devolvida")
        self.assertNotEqual(self.state.rental_view["returned_at"], "")
        self.assertEqual(self.state.rental_view["returned_by"], "9")
        self.assertEqual(self.state.notice, "Devolução registrada.")
        self.assertFalse(self.state.can_return)
        self.assertFalse(self.state.return_confirming)
        self.assertFalse(self.state.return_pending_here)

    async def test_success_goes_to_the_returned_tab(self):
        await self.open()
        self.state.ask_return()
        updates = [u async for u in self.state.submit_return()]
        self.assertTrue(any("/locacoes/nova" in str(u) for u in updates))
        self.assertEqual(self.state.list_tab, "returned")
        self.assertEqual(self.state.list_notice, f"Locação #{RETURNED['id']} devolvida.")

    async def test_failed_return_stays_on_the_detail(self):
        self.ret.side_effect = RentalError("unknown")
        await self.open()
        self.state.ask_return()
        updates = [u async for u in self.state.submit_return()]
        self.assertFalse(any("/locacoes/nova" in str(u) for u in updates))
        self.assertEqual((self.state.list_tab, self.state.list_notice), ("active", ""))

    async def test_audit_failure_is_reported_without_suggesting_a_new_return(self):
        self.ret.return_value = (RETURNED, False, None)
        await self.open()
        await self.confirm()
        self.assertIn("auditoria não foi confirmada", self.state.notice)
        self.assertIn("Não repita", self.state.notice)
        # O aviso acompanha a locação até a aba "Devolvidas".
        self.assertIn("não repita a devolução", self.state.list_notice)

    async def test_double_submit_sends_one_request(self):
        await self.open()
        self.state.ask_return()
        first = self.state.submit_return()
        await first.__anext__()  # primeiro evento marcou a operação em andamento
        await consume(self.state.submit_return())
        await consume(first)
        self.assertEqual(self.ret.await_count, 1)

    async def test_unknown_result_keeps_the_key_and_repeat_reuses_it(self):
        self.ret.side_effect = RentalError("unknown")
        await self.open()
        await self.confirm()
        self.assertTrue(self.state.return_pending_here)
        self.assertIn("ainda desconhecido", self.state.message)
        self.assertFalse(self.state.can_return)  # nada de nova chave enquanto pendente
        first_key = self.ret.await_args.args[2]
        self.ret.side_effect = None
        await consume(self.state.repeat_return())
        self.assertEqual(self.ret.await_args.args[2], first_key)
        self.assertEqual(self.state.rental_view["status"], "Devolvida")
        self.assertFalse(self.state.return_pending_here)

    async def test_refreshing_the_detail_resolves_an_unknown_return(self):
        self.ret.side_effect = RentalError("unknown")
        await self.open()
        await self.confirm()
        self.get.return_value = RETURNED
        await self.open()
        self.assertFalse(self.state.return_pending_here)
        self.assertEqual(self.state.notice, "Devolução confirmada pelo registro persistido.")
        self.assertEqual(self.ret.await_count, 1)

    async def test_conflict_refreshes_the_detail_with_the_existing_return(self):
        self.ret.side_effect = RentalError("conflict")
        await self.open()
        self.get.return_value = RETURNED
        await self.confirm()
        self.assertIn("já foi devolvida", self.state.message)
        self.assertEqual(self.state.rental_view["status"], "Devolvida")
        self.assertFalse(self.state.return_pending_here)

    async def test_not_found_and_input_errors_clear_the_attempt(self):
        for category in ("notfound", "input"):
            with self.subTest(category=category):
                self.ret.side_effect = RentalError(category)
                await self.open()
                await self.confirm()
                self.assertFalse(self.state.return_pending_here)
                self.assertNotEqual(self.state.message, "")

    async def test_rate_limit_on_repeat_keeps_the_key(self):
        self.ret.side_effect = RentalError("unknown")
        await self.open()
        await self.confirm()
        self.ret.side_effect = RentalError("ratelimited", retry_after=20)
        await consume(self.state.repeat_return())
        self.assertTrue(self.state.return_pending_here)
        self.assertIn("limite de requisições", self.state.message)

    async def test_writes_disabled_blocks_without_request(self):
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}):
            await self.open()
            self.assertTrue(self.state.writes_blocked)
            self.assertFalse(self.state.can_return)
            await self.confirm()
        self.ret.assert_not_awaited()

    async def test_response_for_another_account_is_not_shown_as_success(self):
        self.ret.return_value = ({**RETURNED, "returned_by": 10}, True, None)
        await self.open()
        await self.confirm()
        self.assertTrue(self.state.return_pending_here)
        self.assertNotEqual(self.state.rental_view["status"], "Devolvida")

    async def test_logout_discards_the_late_response(self):
        async def late(token, rental_id, key):
            await self.session.logout()
            return RETURNED, True, None

        self.ret.side_effect = late
        await self.open()
        await self.confirm()
        self.assertFalse(self.state.has_rental)
        self.assertFalse(self.state.return_pending_here)

    async def test_member_and_admin_can_return(self):
        for role in ("member", "admin"):
            with self.subTest(role=role):
                self.session._user_role = role
                self.me.return_value = {**ME, "role": role}
                self.get.return_value = ACTIVE_13
                await self.open()
                await self.confirm()
                self.assertEqual(self.state.rental_view["status"], "Devolvida")

    async def test_returned_rental_has_no_action_and_shows_lateness(self):
        self.get.return_value = {**RETURNED, "returned_at": RETURNED["due_at"] + 1}
        await self.open()
        self.assertFalse(self.state.can_return)
        self.assertFalse(self.state.is_active_rental)
        self.assertEqual(self.state.rental_view["returned_late"], "1")
        self.assertEqual(self.state.rental_view["overdue"], "")
        self.get.return_value = {**RETURNED, "returned_at": RETURNED["due_at"] - 1}
        await self.open()
        self.assertEqual(self.state.rental_view["returned_late"], "")
        self.state.ask_return()
        self.assertFalse(self.state.return_confirming)

    async def test_late_return_shows_the_generated_fine(self):
        late = {**RETURNED, "returned_at": RETURNED["due_at"] + 49 * 3600 * 1000}
        self.ret.return_value = (late, True, fine_for(late))
        await self.open()
        await self.confirm()
        self.assertIn("Multa por atraso gerada: R$ 9,00 (3 dias), multa nº 7.", self.state.list_notice)
        self.assertEqual(self.state.rental_view["fine"], "R$ 9,00 (3 dias)")
        self.assertEqual(self.state.rental_view["fine_href"], "/multas/7")

    async def test_returned_detail_loads_the_fine_of_the_rental(self):
        late = {**RETURNED, "returned_at": RETURNED["due_at"] + 49 * 3600 * 1000}
        self.get.return_value = late
        self.fines.return_value = {"items": [fine_for(late)], "page": 1, "per_page": 1, "total": 1}
        await self.open()
        self.assertEqual(self.fines.await_args.kwargs, {"rental_id": late["id"]})
        self.assertEqual(self.state.rental_view["fine_status"], "Em aberto")
        self.assertEqual(self.state.rental_view["fine_balance"], "R$ 9,00")
        self.policy.assert_not_awaited()

    async def test_overdue_active_rental_shows_an_estimate_from_the_policy(self):
        now_ms = 1_900_000_000_000
        self.get.return_value = {**ACTIVE_13, "rented_at": now_ms - 5 * 24 * 3600 * 1000, "due_at": now_ms - 49 * 3600 * 1000}
        with patch("ProjetoLocadora.locacoes_state.time.time", return_value=now_ms / 1000):
            await self.open()
            self.assertEqual(self.state.rental_view["fine_estimate"], "R$ 9,00 (3 dias)")
        self.fines.assert_not_awaited()

    async def test_failed_fine_lookup_keeps_the_detail(self):
        self.get.return_value = {**RETURNED, "returned_at": RETURNED["due_at"] + 1}
        self.fines.side_effect = FineError("unavailable")
        await self.open()
        self.assertEqual(self.state.detail_state, "ready")
        self.assertEqual(self.state.rental_view["fine"], "")


if __name__ == "__main__":
    unittest.main()
