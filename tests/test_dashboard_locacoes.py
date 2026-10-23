"""Dashboard de locações: cálculo, estado e apresentação. Listagem e sessão substituídas por doubles locais."""

from datetime import datetime, timezone
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State, render_dashboard
from ProjetoLocadora.dashboard_state import (
    LOCACOES_PAGINAS_MAX, LOCACOES_POR_PAGINA, MOVIMENTO_DIAS, DashboardState, distribuir_generos, resumir_locacoes,
)
from ProjetoLocadora.locacoes_client import RentalError
from tests.test_locacoes_client import ACTIVE_13

ME = {"id": 1, "role": "admin", "is_active": True}
CSS = (Path(__file__).resolve().parents[1] / "assets" / "dashboard.css").read_text(encoding="utf-8")


def ms(text: str) -> int:
    """Instante UTC em milissegundos."""
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


# 23/10/2026 15:00 em Brasília.
NOW = ms("2026-10-23T18:00:00")


def rental(rid, rented, due, returned=None):
    item = {**ACTIVE_13, "id": rid, "rented_at": ms(rented), "due_at": ms(due)}
    if returned:
        item.update(status="returned", returned_at=ms(returned), returned_by=9)
    return item


def page(items, total=None, number=1):
    return {"items": items, "page": number, "per_page": LOCACOES_POR_PAGINA, "total": len(items) if total is None else total}


class TestRentalSummary(unittest.TestCase):
    def test_counts_active_and_overdue(self):
        result = resumir_locacoes([
            rental(1, "2026-10-20T12:00:00", "2026-10-22T12:00:00"),                          # ativa vencida
            rental(2, "2026-10-21T12:00:00", "2026-10-30T12:00:00"),                          # ativa no prazo
            rental(3, "2026-10-19T12:00:00", "2026-10-20T12:00:00", "2026-10-22T12:00:00"),   # devolvida
        ], NOW)
        self.assertEqual((result["ativas"], result["vencidas"]), (2, 1))

    def test_days_follow_brasilia_and_window_ends_today(self):
        result = resumir_locacoes([
            # 02:30 UTC de 23/10 = 23:30 de 22/10 em Brasília.
            rental(1, "2026-10-23T02:30:00", "2026-10-30T12:00:00"),
            rental(2, "2026-10-23T12:00:00", "2026-10-30T12:00:00"),
            rental(3, "2026-10-01T12:00:00", "2026-10-02T12:00:00", "2026-10-22T15:00:00"),   # retirada fora da janela
        ], NOW)
        days = result["dias"]
        self.assertEqual(len(days), MOVIMENTO_DIAS)
        self.assertEqual((days[0]["data"], days[-1]["data"]), ("10/10", "23/10"))
        by_date = {d["data"]: d for d in days}
        self.assertEqual((by_date["22/10"]["retiradas"], by_date["22/10"]["devolucoes"]), (1, 1))
        self.assertEqual(by_date["23/10"]["retiradas"], 1)
        self.assertEqual((result["retiradas"], result["devolucoes"]), (2, 1))
        self.assertEqual(by_date["23/10"]["semana"], "sex")

    def test_heights_are_proportional_and_texts_pluralized(self):
        result = resumir_locacoes([
            rental(1, "2026-10-23T12:00:00", "2026-10-30T12:00:00"),
            rental(2, "2026-10-23T13:00:00", "2026-10-30T12:00:00"),
            rental(3, "2026-10-22T12:00:00", "2026-10-30T12:00:00"),
        ], NOW)
        by_date = {d["data"]: d for d in result["dias"]}
        self.assertEqual(by_date["23/10"]["altura_retiradas"], 100)
        self.assertEqual(by_date["22/10"]["altura_retiradas"], 50)
        self.assertEqual(by_date["21/10"]["altura_retiradas"], 0)
        self.assertEqual(by_date["23/10"]["texto_retiradas"], "2 retiradas")
        self.assertEqual(by_date["22/10"]["texto_retiradas"], "1 retirada")
        self.assertEqual(by_date["22/10"]["texto_devolucoes"], "0 devoluções")
        self.assertEqual(by_date["22/10"]["rotulo"], "22/10: 1 retirada, 0 devoluções")

    def test_no_rentals_has_empty_window_without_invented_values(self):
        result = resumir_locacoes([], NOW)
        self.assertEqual((result["ativas"], result["retiradas"], result["devolucoes"]), (0, 0, 0))
        self.assertTrue(all(d["altura_retiradas"] == d["altura_devolucoes"] == 0 for d in result["dias"]))

    def test_month_window_labels_every_fifth_day_including_today(self):
        days = resumir_locacoes([], NOW, 30)["dias"]
        self.assertEqual(len(days), 30)
        labeled = [d["eixo"] for d in days if d["eixo"]]
        self.assertEqual(labeled[-1], "23/10")
        self.assertEqual(len(labeled), 6)
        self.assertTrue(all(d["eixo"] == d["data"] for d in resumir_locacoes([], NOW, 7)["dias"]))

    def test_genre_share_is_part_of_the_displayed_collection(self):
        rows = distribuir_generos([{"genero": g} for g in ("Ação", "Ação", "Drama", "Terror")])
        self.assertEqual([r["percentual"] for r in rows], [50, 25, 25])


class TestDashboardRentalsState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.dashboard = await self.root.get_state(DashboardState)
        self.session = await self.dashboard.get_state(State)
        self.session._user_id = "1"
        self.session._user_role = "member"
        self.session._xano_auth_token = "synthetic-secret"
        self.me = patch("ProjetoLocadora.dashboard_state.get_me_xano", new=AsyncMock(return_value={**ME, "role": "member"})).start()
        self.list = patch("ProjetoLocadora.dashboard_state.list_rentals", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)
        now = patch("ProjetoLocadora.dashboard_state.time.time", return_value=NOW / 1000)
        now.start()
        self.addCleanup(now.stop)
        self.list.return_value = page([
            rental(2, "2026-10-23T12:00:00", "2026-10-30T12:00:00"),
            rental(1, "2026-10-20T12:00:00", "2026-10-22T12:00:00"),
        ])

    async def load(self):
        async for _ in self.dashboard.load_rentals():
            pass

    async def test_member_sees_real_active_count_and_movement(self):
        await self.load()
        self.assertEqual(self.dashboard.rentals_status, "success")
        self.assertEqual(self.dashboard.active_rentals, 2)
        self.assertEqual(self.dashboard.overdue_rentals, 1)
        self.assertEqual(self.dashboard.rentals_note, "1 com vencimento ultrapassado")
        self.assertEqual(self.dashboard.movement_note, "2 retiradas e 0 devoluções em 14 dias")
        self.assertEqual(len(self.dashboard.movement), MOVIMENTO_DIAS)
        self.list.assert_awaited_once_with("synthetic-secret", 1, LOCACOES_POR_PAGINA)
        self.me.assert_awaited_once()  # sem conferência recente: confere agora
        self.assertNotIn("synthetic-secret", str(self.dashboard.dict()))

    async def test_recent_session_check_is_reused(self):
        self.session._mark_session_verified()
        await self.load()
        self.me.assert_not_awaited()
        self.assertEqual(self.dashboard.rentals_status, "success")

    async def test_period_switch_recalculates_without_new_requests(self):
        self.list.return_value = page([
            rental(1, "2026-10-21T12:00:00", "2026-10-30T12:00:00"),                          # 2 dias atrás
            rental(2, "2026-10-12T12:00:00", "2026-10-14T12:00:00", "2026-10-13T12:00:00"),   # 11 dias atrás
            rental(3, "2026-09-28T12:00:00", "2026-10-02T12:00:00", "2026-10-01T12:00:00"),   # 25 dias atrás
        ])
        await self.load()
        self.assertEqual(self.dashboard.movement_days, 14)
        self.assertEqual(self.dashboard.movement_note, "2 retiradas e 1 devolução em 14 dias")
        requests = self.list.await_count

        self.dashboard.set_movement_period(7)
        self.assertEqual(len(self.dashboard.movement), 7)
        self.assertEqual(self.dashboard.movement_note, "1 retirada e 0 devoluções em 7 dias")

        self.dashboard.set_movement_period(30)
        self.assertEqual(len(self.dashboard.movement), 30)
        self.assertEqual(self.dashboard.movement_note, "3 retiradas e 2 devoluções em 1 mês")
        # Contadores do card não dependem do período.
        self.assertEqual(self.dashboard.active_rentals, 1)

        self.dashboard.set_movement_period(90)  # fora das opções: ignorado
        self.assertEqual(self.dashboard.movement_days, 30)
        self.assertEqual(self.list.await_count, requests)
        self.assertNotIn("_rentals_loaded", str(self.dashboard.dict()))

    async def test_reads_at_most_the_page_limit_and_flags_partial_counts(self):
        many = page([rental(n, "2026-10-23T12:00:00", "2026-10-30T12:00:00") for n in range(1, 51)], total=400)
        self.list.return_value = many
        await self.load()
        self.assertEqual(self.list.await_count, LOCACOES_PAGINAS_MAX)
        self.assertEqual([c.args[1] for c in self.list.await_args_list], [1, 2, 3])
        self.assertTrue(self.dashboard.rentals_partial)
        self.assertIn("entre as 150 locações mais recentes", self.dashboard.rentals_note)

    async def test_errors_never_show_values(self):
        cases = {
            "notfound": "não está disponível",
            "ratelimited": "limite de requisições",
            "authorization": "não tem permissão",
            "unavailable": "Não foi possível carregar",
            "invalid": "Não foi possível carregar",
        }
        for category, text in cases.items():
            with self.subTest(category=category):
                self.list.side_effect = RentalError(category, retry_after=20 if category == "ratelimited" else None)
                await self.load()
                self.assertEqual(self.dashboard.rentals_status, "error")
                self.assertIn(text, self.dashboard.rentals_message)
                self.assertIsNone(self.dashboard.active_rentals)
                self.assertEqual(self.dashboard.movement, [])

    async def test_rejected_session_is_cleared(self):
        self.list.side_effect = RentalError("authentication")
        await self.load()
        self.assertEqual(self.session._xano_auth_token, "")
        self.me.return_value = None
        self.session._user_id, self.session._xano_auth_token = "1", "synthetic-secret"
        self.list.side_effect = None
        await self.load()
        self.assertEqual(self.session._xano_auth_token, "")
        self.list.assert_awaited_once()  # sessão recusada antes de ler locações

    async def test_logout_discards_a_late_response(self):
        async def late(token, number, per_page):
            await self.session.logout()
            return page([rental(1, "2026-10-23T12:00:00", "2026-10-30T12:00:00")])

        self.list.side_effect = late
        await self.load()
        self.assertIsNone(self.dashboard.active_rentals)
        self.assertEqual(self.dashboard.movement, [])
        self.assertNotEqual(self.dashboard.rentals_status, "success")

    async def test_summary_failure_does_not_erase_rentals(self):
        await self.load()
        with patch("ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", new=AsyncMock(side_effect=RuntimeError("x"))):
            self.session._user_role = "admin"
            self.me.return_value = ME
            async for _ in self.dashboard.refresh_summary():
                pass
        self.assertEqual(self.dashboard.active_rentals, 2)


class TestDashboardRentalsUI(unittest.TestCase):
    def setUp(self):
        self.page = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), str(render_dashboard()))

    def test_card_and_panel_are_bound_to_real_rental_state(self):
        for text in ("dashboard-locacoes-ativas", "active_rentals", "rentals_note", "Carregando locações…",
                     "Indisponível no momento", "dashboard-movimentacao", "Retiradas", "Devoluções",
                     "Retiradas e devoluções por dia", "Carregando movimentação…", "Tentar novamente",
                     "Nenhuma retirada ou devolução nos últimos 14 dias.", "Ver locações", "/locacoes/nova",
                     "vitrine-dash__tip", "vitrine-dash__bar--out", "vitrine-dash__bar--in",
                     # Seletor de período e textos de cada opção.
                     "Período da movimentação", "7 dias", "14 dias", "1 mês", "set_movement_period",
                     "nos últimos 7 dias", "no último mês", "vitrine-dash__days--dense"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        # "Multas pendentes" continua sem fonte de dados.
        self.assertIn("dashboard-multas-pendentes", self.page)

    def test_hover_and_focus_reveal_details_with_motion_respecting_preferences(self):
        for selector in (".vitrine-dash__day:hover .vitrine-dash__tip", ".vitrine-dash__day:focus-visible .vitrine-dash__tip",
                         ".vitrine-dash__genre-item:hover .vitrine-dash__genre-share", "@keyframes vd-grow-up",
                         "@keyframes vd-grow-right", "@media (prefers-reduced-motion: reduce)"):
            with self.subTest(selector=selector):
                self.assertIn(selector, CSS)


if __name__ == "__main__":
    unittest.main()
