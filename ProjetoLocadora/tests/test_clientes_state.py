import unittest
from unittest.mock import AsyncMock, patch

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.xano_client import XanoCustomerAuditError, XanoCustomerError


SUMMARY = {
    "id": 7,
    "nome": "Maria da Silva",
    "cpf_mascarado": "***.***.***-90",
    "status": "active",
    "bloqueio_manual_ativo": False,
}

DETAIL = {
    "id": 7,
    "created_at": 1700000000000,
    "updated_at": 1700000000000,
    "nome": "Maria da Silva",
    "cpf": "01234567890",
    "email": "maria@example.test",
    "telefone": None,
    "status": "active",
    "bloqueio_manual_ativo": False,
    "motivo_bloqueio_manual": None,
    "bloqueado_em": None,
    "bloqueado_por": None,
}


def authenticated_state(role: str = "admin") -> State:
    state = State(_reflex_internal_init=True)
    state._xano_auth_token = "private-token"
    state._user_id = "1"
    state._user_role = role
    return state


class TestCustomerState(unittest.IsolatedAsyncioTestCase):
    async def test_loads_empty_and_populated_pages_without_touching_catalog_state(self):
        state = authenticated_state("member")
        state.films_error = "mensagem preservada"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_customers_xano",
            new=AsyncMock(
                side_effect=[
                    {"items": [], "page": 1, "per_page": 20, "total": 0},
                    {"items": [SUMMARY], "page": 2, "per_page": 20, "total": 21},
                ]
            ),
        ):
            await state.load_customers()
            self.assertEqual(state.customers, [])
            state.customers_page = 2
            await state.load_customers()
        self.assertEqual(state.customers, [SUMMARY])
        self.assertEqual(state.customers_total, 21)
        self.assertEqual(state.films_error, "mensagem preservada")
        self.assertFalse(state.customers_loading)

    async def test_filters_reset_page_and_transport_error_has_own_state(self):
        state = authenticated_state("member")
        state.customers_page = 3
        state.customer_name_search = "Maria"
        state.customer_cpf_search = "012.345.678-90"
        state.films = [{"id": 99}]
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_customers_xano",
            new=AsyncMock(side_effect=XanoCustomerError("Falha de clientes")),
        ) as listing:
            await state.apply_customer_filters()
        self.assertEqual(state.customers_page, 1)
        self.assertEqual(state.customers_error, "Falha de clientes")
        self.assertEqual(state.films, [{"id": 99}])
        self.assertEqual(listing.await_args.kwargs["nome"], "Maria")

    async def test_pagination_changes_only_when_page_exists(self):
        state = authenticated_state("member")
        state.customers_page = 1
        state.customers_per_page = 20
        state.customers_total = 21
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_customers_xano",
            new=AsyncMock(
                return_value={"items": [], "page": 2, "per_page": 20, "total": 21}
            ),
        ) as listing:
            await state.next_customers_page()
        self.assertEqual(state.customers_page, 2)
        listing.assert_awaited_once()

    async def test_member_is_redirected_from_customer_maintenance(self):
        state = authenticated_state("member")
        redirect = await state.load_new_customer()
        self.assertEqual(redirect.args[0][1]._var_value, "/clientes")

    async def test_create_sends_only_registration_fields(self):
        state = authenticated_state("admin")
        state.customer_form_name = "Maria da Silva"
        state.customer_form_cpf = "012.345.678-90"
        state.customer_form_email = "maria@example.test"
        state.customer_form_phone = ""
        state.customer_form_status = "inactive"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_customer_xano",
            new=AsyncMock(return_value=DETAIL),
        ) as create:
            redirect = await state.submit_customer()
        payload = create.await_args.args[1]
        self.assertEqual(
            set(payload), {"nome", "cpf", "email", "telefone"}
        )
        self.assertFalse(
            {"saldo", "pendencia", "bloqueio_manual_ativo", "motivo"} & set(payload)
        )
        self.assertEqual(redirect.args[0][1]._var_value, "/clientes")

    async def test_not_found_and_partial_audit_are_visible(self):
        state = authenticated_state("admin")
        with patch.object(State, "_route_customer_id", return_value=404), patch(
            "ProjetoLocadora.ProjetoLocadora.get_customer_xano",
            new=AsyncMock(side_effect=XanoCustomerError("Cliente não encontrado.")),
        ):
            await state.load_customer_detail()
        self.assertEqual(state.customer_detail_error, "Cliente não encontrado.")

        state.editing_customer = True
        state.editing_customer_id = 7
        state.customer_form_name = "Maria da Silva"
        state.customer_form_cpf = "01234567890"
        state.customer_form_email = "maria@example.test"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.update_customer_xano",
            new=AsyncMock(
                side_effect=XanoCustomerAuditError(
                    "O cliente foi gravado, mas a auditoria não foi concluída."
                )
            ),
        ):
            await state.submit_customer()
        self.assertIn("foi gravado", state.customer_form_error)

    async def test_manual_block_requires_reason_and_preserves_loaded_customer(self):
        state = authenticated_state("admin")
        state.customer_detail = DETAIL.copy()
        with patch(
            "ProjetoLocadora.ProjetoLocadora.set_customer_manual_block_xano",
            new=AsyncMock(),
        ) as block:
            await state.toggle_customer_manual_block()
        block.assert_not_awaited()
        self.assertIn("motivo", state.customer_detail_error.lower())
        self.assertFalse(state.customer_detail["bloqueio_manual_ativo"])


if __name__ == "__main__":
    unittest.main()
