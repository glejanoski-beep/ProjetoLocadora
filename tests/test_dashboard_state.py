"""Estado Reflex real, com sessão e chamadas Xano simuladas localmente."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import reflex as rx

from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.dashboard_state import DashboardState
from ProjetoLocadora.dashboard_client import DashboardErrorCategory, XanoDashboardError


SUMMARY = {"total_filmes": 3, "total_exemplares": 5, "generated_at": "2026-10-18T15:00:00Z"}
ME = {"id": 1, "role": "admin", "is_active": True}


async def consume(event):
    async for _ in event:
        pass


class TestDashboardState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.dashboard = await self.root.get_state(DashboardState)
        self.session = await self.dashboard.get_state(State)
        self.session._user_id = "1"
        self.session._user_role = "admin"
        self.session._xano_auth_token = "synthetic-secret"
        self.me_patch = patch("ProjetoLocadora.dashboard_state.get_me_xano", new_callable=AsyncMock)
        self.api_patch = patch("ProjetoLocadora.dashboard_state.get_dashboard_summary_xano", new_callable=AsyncMock)
        self.me = self.me_patch.start()
        self.api = self.api_patch.start()
        self.addCleanup(self.me_patch.stop)
        self.addCleanup(self.api_patch.stop)
        self.me.return_value = ME
        self.api.return_value = SUMMARY

    async def test_real_sibling_access_and_private_state(self):
        self.assertIs(await self.dashboard.get_state(State), self.session)
        self.assertIsNone(self.dashboard.total_filmes)
        self.assertEqual(self.dashboard.status, "initial")
        self.assertIn("_revision", DashboardState.backend_vars)
        self.assertIn("_request_id", DashboardState.backend_vars)
        self.assertNotIn("_xano_auth_token", DashboardState.backend_vars)
        self.assertNotIn("_invalidate", DashboardState.event_handlers)
        self.assertNotIn("synthetic-secret", str(self.dashboard.dict()))
        other = rx.State(_reflex_internal_init=True)
        self.assertIsNot(await other.get_state(DashboardState), self.dashboard)

    async def test_loading_clears_values_then_accepts_valid_zero(self):
        self.dashboard.total_filmes = 99
        self.dashboard.total_exemplares = 99
        self.dashboard.generated_at = "old"
        event = self.dashboard.load_summary()
        await anext(event)
        self.assertTrue(self.dashboard.loading)
        self.assertEqual(self.dashboard.status, "loading")
        self.assertIsNone(self.dashboard.total_filmes)
        self.assertEqual(self.dashboard.generated_at, "")
        self.api.return_value = {**SUMMARY, "total_filmes": 0, "total_exemplares": 0}
        await consume(event)
        self.assertEqual(self.dashboard.status, "success")
        self.assertEqual(self.dashboard.total_filmes, 0)
        self.assertFalse(self.dashboard.loading)
        self.api.assert_awaited_once_with("synthetic-secret")

    async def test_member_and_anonymous_cannot_call_either_event(self):
        for role, token, expected in (("member", "synthetic-secret", "forbidden"),
                                       ("admin", "", "unauthenticated")):
            for name in ("load_summary", "refresh_summary"):
                with self.subTest(role=role, event=name):
                    self.session._user_role = role
                    self.session._xano_auth_token = token
                    await consume(getattr(self.dashboard, name)())
                    self.assertEqual(self.dashboard.status, expected)
                    self.assertIsNone(self.dashboard.total_filmes)
        self.me.assert_not_awaited()
        self.api.assert_not_awaited()

    async def test_manual_refresh_revalidates_and_preserves_other_modules(self):
        self.session.films_error = "catalog-marker"
        await consume(self.dashboard.load_summary())
        self.me.return_value = {**ME, "role": "member"}
        await consume(self.dashboard.refresh_summary())
        self.assertEqual(self.me.await_count, 2)
        self.assertEqual(self.api.await_count, 1)
        self.assertEqual(self.dashboard.status, "forbidden")
        self.assertIsNone(self.dashboard.total_filmes)
        self.assertEqual(self.session.films_error, "catalog-marker")
        self.assertEqual(self.session._user_role, "member")

    async def test_revalidation_rejects_invalid_inactive_or_different_identity(self):
        for me in (None, {**ME, "is_active": False}, {**ME, "id": 2}, {**ME, "role": "unknown"}):
            with self.subTest(me=me):
                self.session._user_id = "1"
                self.session._user_role = "admin"
                self.session._xano_auth_token = "synthetic-secret"
                self.me.return_value = me
                await consume(self.dashboard.load_summary())
                self.assertEqual(self.dashboard.status, "unauthenticated")
        self.api.assert_not_awaited()

    async def test_legacy_admin_is_accepted_without_active_flag(self):
        self.me.return_value = {"id": 1, "role": "admin"}
        await consume(self.dashboard.load_summary())
        self.assertEqual(self.dashboard.status, "success")

    async def test_session_change_during_revalidation_prevents_business_query(self):
        async def changed(token):
            self.session._user_role = "member"
            return ME

        self.me.side_effect = changed
        await consume(self.dashboard.load_summary())
        self.api.assert_not_awaited()
        self.assertEqual(self.dashboard.status, "initial")

    async def test_error_categories_are_sanitized_without_fallback(self):
        expected = {
            "authentication": "unauthenticated", "authorization": "forbidden",
            "connection": "unavailable", "timeout": "unavailable", "service": "unavailable",
            "invalid_response": "invalid_response", "unexpected_status": "error", "configuration": "error",
        }
        for category in DashboardErrorCategory:
            with self.subTest(category=category):
                self.session._user_id = "1"
                self.session._user_role = "admin"
                self.session._xano_auth_token = "synthetic-secret"
                error = XanoDashboardError(category)
                error.args = ("synthetic-secret sensitive-body",)
                self.api.side_effect = error
                await consume(self.dashboard.load_summary())
                self.assertEqual(self.dashboard.status, expected[category.value])
                self.assertIsNone(self.dashboard.total_filmes)
                self.assertIsNone(self.dashboard.total_exemplares)
                self.assertEqual(self.dashboard.generated_at, "")
                self.assertNotIn("synthetic-secret", self.dashboard.message)
                self.assertNotIn("sensitive-body", self.dashboard.message)
                self.assertFalse(self.dashboard.loading)

    async def test_duplicate_manual_refresh_does_not_start_second_request(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def slow(token):
            started.set()
            await release.wait()
            return SUMMARY

        self.api.side_effect = slow
        task = asyncio.create_task(consume(self.dashboard.load_summary()))
        await started.wait()
        await consume(self.dashboard.refresh_summary())
        release.set()
        await task
        self.api.assert_awaited_once()
        self.me.assert_awaited_once()

    async def test_session_change_during_request_discards_response(self):
        for change in ("logout", "other_admin", "member"):
            with self.subTest(change=change):
                self.session._user_id = "1"
                self.session._user_role = "admin"
                self.session._xano_auth_token = "synthetic-secret"

                async def changed(token):
                    if change == "logout":
                        self.session._xano_auth_token = ""
                    elif change == "other_admin":
                        self.session._user_id = "2"
                    else:
                        self.session._user_role = "member"
                    return SUMMARY

                self.api.side_effect = changed
                await consume(self.dashboard.load_summary())
                self.assertIsNone(self.dashboard.total_filmes)
                self.assertEqual(self.dashboard.status, "initial")
                self.assertFalse(self.dashboard.loading)

    async def test_invalidated_old_request_does_not_overwrite_new_success(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def slow(token):
            started.set()
            await release.wait()
            return {**SUMMARY, "total_filmes": 99}

        self.api.side_effect = slow
        old = asyncio.create_task(consume(self.dashboard.load_summary()))
        await started.wait()
        self.dashboard._invalidate()
        self.api.side_effect = None
        await consume(self.dashboard.refresh_summary())
        release.set()
        await old
        self.assertEqual(self.dashboard.total_filmes, 3)
        self.assertEqual(self.dashboard.status, "success")
        self.assertFalse(self.dashboard.loading)


if __name__ == "__main__":
    unittest.main()
