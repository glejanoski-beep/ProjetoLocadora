import unittest
from unittest.mock import AsyncMock, patch

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.exemplares import Exemplar
from ProjetoLocadora.xano_client import (
    XanoCatalogError,
    XanoExemplarAuditError,
    XanoExemplarError,
)


FILM = {
    "id": 42,
    "titulo": "Filme de teste",
    "genero": "Drama",
    "ano_lancamento": 2020,
    "classificacao": "Livre",
    "valor_locacao_centavos": 1000,
    "status": "active",
}

EXEMPLAR: Exemplar = {
    "id": 8,
    "identificador": "A-01",
    "filme_id": 42,
    "filme_titulo": "Filme de teste",
}


def authenticated_state(role: str) -> State:
    state = State(_reflex_internal_init=True)
    state._xano_auth_token = "private-token"
    state._user_id = "1"
    state._user_role = role
    return state


class TestExemplarState(unittest.IsolatedAsyncioTestCase):
    async def test_member_lists_exemplares_without_loading_maintenance_options(self):
        state = authenticated_state("member")
        state.films_error = "estado do catálogo preservado"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_exemplares_xano",
            new=AsyncMock(return_value=[EXEMPLAR]),
        ) as listing, patch(
            "ProjetoLocadora.ProjetoLocadora.list_films_xano",
            new=AsyncMock(),
        ) as films:
            await state.load_exemplares()

        listing.assert_awaited_once_with("private-token")
        films.assert_not_awaited()
        self.assertEqual(state.exemplares, [EXEMPLAR])
        self.assertEqual(state.films_error, "estado do catálogo preservado")
        self.assertFalse(state.exemplares_loading)

    async def test_admin_loads_film_choices_and_keeps_list_failure_explicit(self):
        state = authenticated_state("admin")
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_exemplares_xano",
            new=AsyncMock(side_effect=XanoExemplarError("Falha de consulta")),
        ), patch(
            "ProjetoLocadora.ProjetoLocadora.list_films_xano",
            new=AsyncMock(return_value=[FILM]),
        ) as films:
            await state.load_exemplares()

        films.assert_awaited_once_with("private-token")
        self.assertEqual(state.exemplares_error, "Falha de consulta")
        self.assertEqual(state.exemplares, [])
        self.assertEqual(state.exemplar_film_options, ["42 | Filme de teste"])

    async def test_admin_create_preserves_literal_identifier_and_selected_film(self):
        state = authenticated_state("admin")
        state.exemplar_identifier = "  A-01 "
        state.exemplar_film_selection = "42 | Filme de teste"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(return_value=EXEMPLAR),
        ) as create:
            await state.submit_exemplar()

        create.assert_awaited_once_with(
            "private-token",
            {"identificador": "  A-01 ", "filme_id": 42},
        )
        self.assertEqual(state.exemplares, [EXEMPLAR])
        self.assertEqual(state.exemplares_success, "Exemplar cadastrado com sucesso.")
        self.assertEqual(state.exemplar_identifier, "")
        self.assertFalse(state.exemplar_form_loading)

    async def test_member_cannot_submit_and_invalid_form_never_calls_xano(self):
        member = authenticated_state("member")
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(),
        ) as create:
            redirect = await member.submit_exemplar()
        create.assert_not_awaited()
        self.assertEqual(redirect.args[0][1]._var_value, "/exemplares")

        admin = authenticated_state("admin")
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(),
        ) as create:
            await admin.submit_exemplar()
        create.assert_not_awaited()
        self.assertIn("identificador", admin.exemplar_form_error.lower())

    async def test_audit_failure_is_shown_without_success(self):
        state = authenticated_state("admin")
        state.exemplar_identifier = "A-01"
        state.exemplar_film_selection = "42 | Filme de teste"
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(
                side_effect=XanoExemplarAuditError(
                    "O exemplar foi gravado, mas a auditoria não foi concluída."
                )
            ),
        ):
            await state.submit_exemplar()

        self.assertIn("foi gravado", state.exemplar_form_error)
        self.assertEqual(state.exemplares_success, "")
        self.assertEqual(state.exemplares, [])

    async def test_catalog_lookup_failure_does_not_hide_exemplar_list(self):
        state = authenticated_state("admin")
        with patch(
            "ProjetoLocadora.ProjetoLocadora.list_exemplares_xano",
            new=AsyncMock(return_value=[EXEMPLAR]),
        ), patch(
            "ProjetoLocadora.ProjetoLocadora.list_films_xano",
            new=AsyncMock(side_effect=XanoCatalogError("Catálogo indisponível")),
        ):
            await state.load_exemplares()

        self.assertEqual(state.exemplares, [EXEMPLAR])
        self.assertEqual(state.exemplar_films_error, "Catálogo indisponível")


if __name__ == "__main__":
    unittest.main()
