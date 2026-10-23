"""Locações registradas: cliente, estado, tela e endpoint. HTTP e Xano substituídos por doubles locais."""

import os
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import reflex as rx

from ProjetoLocadora import locacoes_client as client
from ProjetoLocadora.ProjetoLocadora import State, dashboard_topbar
from ProjetoLocadora.locacoes_client import RentalError
from ProjetoLocadora.locacoes_state import PAGE_SIZE, LocacoesState
from ProjetoLocadora.locacoes_ui import registration
from tests.test_locacoes_client import ACTIVE_13, RETURNED
from tests.test_locacoes_state import CUSTOMER, EXEMPLAR, ME, consume
from tests.test_locacoes_xano_contract import RETURN_FIELDS_13, body, calls, unique_assignment

XANO = Path(__file__).resolve().parents[1] / "xano" / "xano"


def page(items, total=None, number=1, per_page=PAGE_SIZE):
    return {"items": items, "page": number, "per_page": per_page, "total": len(items) if total is None else total}


class TestListRentalsClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Trava fechada: a listagem é leitura e não depende dela.
        env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "false"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.real_client = httpx.AsyncClient
        self.requests = []

    async def call(self, response, number=1, status=""):
        def transport(request):
            self.requests.append(request)
            return response

        def factory(**kwargs):
            return self.real_client(**kwargs, transport=httpx.MockTransport(transport))

        with patch.object(client.httpx, "AsyncClient", side_effect=factory):
            return await client.list_rentals("private-token", number, PAGE_SIZE, status=status)

    async def test_reads_one_page_with_the_detail_contract(self):
        result = await self.call(httpx.Response(200, json=page([RETURNED, {**ACTIVE_13, "id": 2}], total=12)))
        self.assertEqual([r["id"] for r in result["items"]], [3, 2])
        self.assertEqual(result["total"], 12)
        request = self.requests[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.path, "/api:rentals/locacoes")
        self.assertEqual(dict(request.url.params), {"page": "1", "per_page": str(PAGE_SIZE)})
        self.assertEqual(request.headers["Authorization"], "Bearer private-token")

    async def test_invalid_pages_are_rejected_without_partial_data(self):
        invalid = [
            {"items": [ACTIVE_13], "page": 1, "per_page": PAGE_SIZE},                      # sem total
            page([ACTIVE_13], number=2),                                                   # página trocada
            page([ACTIVE_13], total=0),                                                    # total menor que itens
            page([ACTIVE_13, ACTIVE_13]),                                                  # id repetido
            page([{**ACTIVE_13, "cpf": "000"}]),                                           # dado pessoal extra
            page([{**ACTIVE_13, "returned_by": 9}]),                                       # ativa com devolução
            page([ACTIVE_13] * (PAGE_SIZE + 1)),                                           # mais itens que a página
            [ACTIVE_13],
        ]
        for data in invalid:
            with self.subTest(data=str(data)[:60]), self.assertRaises(RentalError) as error:
                await self.call(httpx.Response(200, json=data))
            self.assertEqual(error.exception.category, "invalid")

    async def test_status_filter_is_sent_and_enforced(self):
        await self.call(httpx.Response(200, json=page([RETURNED])), status="returned")
        self.assertEqual(dict(self.requests[-1].url.params), {"page": "1", "per_page": str(PAGE_SIZE), "status": "returned"})
        # Serviço que ignorasse o filtro misturaria as abas: resposta rejeitada.
        with self.assertRaises(RentalError) as error:
            await self.call(httpx.Response(200, json=page([RETURNED])), status="active")
        self.assertEqual(error.exception.category, "invalid")
        sent = len(self.requests)
        with self.assertRaises(RentalError) as error:
            await self.call(httpx.Response(200, json=page([])), status="xpto")
        self.assertEqual((error.exception.category, len(self.requests)), ("input", sent))

    async def test_missing_route_and_rate_limit_are_reported(self):
        with self.assertRaises(RentalError) as error:
            await self.call(httpx.Response(404, json={"message": "Unable to locate request."}))
        self.assertEqual(error.exception.category, "notfound")
        with self.assertRaises(RentalError) as error:
            await self.call(httpx.Response(429, json={}))
        self.assertEqual(error.exception.category, "ratelimited")


class TestRentalListState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(LocacoesState)
        self.session = await self.root.get_state(State)
        self.session._user_id = "9"
        self.session._user_role = "member"
        self.session._xano_auth_token = "private-session-token"
        env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.mocks = {}
        values = {
            "get_me_xano": ME,
            "list_customers_xano": {"items": [CUSTOMER], "total": 1, "page": 1, "per_page": PAGE_SIZE},
            "available_exemplars": {"items": [EXEMPLAR], "total": 1, "page": 1, "per_page": PAGE_SIZE},
            "create_rental": ({**ACTIVE_13, "id": 4}, True),
            "list_rentals": page([RETURNED, {**ACTIVE_13, "id": 2}]),
        }
        for name, value in values.items():
            p = patch(f"ProjetoLocadora.locacoes_state.{name}", new_callable=AsyncMock)
            self.mocks[name] = p.start()
            self.mocks[name].return_value = value
            self.addCleanup(p.stop)

    async def test_opening_the_page_lists_registered_rentals_with_detail_links(self):
        await consume(self.state.load_new())
        self.assertEqual(self.state.list_state, "ready")
        rows = self.state.rental_rows
        self.assertEqual([r["number"] for r in rows], ["#3", "#2"])
        self.assertEqual(rows[0]["href"], "/locacoes/3")
        self.assertEqual(rows[0]["status"], "Devolvida")
        self.assertEqual(rows[0]["done"], "1")
        self.assertEqual(rows[1]["status"], "Ativa")
        self.assertEqual(rows[0]["film"], RETURNED["film_title"])
        self.assertEqual(rows[0]["exemplar"], RETURNED["exemplar_identifier"])
        self.assertEqual(rows[0]["customer"], RETURNED["customer_name"])
        self.assertEqual(self.mocks["list_rentals"].await_args.args, ("private-session-token", 1, PAGE_SIZE))
        self.assertEqual(self.mocks["get_me_xano"].await_count, 1)  # a lista reaproveita a conferência recente

    async def test_tabs_filter_in_xano_and_keep_counts(self):
        self.mocks["list_rentals"].return_value = page([{**ACTIVE_13, "id": 2}], total=1)
        await consume(self.state.load_new())
        self.assertEqual(self.state.list_tab, "active")
        self.assertEqual(self.mocks["list_rentals"].await_args.kwargs, {"status": "active"})
        self.assertEqual(self.state.tab_active_label, "Ativas (1)")
        self.assertEqual(self.state.tab_returned_label, "Devolvidas")

        self.mocks["list_rentals"].return_value = page([RETURNED], total=1)
        await consume(self.state.set_list_tab("returned"))
        self.assertEqual(self.mocks["list_rentals"].await_args.args[1], 1)
        self.assertEqual(self.mocks["list_rentals"].await_args.kwargs, {"status": "returned"})
        self.assertEqual(self.state.tab_returned_label, "Devolvidas (1)")
        self.assertEqual(self.state.tab_active_label, "Ativas (1)")
        self.assertTrue(self.state.rental_rows[0]["when"].startswith("Devolvida "))

        calls = self.mocks["list_rentals"].await_count
        await consume(self.state.set_list_tab("returned"))  # mesma aba: nada a buscar
        await consume(self.state.set_list_tab("xpto"))
        self.assertEqual(self.mocks["list_rentals"].await_count, calls)

    async def test_new_registration_returns_to_the_active_tab(self):
        await consume(self.state.load_new())
        self.state.list_tab = "returned"
        await consume(self.state._refresh_list_after_registration())
        self.assertEqual(self.state.list_tab, "active")
        self.assertEqual(self.mocks["list_rentals"].await_args.kwargs, {"status": "active"})

    async def test_empty_list_is_not_an_error(self):
        self.mocks["list_rentals"].return_value = page([])
        await consume(self.state.load_new())
        self.assertEqual(self.state.list_state, "empty")
        self.assertEqual(self.state.rental_rows, [])

    async def test_list_failure_is_isolated_from_the_form(self):
        cases = {
            "notfound": "ainda não está disponível",
            "unavailable": "Não foi possível carregar as locações",
            "invalid": "Não foi possível carregar as locações",
        }
        for category, text in cases.items():
            with self.subTest(category=category):
                self.mocks["list_rentals"].side_effect = RentalError(category)
                await consume(self.state.load_new())
                self.assertEqual(self.state.list_state, "error")
                self.assertIn(text, self.state.list_message)
                self.assertTrue(self.state.options_loaded)  # formulário segue utilizável
                self.assertEqual(self.state.message, "")
                self.assertEqual(self.state.rental_rows, [])

    async def test_rate_limit_waits_before_a_new_list_request(self):
        self.mocks["list_rentals"].side_effect = RentalError("ratelimited", retry_after=20)
        await consume(self.state.load_new())
        self.assertIn("limite de requisições", self.state.list_message)
        self.mocks["list_rentals"].side_effect = None
        await consume(self.state.load_rentals())
        self.assertEqual(self.mocks["list_rentals"].await_count, 1)
        self.assertEqual(self.state.list_state, "error")

    async def test_successful_registration_refreshes_the_first_page(self):
        await consume(self.state.load_new())
        self.mocks["list_rentals"].return_value = page([{**ACTIVE_13, "id": 4}, RETURNED], total=2)
        self.state.capture_customer(self.state.customer_options[0])
        self.state.capture_exemplar(self.state.exemplar_options[0])
        self.state.capture_due("2030-01-02T12:00")
        await consume(self.state.submit())
        self.assertEqual(self.mocks["create_rental"].await_count, 1)
        self.assertEqual(self.mocks["list_rentals"].await_count, 2)
        self.assertEqual(self.mocks["list_rentals"].await_args.args[1], 1)
        self.assertEqual(self.state.rental_rows[0]["number"], "#4")

    async def test_failed_or_blocked_registration_does_not_refresh(self):
        await consume(self.state.load_new())
        self.mocks["create_rental"].side_effect = RentalError("input")
        self.state.capture_customer(self.state.customer_options[0])
        self.state.capture_exemplar(self.state.exemplar_options[0])
        self.state.capture_due("2030-01-02T12:00")
        await consume(self.state.submit())
        self.assertEqual(self.mocks["list_rentals"].await_count, 1)

    async def test_older_rentals_are_reachable_by_page(self):
        self.mocks["list_rentals"].return_value = page([{**ACTIVE_13, "id": n} for n in range(25, 15, -1)], total=25)
        await consume(self.state.load_new())
        self.assertTrue(self.state.list_paginated)
        self.assertFalse(self.state.list_previous)
        self.assertTrue(self.state.list_next)
        self.mocks["list_rentals"].return_value = page([{**ACTIVE_13, "id": n} for n in range(15, 5, -1)], total=25, number=2)
        await consume(self.state.rentals_page(1))
        self.assertEqual(self.mocks["list_rentals"].await_args.args[1], 2)
        self.assertEqual(self.state.rental_rows[0]["number"], "#15")
        self.assertEqual(self.state.list_paging, "Página 2 · 25 locação(ões)")
        await consume(self.state.rentals_page(-1))
        self.assertEqual(self.mocks["list_rentals"].await_args.args[1], 1)
        for direction in (0, 2, -1):
            await consume(self.state.rentals_page(direction))  # fora dos limites: sem requisição
        self.assertEqual(self.mocks["list_rentals"].await_count, 3)

    async def test_logout_discards_the_list_and_late_responses(self):
        await consume(self.state.load_new())

        async def late(token, number, per_page, status=""):
            await self.session.logout()
            return page([ACTIVE_13])

        self.mocks["list_rentals"].side_effect = late
        await consume(self.state.load_rentals())
        self.assertEqual(self.state.rental_rows, [])
        self.assertEqual(self.state.list_state, "idle")
        self.assertNotIn("private-session-token", str(self.state.dict()))

    async def test_session_rejection_clears_the_session_and_the_list(self):
        self.mocks["list_rentals"].side_effect = RentalError("authentication")
        await consume(self.state.load_new())
        self.assertEqual(self.session._xano_auth_token, "")
        self.assertEqual(self.state.rental_rows, [])
        self.assertNotEqual(self.state.list_state, "ready")


class TestRentalListPage(unittest.TestCase):
    def test_section_lives_on_the_registration_page_with_states_and_detail_link(self):
        text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), str(registration(State.user_role == "admin", dashboard_topbar("/locacoes/nova"))))
        for expected in ("Locações registradas", "Carregando locações…", "Nenhuma locação ativa", "Nenhuma locação devolvida",
                         "Atualizar lista", "Lista de locações", " · Exemplar ", "Abrir detalhes da locação",
                         "Situação das locações", "vitrine-locacoes__tab", "vitrine-locacoes__row",
                         "vitrine-locacoes__item", "Locações anteriores", "Próximas locações"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        # Formulário mantido; a lista divide a área de trabalho com ele (coluna lateral no desktop).
        self.assertLess(text.index("vitrine-locacoes__workspace"), text.index("vitrine-locacoes__flow"))
        self.assertLess(text.index("Vencimento e confirmação"), text.index("Locações registradas"))
        self.assertIn("Confirmar locação", text)

    def test_styles_put_the_list_beside_the_form_on_wide_screens(self):
        css = (Path(__file__).resolve().parents[1] / "assets" / "locacoes.css").read_text(encoding="utf-8")
        for selector in (".vitrine-locacoes__workspace", ".vitrine-locacoes__list ", ".vitrine-locacoes__item ", "@media (min-width: 1180px)", "position: sticky"):
            self.assertIn(selector, css)


class TestListEndpointContract(unittest.TestCase):
    def setUp(self):
        self.source = (XANO / "api/locacoes/locacoes_GET.xs").read_text(encoding="utf-8")
        self.endpoint = body(self.source)
        self.stack = next(calls(self.endpoint, "stack"))[1]

    def test_authenticated_member_read_only_paginated_newest_first(self):
        self.assertTrue(self.source.startswith("// ") or self.source.startswith("query"))
        self.assertIn('query "locacoes" verb=GET', self.source)
        self.assertEqual(unique_assignment(self.endpoint, "auth"), '"user"')
        self.assertEqual(self.stack[:2], ("function.run", '"Quick Start/enforce_role"'))
        self.assertIn('required_role: "member"', self.source)
        for statement in ("db.add", "db.edit", "db.del", "db.patch", "db.transaction"):
            self.assertEqual(list(calls(self.stack, statement)), [], statement)
        self.assertIn('sort = {rental.id: "desc"}', self.source)
        self.assertIn("$input.per_page <= 50", self.source)
        self.assertIn('error_type = "inputerror"', self.source)

    def test_optional_status_filter_is_validated(self):
        self.assertIn("text status? filters=trim", self.source)
        self.assertIn('$status == "" || $status == "active" || $status == "returned"', self.source)
        self.assertIn('where = $status == "" || $db.rental.status == $status', self.source)

    def test_projection_is_the_13_field_detail_contract_without_personal_data(self):
        expected = [f'"items.{field}"' for field in re.findall(r'"(\w+)"', RETURN_FIELDS_13)]
        outputs = re.findall(r"^\s*output = \[(.*)\]$", self.source, re.MULTILINE)
        self.assertEqual(len(outputs), 1)
        output = [token.strip() for token in outputs[0].split(",")]
        for field in expected:
            self.assertIn(field, output)
        self.assertEqual(len([token for token in output if token.startswith('"items.')]), 13)
        for prohibited in ("cpf", "email", "telefone", "operation_key", "condition_reason"):
            self.assertNotIn(prohibited, self.source)


if __name__ == "__main__":
    unittest.main()
