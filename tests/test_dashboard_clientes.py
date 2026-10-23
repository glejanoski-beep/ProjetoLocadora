"""Dashboard de clientes: cálculo, estado e ranking. Listagens e sessão substituídas por doubles locais."""

import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.dashboard_state import (
    CLIENTES_LISTADOS, CLIENTES_PAGINAS_MAX, CLIENTES_POR_PAGINA, DashboardState,
    locacoes_vencidas, ranking_clientes, resumir_clientes,
)
from ProjetoLocadora.xano_client import XanoCustomerError
from tests.test_dashboard_locacoes import NOW, ms, rental

ME = {"id": 1, "role": "member", "is_active": True}


def customer(cid, status="active", blocked=False):
    return {
        "id": cid, "nome": f"Cliente local {cid}", "cpf_mascarado": "***.***.***-00",
        "status": status, "bloqueio_manual_ativo": blocked,
    }


def page(items, total=None, number=1):
    return {"items": items, "page": number, "per_page": CLIENTES_POR_PAGINA, "total": len(items) if total is None else total}


class TestCustomerSummary(unittest.TestCase):
    def test_counts_status_and_manual_block_independently(self):
        result = resumir_clientes([customer(1), customer(2, blocked=True), customer(3, "inactive"), customer(4, "inactive", True)])
        self.assertEqual((result["ativos"], result["inativos"], result["bloqueados"]), (2, 2, 2))
        self.assertEqual(result["percentual_ativos"], 50)
        self.assertEqual(result["lista"][1], {
            "id": 2, "nome": "Cliente local 2", "cpf_mascarado": "***.***.***-00",
            "ativo": True, "bloqueado": True, "href": "/clientes/2",
        })

    def test_list_is_limited_and_empty_has_no_invented_share(self):
        self.assertEqual(len(resumir_clientes([customer(n) for n in range(1, 20)])["lista"]), CLIENTES_LISTADOS)
        empty = resumir_clientes([])
        self.assertEqual((empty["ativos"], empty["inativos"], empty["percentual_ativos"], empty["lista"]), (0, 0, 0, []))


class TestRentalInsights(unittest.TestCase):
    def test_ranking_counts_per_customer_with_proportional_bars(self):
        rentals = [
            {**rental(n, "2026-10-20T12:00:00", "2026-10-30T12:00:00"), "customer_id": cid, "customer_name": f"C{cid}"}
            for n, cid in enumerate([7, 7, 7, 8, 9, 9], start=1)
        ]
        rows = ranking_clientes(rentals)
        self.assertEqual([(r["nome"], r["total"], r["largura"]) for r in rows], [("C7", 3, 100), ("C9", 2, 67), ("C8", 1, 33)])
        self.assertEqual(rows[2]["rotulo"], "1 locação")
        self.assertEqual(rows[0]["href"], "/clientes/7")
        self.assertEqual(ranking_clientes([]), [])

    def test_overdue_only_active_past_due_most_late_first(self):
        rentals = [
            rental(1, "2026-10-10T12:00:00", "2026-10-20T12:00:00"),                          # 3 dias
            rental(2, "2026-10-10T12:00:00", "2026-10-23T12:00:00"),                          # horas
            rental(3, "2026-10-01T12:00:00", "2026-10-02T12:00:00", "2026-10-03T12:00:00"),   # devolvida
            rental(4, "2026-10-21T12:00:00", "2026-10-30T12:00:00"),                          # no prazo
            rental(5, "2026-10-01T12:00:00", "2026-10-22T12:00:00"),                          # 1 dia
        ]
        rows = locacoes_vencidas(rentals, NOW)
        self.assertEqual([r["id"] for r in rows], [1, 5, 2])
        self.assertEqual([r["atraso"] for r in rows], ["3 dias de atraso", "1 dia de atraso", "Venceu há menos de 1 dia"])
        self.assertEqual(rows[0]["href"], "/locacoes/1")
        self.assertLess(ms("2026-10-23T12:00:00"), NOW)


class TestDashboardCustomersState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.dashboard = await self.root.get_state(DashboardState)
        self.session = await self.dashboard.get_state(State)
        self.session._user_id = "1"
        self.session._user_role = "member"
        self.session._xano_auth_token = "synthetic-secret"
        self.me = patch("ProjetoLocadora.dashboard_state.get_me_xano", new=AsyncMock(return_value=ME)).start()
        self.list = patch("ProjetoLocadora.dashboard_state.list_customers_xano", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)
        self.list.return_value = page([customer(1), customer(2, "inactive"), customer(3, blocked=True)])

    async def load(self):
        async for _ in self.dashboard.load_customers():
            pass

    async def test_member_sees_real_counts_and_list(self):
        await self.load()
        d = self.dashboard
        self.assertEqual(d.customers_status, "success")
        self.assertEqual((d.customers_total, d.customers_active, d.customers_inactive, d.customers_blocked), (3, 2, 1, 1))
        self.assertEqual(d.customers_active_pct, 67)
        self.assertEqual(d.customers_note, "2 ativos · 1 com bloqueio manual")
        self.assertEqual(len(d.customers_list), 3)
        self.list.assert_awaited_once_with("synthetic-secret", page=1, per_page=CLIENTES_POR_PAGINA)
        self.me.assert_awaited_once()
        self.assertNotIn("synthetic-secret", str(d.dict()))

    async def test_recent_session_check_is_reused(self):
        self.session._mark_session_verified()
        await self.load()
        self.me.assert_not_awaited()

    async def test_reads_at_most_the_page_limit_and_flags_partial(self):
        self.list.return_value = page([customer(n) for n in range(1, 51)], total=400)
        await self.load()
        self.assertEqual(self.list.await_count, CLIENTES_PAGINAS_MAX)
        self.assertEqual(self.dashboard.customers_total, 400)
        self.assertIn("entre os 100 primeiros por nome", self.dashboard.customers_note)

    async def test_errors_never_show_values(self):
        self.list.side_effect = XanoCustomerError("Não foi possível consultar os clientes no Xano.")
        await self.load()
        d = self.dashboard
        self.assertEqual(d.customers_status, "error")
        self.assertEqual(d.customers_message, "Não foi possível consultar os clientes no Xano.")
        self.assertIsNone(d.customers_total)
        self.assertEqual(d.customers_list, [])

    async def test_rejected_token_clears_session_and_redirects(self):
        self.list.side_effect = XanoCustomerError("Você não tem permissão para realizar esta operação.", status=401)
        updates = [u async for u in self.dashboard.load_customers()]
        self.assertEqual(self.session._xano_auth_token, "")
        self.assertTrue(any("/login" in str(u) for u in updates if u is not None))

    async def test_session_change_discards_late_response(self):
        async def late(*args, **kwargs):
            self.session._clear_session()
            await self.session._sync_dashboard_session()
            return page([customer(1)])

        self.list.side_effect = late
        await self.load()
        self.assertIsNone(self.dashboard.customers_total)
        self.assertEqual(self.dashboard.customers_list, [])


if __name__ == "__main__":
    unittest.main()
