"""Estado Reflex real com APIs substituídas por doubles apenas neste processo."""

import asyncio
import os
import re
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.xano_client import XanoCustomerError, XanoExemplarError, XanoSessionUnavailable
from ProjetoLocadora.locacoes_state import PAGE_SIZE, LocacoesState, _customer_label, _exemplar_label
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
            "list_rentals": {"items": [RENTAL], "total": 1, "page": 1, "per_page": PAGE_SIZE},
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
        await consume(self.state.load_admin_exemplars())
        self.state.capture_condition_exemplar(_exemplar_label(EXEMPLAR))
        self.state.capture_condition("available")
        self.state.capture_reason("Exemplar conferido para teste local")
        self.mocks["confirm_condition"].return_value = False
        await consume(self.state.save_condition())
        self.mocks["confirm_condition"].assert_awaited_once()
        self.mocks["create_rental"].assert_not_awaited()
        self.assertIn("auditoria não confirmada", self.state.notice)

    async def test_condition_without_reason_or_exemplar_explains_and_sends_nothing(self):
        self.session._user_role = "admin"
        self.mocks["get_me_xano"].return_value = {**ME, "role": "admin"}
        await self.choose()
        await consume(self.state.load_admin_exemplars())
        me_calls = self.mocks["get_me_xano"].await_count

        self.state.capture_condition("available")
        await consume(self.state.save_condition())
        self.assertEqual(self.state.message, "Selecione o exemplar conferido.")

        self.state.capture_condition_exemplar(_exemplar_label(EXEMPLAR))
        self.state.capture_reason("   ")
        await consume(self.state.save_condition())
        self.assertIn("Informe o motivo da confirmação", self.state.message)
        self.assertNotIn("vencimento", self.state.message)

        # Nada foi enviado: nem conferência de sessão nem gravação.
        self.mocks["confirm_condition"].assert_not_awaited()
        self.assertEqual(self.mocks["get_me_xano"].await_count, me_calls)
        self.assertFalse(self.state.loading)

    async def test_form_issues_gate_the_confirm_button(self):
        await consume(self.state.load_new())
        self.assertFalse(self.state.can_create)
        self.assertEqual(
            self.state.form_issues,
            ["Selecione um cliente.", "Selecione um exemplar disponível.", "Informe a data e hora de vencimento."],
        )
        self.state.capture_customer(_customer_label(CUSTOMER))
        self.state.capture_exemplar(_exemplar_label(EXEMPLAR))
        self.state.capture_due("2030-13-45T99:00")
        self.assertFalse(self.state.can_create)
        self.assertEqual(self.state.form_issues, ["Data ou hora de vencimento inválida."])
        self.state.capture_due("2020-01-02T12:00")
        self.assertIn("O vencimento deve ser posterior ao momento atual.", self.state.form_issues)
        self.assertFalse(self.state.can_create)
        self.state.capture_due("2030-01-02T12:00")
        self.assertEqual(self.state.form_issues, [])
        self.assertTrue(self.state.can_create)

    async def test_inactive_or_blocked_selection_is_reported_and_disables_confirm(self):
        for changes, text in (({"status": "inactive"}, "inativo"), ({"bloqueio_manual_ativo": True}, "bloqueado")):
            with self.subTest(changes=changes):
                customer = {**CUSTOMER, **changes}
                self.mocks["list_customers_xano"].return_value = {"items": [customer], "total": 1, "page": 1, "per_page": 20}
                await self.choose()
                self.state.customer_choice = _customer_label(customer)
                self.state.capture_customer(_customer_label(customer))
                self.assertTrue(any(text in issue for issue in self.state.form_issues))
                self.assertFalse(self.state.can_create)

    async def test_writes_disabled_keeps_valid_form_unsubmittable(self):
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}):
            await self.choose()
            self.assertEqual(self.state.form_issues, [])
            self.assertFalse(self.state.can_create)

    async def test_paging_customers_keeps_exemplar_and_customer_selection(self):
        await self.choose()
        other = {**CUSTOMER, "id": 7, "nome": "Outra pessoa"}
        self.mocks["list_customers_xano"].return_value = {"items": [other], "total": 40, "page": 2, "per_page": 20}
        self.mocks["available_exemplars"].reset_mock()
        await consume(self.state.customer_page(1))
        self.mocks["available_exemplars"].assert_not_awaited()
        self.assertEqual(self.state.exemplar_choice, _exemplar_label(EXEMPLAR))
        self.assertEqual(self.state.customer_choice, _customer_label(CUSTOMER))
        self.assertIn(_customer_label(CUSTOMER), self.state.customer_options)
        self.assertEqual(self.state.form_issues, [])
        await consume(self.state.submit())
        self.assertEqual(self.mocks["create_rental"].await_args.args[1]["customer_id"], CUSTOMER["id"])

    async def test_paging_exemplars_keeps_customer_and_exemplar_selection(self):
        await self.choose()
        other = {**EXEMPLAR, "id": 8, "identificador": "LOCAL-8"}
        self.mocks["available_exemplars"].return_value = {"items": [other], "total": 40, "page": 2, "per_page": 20}
        self.mocks["list_customers_xano"].reset_mock()
        await consume(self.state.exemplar_page(1))
        self.mocks["list_customers_xano"].assert_not_awaited()
        self.assertEqual(self.state.customer_choice, _customer_label(CUSTOMER))
        self.assertEqual(self.state.exemplar_choice, _exemplar_label(EXEMPLAR))
        self.assertIn(_exemplar_label(EXEMPLAR), self.state.exemplar_options)

    async def test_selection_that_disappears_from_its_own_page_is_dropped(self):
        await self.choose()
        self.mocks["available_exemplars"].return_value = {"items": [], "total": 0, "page": 1, "per_page": 20}
        await consume(self.state.search_customers())  # recarrega só clientes: exemplar permanece
        self.assertEqual(self.state.exemplar_choice, _exemplar_label(EXEMPLAR))
        self.state._exemplar_page = 1
        await consume(self.state._load_options(customers=False))  # exemplar sumiu da página em que foi escolhido
        self.assertEqual(self.state.exemplar_choice, "")
        self.assertEqual(self.state.customer_choice, _customer_label(CUSTOMER))
        self.assertIn("Selecione um exemplar disponível.", self.state.form_issues)

    async def test_refreshed_customer_that_became_blocked_is_flagged(self):
        await self.choose()
        blocked = {**CUSTOMER, "bloqueio_manual_ativo": True}
        self.mocks["list_customers_xano"].return_value = {"items": [blocked], "total": 1, "page": 1, "per_page": 20}
        await consume(self.state.search_customers())
        self.assertIn("O cliente selecionado está bloqueado.", self.state.form_issues)
        self.assertFalse(self.state.can_create)

    async def test_transient_session_check_failure_does_not_log_out_or_invent_options(self):
        self.mocks["get_me_xano"].side_effect = XanoSessionUnavailable("rede")
        await consume(self.state.load_new())
        self.assertIn("Não foi possível consultar o serviço de locações.", self.state.message)
        self.assertEqual(self.session._xano_auth_token, "private-session-token")
        self.assertEqual(self.session._user_id, "9")
        self.assertEqual(self.state.customer_options, [])
        self.mocks["list_customers_xano"].assert_not_awaited()
        # nova tentativa após a rede voltar carrega as opções reais
        self.mocks["get_me_xano"].side_effect = None
        await consume(self.state.load_new())
        self.assertEqual(self.state.message, "")
        self.assertEqual(self.state.customer_options, [_customer_label(CUSTOMER)])

    async def test_options_are_requested_with_the_ten_item_page_size(self):
        self.assertEqual(PAGE_SIZE, 10)
        await consume(self.state.load_new())
        self.assertEqual(self.mocks["list_customers_xano"].await_args.kwargs["per_page"], 10)
        self.assertEqual(self.mocks["available_exemplars"].await_args.args[2], 10)

    async def test_pagination_only_when_more_than_one_page(self):
        await consume(self.state.load_new())
        self.assertFalse(self.state.customer_paginated)
        self.assertFalse(self.state.exemplar_paginated)
        self.mocks["list_customers_xano"].return_value = {"items": [CUSTOMER], "total": 11, "page": 1, "per_page": 10}
        await consume(self.state.search_customers())
        self.assertTrue(self.state.customer_paginated)
        self.assertTrue(self.state.customer_next)
        self.assertFalse(self.state.customer_previous)
        await consume(self.state.customer_page(1))
        self.assertEqual(self.state._customer_page, 2)
        self.assertFalse(self.state.customer_next)  # 2 * 10 >= 11

    async def test_customer_cards_disable_ineligible_with_reason_and_mask_cpf(self):
        rows = [CUSTOMER, {**CUSTOMER, "id": 2, "nome": "Inativo", "status": "inactive"},
                {**CUSTOMER, "id": 3, "nome": "Bloqueado", "bloqueio_manual_ativo": True},
                {**CUSTOMER, "id": 4, "nome": "Ambos", "status": "inactive", "bloqueio_manual_ativo": True}]
        self.mocks["list_customers_xano"].return_value = {"items": rows, "total": 4, "page": 1, "per_page": 10}
        await consume(self.state.load_new())
        cards = {c["name"]: c for c in self.state.customer_cards}
        self.assertFalse(cards["Cliente local"]["disabled"])
        self.assertEqual(cards["Inativo"]["reason"], "Inativo")
        self.assertEqual(cards["Bloqueado"]["reason"], "Bloqueado")
        self.assertEqual(cards["Ambos"]["reason"], "Inativo e Bloqueado")
        self.assertTrue(all(c["disabled"] for n, c in cards.items() if n != "Cliente local"))
        self.assertTrue(all(c["cpf"].startswith("***") for c in cards.values()))

    async def test_selected_card_is_highlighted_and_summaries_are_human_readable(self):
        await self.choose()
        self.assertTrue(self.state.customer_cards[0]["selected"])
        self.assertTrue(self.state.exemplar_cards[0]["selected"])
        self.assertEqual(self.state.customer_summary, "Cliente local · ***.***.***-00")
        self.assertEqual(self.state.exemplar_summary, "LOCAL-2 · Filme local")
        self.assertEqual(self.state.due_summary, "02/01/2030 às 12:00")

    async def test_due_summary_is_empty_for_invalid_or_past_values(self):
        await consume(self.state.load_new())
        for value in ("", "2020-01-02T12:00", "2030-13-45T99:00"):
            with self.subTest(value=value):
                self.state.capture_due(value)
                self.assertEqual(self.state.due_summary, "")

    async def test_progress_follows_the_real_pending_fields(self):
        def states():
            return [step["state"] for step in self.state.steps]

        await consume(self.state.load_new())
        self.assertEqual(states(), ["current", "todo", "todo"])
        self.state.capture_customer(_customer_label(CUSTOMER))
        self.assertEqual(states(), ["done", "current", "todo"])
        self.state.capture_exemplar(_exemplar_label(EXEMPLAR))
        self.assertEqual(states(), ["done", "done", "current"])
        self.state.capture_due("2030-01-02T12:00")
        self.assertEqual(states(), ["done", "done", "done"])

    async def test_blocked_writes_flag_follows_configuration_without_enabling_submit(self):
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}):
            await self.choose()
            self.assertTrue(self.state.writes_blocked)
            self.assertFalse(self.state.can_create)
        await consume(self.state.load_new())
        self.assertFalse(self.state.writes_blocked)

    async def test_new_search_keeps_selected_customer_even_when_results_do_not_match(self):
        await self.choose()
        self.mocks["list_customers_xano"].return_value = {"items": [], "total": 0, "page": 1, "per_page": 10}
        self.state.capture_customer_search("sem correspondência")
        await consume(self.state.search_customers())
        self.assertEqual(self.state.customer_cards, [])
        self.assertEqual(self.state.customer_choice, _customer_label(CUSTOMER))
        self.assertEqual(self.state.exemplar_choice, _exemplar_label(EXEMPLAR))
        self.assertEqual(self.state.form_issues, [])
        self.assertEqual(self.state.customer_summary, "Cliente local · ***.***.***-00")

    async def test_opening_the_page_makes_no_admin_list_request(self):
        self.session._user_role = "admin"
        self.mocks["get_me_xano"].return_value = {**ME, "role": "admin"}
        await consume(self.state.load_new())
        self.mocks["list_exemplares_xano"].assert_not_awaited()
        self.assertEqual(self.mocks["list_customers_xano"].await_count, 1)
        self.assertEqual(self.mocks["available_exemplars"].await_count, 1)
        self.assertEqual(self.mocks["get_me_xano"].await_count, 1)
        self.assertEqual(self.state.customer_options, [_customer_label(CUSTOMER)])

    async def test_admin_list_loads_on_demand_and_its_failure_does_not_hide_options(self):
        self.session._user_role = "admin"
        self.mocks["get_me_xano"].return_value = {**ME, "role": "admin"}
        await consume(self.state.load_new())
        self.mocks["list_exemplares_xano"].side_effect = XanoExemplarError("falha")
        await consume(self.state.load_admin_exemplars())
        self.assertIn("exemplares para conferência", self.state.message)
        self.assertFalse(self.state.admin_loaded)
        self.assertEqual(self.state.customer_options, [_customer_label(CUSTOMER)])
        self.assertEqual(self.state.exemplar_options, [_exemplar_label(EXEMPLAR)])
        self.mocks["list_exemplares_xano"].side_effect = None
        await consume(self.state.load_admin_exemplars())
        self.assertTrue(self.state.admin_loaded)
        self.assertEqual(self.state.admin_exemplar_options, [_exemplar_label(EXEMPLAR)])

    async def test_member_cannot_load_admin_list(self):
        await consume(self.state.load_admin_exemplars())
        self.mocks["list_exemplares_xano"].assert_not_awaited()
        self.assertIn("permissão", self.state.message)

    async def test_customers_429_shows_limit_and_blocks_new_reads_until_retry_after(self):
        self.mocks["list_customers_xano"].side_effect = XanoCustomerError("limite", retry_after=20)
        with patch("ProjetoLocadora.locacoes_state.time.monotonic", return_value=1000.0):
            await consume(self.state.load_new())
        self.assertIn("limite de requisições", self.state.message)
        self.assertIn("20 s", self.state.message)
        self.assertEqual(self.session._xano_auth_token, "private-session-token")
        self.mocks["list_customers_xano"].side_effect = None
        calls = self.mocks["get_me_xano"].await_count
        with patch("ProjetoLocadora.locacoes_state.time.monotonic", return_value=1010.0):
            await consume(self.state.load_new())  # “Tentar novamente” antes do prazo
        self.assertEqual(self.mocks["get_me_xano"].await_count, calls)  # nenhuma requisição
        self.assertIn("aguarde mais 10 s", self.state.message)
        with patch("ProjetoLocadora.locacoes_state.time.monotonic", return_value=1021.0):
            await consume(self.state.load_new())
        self.assertEqual(self.state.message, "")
        self.assertEqual(self.state.customer_options, [_customer_label(CUSTOMER)])

    async def test_available_exemplars_429_is_reported_as_rate_limit(self):
        self.mocks["available_exemplars"].side_effect = RentalError("ratelimited", retry_after=20)
        await consume(self.state.load_new())
        self.assertIn("limite de requisições", self.state.message)
        self.assertEqual(self.session._xano_auth_token, "private-session-token")

    async def test_session_check_429_is_reported_without_logout(self):
        self.mocks["get_me_xano"].side_effect = XanoSessionUnavailable("limite", retry_after=20)
        await consume(self.state.load_new())
        self.assertIn("limite de requisições", self.state.message)
        self.assertEqual(self.session._user_id, "9")
        self.mocks["list_customers_xano"].assert_not_awaited()

    async def test_non_rate_limit_customer_error_names_the_failing_operation(self):
        self.mocks["list_customers_xano"].side_effect = XanoCustomerError("Rota de clientes não encontrada.")
        await consume(self.state.load_new())
        self.assertEqual(self.state.message, "Não foi possível carregar os clientes. Rota de clientes não encontrada.")

    async def test_routes_and_visual_components_render(self):
        from ProjetoLocadora.ProjetoLocadora import rental_detail_page, rental_registration_page

        rendered = str(rental_registration_page()) + str(rental_detail_page())
        rendered = re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), rendered)
        for text in ("Confirmar locação", "horário de Brasília", "Consultar tentativa", "Conferir condição", "/backoffice"):
            self.assertIn(text, rendered)
        self.assertNotIn("private-session-token", rendered)
