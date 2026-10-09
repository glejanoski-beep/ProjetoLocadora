import unittest
from unittest.mock import AsyncMock, patch

import httpx
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.xano_client import get_me_xano, is_authorized_employee


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

    def test_reset_auth_token_and_passwords_are_backend_only(self):
        for field_name in ("_reset_auth_token", "_new_password", "_confirm_new_password"):
            with self.subTest(field=field_name):
                self.assertIn(field_name, State.backend_vars)
                self.assertNotIn(field_name, State.base_vars)

    def test_identity_assignment_helper_is_not_a_public_event(self):
        self.assertFalse(hasattr(State, "set_user"))

    def test_state_has_login_and_logout_handlers(self):
        self.assertTrue(callable(getattr(State, "handle_login", None)))
        self.assertTrue(callable(getattr(State, "logout", None)))

    def test_state_has_password_recovery_handlers(self):
        self.assertTrue(callable(getattr(State, "request_reset_link", None)))
        self.assertTrue(callable(getattr(State, "consume_reset_link", None)))
        self.assertTrue(callable(getattr(State, "update_password", None)))

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


class TestReflexAuthFlows(unittest.IsolatedAsyncioTestCase):
    async def test_login_accepts_active_member_and_admin(self):
        for role in ("member", "admin"):
            with self.subTest(role=role):
                state = State(_reflex_internal_init=True)
                state._login_email = f"{role}@example.test"
                state._login_password = "test-password"

                with (
                    patch(
                        "ProjetoLocadora.ProjetoLocadora.login_xano",
                        new=AsyncMock(
                            return_value={"authToken": f"token-{role}"}
                        ),
                    ) as login,
                    patch(
                        "ProjetoLocadora.ProjetoLocadora.get_me_xano",
                        new=AsyncMock(
                            return_value={
                                "id": 1,
                                "name": role,
                                "email": f"{role}@example.test",
                                "role": role,
                                "is_active": True,
                            }
                        ),
                    ) as get_me,
                ):
                    await state.handle_login()

                login.assert_awaited_once_with(
                    f"{role}@example.test", "test-password"
                )
                get_me.assert_awaited_once_with(f"token-{role}")
                self.assertEqual(state._xano_auth_token, f"token-{role}")
                self.assertEqual(state._user_role, role)
                self.assertEqual(state._user_id, "1")

    async def test_session_revalidation_clears_inactive_account(self):
        state = State(_reflex_internal_init=True)
        state._xano_auth_token = "valid-token"
        state._user_id = "42"
        state._user_name = "Inactive User"
        state._user_email = "inactive@example.test"
        state._user_role = "member"

        with patch(
            "ProjetoLocadora.ProjetoLocadora.get_me_xano",
            new=AsyncMock(
                return_value={
                    "id": 42,
                    "role": "member",
                    "is_active": False,
                }
            ),
        ) as get_me:
            redirect = await state.require_session()

        get_me.assert_awaited_once_with("valid-token")
        self.assertEqual(redirect.args[0][1]._var_value, "/login")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state._xano_auth_token, "")
        self.assertEqual(state._user_id, "")
        self.assertEqual(state._user_name, "")
        self.assertEqual(state._user_email, "")
        self.assertEqual(state._user_role, "")

    async def test_logout_clears_session_and_redirects_to_login(self):
        state = State(_reflex_internal_init=True)
        state._xano_auth_token = "valid-token"
        state._user_id = "42"
        state._user_role = "admin"

        redirect = await state.logout()

        self.assertEqual(redirect.args[0][1]._var_value, "/login")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state._xano_auth_token, "")
        self.assertEqual(state._user_id, "")
        self.assertEqual(state._user_role, "")

    async def test_get_me_sends_bearer_token_using_local_mock_transport(self):
        auth_token = "test-token"
        real_async_client = httpx.AsyncClient

        def handle_request(request):
            self.assertEqual(
                request.headers["Authorization"],
                f"Bearer {auth_token}",
            )
            self.assertEqual(str(request.url), "https://xano.test/api/auth/me")
            return httpx.Response(
                200,
                json={
                    "id": 42,
                    "role": "member",
                    "is_active": True,
                },
            )

        def mock_client_factory(**kwargs):
            return real_async_client(
                transport=httpx.MockTransport(handle_request),
                **kwargs,
            )

        with patch(
            "ProjetoLocadora.xano_client.httpx.AsyncClient",
            side_effect=mock_client_factory,
        ):
            result = await get_me_xano(
                auth_token,
                base_url="https://xano.test/api",
            )

        self.assertEqual(result["id"], 42)
        self.assertEqual(result["role"], "member")


if __name__ == "__main__":
    unittest.main()
