"""Distribuição do acervo por gênero a partir do catálogo real; sem rede."""

import re
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora import dashboard
from ProjetoLocadora.ProjetoLocadora import State, render_dashboard
from ProjetoLocadora.dashboard_state import (
    GENERO_OUTROS,
    GENEROS_EXIBIDOS,
    DashboardState,
    distribuir_generos,
)
from ProjetoLocadora.xano_client import XanoCatalogError


SUMMARY = {"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-18T15:00:00Z"}
ME = {"id": 1, "role": "admin", "is_active": True}


def films(*genres):
    return [{"id": index + 1, "genero": genre} for index, genre in enumerate(genres)]


async def consume(event):
    async for _ in event:
        pass


class TestDistribuirGeneros(unittest.TestCase):
    def test_counts_real_films_and_orders_by_total(self):
        rows = distribuir_generos(films("Ação", "Drama", "Ação", "Terror", "Ação", "Drama"))
        self.assertEqual(
            [(row["genero"], row["total"]) for row in rows],
            [("Ação", 3), ("Drama", 2), ("Terror", 1)],
        )
        self.assertEqual([row["rotulo"] for row in rows], ["3 filmes", "2 filmes", "1 filme"])

    def test_groups_case_and_spacing_variants_keeping_first_spelling(self):
        rows = distribuir_generos(films("Ação", "  ação ", "AÇÃO", "Comédia  romântica", "comédia romântica"))
        self.assertEqual([(r["genero"], r["total"]) for r in rows], [("Ação", 3), ("Comédia romântica", 2)])

    def test_bars_are_relative_to_the_largest_and_never_invented(self):
        rows = distribuir_generos(films(*["A"] * 8, *["B"] * 4, "C"))
        self.assertEqual([r["largura"] for r in rows], [100, 50, 12])
        self.assertTrue(all(r["largura"] >= 4 for r in rows))

    def test_excess_genres_are_grouped_into_others(self):
        names = [f"G{index}" for index in range(GENEROS_EXIBIDOS + 3)]
        rows = distribuir_generos(films(*names))
        self.assertEqual(len(rows), GENEROS_EXIBIDOS + 1)
        self.assertEqual(rows[-1]["genero"], GENERO_OUTROS)
        self.assertEqual(rows[-1]["total"], 3)
        self.assertEqual(sum(r["total"] for r in rows), len(names))

    def test_empty_catalog_and_blank_genres(self):
        self.assertEqual(distribuir_generos([]), [])
        self.assertEqual(distribuir_generos(films("", "   ")), [])


class TestDashboardGenresState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.dashboard = await self.root.get_state(DashboardState)
        self.session = await self.dashboard.get_state(State)
        self.session._user_id = "1"
        self.session._user_role = "admin"
        self.session._xano_auth_token = "synthetic-secret"
        patches = {
            "me": patch("ProjetoLocadora.dashboard_state.get_me_xano", new_callable=AsyncMock),
            "api": patch("ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", new_callable=AsyncMock),
            "films": patch("ProjetoLocadora.dashboard_state.list_films_xano", new_callable=AsyncMock),
        }
        for name, item in patches.items():
            setattr(self, name, item.start())
            self.addCleanup(item.stop)
        self.me.return_value = ME
        self.api.return_value = SUMMARY

    async def test_success_loads_genres_from_the_existing_catalog_endpoint(self):
        self.films.return_value = films("Ação", "Drama", "Ação")
        await consume(self.dashboard.load_summary())
        self.films.assert_awaited_once_with("synthetic-secret")
        self.assertEqual(self.dashboard.status, "success")
        self.assertEqual(self.dashboard.genres_status, "success")
        self.assertEqual([(g["genero"], g["total"]) for g in self.dashboard.genres], [("Ação", 2), ("Drama", 1)])
        self.assertEqual(self.dashboard.total_filmes, 3)

    async def test_catalog_failure_keeps_totals_and_flags_genres_only(self):
        for error in (XanoCatalogError("falha"), RuntimeError("inesperado")):
            with self.subTest(error=type(error).__name__):
                self.films.side_effect = error
                await consume(self.dashboard.refresh_summary())
                self.assertEqual(self.dashboard.status, "success")
                self.assertEqual(self.dashboard.total_filmes, 3)
                self.assertEqual(self.dashboard.genres_status, "error")
                self.assertEqual(self.dashboard.genres, [])

    async def test_member_never_queries_the_catalog_for_genres(self):
        self.session._user_role = "member"
        await consume(self.dashboard.load_summary())
        self.films.assert_not_awaited()
        self.assertEqual(self.dashboard.genres, [])
        self.assertEqual(self.dashboard.genres_status, "initial")

    async def test_summary_error_and_invalidation_clear_genres(self):
        self.films.return_value = films("Ação")
        await consume(self.dashboard.load_summary())
        self.assertEqual(len(self.dashboard.genres), 1)
        self.dashboard._invalidate()
        self.assertEqual((self.dashboard.genres, self.dashboard.genres_status), ([], "initial"))

    async def test_secret_token_is_not_stored_in_public_state(self):
        self.films.return_value = films("Ação")
        await consume(self.dashboard.load_summary())
        self.assertNotIn("synthetic-secret", str(self.dashboard.dict()))


class TestGenrePanelUI(unittest.TestCase):
    def setUp(self):
        self.page = re.sub(
            r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), str(render_dashboard())
        )

    def test_panel_is_bound_to_real_state_and_admin_only(self):
        for text in ("genres_status", "Filmes por gênero", "Acervo por gênero",
                     "Distribuição disponível apenas para administradores.",
                     "Nenhum filme cadastrado.", "Ver acervo", "Carregando distribuição"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertIn("vitrine-dash__genre-fill", self.page)

    def test_error_message_is_an_alert_and_no_example_data(self):
        self.assertIn("Não foi possível carregar a distribuição por gênero.", self.page)
        for invented in ("Ação lidera", "8 filmes", "6 filmes", "Comédia", "Terror"):
            with self.subTest(text=invented):
                self.assertNotIn(invented, self.page)

    def test_movement_panel_is_explicitly_empty_before_rentals_load(self):
        # Antes da resposta da listagem de locações: área vazia, sem barras inventadas.
        self.assertIn("Movimentação de locações", self.page)
        self.assertIn("Nenhuma locação para exibir.", self.page)

    def test_genre_rows_reveal_share_on_hover_and_focus(self):
        for text in ("vitrine-dash__genre-share", "% do acervo", "tabIndex:0"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)

    def test_panel_function_accepts_a_role(self):
        self.assertIsInstance(dashboard.genre_panel("admin").render(), dict)
        self.assertIsInstance(dashboard.genre_panel("member").render(), dict)


if __name__ == "__main__":
    unittest.main()
