"""Reaproveitamento de auth/me recente em leituras; escritas sempre conferem de novo."""

import os
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import SESSION_CHECK_REUSE_SECONDS, State
from ProjetoLocadora.dashboard_state import DashboardState
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.locacoes_state import LocacoesState, _customer_label, _exemplar_label
from ProjetoLocadora.xano_client import XanoCustomerError, XanoSessionUnavailable
from tests.test_locacoes_client import RENTAL

ME = {"id": 9, "role": "admin", "is_active": True}
CUSTOMER = {"id": 1, "nome": "Cliente local", "cpf_mascarado": "***.***.***-00", "status": "active", "bloqueio_manual_ativo": False}
EXEMPLAR = {"id": 2, "identificador": "LOCAL-2", "filme_id": 4, "filme_titulo": "Filme local"}
SUMMARY = {"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-23T12:00:00Z"}


async def consume(event):
    async for _ in event:
        pass


class _Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class TestSessionCheckReuse(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.session = await self.root.get_state(State)
        self.rentals = await self.root.get_state(LocacoesState)
        self.session._user_id = "9"
        self.session._user_role = "admin"
        self.session._xano_auth_token = "private-session-token"
        self.clock = _Clock()
        for target in ("ProjetoLocadora.ProjetoLocadora.time.monotonic", "ProjetoLocadora.locacoes_state.time.monotonic"):
            p = patch(target, new=self.clock)
            p.start()
            self.addCleanup(p.stop)
        env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        # Um único double de auth/me para todos os módulos: conta as consultas reais.
        self.me = AsyncMock(return_value=ME)
        for target in ("ProjetoLocadora.ProjetoLocadora.get_me_xano", "ProjetoLocadora.locacoes_state.get_me_xano", "ProjetoLocadora.dashboard_state.get_me_xano"):
            p = patch(target, new=self.me)
            p.start()
            self.addCleanup(p.stop)
        self.mocks = {}
        values = {
            "list_customers_xano": {"items": [CUSTOMER], "total": 1, "page": 1, "per_page": 10},
            "available_exemplars": {"items": [EXEMPLAR], "total": 1, "page": 1, "per_page": 10},
            "list_exemplares_xano": [EXEMPLAR],
            "create_rental": (RENTAL, True), "reconcile_rental": RENTAL, "confirm_condition": True,
            "list_rentals": {"items": [RENTAL], "total": 1, "page": 1, "per_page": 10},
        }
        for name, value in values.items():
            p = patch(f"ProjetoLocadora.locacoes_state.{name}", new_callable=AsyncMock)
            self.mocks[name] = p.start()
            self.mocks[name].return_value = value
            self.addCleanup(p.stop)

    async def open_rental_page(self):
        """Mesma sequência do on_load: require_session e depois a carga de opções."""
        redirect = await self.session.require_session()
        self.assertIsNone(redirect)
        await consume(self.rentals.load_new())

    # --- redução de chamadas --------------------------------------------
    async def test_recent_validation_removes_repeated_auth_me_on_rental_page(self):
        await self.open_rental_page()
        self.assertEqual(self.me.await_count, 1)  # antes: 2 (require_session + _authorize)
        await consume(self.rentals.search_customers())
        await consume(self.rentals.exemplar_page(1))  # sem próxima página: nenhuma consulta
        self.assertEqual(self.me.await_count, 1)  # busca: antes 2 chamadas, agora 1 (só clientes)
        self.assertEqual(self.mocks["list_customers_xano"].await_count, 2)

    async def test_reuse_expires_after_the_window(self):
        await self.open_rental_page()
        self.clock.now += SESSION_CHECK_REUSE_SECONDS
        await consume(self.rentals.search_customers())
        self.assertEqual(self.me.await_count, 2)
        self.clock.now += SESSION_CHECK_REUSE_SECONDS - 1
        await consume(self.rentals.search_customers())
        self.assertEqual(self.me.await_count, 2)  # a conferência anterior renovou a janela

    async def test_dashboard_entry_reuses_but_manual_refresh_revalidates(self):
        dashboard = await self.root.get_state(DashboardState)
        with patch("ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", AsyncMock(return_value=SUMMARY)), \
                patch("ProjetoLocadora.dashboard_state.list_films_xano", AsyncMock(return_value=[])):
            self.assertIsNone(await self.session.require_session())
            await consume(dashboard.load_summary())
            self.assertEqual(self.me.await_count, 1)  # antes: 2
            self.assertEqual(dashboard.status, "success")
            await consume(dashboard.refresh_summary())
            self.assertEqual(self.me.await_count, 2)  # “Atualizar” sempre revalida

    # --- isolamento por sessão -----------------------------------------
    async def test_other_session_token_or_account_never_reuses(self):
        await self.session.require_session()
        other = await rx.State(_reflex_internal_init=True).get_state(State)
        other._user_id, other._user_role, other._xano_auth_token = "9", "admin", "private-session-token"
        self.assertFalse(other._recently_verified())  # outro cliente/aba
        self.session._xano_auth_token = "another-token"
        self.assertFalse(self.session._recently_verified())
        self.session._xano_auth_token = "private-session-token"
        self.assertTrue(self.session._recently_verified())
        self.session._user_id = "10"
        self.assertFalse(self.session._recently_verified())

    async def test_logout_and_identity_change_invalidate(self):
        await self.session.require_session()
        await self.session.logout()
        self.assertEqual(self.session._me_verified_key, "")
        self.assertFalse(self.session._recently_verified())
        self.session._user_id, self.session._user_role, self.session._xano_auth_token = "9", "admin", "t2"
        self.session._mark_session_verified()
        self.session._set_user({"id": 9, "role": "member"})  # troca de papel
        self.assertFalse(self.session._recently_verified())

    async def test_expired_window_with_invalid_session_logs_out(self):
        await self.session.require_session()
        self.clock.now += SESSION_CHECK_REUSE_SECONDS + 1
        self.me.return_value = None  # token revogado
        result = await self.session.require_session()
        self.assertIn("/login", str(result))
        self.assertFalse(self.session.is_authenticated)
        self.assertFalse(self.session._recently_verified())

    async def test_backend_401_or_403_on_read_drops_the_reuse(self):
        await self.open_rental_page()
        self.mocks["list_customers_xano"].side_effect = XanoCustomerError("Você não tem permissão para realizar esta operação.", status=403)
        await consume(self.rentals.search_customers())
        self.assertIn("permissão", self.rentals.message)
        self.assertFalse(self.session._recently_verified())
        self.mocks["list_customers_xano"].side_effect = None
        await consume(self.rentals.search_customers())
        self.assertEqual(self.me.await_count, 2)  # próxima leitura confere de novo

    async def test_backend_authorization_refusal_drops_the_reuse(self):
        await self.open_rental_page()
        self.mocks["available_exemplars"].side_effect = RentalError("authorization")
        await consume(self.rentals.exemplar_page(1))  # sem próxima página: nada é enviado
        self.rentals._exemplar_total = 40
        await consume(self.rentals.exemplar_page(1))
        self.assertIn("permissão", self.rentals.message)
        self.assertFalse(self.session._recently_verified())

    # --- escritas -------------------------------------------------------
    async def test_writes_always_check_auth_me_now(self):
        await self.open_rental_page()
        self.assertTrue(self.session._recently_verified())
        self.rentals.capture_customer(_customer_label(CUSTOMER))
        self.rentals.capture_exemplar(_exemplar_label(EXEMPLAR))
        self.rentals.capture_due("2030-01-02T12:00")
        before = self.me.await_count
        await consume(self.rentals.submit())
        self.assertEqual(self.me.await_count, before + 1)
        self.mocks["create_rental"].assert_awaited_once()

    async def test_condition_write_and_reconciliation_check_now(self):
        await self.open_rental_page()
        await consume(self.rentals.load_admin_exemplars())
        self.assertEqual(self.me.await_count, 1)  # leitura sob demanda reaproveita
        self.rentals.capture_condition_exemplar(_exemplar_label(EXEMPLAR))
        self.rentals.capture_condition("available")
        self.rentals.capture_reason("Conferido")
        await consume(self.rentals.save_condition())
        self.assertEqual(self.me.await_count, 2)
        self.rentals._pending = {"customer_id": 1, "exemplar_id": 2, "due_at": "2030-01-02T15:00:00Z", "operation_key": "6f2c1a43-6c42-4bd0-9f0b-2d2a1b7a5d11"}
        await consume(self.rentals.reconcile())
        self.assertEqual(self.me.await_count, 3)

    async def test_revoked_account_is_caught_by_the_next_write(self):
        await self.open_rental_page()
        self.me.return_value = {**ME, "is_active": False}
        self.rentals.capture_customer(_customer_label(CUSTOMER))
        self.rentals.capture_exemplar(_exemplar_label(EXEMPLAR))
        self.rentals.capture_due("2030-01-02T12:00")
        await consume(self.rentals.submit())
        self.mocks["create_rental"].assert_not_awaited()
        self.assertFalse(self.session.is_authenticated)

    # --- limite do plano ------------------------------------------------
    async def test_429_on_expired_check_waits_and_is_not_retried(self):
        await self.open_rental_page()
        self.clock.now += SESSION_CHECK_REUSE_SECONDS + 1
        self.me.side_effect = XanoSessionUnavailable("limite", retry_after=20)
        await consume(self.rentals.search_customers())
        self.assertIn("limite de requisições", self.rentals.message)
        calls = self.me.await_count
        self.clock.now += 5
        await consume(self.rentals.search_customers())
        self.assertEqual(self.me.await_count, calls)  # sem nova requisição antes do Retry-After
        self.assertEqual(self.session._user_id, "9")  # sem logout


if __name__ == "__main__":
    unittest.main()
