"""Árvore de componentes com estados controlados; não é teste de navegador.

As condições são avaliadas com valores literais nos testes de apresentação.
A compilação Reflex verifica separadamente os componentes reativos reais.
"""

import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import reflex as rx

from ProjetoLocadora import dashboard
from ProjetoLocadora.ProjetoLocadora import render_dashboard
from ProjetoLocadora.dashboard_state import DashboardState


class TestDashboardUI(unittest.TestCase):
    def view(self, role="admin", status="initial", loading=False, total=0):
        controlled = SimpleNamespace(
            status=status, loading=loading, total_filmes=total,
            total_exemplares=total, generated_at="2026-10-18T15:00:00Z",
            refresh_summary=DashboardState.refresh_summary,
        )

        def literal_condition(condition, yes, no=None):
            self.assertIsInstance(condition, bool)
            return yes if condition else (no if no is not None else rx.fragment())

        with patch.object(dashboard, "DashboardState", controlled), patch.object(
            dashboard, "DashboardPresentationState", SimpleNamespace(
                generated_at_display=dashboard.format_generated_at(controlled.generated_at),
            ),
        ), patch.object(
            dashboard.rx, "cond", side_effect=literal_condition,
        ):
            return dashboard.render_acervo_summary(role)

    def rendered(self, component):
        return re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), str(component))

    def nodes(self, component):
        yield component
        for child in component.children:
            yield from self.nodes(child)

    def test_success_zero_labels_timestamp_and_refresh_binding(self):
        component = self.view(status="success", total=0)
        rendered = self.rendered(component)
        for text in ("Total de filmes cadastrados", "Total de exemplares cadastrados",
                     "Inclui filmes ativos e inativos", "não indica disponibilidade",
                     "18/10/2026 às 12:00:00", "(horário de Brasília)"):
            self.assertIn(text, rendered)
        cards = [node for node in self.nodes(component)
                 if str(getattr(node, "id", "")) in ('dashboard-total-filmes', 'dashboard-total-exemplares')]
        self.assertEqual(len(cards), 2)
        for card in cards:
            self.assertRegex(str(card), r'size:"7"\},0\)')
        buttons = [node for node in self.nodes(component) if (getattr(node, "tag", "") or "").endswith("Button")]
        self.assertEqual(len(buttons), 1)
        self.assertEqual(str(buttons[0].disabled), "false")
        self.assertEqual(buttons[0].event_triggers["on_click"].events[0].handler, DashboardState.refresh_summary)

    def test_loading_disables_refresh_and_hides_old_values(self):
        component = self.view(status="success", loading=True, total=76543)
        self.assertIn("Carregando resumo", self.rendered(component))
        self.assertNotIn("76543", self.rendered(component))
        self.assertNotIn("2026-10-18", self.rendered(component))
        button = next(n for n in self.nodes(component) if (getattr(n, "tag", "") or "").endswith("Button"))
        self.assertEqual(str(button.disabled), "true")
        self.assertIn('role:"status"', self.rendered(component))

    def test_errors_have_distinct_messages_and_never_show_stale_totals(self):
        for status, text in (
            ("unavailable", "Não foi possível consultar"),
            ("invalid_response", "resposta inválida"),
            ("unauthenticated", "Sessão inválida"),
            ("forbidden", "restrito a administradores"),
            ("error", "não está disponível"),
            ("initial", "ainda não consultado"),
        ):
            with self.subTest(status=status):
                component = self.view(status=status, total=76543)
                self.assertIn(text, self.rendered(component))
                self.assertNotIn("76543", self.rendered(component))
                self.assertNotIn("2026-10-18", self.rendered(component))
                if status == "unauthenticated":
                    self.assertIn('/login', self.rendered(component))

    def test_member_cannot_see_loaded_totals_or_refresh(self):
        rendered = self.rendered(self.view(role="member", status="success", total=76543))
        self.assertIn("restrito a administradores", rendered)
        for hidden in ("76543", "Atualizar", "Total de filmes cadastrados", "2026-10-18"):
            self.assertNotIn(hidden, rendered)

    def test_real_dashboard_keeps_navigation_and_future_indicators(self):
        # Renderiza as condições reativas reais, sem avaliar uma sessão falsa.
        rendered = self.rendered(render_dashboard())
        for text in ("Backoffice da locadora", "Sair", "/filmes", "/clientes", "/exemplares",
                     "Resumo da sessão", "Locações ativas", "Exemplares disponíveis",
                     "Multas pendentes", "Dados indisponíveis", "dashboard-summary"):
            self.assertIn(text, rendered)
        self.assertEqual(rendered.count("Dados indisponíveis"), 3)


class TestDashboardTimestampPresentation(unittest.TestCase):
    def test_sao_paulo_conversion_and_date_rollover(self):
        for original, expected in (
            ("2026-10-19T02:00:11Z", "18/10/2026 às 23:00:11"),
            ("2026-01-01T01:00:00Z", "31/12/2025 às 22:00:00"),
            ("2026-10-18T15:00:00.123456789Z", "18/10/2026 às 12:00:00"),
            # Regra histórica de verão: impede substituir ZoneInfo por -03 fixo.
            ("2018-12-01T02:00:00Z", "01/12/2018 às 00:00:00"),
        ):
            with self.subTest(original=original):
                self.assertEqual(dashboard.format_generated_at(original), expected + " (horário de Brasília)")

    def test_empty_and_invalid_timestamps_do_not_become_dates(self):
        self.assertEqual(dashboard.format_generated_at(""), "")
        for value in ("invalidZ", "2026-02-30T00:00:00Z", "2026-10-18T15:00:00", "2026-10-18T15:00:00+00:00"):
            with self.subTest(value=value):
                self.assertEqual(dashboard.format_generated_at(value), "Horário indisponível")


class TestDashboardPresentationState(unittest.IsolatedAsyncioTestCase):
    async def test_computed_presentation_tracks_parent_without_changing_utc(self):
        root = rx.State(_reflex_internal_init=True)
        parent = await root.get_state(DashboardState)
        visual = await root.get_state(dashboard.DashboardPresentationState)
        original = "2026-10-19T02:00:11Z"
        parent.generated_at = original
        self.assertEqual(visual.generated_at_display, "18/10/2026 às 23:00:11 (horário de Brasília)")
        self.assertEqual(parent.generated_at, original)
        parent._invalidate()
        self.assertEqual(visual.generated_at_display, "")


if __name__ == "__main__":
    unittest.main()
