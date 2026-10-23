"""Estado Reflex real com APIs substituídas por doubles apenas neste processo."""

import asyncio
import os
import re
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.locacoes_state import LocacoesState, _customer_label, _exemplar_label
from tests.test_locacoes_client import KEY, PAYLOAD, RENTAL

ME = {"id": 9, "role": "member", "is_active": True}
CUSTOMER = {"id": 1, "nome": "Cliente local", "cpf_mascarado": "***.***.***-00", "status": "active", "bloqueio_manual_ativo": False}
EXEMPLAR = {"id": 2, "identificador": "LOCAL-2", "filme_id": 4, "filme_titulo": "Filme local"}


async def consume(event):
    async for _ in event:
        pass


class TestRentalState(unittest.IsolatedAsyncioTestCase):
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
        self.mocks = {}
        values = {
            "get_me_xano": ME,
            "list_customers_xano": {"items": [CUSTOMER], "total": 1, "page": 1, "per_page": 20},
            "available_exemplars": {"items": [EXEMPLAR], "total": 1, "page": 1, "per_page": 20},
            "list_exemplares_xano": [EXEMPLAR],
            "create_rental": (RENTAL, True), "reconcile_rental": RENTAL,
            "get_rental": RENTAL, "confirm_condition": True,
        }
        for name, value in values.items():
            p = patch(f"ProjetoLocadora.locacoes_state.{name}", new_callable=AsyncMock)
            self.mocks[name] = p.start()
            self.mocks[name].return_value = value
            self.addCleanup(p.stop)

    async def choose(self):
        await consume(self.state.load_new())
        self.state.capture_customer(_customer_label(CUSTOMER))
        self.state.capture_exemplar(_exemplar_label(EXEMPLAR))
        self.state.capture_due("2030-01-02T12:00")

    async def test_private_attempt_identity_and_unsafe_helpers_are_not_events(self):
        self.assertIn("_pending", LocacoesState.backend_vars)
        self.assertIn("_customers", LocacoesState.backend_vars)
        self.assertNotIn("_invalidate", LocacoesState.event_handlers)
        self.assertNotIn("_authorize", LocacoesState.event_handlers)
        self.assertNotIn("_send", LocacoesState.event_handlers)
        self.assertNotIn("private-session-token", str(self.state.dict()))
        self.assertNotIn("_pending", self.state.dict())

    async def test_member_loads_real_options_and_no_admin_data(self):
        await self.choose()
        self.assertEqual(len(self.state.customer_options), 1)
        self.assertEqual(len(self.state.exemplar_options), 1)
        self.assertTrue(self.state.can_create)
        self.mocks["list_exemplares_xano"].assert_not_awaited()

    async def test_missing_config_never_invents_options(self):
        with patch.dict(os.environ, {"XANO_RENTAL_API_URL": ""}):
            await consume(self.state.load_new())
        self.assertIn("não está configurado", self.state.message)
        self.assertEqual(self.state.customer_options, [])
        self.assertFalse(self.state.can_create)
        self.mocks["available_exemplars"].assert_not_awaited()

    async def test_disabled_backend_configuration_prevents_direct_submit(self):
        await self.choose()
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}):
            await consume(self.state.submit())
        self.mocks["create_rental"].assert_not_awaited()
        self.assertIn("habilitação", self.state.message)

    async def test_data_loading_failure_is_not_empty_success(self):
        self.mocks["available_exemplars"].side_effect = RentalError("unavailable")
        await consume(self.state.load_new())
        self.assertFalse(self.state._options_ready)
        self.assertIn("não consultada", self.state.exemplar_paging)
        self.assertNotEqual(self.state.message, "")
        self.assertFalse(self.state.can_create)

    async def test_valid_empty_availability_is_explicit_zero(self):
        self.mocks["available_exemplars"].return_value = {"items": [], "total": 0, "page": 1, "per_page": 20}
        await consume(self.state.load_new())
        self.assertTrue(self.state._options_ready)
        self.assertIn("0 exemplar", self.state.exemplar_paging)
        self.assertEqual(self.state.message, "")
        self.assertFalse(self.state.can_create)

    async def test_submit_uses_server_selected_ids_and_preserves_audit_warning(self):
        await self.choose()
        self.mocks["create_rental"].return_value = (RENTAL, False)
        await consume(self.state.submit())
        token, payload = self.mocks["create_rental"].await_args.args
        self.assertEqual(token, "private-session-token")
        self.assertEqual(set(payload), set(PAYLOAD))
        self.assertEqual(payload["due_at"], PAYLOAD["due_at"])
        self.assertNotIn("registered_by", payload)
        self.assertIn("auditoria não foi confirmada", self.state.notice)
        self.assertIn("Locação #3", self.state.confirmation)
        self.assertFalse(self.state._pending)

    async def test_forged_selection_blocked_before_post(self):
        await self.choose()
        self.state.customer_choice = "999 | Cliente inventado"
        await consume(self.state.submit())
        self.mocks["create_rental"].assert_not_awaited()

    async def test_blocked_or_inactive_customer_cannot_be_submitted(self):
        for changes in ({"status": "inactive"}, {"bloqueio_manual_ativo": True}):
            with self.subTest(changes=changes):
                await self.choose()
                self.state._customers = [{**CUSTOMER, **changes}]
                await consume(self.state.submit())
        self.mocks["create_rental"].assert_not_awaited()

    async def test_double_event_does_not_issue_two_posts(self):
        await self.choose()
        first = self.state.submit()
        await anext(first)
        await consume(self.state.submit())
        self.mocks["create_rental"].assert_not_awaited()
        await consume(first)
        self.mocks["create_rental"].assert_awaited_once()

    async def test_timeout_preserves_key_and_payload_despite_public_form_tampering(self):
        await self.choose()
        self.mocks["create_rental"].side_effect = RentalError("unknown")
        await consume(self.state.submit())
        original = dict(self.state._pending)
        self.assertTrue(self.state.uncertain)
        self.state.customer_choice = "99 | Alterado"
        self.state.due_local = "2030-01-10T12:00"
        await consume(self.state.load_new())
        self.assertEqual(dict(self.state._pending), original)
        await consume(self.state.submit())
        self.assertEqual(self.mocks["create_rental"].await_count, 1)
        self.mocks["create_rental"].side_effect = None
        await consume(self.state.repeat_pending())
        self.assertEqual(self.mocks["create_rental"].await_args.args[1], original)
        self.assertFalse(self.state._pending)
        self.assertFalse(self.state.uncertain)

    async def test_unknown_reconciles_without_new_post(self):
        self.state._pending = PAYLOAD.copy()
        self.state._unknown = True
        await consume(self.state.reconcile())
        self.mocks["reconcile_rental"].assert_awaited_once_with("private-session-token", KEY)
        self.mocks["create_rental"].assert_not_awaited()
        self.assertIn("Locação #3", self.state.confirmation)
        self.assertFalse(self.state._pending)

    async def test_reconciliation_notfound_keeps_attempt_until_resolved(self):
        self.state._pending = PAYLOAD.copy()
        self.mocks["reconcile_rental"].side_effect = RentalError("notfound")
        await consume(self.state.reconcile())
        self.assertEqual(dict(self.state._pending), PAYLOAD)
        self.assertIn("processamento", self.state.message)

    async def test_disabling_writes_does_not_lose_an_earlier_unknown_attempt(self):
        self.state._pending = PAYLOAD.copy()
        self.state._unknown = True
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}):
            await consume(self.state.repeat_pending())
        self.assertEqual(dict(self.state._pending), PAYLOAD)
        self.assertTrue(self.state.uncertain)
        self.mocks["create_rental"].assert_not_awaited()

    async def test_reconciliation_mismatched_rental_does_not_confirm(self):
        self.state._pending = PAYLOAD.copy()
        self.mocks["reconcile_rental"].return_value = {**RENTAL, "customer_id": 99}
        await consume(self.state.reconcile())
        self.assertFalse(self.state._rental)
        self.assertTrue(self.state._pending)

    async def test_conflict_clears_selection_for_refresh_without_success(self):
        await self.choose()
        self.mocks["create_rental"].side_effect = RentalError("conflict")
        await consume(self.state.submit())
        self.assertFalse(self.state._pending)
        self.assertFalse(self.state._rental)
        self.assertEqual(self.state.exemplar_options, [])

    async def test_logout_discards_late_creation_response(self):
        await self.choose()
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args):
            started.set()
            await release.wait()
            return RENTAL, True

        self.mocks["create_rental"].side_effect = delayed
        task = asyncio.create_task(consume(self.state.submit()))
        await started.wait()
        await self.session.logout()
        release.set()
        await task
        self.assertFalse(self.state._pending)
        self.assertFalse(self.state._rental)
        self.assertEqual(self.state.confirmation, "")
        self.assertFalse(self.state.loading)

    async def test_changed_account_discards_late_options(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            started.set()
            await release.wait()
            return {"items": [EXEMPLAR], "page": 1, "per_page": 20, "total": 1}

        self.mocks["available_exemplars"].side_effect = delayed
        task = asyncio.create_task(consume(self.state.load_new()))
        await started.wait()
        self.session._set_user({**ME, "id": 10})
        await self.session._sync_dashboard_session()
        release.set()
        await task
        self.assertEqual(self.state.customer_options, [])
        self.assertEqual(self.state.exemplar_options, [])

    async def test_inactive_user_revokes_session_before_data(self):
        self.mocks["get_me_xano"].return_value = {**ME, "is_active": False}
        await consume(self.state.load_new())
        self.assertEqual(self.session._xano_auth_token, "")
        self.mocks["list_customers_xano"].assert_not_awaited()

    async def test_member_cannot_submit_admin_condition_directly(self):
        self.state._admin_exemplars = [EXEMPLAR]
        self.state.condition_exemplar = _exemplar_label(EXEMPLAR)
        self.state.condition_reason = "Tentativa local"
        await consume(self.state.save_condition())
        self.mocks["confirm_condition"].assert_not_awaited()
        self.assertIn("permissão", self.state.message)

    async def test_admin_condition_is_separate_from_rental_creation(self):
        self.session._user_role = "admin"
        self.mocks["get_me_xano"].return_value = {**ME, "role": "admin"}
        await self.choose()
        self.state.capture_condition_exemplar(_exemplar_label(EXEMPLAR))
        self.state.capture_condition("available")
        self.state.capture_reason("Exemplar conferido para teste local")
        self.mocks["confirm_condition"].return_value = False
        await consume(self.state.save_condition())
        self.mocks["confirm_condition"].assert_awaited_once()
        self.mocks["create_rental"].assert_not_awaited()
        self.assertIn("auditoria não confirmada", self.state.notice)

    async def test_routes_and_visual_components_render(self):
        from ProjetoLocadora.ProjetoLocadora import rental_detail_page, rental_registration_page

        rendered = str(rental_registration_page()) + str(rental_detail_page())
        rendered = re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), rendered)
        for text in ("Confirmar locação", "horário de Brasília", "Consultar tentativa", "Conferir condição", "/backoffice"):
            self.assertIn(text, rendered)
        self.assertNotIn("private-session-token", rendered)
