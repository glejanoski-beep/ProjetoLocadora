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
from pathlib import Path

from ProjetoLocadora.ProjetoLocadora import (
    DASHBOARD_NAV_ITEMS,
    DASHBOARD_NAV_UPCOMING,
    dashboard_topbar,
    render_dashboard,
)
from ProjetoLocadora.dashboard_state import DashboardState


CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "dashboard.css"


class TestDashboardUI(unittest.TestCase):
    def view(self, role="admin", status="initial", loading=False, total=0,
             builder=None):
        builder = builder or dashboard.render_acervo_summary
        controlled = SimpleNamespace(
            status=status, loading=loading, total_filmes=total,
            total_exemplares=total, generated_at="2026-10-18T15:00:00Z",
            refresh_summary=DashboardState.refresh_summary,
            load_rentals=DashboardState.load_rentals,
            load_customers=DashboardState.load_customers,
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
            return builder(role)

    def rendered(self, component):
        return re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), str(component))

    def nodes(self, component):
        yield component
        for child in component.children:
            yield from self.nodes(child)

    def test_success_zero_labels_and_real_values(self):
        component = self.view(status="success", total=0)
        rendered = self.rendered(component)
        for text in ("Filmes cadastrados", "Exemplares cadastrados",
                     "Inclui filmes ativos e inativos", "não indica disponibilidade"):
            self.assertIn(text, rendered)
        cards = [node for node in self.nodes(component)
                 if str(getattr(node, "id", "")) in ('dashboard-total-filmes', 'dashboard-total-exemplares')]
        self.assertEqual(len(cards), 2)
        for card in cards:
            self.assertRegex(str(card), r'vitrine-dash__value"\},0\)')

    def test_toolbar_has_timestamp_and_refresh_binding(self):
        component = self.view(status="success", total=0, builder=dashboard.render_summary_toolbar)
        rendered = self.rendered(component)
        for text in ("18/10/2026 às 12:00:00", "(horário de Brasília)", "Gerado em"):
            self.assertIn(text, rendered)
        buttons = [node for node in self.nodes(component) if (getattr(node, "tag", "") or "").endswith("Button")]
        self.assertEqual(len(buttons), 1)
        self.assertEqual(str(buttons[0].disabled), "false")
        self.assertEqual(
            [event.handler for event in buttons[0].event_triggers["on_click"].events],
            [DashboardState.refresh_summary, DashboardState.load_rentals, DashboardState.load_customers],
        )

    def test_member_has_no_toolbar_or_refresh(self):
        component = self.view(role="member", status="success", total=7, builder=dashboard.render_summary_toolbar)
        rendered = self.rendered(component)
        self.assertNotIn("Atualizar", rendered)
        self.assertNotIn("Gerado em", rendered)

    def test_loading_disables_refresh_and_hides_old_values(self):
        component = self.view(status="success", loading=True, total=76543)
        self.assertIn("Carregando resumo", self.rendered(component))
        self.assertNotIn("76543", self.rendered(component))
        self.assertNotIn("2026-10-18", self.rendered(component))
        toolbar = self.view(status="success", loading=True, total=76543,
                            builder=dashboard.render_summary_toolbar)
        button = next(n for n in self.nodes(toolbar) if (getattr(n, "tag", "") or "").endswith("Button"))
        self.assertEqual(str(button.disabled), "true")
        self.assertNotIn("2026-10-18", self.rendered(toolbar))
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
        for hidden in ("76543", "Atualizar", "Filmes cadastrados", "2026-10-18"):
            self.assertNotIn(hidden, rendered)

    def test_real_dashboard_keeps_navigation_logout_and_summary(self):
        # Renderiza as condições reativas reais, sem avaliar uma sessão falsa.
        rendered = self.rendered(render_dashboard())
        for text in ("Visão geral", "Sair", "/filmes", "/clientes", "/exemplares", "/backoffice",
                     "Atualizar", "dashboard-summary", "CINEBYTE", "Navegação principal"):
            self.assertIn(text, rendered)
        self.assertIn("logout", rendered)
        self.assertNotIn("Backoffice da locadora", rendered)
        self.assertNotIn("ROTA", rendered)

    def test_unavailable_indicators_are_explicitly_empty(self):
        rendered = self.rendered(render_dashboard())
        for identifier in ("dashboard-locacoes-ativas", "dashboard-clientes-total", "dashboard-multas-pendentes"):
            self.assertIn(identifier, rendered)
        # 3 cards + 6 subtítulos de painel sem resposta.
        self.assertEqual(rendered.count("Sem dados ainda"), 9)
        self.assertEqual(rendered.count("Sem dados ainda · será alimentado pelo histórico real"), 6)
        for title in ("Movimentação de locações", "Acervo por gênero", "Clientes", "Situação dos clientes",
                      "Locações vencidas", "Clientes que mais alugam"):
            self.assertIn(title, rendered)
        # Nenhum valor ilustrativo dos exemplos da referência.
        # Como palavra isolada: hashes gerados pelo Reflex podem conter "28".
        for invented in ("Marina Lopes", "Ação lidera", "8 filmes", "28", "AO VIVO"):
            self.assertNotRegex(rendered, rf"(?<!\w){re.escape(invented)}(?!\w)")

    def test_navigation_links_only_to_existing_pages_and_marks_upcoming(self):
        self.assertEqual(
            [href for _, href in DASHBOARD_NAV_ITEMS],
            ["/backoffice", "/filmes", "/exemplares", "/clientes", "/locacoes/nova"],
        )
        rendered = self.rendered(dashboard_topbar())
        for label in DASHBOARD_NAV_UPCOMING:
            self.assertIn(label, rendered)
        self.assertEqual(rendered.count("Em breve"), len(DASHBOARD_NAV_UPCOMING))
        self.assertEqual(rendered.count('"aria-disabled":"true"'), len(DASHBOARD_NAV_UPCOMING))
        self.assertEqual(rendered.count('"aria-current":"page"'), 1)
        for forbidden in ("/multas", "/relatorios"):
            self.assertNotIn(forbidden, rendered)

    def test_user_block_uses_session_data_and_translated_roles(self):
        rendered = self.rendered(dashboard_topbar())
        for var in ("user_name", "user_role_label", "user_initials"):
            self.assertIn(var, rendered)
        self.assertNotIn("color_mode", rendered.lower())

    def test_color_mode_button_removed_from_dashboard_only(self):
        self.assertNotIn("color_mode", self.rendered(render_dashboard()).lower())


class TestDashboardUserPresentation(unittest.TestCase):
    def test_initials_come_from_real_name(self):
        for name, expected in (
            ("Marina Lopes", "ML"),
            ("  ana  maria  souza ", "AS"),
            ("joão", "J"),
            ("", ""),
            ("   ", ""),
        ):
            with self.subTest(name=name):
                self.assertEqual(dashboard.user_initials(name), expected)

    def test_role_label_translation(self):
        from ProjetoLocadora.ProjetoLocadora import State

        for role, label in (("admin", "Administrador"), ("member", "Funcionário"), ("", "Funcionário")):
            with self.subTest(role=role):
                state = State(_reflex_internal_init=True)
                state._user_role = role
                self.assertEqual(State.user_role_label.fget(state), label)


class TestDashboardStyles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_tokens_scope_and_responsiveness(self):
        for token in ("#07070a", "#dc2638", '"Inter"', '"Space Mono"', ".vitrine-dash",
                      "border-radius: 24px", "@media (max-width: 1100px)",
                      "@media (max-width: 640px)", "overflow-x: hidden",
                      ":focus-visible", "prefers-reduced-motion"):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_css_does_not_leak_to_other_pages(self):
        selectors = re.findall(r"^([.#a-zA-Z][^{]*)\{", self.css, flags=re.M)
        for selector in selectors:
            for part in selector.split(","):
                with self.subTest(selector=part.strip()):
                    self.assertIn("vitrine-dash", part)


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
