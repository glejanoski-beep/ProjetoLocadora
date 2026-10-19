import inspect
import json
import unittest
from pathlib import Path

from ProjetoLocadora.ProjetoLocadora import (
    app,
    cassette_badge,
    login_footer,
    login_form,
    login_header,
    login_page,
    login_panel,
    password_recovery_dialog,
)


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets" / "login.css"


def _walk_render_tree(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_render_tree(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_render_tree(value)


def _literal_contents(rendered) -> list[str]:
    contents: list[str] = []
    for node in _walk_render_tree(rendered):
        raw = node.get("contents")
        if not isinstance(raw, str):
            continue
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, str):
            contents.append(value)
    return contents


class TestLoginInterfaceStructure(unittest.TestCase):
    def test_reusable_components_render(self):
        for component_factory in (
            cassette_badge,
            login_header,
            login_form,
            password_recovery_dialog,
            login_footer,
            login_panel,
        ):
            with self.subTest(component=component_factory.__name__):
                self.assertIsInstance(component_factory().render(), dict)

    def test_page_contains_required_content_once(self):
        rendered = login_page().render()
        contents = _literal_contents(rendered)

        for text in (
            "CINEBYTE",
            " LOCADORA",
            "ACESSO DO FUNCIONÁRIO",
            "Entre para gerenciar o acervo e os aluguéis.",
            "LOGIN",
            "SENHA",
            "Esqueci minha senha",
            "ENTRAR NO SISTEMA",
            "ÁREA RESTRITA • VERSÃO 2.4.8",
        ):
            with self.subTest(text=text):
                self.assertEqual(contents.count(text), 1)

    def test_login_uses_one_form_submit_path(self):
        source = inspect.getsource(login_form)

        self.assertIn("on_submit=State.submit_login", source)
        self.assertIn('type="submit"', source)
        self.assertIn('name="login"', source)
        self.assertIn('name="password"', source)
        self.assertIn('html_for=field_id', inspect.getsource(login_header.__globals__["login_field"]))
        self.assertNotIn("on_click=State.handle_login", source)

    def test_password_toggle_is_accessible_and_reactive(self):
        source = inspect.getsource(
            login_header.__globals__["password_visibility_button"]
        )

        self.assertIn("State.toggle_password_visibility", source)
        self.assertIn("aria_label=State.password_toggle_label", source)
        self.assertIn('type="button"', source)

    def test_recovery_dialog_is_controlled_and_uses_real_submit_handler(self):
        source = inspect.getsource(password_recovery_dialog)

        self.assertIn("rx.dialog.root", source)
        self.assertIn("rx.dialog.title", source)
        self.assertIn("rx.dialog.description", source)
        self.assertIn("open=State.reset_dialog_open", source)
        self.assertIn("on_open_change=State.set_reset_dialog_open", source)
        self.assertIn("on_submit=State.submit_reset_link", source)

    def test_app_registers_fonts_and_local_stylesheet(self):
        stylesheets = list(app.stylesheets)

        self.assertIn("/login.css", stylesheets)
        self.assertTrue(any("Press+Start+2P" in item for item in stylesheets))
        self.assertTrue(any("Space+Mono" in item for item in stylesheets))


class TestLoginStyles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_visual_tokens_and_required_dimensions_are_present(self):
        for token in (
            "#09090f",
            "#111118",
            "#0b0b11",
            "#6d28d9",
            "#8b2cf5",
            "#0891b2",
            "#ff7a45",
            "width: min(100%, 460px)",
            "height: 54px",
            "min-height: 56px",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_css_is_scoped_and_supports_interaction_and_responsiveness(self):
        for selector in (
            ".retro-login",
            ".retro-login__panel",
            ":focus-visible",
            ":hover",
            ":active",
            "overflow-x: hidden",
            "overflow-y: auto",
            "@media (max-width: 480px)",
            "@media (max-height: 760px)",
            "@media (prefers-reduced-motion: reduce)",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css)


if __name__ == "__main__":
    unittest.main()
