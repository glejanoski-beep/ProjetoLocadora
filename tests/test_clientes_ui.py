"""Estrutura, estado de apresentação e estilos de Clientes; não é teste de navegador."""

import re
import unittest
from pathlib import Path

from ProjetoLocadora.ProjetoLocadora import (
    State,
    customer_block_panel,
    customer_history_panel,
    customer_status_badge,
    customers_filters,
    render_customer_detail,
    render_customer_form,
    render_customers_page,
)


CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "clientes.css"


def _text(component) -> str:
    return re.sub(
        r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), str(component)
    )


class TestCustomersListUI(unittest.TestCase):
    def setUp(self):
        self.page = _text(render_customers_page())

    def test_header_navigation_and_admin_only_register_link(self):
        for text in ("CADASTRO", "Clientes", "Cadastrar cliente", "/clientes/novo",
                     "Navegação principal"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertRegex(self.page, r'"aria-current":"page"[^}]*to:"/clientes"')
        self.assertRegex(
            self.page,
            r'user_role_rx_state_\?\.valueOf\?\.\(\) === "admin"[^;]*?to:"/clientes/novo"',
        )

    def test_search_by_name_and_full_cpf_keep_handlers_and_labels(self):
        for text in ("capture_customer_name_search", "capture_customer_cpf_search",
                     "apply_customer_filters", "Buscar cliente por nome",
                     "Buscar cliente por CPF completo", "Buscar por nome", "CPF completo",
                     "Buscar"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertIsInstance(customers_filters().render(), dict)

    def test_server_pagination_is_preserved(self):
        for text in ("previous_customers_page", "next_customers_page",
                     "customers_has_previous_page", "customers_has_next_page",
                     "Anterior", "Próxima", "Página ", " cliente(s)"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)

    def test_summary_uses_only_the_server_total(self):
        self.assertIn("customers_total", self.page)
        for forbidden in ("ativos", "bloqueados", "customers_view.length"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)

    def test_states_and_messages_are_preserved(self):
        for text in ("Carregando clientes", "Nenhum cliente encontrado.", 'role:"alert"',
                     'role:"status"', "customers_error", "customers_success"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)

    def test_table_columns_do_not_expose_contact_or_extra_personal_data(self):
        for header in ("Cliente", "CPF", "Situação", "Bloqueio manual"):
            self.assertIn(f'"{header}"', self.page)
        for forbidden in ("E-mail", "Telefone", "email", "telefone", '"Contato"', "CONTATO"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)
        self.assertIn("cpf_mascarado", self.page)
        self.assertNotIn('["cpf"]', self.page)

    def test_rows_link_to_existing_detail_route_and_offer_no_delete(self):
        self.assertIn("/clientes/", self.page)
        self.assertIn("Consultar", self.page)
        for forbidden in ("Excluir", "Apagar", "Remover cliente", "delete"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)

    def test_status_values_stay_active_inactive(self):
        badge = _text(customer_status_badge("active"))
        self.assertIn("Ativo", badge)
        self.assertIn("Inativo", badge)
        for forbidden in ("ATIVO", "INATIVO"):
            self.assertNotIn(forbidden, self.page)

    def test_no_fictional_customers_or_metrics(self):
        for invented in ("Ana Ribeiro", "Bruno Lima", "Diego Fontes", "***.***.***-24",
                         "8 clientes", "Marina Lopes", "ROTA"):
            with self.subTest(text=invented):
                self.assertNotIn(invented, self.page)


class TestCustomersViewState(unittest.TestCase):
    def test_rows_keep_summary_fields_and_add_initials_only(self):
        state = State(_reflex_internal_init=True)
        state.customers = [
            {"id": 1, "nome": "Ana Maria Ribeiro", "cpf_mascarado": "***.***.***-24",
             "status": "active", "bloqueio_manual_ativo": False},
            {"id": 2, "nome": "   ", "cpf_mascarado": "***.***.***-17",
             "status": "inactive", "bloqueio_manual_ativo": True},
        ]
        rows = State.customers_view.fget(state)
        self.assertEqual([row["iniciais"] for row in rows], ["AR", "?"])
        self.assertEqual(
            set(rows[0]),
            {"id", "nome", "cpf_mascarado", "status", "bloqueio_manual_ativo", "iniciais"},
        )
        self.assertEqual(rows[1]["status"], "inactive")
        self.assertTrue(rows[1]["bloqueio_manual_ativo"])
        self.assertNotIn("iniciais", state.customers[0])

    def test_detail_initials_follow_loaded_customer(self):
        state = State(_reflex_internal_init=True)
        self.assertEqual(State.customer_detail_initials.fget(state), "")
        state.customer_detail = {
            "id": 3, "nome": "Diego Fontes", "cpf": "41830277590", "email": None,
            "telefone": None, "status": "inactive", "bloqueio_manual_ativo": False,
            "motivo_bloqueio_manual": None, "bloqueado_em": None, "bloqueado_por": None,
        }
        self.assertEqual(State.customer_detail_initials.fget(state), "DF")


class TestCustomerFormUI(unittest.TestCase):
    def setUp(self):
        self.form = _text(render_customer_form())

    def test_form_keeps_handlers_labels_and_limits(self):
        for text in ("capture_customer_name", "capture_customer_cpf", "capture_customer_email",
                     "capture_customer_phone", "capture_customer_status", "submit_customer",
                     "Nome completo do cliente", "CPF do cliente", "E-mail do cliente",
                     "Telefone do cliente", "Situação cadastral do cliente",
                     "maxLength:200", "maxLength:254", 'type:"email"',
                     "Salvar cliente", "Cancelar"):
            with self.subTest(text=text):
                self.assertIn(text, self.form)

    def test_contact_rule_title_and_error_are_preserved(self):
        for text in ("Informe ao menos um contato: e-mail ou telefone.", "Editar cliente",
                     "Cadastrar cliente", "customer_form_error", 'role:"alert"',
                     "customer_form_loading", "editing_customer_id"):
            with self.subTest(text=text):
                self.assertIn(text, self.form)

    def test_status_picker_only_for_editing_and_uses_contract_values(self):
        self.assertIn("editing_customer", self.form)
        self.assertIn('capture_customer_status', self.form)
        self.assertIn('"active"', self.form)
        self.assertIn('"inactive"', self.form)
        self.assertNotIn("ATIVO", self.form)

    def test_routes_back_to_clients_and_no_modal(self):
        self.assertGreaterEqual(self.form.count('to:"/clientes"'), 3)
        self.assertNotIn("Dialog.Root", self.form)


class TestCustomerDetailUI(unittest.TestCase):
    def setUp(self):
        self.detail = _text(render_customer_detail())

    def test_detail_keeps_data_edit_link_and_states(self):
        for text in ("Voltar aos clientes", "Dados do cliente", "CPF", "E-mail", "Telefone",
                     "Situação", "Bloqueio manual", "Não informado", "Editar cadastro",
                     "/editar", "Carregando cliente", "customer_detail_error",
                     "customers_success", 'role:"alert"'):
            with self.subTest(text=text):
                self.assertIn(text, self.detail)
        self.assertRegex(
            self.detail,
            r'user_role_rx_state_\?\.valueOf\?\.\(\) === "admin"[^;]*?Editar cadastro',
        )

    def test_block_control_is_admin_only_and_keeps_handlers(self):
        panel = _text(customer_block_panel())
        for text in ("toggle_customer_manual_block", "capture_customer_block_reason",
                     "customer_block_loading", "Aplicar bloqueio manual",
                     "Remover bloqueio manual", "Motivo do bloqueio manual", "maxLength:500",
                     "Controle de bloqueio manual"):
            with self.subTest(text=text):
                self.assertIn(text, panel)
        self.assertRegex(
            self.detail,
            r'=== "admin"\?\.valueOf\?\.\(\)\)\?\(jsx\(Fragment,\{\},jsx\("section",\{"aria-label":"Controle de bloqueio manual"',
        )

    def test_block_registered_name_is_the_session_user(self):
        panel = _text(customer_block_panel())
        self.assertIn("registrado em nome de", panel)
        self.assertIn("user_name", panel)

    def test_history_is_a_disabled_placeholder_without_fictional_data(self):
        panel = _text(customer_history_panel())
        for tab in ("Locações", "Multas", "Pagamentos"):
            self.assertIn(tab, panel)
        self.assertEqual(panel.count("Em breve"), 3)
        self.assertEqual(panel.count('"aria-disabled":"true"'), 3)
        self.assertIn(
            "Aguardando implementação das capacidades de locações, multas e pagamentos. "
            "Nenhum saldo ou histórico financeiro é apresentado nesta versão.",
            panel,
        )
        for forbidden in ("R$", "Saldo:", "saldo de"):
            self.assertNotIn(forbidden, panel)

    def test_detail_has_no_delete_action(self):
        for forbidden in ("Excluir", "Apagar", "delete"):
            self.assertNotIn(forbidden, self.detail)


class TestCustomersStyles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_tokens_and_responsiveness(self):
        for token in ("#dc2638", '"Inter"', '"Space Mono"', "border: 1px dashed",
                      "@media (max-width: 1100px)", "@media (max-width: 900px)",
                      "@media (max-width: 640px)", "attr(data-label)", ":focus-visible",
                      "backdrop-filter"):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_css_does_not_leak_to_other_pages(self):
        selectors = re.findall(r"^([.#a-zA-Z][^{]*)\{", self.css, flags=re.M)
        self.assertTrue(selectors)
        for selector in selectors:
            for part in selector.split(","):
                with self.subTest(selector=part.strip()):
                    self.assertIn("vitrine-clientes", part)


if __name__ == "__main__":
    unittest.main()
