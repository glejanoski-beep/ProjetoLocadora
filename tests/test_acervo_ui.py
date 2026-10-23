"""Estrutura, estado de apresentação e estilos do Acervo; não é teste de navegador."""

import re
import unittest
from pathlib import Path

from ProjetoLocadora.catalogo_filmes import CLASSIFICACOES
from ProjetoLocadora.ProjetoLocadora import (
    CLASSIFICATION_BADGES,
    FILM_POSTER_TONES,
    FILM_STATUS_FILTERS,
    State,
    classification_badge,
    films_filters,
    render_dashboard,
    render_film_form,
    render_films_page,
)


CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "acervo.css"


def _text(component) -> str:
    return re.sub(
        r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match[1], 16)), str(component)
    )


def _film(film_id, status="active", genre="Drama"):
    return {
        "id": film_id,
        "titulo": f"Filme {film_id}",
        "genero": genre,
        "ano_lancamento": 2000 + film_id,
        "classificacao": "Livre",
        "valor_locacao_centavos": 1990,
        "valor_locacao_display": "R$ 19,90",
        "status": status,
    }


class TestAcervoListStructure(unittest.TestCase):
    def setUp(self):
        self.page = _text(render_films_page())

    def test_header_navigation_and_admin_actions(self):
        for text in ("ACERVO", "Catálogo de filmes", "Cadastrar filme", "/filmes/novo",
                     "Navegação principal"):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertEqual(self.page.count('"aria-current":"page"'), 1)
        self.assertRegex(self.page, r'"aria-current":"page"[^}]*to:"/filmes"')
        self.assertIn('user_role_rx_state_?.valueOf?.() === "admin"', self.page)

    def test_search_and_filters_keep_existing_handlers(self):
        for handler in ("capture_title_search", "capture_genre_filter", "apply_film_filters",
                        "capture_film_status_filter"):
            with self.subTest(handler=handler):
                self.assertIn(handler, self.page)
        for label in ("Buscar por título", "Filtrar por gênero", "Buscar", "Filtrar por status"):
            self.assertIn(label, self.page)
        for _, label in FILM_STATUS_FILTERS:
            self.assertIn(label, self.page)

    def test_states_and_messages_are_preserved(self):
        for text in ("Carregando filmes", "Nenhum filme encontrado.", "Nenhum filme com este status.",
                     "Mostrando ", 'role:"alert"', 'role:"status"'):
            with self.subTest(text=text):
                self.assertIn(text, self.page)
        self.assertIn("films_error", self.page)
        self.assertIn("films_success", self.page)

    def test_card_uses_real_fields_and_admin_only_edit_link(self):
        for field in ("titulo", "genero", "ano_lancamento", "valor_locacao_display",
                      "classificacao", "status"):
            with self.subTest(field=field):
                self.assertIn(field, self.page)
        self.assertIn("/filmes/", self.page)
        self.assertIn("/editar", self.page)
        self.assertIn("vitrine-acervo__edit", self.page)
        self.assertIn("Editar", self.page)

    def test_no_fictional_films_or_prices(self):
        for invented in ("Gui", "Creed", "Sherek", "Velozes", "R$ 15,90", "5 filmes",
                         "Marina Lopes", "ROTA"):
            with self.subTest(text=invented):
                self.assertNotIn(invented, self.page)

    def test_no_grid_list_toggle(self):
        self.assertNotIn("grade", self.page.lower())

    def test_poster_tone_is_stable_by_id_and_posters_are_decorative(self):
        self.assertEqual(FILM_POSTER_TONES, 5)
        self.assertIn("vitrine-acervo__poster--tone-", self.page)
        self.assertIn('?.["id"] % 5', self.page)
        self.assertIn('"aria-hidden":"true"', self.page)

    def test_filters_component_renders(self):
        self.assertIsInstance(films_filters().render(), dict)


class TestClassificationBadges(unittest.TestCase):
    def test_every_classification_has_a_badge(self):
        self.assertEqual(set(CLASSIFICATION_BADGES), set(CLASSIFICACOES))

    def test_badge_is_accessible_with_full_label(self):
        rendered = _text(classification_badge("12 anos"))
        self.assertIn("12 anos", rendered)
        self.assertIn("vitrine-acervo__rating--12", rendered)
        self.assertIn("img", rendered)


class TestAcervoForm(unittest.TestCase):
    def setUp(self):
        self.form = _text(render_film_form())

    def test_form_keeps_handlers_validation_attributes_and_submit(self):
        for handler in ("capture_film_title", "capture_film_genre", "capture_film_year",
                        "capture_film_rent_price", "capture_film_classification",
                        "capture_film_status", "submit_film"):
            with self.subTest(handler=handler):
                self.assertIn(handler, self.form)
        for attribute in ("maxLength:200", "maxLength:100", "maxLength:4", 'inputMode:"numeric"'):
            with self.subTest(attribute=attribute):
                self.assertIn(attribute, self.form)
        for label in ("Título", "Gênero", "Ano de lançamento", "Valor da locação",
                      "Classificação indicativa", "Salvar alterações", "Cancelar"):
            self.assertIn(label, self.form)

    def test_year_field_sends_strings_to_the_str_handler(self):
        # type="number" faz o Reflex enviar int e quebrar State.form_year (str).
        self.assertNotIn('type:"number"', self.form)
        year_input = self.form[self.form.index('id:"film-year"') - 400: self.form.index('id:"film-year"') + 600]
        self.assertIn("capture_film_year", year_input)
        self.assertNotIn("parseFloat", year_input)
        self.assertNotIn("valueAsNumber", year_input)

    def test_form_title_depends_on_editing_state_and_error_is_alert(self):
        for text in ("Editar filme", "Cadastrar filme", "form_error", 'role:"alert"'):
            self.assertIn(text, self.form)

    def test_all_classifications_are_selectable_and_status_only_when_editing(self):
        for name in CLASSIFICACOES:
            with self.subTest(name=name):
                self.assertIn(f'"aria-label":"{name}"', self.form)
        self.assertIn("editing_film", self.form)
        self.assertIn("Inativo", self.form)

    def test_routes_back_to_catalog_are_kept(self):
        # Fechar e Cancelar voltam ao catálogo, além do item de navegação.
        self.assertGreaterEqual(self.form.count('to:"/filmes"'), 3)


class TestFilmStatusPresentationFilter(unittest.TestCase):
    def state(self, films, status_filter="all"):
        state = State(_reflex_internal_init=True)
        state.films = films
        state.film_status_filter = status_filter
        return state

    def test_filters_use_only_active_and_inactive_values(self):
        self.assertEqual([value for value, _ in FILM_STATUS_FILTERS], ["all", "active", "inactive"])

    def test_visible_films_by_status_without_changing_loaded_list(self):
        films = [_film(1, "active"), _film(2, "inactive"), _film(3, "active")]
        for status_filter, expected in (("all", [1, 2, 3]), ("active", [1, 3]), ("inactive", [2])):
            with self.subTest(status_filter=status_filter):
                state = self.state(films, status_filter)
                self.assertEqual([f["id"] for f in State.visible_films.fget(state)], expected)
                self.assertEqual(len(state.films), 3)

    def test_unknown_filter_value_is_ignored(self):
        state = self.state([_film(1)])
        state.capture_film_status_filter("inactive")
        state.capture_film_status_filter("qualquer")
        self.assertEqual(state.film_status_filter, "inactive")
        state.capture_film_status_filter("all")
        self.assertEqual(state.film_status_filter, "all")

    def test_filter_does_not_call_the_catalog_client(self):
        from unittest.mock import patch

        with patch("ProjetoLocadora.ProjetoLocadora.list_films_xano") as list_films:
            state = self.state([_film(1), _film(2, "inactive")])
            state.capture_film_status_filter("active")
            State.visible_films.fget(state)
        list_films.assert_not_called()


class TestSharedTopbarKeepsDashboard(unittest.TestCase):
    def test_dashboard_still_marks_overview_as_current(self):
        rendered = _text(render_dashboard())
        self.assertEqual(rendered.count('"aria-current":"page"'), 1)
        self.assertRegex(rendered, r'"aria-current":"page"[^}]*to:"/backoffice"')


class TestAcervoStyles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_tokens_posters_and_responsiveness(self):
        for token in ("var(--vd-red)", '"Inter"', '"Space Mono"',
                      "grid-template-columns: minmax(0, 1fr)", "@media (max-width: 640px)",
                      ":focus-visible", "border: 1px dashed"):
            with self.subTest(token=token):
                self.assertIn(token, self.css)
        for tone in range(FILM_POSTER_TONES):
            self.assertIn(f"vitrine-acervo__poster--tone-{tone}", self.css)

    def test_css_does_not_leak_to_other_pages(self):
        selectors = re.findall(r"^([.#a-zA-Z][^{]*)\{", self.css, flags=re.M)
        self.assertTrue(selectors)
        for selector in selectors:
            for part in selector.split(","):
                with self.subTest(selector=part.strip()):
                    self.assertIn("vitrine-acervo", part)


if __name__ == "__main__":
    unittest.main()
