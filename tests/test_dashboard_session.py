"""Integrações de sessão/rotas: estados reais e HTTP exclusivamente mockado."""

import ast
import asyncio
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.dashboard_state import DashboardState
from ProjetoLocadora.dashboard_client import DashboardErrorCategory, XanoDashboardError
from tests.test_dashboard_state import ME, SUMMARY, consume


class TestDashboardSession(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.session = await self.root.get_state(State)
        self.dashboard = await self.session.get_state(DashboardState)
        self.session._user_id = "1"
        self.session._user_role = "admin"
        self.session._xano_auth_token = "synthetic-secret"
        self.dashboard.total_filmes = 3
        self.dashboard.total_exemplares = 5
        self.dashboard.generated_at = SUMMARY["generated_at"]
        self.dashboard.status = "success"

    def assert_cleared(self):
        self.assertIsNone(self.dashboard.total_filmes)
        self.assertIsNone(self.dashboard.total_exemplares)
        self.assertEqual(self.dashboard.generated_at, "")
        self.assertFalse(self.dashboard.loading)

    async def test_logout_clears_loaded_values_and_redirects(self):
        before = self.session._session_revision
        redirect = await self.session.logout()
        self.assert_cleared()
        self.assertGreater(self.session._session_revision, before)
        self.assertIn("/login", str(redirect))

    async def test_all_async_missing_session_paths_clear_dashboard(self):
        names = (
            "load_exemplares", "submit_exemplar", "load_customers", "load_new_customer",
            "load_customer_detail", "load_customer_for_edit", "submit_customer",
            "toggle_customer_manual_block", "load_films", "load_new_film",
            "load_film_for_edit", "submit_film", "require_session",
        )
        for name in names:
            with self.subTest(event=name):
                self.session._xano_auth_token = ""
                self.dashboard.total_filmes = 77
                result = await getattr(self.session, name)()
                self.assert_cleared()
                self.assertIn("/login", str(result))

    async def test_role_and_identity_changes_invalidate_without_changing_other_modules(self):
        for me in ({**ME, "role": "member"}, {**ME, "id": 2}):
            with self.subTest(me=me):
                self.dashboard.total_filmes = 77
                self.session.films_error = "unchanged"
                with patch("ProjetoLocadora.ProjetoLocadora.get_me_xano", AsyncMock(return_value=me)):
                    await self.session.require_session()
                self.assert_cleared()
                self.assertEqual(self.session.films_error, "unchanged")

    async def test_expired_or_inactive_session_clears_and_redirects(self):
        for me in (None, {**ME, "is_active": False}):
            with self.subTest(me=me):
                self.session._xano_auth_token = "synthetic-secret"
                self.dashboard.total_filmes = 77
                with patch("ProjetoLocadora.ProjetoLocadora.get_me_xano", AsyncMock(return_value=me)):
                    result = await self.session.load_dashboard()
                self.assert_cleared()
                self.assertIn("/login", str(result))

    async def test_restore_without_token_clears_previously_loaded_values(self):
        self.session._xano_auth_token = ""
        await self.session.restore_session()
        self.assert_cleared()

    async def test_summary_401_ends_session_and_emits_login_redirect(self):
        with patch("ProjetoLocadora.dashboard_state.get_me_xano", AsyncMock(return_value=ME)), patch(
            "ProjetoLocadora.dashboard_state.get_dashboard_summary_xano",
            AsyncMock(side_effect=XanoDashboardError(DashboardErrorCategory.AUTHENTICATION)),
        ):
            updates = [update async for update in self.dashboard.refresh_summary()]
        self.assert_cleared()
        self.assertEqual(self.session._xano_auth_token, "")
        self.assertTrue(any("/login" in str(update) for update in updates))

    async def test_sync_revision_blocks_pending_reply_even_before_async_cleanup(self):
        async def old_reply(token):
            self.session._clear_session()
            self.session._xano_auth_token = token
            self.session._set_user(ME)
            return {**SUMMARY, "total_filmes": 99}

        with patch("ProjetoLocadora.dashboard_state.get_me_xano", AsyncMock(return_value=ME)), patch(
            "ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", side_effect=old_reply,
        ):
            await consume(self.dashboard.load_summary())
        self.assert_cleared()

    async def test_entry_validates_before_one_summary_and_member_never_queries(self):
        for role in ("admin", "member"):
            with self.subTest(role=role):
                self.session._user_role = role
                me = {**ME, "role": role}
                with patch("ProjetoLocadora.ProjetoLocadora.get_me_xano", AsyncMock(return_value=me)) as guard, patch(
                    "ProjetoLocadora.dashboard_state.get_me_xano", AsyncMock(return_value=me),
                ), patch("ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", AsyncMock(return_value=SUMMARY)) as api:
                    event = await self.session.load_dashboard()
                    guard.assert_awaited_once()
                    api.assert_not_awaited()
                    self.assertEqual(event.handler, DashboardState.load_summary)
                    await consume(self.dashboard.load_summary())
                    if role == "admin":
                        api.assert_awaited_once()
                    else:
                        api.assert_not_awaited()
                        await consume(self.dashboard.refresh_summary())
                        api.assert_not_awaited()

    async def test_relogin_same_identity_and_token_discards_old_response(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def slow(token):
            started.set()
            await release.wait()
            return {**SUMMARY, "total_filmes": 99}

        with patch("ProjetoLocadora.dashboard_state.get_me_xano", AsyncMock(return_value=ME)), patch(
            "ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", side_effect=slow,
        ):
            old = asyncio.create_task(consume(self.dashboard.load_summary()))
            await started.wait()
            await self.session.logout()
            self.session._login_email = "synthetic@example.test"
            self.session._login_password = "synthetic-password"
            with patch("ProjetoLocadora.ProjetoLocadora.login_xano", AsyncMock(return_value={"authToken": "synthetic-secret"})), patch(
                "ProjetoLocadora.ProjetoLocadora.get_me_xano", AsyncMock(return_value=ME),
            ):
                await self.session.handle_login()
            release.set()
            await old
        self.assert_cleared()
        self.assertNotEqual(self.dashboard.status, "success")

    def test_both_routes_register_only_the_same_entry_event(self):
        tree = ast.parse(Path("ProjetoLocadora/ProjetoLocadora.py").read_text())
        found = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    kwargs = {k.arg: k.value for k in decorator.keywords}
                    route = kwargs.get("route")
                    if isinstance(route, ast.Constant) and route.value in ("/", "/backoffice"):
                        found[route.value] = ast.unparse(kwargs["on_load"])
        self.assertEqual(found, {"/": "State.load_dashboard", "/backoffice": "State.load_dashboard"})


if __name__ == "__main__":
    unittest.main()
