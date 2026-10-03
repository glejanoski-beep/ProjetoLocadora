import unittest

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.xano_client import is_authorized_employee


class TestReflexAuthState(unittest.TestCase):
    def test_xano_token_is_backend_only(self):
        self.assertIn("_xano_auth_token", State.backend_vars)
        self.assertNotIn("_xano_auth_token", State.base_vars)

    def test_authentication_flag_is_read_only_computed_state(self):
        self.assertIn("is_authenticated", State.computed_vars)
        self.assertNotIn("is_authenticated", State.base_vars)

    def test_identity_fields_are_not_client_writable(self):
        for field_name in ("user_id", "user_name", "user_email", "user_role"):
            with self.subTest(field=field_name):
                self.assertNotIn(field_name, State.base_vars)
                self.assertIn(field_name, State.computed_vars)

    def test_password_is_not_persisted_in_reflex_state(self):
        self.assertNotIn("password", State.base_vars)

    def test_identity_assignment_helper_is_not_a_public_event(self):
        self.assertFalse(hasattr(State, "set_user"))

    def test_state_has_login_and_logout_handlers(self):
        self.assertTrue(callable(getattr(State, "handle_login", None)))
        self.assertTrue(callable(getattr(State, "logout", None)))

    def test_member_and_admin_active_users_are_allowed(self):
        self.assertTrue(
            is_authorized_employee({"id": 1, "role": "member", "is_active": True})
        )
        self.assertTrue(
            is_authorized_employee({"id": 2, "role": "admin", "is_active": True})
        )

    def test_inactive_or_unrecognized_users_are_rejected(self):
        self.assertFalse(
            is_authorized_employee({"id": 3, "role": "admin", "is_active": False})
        )
        self.assertFalse(
            is_authorized_employee({"id": 4, "role": "customer", "is_active": True})
        )

    def test_legacy_account_without_active_flag_remains_allowed(self):
        self.assertTrue(is_authorized_employee({"id": 5, "role": "member"}))


if __name__ == "__main__":
    unittest.main()
