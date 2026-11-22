import unittest
from pathlib import Path

from ProjetoLocadora.usuarios_state import UsuariosState
from ProjetoLocadora.usuarios_ui import users_page


class TestUsuariosInterface(unittest.TestCase):
    def test_own_account_cannot_open_edit_dialog(self) -> None:
        state = UsuariosState(_reflex_internal_init=True)
        state._me = 7
        state._users = [{
            "id": 7,
            "name": "Admin",
            "email": "admin@example.test",
            "role": "admin",
            "is_active": True,
            "created_at": 1700000000000,
        }]

        state.open_edit(7)

        self.assertFalse(state.edit_open)

    def test_users_page_contains_existing_list_and_edit_dialog(self) -> None:
        component = users_page(None)
        rendered = str(component)

        self.assertIn("vitrine-dash__title", rendered)
        self.assertIn("vitrine-usuarios__filters", rendered)
        self.assertIn("vitrine-exemplares-dialog", rendered)

    def test_light_theme_has_specific_users_and_modal_styles(self) -> None:
        css_path = Path(__file__).resolve().parents[2] / "assets" / "usuarios.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn('[data-theme="light"] .vitrine-usuarios__search', css)
        self.assertIn('[data-theme="light"] .vitrine-usuarios__row-button', css)
        self.assertIn('[data-theme="light"] .vitrine-exemplares-dialog:', css)

