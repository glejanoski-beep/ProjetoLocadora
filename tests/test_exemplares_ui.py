"""Estrutura, agrupamento e estilos da tela de Exemplares; não é teste de navegador."""

import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ProjetoLocadora.ProjetoLocadora import (
    EXEMPLAR_FILTER_ALL,
    State,
    exemplar_dialog,
    exemplares_filters,
    render_exemplares_page,
)
from ProjetoLocadora.xano_client import XanoExemplarError


CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "exemplares.css"


def _text(component) -> str:
    return re.sub(
        r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), str(component)
    )


def _film(film_id, title, genre="Drama", year=2000):
    return {
        "id": film_id,
        "titulo": title,
        "genero": genre,
        "ano_lancamento": year,
        "classificacao": "Livre",
        "valor_locacao_centavos": 1000,
        "status": "active",
    }


def _exemplar(item_id, code, film_id, title):
    return {"id": item_id, "identificador": code, "filme_id": film_id, "filme_titulo": title}


FILMS = [_film(1, "Alfa", "Ação", 2006), _film(2, "Beta", "Terror", 2020), _film(3, "Gama")]
EXEMPLARES = [
    _exemplar(10, "ALF-001", 1, "Alfa"),
    _exemplar(11, "BET-001", 2, "Beta"),
    _exemplar(12, "bet-xyz", 2, "Beta"),
]


def make_state(role="admin", films=None, exemplares=None) -> State:
    state = State(_reflex_internal_init=True)
    state._xano_auth_token = "private-token"
    state._user_id = "1"
    state._user_role = role
    state.exemplar_films = FILMS if films is None else films
    state.exemplares = EXEMPLARES if exemplares is None else exemplares
    return state


class TestExemplaresPageStructure(unittest.TestCase):
    def setUp(self):
        self.page = _text(render_exemplares_page())

    def test_header_navigation_filters_and_admin_actions(self):
        for text in ("ACERVO", "Exemplares", "Cadastrar exemplar", "Navegação principal",
                     "Buscar por identificador", "Filtrar por filme"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertRegex(self.page, r'"aria-current":"page"[^}]*to:"/exemplares"')
        self.assertIn('user_role_rx_state_?.valueOf?.() === "admin"', self.page)

    def test_states_and_messages_are_preserved(self):
        for text in ("Carregando exemplares", "Nenhum exemplar encontrado.",
                     "Nenhum exemplar corresponde aos filtros.", 'role:"alert"', 'role:"status"'):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        for var in ("exemplares_error", "exemplares_success", "exemplar_films_error"):
            self.assertIn(var, self.page)

    def test_group_rows_show_real_fields_without_edit_actions(self):
        for field in ("filme_id", "titulo", "detalhe", "identificador", "unidade"):
            with self.subTest(field=field):
                self.assertIn(field, self.page)
        self.assertIn("ID do filme: ", self.page)
        for forbidden in ("Editar", "pencil", "Excluir", "Devolver", "Emprestar", "Locar"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.page)

    def test_no_fictional_data(self):
        for invented in ("Carros", "Sherek", "Velozes", "CAR-001", "CREED-001", "cor4",
                         "Marina Lopes", "ROTA"):
            with self.subTest(text=invented):
                self.assertNotIn(invented, self.page)

    def test_copy_shortcut_reuses_selection_handler_and_opens_dialog(self):
        for text in ("Outra cópia", "Adicionar cópia", "capture_exemplar_film_selection",
                     "set_exemplar_dialog_open"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertNotIn("identificador_auto", self.page)

    def test_filters_render(self):
        self.assertIsInstance(exemplares_filters().render(), dict)
        filters = _text(exemplares_filters())
        for handler in ("capture_exemplar_search", "capture_exemplar_film_filter"):
            self.assertIn(handler, filters)


class TestExemplarDialog(unittest.TestCase):
    def setUp(self):
        self.dialog = _text(exemplar_dialog())

    def test_dialog_is_controlled_and_keeps_existing_handlers(self):
        for text in ("exemplar_dialog_open", "set_exemplar_dialog_open", "capture_exemplar_identifier",
                     "capture_exemplar_film_selection", "submit_exemplar", "exemplar_form_loading",
                     "Cadastrar exemplar", "Cancelar", "Fechar",
                     "Identificador do exemplar", "Filme associado ao exemplar"):
            with self.subTest(text=text):
                self.assertIn(text, self.dialog)

    def test_dialog_shows_form_errors_as_alerts_and_has_accessible_title(self):
        for text in ("exemplar_form_error", "exemplar_films_error", 'role:"alert"',
                     "Cada cópia física do filme é um exemplar."):
            self.assertIn(text, self.dialog)
        self.assertIn("Dialog.Title", self.dialog)
        self.assertIn("Dialog.Description", self.dialog)

    def test_dialog_is_only_rendered_for_admin(self):
        page = _text(render_exemplares_page())
        self.assertRegex(page, r'=== "admin"[^;]*?\?\(jsx\(Fragment,\{\},jsx\(RadixThemesDialog')


class TestExemplarGroups(unittest.TestCase):
    def groups(self, state):
        return State.exemplar_groups.fget(state)

    def test_admin_groups_follow_film_list_and_include_films_without_copies(self):
        groups = self.groups(make_state())
        self.assertEqual([g["filme_id"] for g in groups], [1, 2, 3])
        self.assertEqual([g["count"] for g in groups], [1, 2, 0])
        self.assertEqual([g["unidade"] for g in groups], ["exemplar", "exemplares", "exemplares"])
        self.assertEqual(groups[0]["detalhe"], "Ação · 2006")
        self.assertEqual(groups[1]["opcao"], "2 | Beta")
        self.assertTrue(all(g["pode_adicionar"] for g in groups))
        self.assertEqual(
            [item["identificador"] for item in groups[1]["exemplares"]], ["BET-001", "bet-xyz"]
        )

    def test_member_sees_only_films_with_copies_and_no_extra_data(self):
        groups = self.groups(make_state("member", films=[]))
        self.assertEqual([g["filme_id"] for g in groups], [1, 2])
        for group in groups:
            self.assertEqual(group["detalhe"], "")
            self.assertFalse(group["pode_adicionar"])

    def test_groups_use_catalog_cover_for_every_profile(self):
        for role, films in (("admin", None), ("member", [])):
            with self.subTest(role=role):
                state = make_state(role, films=films)
                state.exemplar_covers = {2: "https://img.local/beta.jpg"}
                covers = {g["filme_id"]: g["capa_url"] for g in self.groups(state)}
                self.assertEqual(covers[2], "https://img.local/beta.jpg")
                self.assertEqual(covers[1], "")

    def test_thumbnail_renders_cover_image_over_gradient(self):
        self.assertIn("vitrine-exemplares__thumb-img", _text(render_exemplares_page()))

    def test_admin_without_film_list_falls_back_to_exemplares_only(self):
        state = make_state(films=[])
        state.exemplar_films_error = "Falha"
        self.assertEqual([g["filme_id"] for g in self.groups(state)], [1, 2])

    def test_no_exemplares_and_no_films_yields_no_groups(self):
        self.assertEqual(self.groups(make_state(films=[], exemplares=[])), [])

    def test_identifier_search_is_presentation_only_and_case_insensitive(self):
        state = make_state()
        state.capture_exemplar_search("  BET-")
        groups = self.groups(state)
        self.assertEqual([g["filme_id"] for g in groups], [2])
        self.assertEqual(groups[0]["count"], 2)
        state.capture_exemplar_search("xyz")
        groups = self.groups(state)
        self.assertEqual([i["identificador"] for i in groups[0]["exemplares"]], ["bet-xyz"])
        state.capture_exemplar_search("nada")
        self.assertEqual(self.groups(state), [])
        self.assertEqual(len(state.exemplares), 3)

    def test_film_filter_uses_option_and_all_sentinel(self):
        state = make_state()
        state.capture_exemplar_film_filter("3 | Gama")
        groups = self.groups(state)
        self.assertEqual([(g["filme_id"], g["count"]) for g in groups], [(3, 0)])
        state.capture_exemplar_film_filter(EXEMPLAR_FILTER_ALL)
        self.assertEqual(len(self.groups(state)), 3)

    def test_filter_options_and_summary_use_real_counts(self):
        state = make_state()
        self.assertEqual(
            State.exemplar_filter_options.fget(state),
            [EXEMPLAR_FILTER_ALL, "1 | Alfa", "2 | Beta", "3 | Gama"],
        )
        self.assertEqual(State.exemplar_summary.fget(state), "3 exemplares · 2 de 3 filmes com cópia")
        member = make_state("member", films=[], exemplares=[EXEMPLARES[0]])
        self.assertEqual(State.exemplar_summary.fget(member), "1 exemplar")

    def test_filters_do_not_call_xano(self):
        with patch("ProjetoLocadora.ProjetoLocadora.list_exemplares_xano") as exemplares, patch(
            "ProjetoLocadora.ProjetoLocadora.list_films_xano"
        ) as films:
            state = make_state()
            state.capture_exemplar_search("alf")
            state.capture_exemplar_film_filter("1 | Alfa")
            self.groups(state)
        exemplares.assert_not_called()
        films.assert_not_called()


class TestExemplarDialogState(unittest.IsolatedAsyncioTestCase):
    def test_admin_opens_and_close_discards_draft(self):
        state = make_state()
        state.exemplar_form_error = "erro antigo"
        state.set_exemplar_dialog_open(True)
        self.assertTrue(state.exemplar_dialog_open)
        self.assertEqual(state.exemplar_form_error, "")
        state.capture_exemplar_identifier("X-1")
        state.capture_exemplar_film_selection("1 | Alfa")
        state.set_exemplar_dialog_open(False)
        self.assertFalse(state.exemplar_dialog_open)
        self.assertEqual((state.exemplar_identifier, state.exemplar_film_selection), ("", ""))

    def test_member_cannot_open_dialog(self):
        state = make_state("member")
        state.set_exemplar_dialog_open(True)
        self.assertFalse(state.exemplar_dialog_open)

    def test_shortcut_preselects_film_without_generating_identifier(self):
        state = make_state()
        state.capture_exemplar_film_selection("2 | Beta")
        state.set_exemplar_dialog_open(True)
        self.assertEqual(state.exemplar_film_selection, "2 | Beta")
        self.assertEqual(state.exemplar_identifier, "")

    async def test_success_closes_dialog_and_error_keeps_it_open(self):
        created = _exemplar(99, "NEW-001", 1, "Alfa")
        state = make_state()
        state.set_exemplar_dialog_open(True)
        state.capture_exemplar_identifier("NEW-001")
        state.capture_exemplar_film_selection("1 | Alfa")
        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(side_effect=XanoExemplarError("Já existe um exemplar com este identificador.")),
        ):
            await state.submit_exemplar()
        self.assertTrue(state.exemplar_dialog_open)
        self.assertEqual(state.exemplar_form_error, "Já existe um exemplar com este identificador.")
        self.assertEqual(state.exemplar_identifier, "NEW-001")

        with patch(
            "ProjetoLocadora.ProjetoLocadora.create_exemplar_xano",
            new=AsyncMock(return_value=created),
        ) as create:
            await state.submit_exemplar()
        create.assert_awaited_once_with("private-token", {"identificador": "NEW-001", "filme_id": 1})
        self.assertFalse(state.exemplar_dialog_open)
        self.assertEqual(state.exemplares_success, "Exemplar cadastrado com sucesso.")
        self.assertEqual(state.exemplares[0], created)

    async def test_validation_error_keeps_dialog_open_without_calling_xano(self):
        state = make_state()
        state.set_exemplar_dialog_open(True)
        with patch("ProjetoLocadora.ProjetoLocadora.create_exemplar_xano", new=AsyncMock()) as create:
            await state.submit_exemplar()
        create.assert_not_awaited()
        self.assertTrue(state.exemplar_dialog_open)
        self.assertEqual(state.exemplar_form_error, "Informe o identificador do exemplar.")


class TestExemplaresStyles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_tokens_tones_and_responsiveness(self):
        for token in ("#dc2638", '"Inter"', '"Space Mono"', "border: 1px dashed",
                      "@media (max-width: 1100px)", "@media (max-width: 640px)",
                      ":focus-visible", "backdrop-filter"):
            with self.subTest(token=token):
                self.assertIn(token, self.css)
        for tone in range(5):
            self.assertIn(f"vitrine-exemplares__row--tone-{tone}", self.css)

    def test_css_does_not_leak_to_other_pages(self):
        selectors = re.findall(r"^([.#a-zA-Z][^{]*)\{", self.css, flags=re.M)
        self.assertTrue(selectors)
        for selector in selectors:
            for part in selector.split(","):
                with self.subTest(selector=part.strip()):
                    self.assertIn("vitrine-exemplares", part)


if __name__ == "__main__":
    unittest.main()
