"""Estrutura e estilos das telas de locação; não é teste de navegador."""

import re
import unittest
from pathlib import Path

from ProjetoLocadora.ProjetoLocadora import State, dashboard_topbar, rental_detail_page, rental_registration_page
from ProjetoLocadora.locacoes_ui import detail, registration

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _text(component) -> str:
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), str(component))


class TestRentalPages(unittest.TestCase):
    def setUp(self):
        self.form = _text(registration(State.user_role == "admin", dashboard_topbar("/locacoes/nova")))
        self.detail = _text(detail(dashboard_topbar("/locacoes/nova")))

    def test_pages_share_dashboard_shell_and_navigation(self):
        for page in (self.form, self.detail):
            self.assertIn("vitrine-dash vitrine-locacoes", page)
            self.assertIn("Navegação principal", page)
            self.assertRegex(page, r'"aria-current":"page"[^}]*to:"/locacoes/nova"')

    def test_registration_has_three_numbered_steps_in_one_flow(self):
        for text in ("Selecionar cliente", "Selecionar exemplar", "Vencimento e confirmação",
                     "Etapa 1: cliente", "Etapa 2: exemplar", "Etapa 3: vencimento e confirmação",
                     "Progresso do registro", "vitrine-locacoes__flow", "cópia física do filme"):
            with self.subTest(text=text):
                self.assertIn(text, self.form)
        self.assertLess(self.form.index("Selecionar cliente"), self.form.index("Selecionar exemplar"))
        self.assertLess(self.form.index("Selecionar exemplar"), self.form.index("Vencimento e confirmação"))

    def test_registration_exposes_contract_controls_and_states(self):
        self.assertIn('user_role_rx_state_?.valueOf?.() === "admin"', self.form)
        for text in ("Registrar locação", "Buscar cliente para locação", "Vencimento no horário de Brasília",
                     "Resumo da locação", "Confirmar locação", "Tentativa pendente de confirmação",
                     'role:"alert"', 'role:"status"', "Nenhum cliente encontrado.",
                     "Nenhum exemplar disponível para locação no momento.", "Tentar novamente",
                     "Confirmar registra a retirada (uma locação)", "A devolução não faz parte desta etapa"):
            with self.subTest(text=text):
                self.assertIn(text, self.form)

    def test_search_submits_with_enter_and_cards_are_keyboard_buttons(self):
        self.assertIn('type:"submit"', self.form)
        self.assertIn("aria-pressed", self.form)
        self.assertIn("vitrine-locacoes__card", self.form)

    def test_pagination_is_conditional(self):
        self.assertIn("customer_paginated", self.form)
        self.assertIn("exemplar_paginated", self.form)

    def test_condition_check_is_a_collapsed_admin_only_section(self):
        self.assertIn("Ação administrativa: conferir condição do exemplar", self.form)
        self.assertIn('jsx("details"', self.form)
        self.assertNotIn("open:true", self.form)
        self.assertLess(self.form.index("Etapa 3: vencimento e confirmação"), self.form.index("Ação administrativa"))

    def test_blocked_writes_notice_is_neutral_and_explicit(self):
        self.assertIn("writes_blocked", self.form)
        self.assertIn("bloqueado neste ambiente", self.form)

    def test_detail_shows_backend_fields_only(self):
        for text in ("Dados da locação", "Retirada", "Vencimento (horário de Brasília)", "Exemplar", "Filme",
                     "Registrada por", "Atualizar detalhes"):
            with self.subTest(text=text):
                self.assertIn(text, self.detail)

    def test_routes_registered_and_stylesheet_loaded(self):
        self.assertTrue(callable(rental_registration_page) and callable(rental_detail_page))
        self.assertTrue((ASSETS / "locacoes.css").is_file())
        source = (Path(__file__).resolve().parents[1] / "ProjetoLocadora" / "ProjetoLocadora.py").read_text(encoding="utf-8")
        self.assertIn('"/locacoes.css"', source)


if __name__ == "__main__":
    unittest.main()
