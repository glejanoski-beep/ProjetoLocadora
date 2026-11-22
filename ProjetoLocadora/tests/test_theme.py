import unittest

from ProjetoLocadora.ProjetoLocadora import State, dashboard_topbar


class TestTheme(unittest.TestCase):
    def setUp(self) -> None:
        self.state = State(_reflex_internal_init=True)

    def test_dark_is_the_default_theme(self) -> None:
        self.assertEqual(self.state.theme_mode, "dark")

    def test_toggle_changes_theme_without_changing_session(self) -> None:
        self.state._user_id = "7"
        self.state.theme_mode = "dark"

        event = self.state.toggle_theme()

        self.assertEqual(self.state.theme_mode, "light")
        self.assertEqual(self.state._user_id, "7")
        self.assertIsNotNone(event)

    def test_toggle_back_to_dark(self) -> None:
        self.state.theme_mode = "light"

        self.state.toggle_theme()

        self.assertEqual(self.state.theme_mode, "dark")

    def test_invalid_theme_is_normalized(self) -> None:
        self.state.theme_mode = "sepia"

        self.state.normalize_theme()

        self.assertEqual(self.state.theme_mode, "dark")
        self.assertEqual(self.state.theme_toggle_label, "Ativar modo claro")

    def test_topbar_contains_theme_button_and_accessible_label(self) -> None:
        component = dashboard_topbar("/backoffice")
        rendered = str(component)

        self.assertIn("vitrine-dash__theme-toggle", rendered)
        self.assertIn("theme_toggle_label", rendered)

