"""Relatórios (gerar-relatorios): período, contrato, ranking, estado e contrato Xano.

HTTP simulado localmente; NÃO consulta o Xano. Totais reais exigem conferência no workspace.
"""

from datetime import date, datetime, timezone
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import reflex as rx

from ProjetoLocadora import relatorios_client as client
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.relatorios import (
    atalho, intervalo_ms, percentual, ranking, validar_periodo, validar_relatorio,
)
from ProjetoLocadora.relatorios_state import RelatoriosState
from tests.test_locacoes_xano_contract import ROOT, body, calls, flatten, predicate_exists

FROM, TO = intervalo_ms(date(2026, 10, 1), date(2026, 10, 31))
REPORT = {
    "from": FROM, "to": TO, "generated_at": TO + 1000,
    "rentals": {"checkouts": 9, "returns": 4, "late_returns": 1, "active_now": 5, "overdue_now": 2},
    "fines": {"generated_count": 1, "generated_cents": 300, "waived_count": 0, "waived_cents": 0, "open_balance_cents": 0},
    "payments": {"received_cents": 300, "received_count": 2, "by_method": {"cash": 300, "pix": 0, "debit_card": 0, "credit_card": 0}, "reversed_count": 0, "reversed_cents": 0},
    "films": [
        {"film_id": 1, "film_title": "Carros", "rentals": 3, "exemplars": 2},
        {"film_id": 2, "film_title": "Creed", "rentals": 5, "exemplars": 1},
        {"film_id": 3, "film_title": "Batman", "rentals": 1, "exemplars": 3},
    ],
}


async def consume(event):
    async for _ in event:
        pass


class TestPeriod(unittest.TestCase):
    def test_interval_is_brasilia_midnight_to_next_midnight(self):
        start, end = intervalo_ms(date(2026, 10, 1), date(2026, 10, 1))
        self.assertEqual(datetime.fromtimestamp(start / 1000, timezone.utc).isoformat(), "2026-10-01T03:00:00+00:00")
        self.assertEqual(end - start, 24 * 3600 * 1000)

    def test_shortcuts_include_today_and_handle_month_and_year_turns(self):
        self.assertEqual(atalho("7d", date(2026, 11, 6)), (date(2026, 10, 31), date(2026, 11, 6)))
        self.assertEqual(atalho("30d", date(2026, 11, 6)), (date(2026, 10, 8), date(2026, 11, 6)))
        self.assertEqual(atalho("month", date(2026, 11, 6)), (date(2026, 11, 1), date(2026, 11, 6)))
        self.assertEqual(atalho("last_month", date(2026, 1, 15)), (date(2025, 12, 1), date(2025, 12, 31)))
        self.assertEqual(atalho("last_month", date(2028, 3, 1)), (date(2028, 2, 1), date(2028, 2, 29)))

    def test_manual_period_validation(self):
        self.assertEqual(validar_periodo("2026-10-01", "2026-10-01"), (date(2026, 10, 1), date(2026, 10, 1)))
        self.assertEqual(validar_periodo("2025-11-07", "2026-11-07")[0], date(2025, 11, 7))  # 366 dias
        for start, end in (("2026-10-02", "2026-10-01"), ("", "2026-10-01"), ("2026-02-30", "2026-03-01"), ("2025-01-01", "2026-12-31")):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validar_periodo(start, end)


class TestReportContract(unittest.TestCase):
    def test_valid_report(self):
        self.assertEqual(validar_relatorio(REPORT, FROM, TO), REPORT)

    def test_incoherent_report_is_rejected(self):
        def changed(section, **values):
            return {**REPORT, section: {**REPORT[section], **values}}

        variants = [
            {**REPORT, "from": FROM + 1},
            changed("rentals", late_returns=5),
            changed("rentals", overdue_now=6),
            changed("rentals", checkouts=-1),
            changed("payments", received_cents=301),
            changed("fines", generated_cents="300"),
            {**REPORT, "films": [REPORT["films"][0], REPORT["films"][0]]},
            {**REPORT, "films": [{**REPORT["films"][0], "rentals": 0}]},
            {**REPORT, "films": [{**REPORT["films"][0], "customer_name": "x"}]},
            {**REPORT, "films": [{**REPORT["films"][0], "rentals": 99}]},
            {**REPORT, "cpf": "x"},
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validar_relatorio(value, FROM, TO)

    def test_ranking_and_percentage(self):
        films = REPORT["films"] + [{"film_id": 4, "film_title": "alien", "rentals": 3, "exemplars": 1}]
        self.assertEqual([f["film_title"] for f in ranking(films)], ["Creed", "alien", "Carros", "Batman"])
        many = [{"film_id": i, "film_title": f"F{i:02d}", "rentals": 1, "exemplars": 1} for i in range(1, 15)]
        self.assertEqual(len(ranking(many)), 10)
        self.assertEqual(percentual(1, 4), "25%")
        self.assertEqual(percentual(0, 0), "—")


class TestReportTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.requests = []

    async def call(self, response):
        def handler(request):
            self.requests.append(request)
            return response

        real = httpx.AsyncClient

        def fake(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real(*args, **kwargs)

        with patch("ProjetoLocadora.multas_client.httpx.AsyncClient", side_effect=fake):
            return await client.operational_report("tok", FROM, TO)

    async def test_single_read_with_period(self):
        self.assertEqual(await self.call(httpx.Response(200, json=REPORT)), REPORT)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].url.path, "/api:rentals/relatorios/operacional")
        self.assertEqual(dict(self.requests[0].url.params), {"from": str(FROM), "to": str(TO)})

    async def test_error_categories(self):
        for response, category in (
            (httpx.Response(403, json={}), "authorization"),
            (httpx.Response(401, json={}), "authentication"),
            (httpx.Response(400, json={"message": "Período inválido."}), "input"),
            (httpx.Response(429, json={}), "ratelimited"),
            (httpx.Response(200, json={**REPORT, "to": TO + 1}), "invalid"),
            (httpx.Response(500, json={}), "unavailable"),
        ):
            with self.subTest(category=category), self.assertRaises(client.ReportError) as error:
                await self.call(response)
            self.assertEqual(error.exception.category, category)

    async def test_invalid_period_is_not_sent(self):
        with self.assertRaises(client.ReportError):
            await client.operational_report("tok", TO, FROM)
        self.assertEqual(self.requests, [])


class TestReportState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(RelatoriosState)
        self.session = await self.root.get_state(State)
        self.session._user_id, self.session._user_role, self.session._xano_auth_token = "3", "admin", "private-token"
        patch("ProjetoLocadora.multas_state.get_me_xano", new=AsyncMock(return_value={"id": 3, "role": "admin", "is_active": True})).start()
        self.api = patch("ProjetoLocadora.relatorios_state.operational_report", new=AsyncMock(return_value=REPORT)).start()
        patch("ProjetoLocadora.relatorios_state.hoje_brasilia", return_value=date(2026, 10, 31)).start()
        self.addCleanup(patch.stopall)

    async def test_admin_opens_last_30_days(self):
        await consume(self.state.open_page())
        self.assertEqual((self.state.start_text, self.state.end_text), ("2026-10-02", "2026-10-31"))
        self.assertEqual(self.api.await_args.args[1:], intervalo_ms(date(2026, 10, 2), date(2026, 10, 31)))
        self.assertEqual(self.state.state, "ready")
        self.assertEqual(self.state.film_rows[0]["title"], "Creed")
        self.assertEqual(self.state.film_rows[0]["detail"], "5 locações · 1 exemplar")
        self.assertEqual(self.state.film_rows[0]["width"], "100%")
        self.assertEqual(self.state.rental_cards[2]["note"], "25% das devoluções")
        self.assertEqual(self.state.finance_cards[1]["value"], "R$ 3,00")

    async def test_member_never_queries(self):
        self.session._user_role = "member"
        await consume(self.state.open_page())
        self.assertEqual(self.state.state, "forbidden")
        self.api.assert_not_awaited()

    async def test_invalid_manual_period_is_not_sent(self):
        self.state.capture_start("2026-10-31")
        self.state.capture_end("2026-10-01")
        await consume(self.state.generate())
        self.assertIn("início", self.state.message)
        self.api.assert_not_awaited()
        self.assertEqual(self.state.shortcut, "")

    async def test_logout_discards_the_late_report(self):
        async def late(*args):
            await self.session.logout()
            return REPORT

        self.api.side_effect = late
        await consume(self.state.open_page())
        self.assertFalse(self.state.has_report)
        self.assertEqual(self.state.film_rows, [])

    async def test_backend_refusal_shows_restriction(self):
        self.api.side_effect = client.ReportError("authorization")
        await consume(self.state.open_page())
        self.assertEqual(self.state.state, "forbidden")


class TestReportXanoContract(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "api/locacoes/relatorios_operacional_GET.xs").read_text(encoding="utf-8")
        self.stack = next(calls(body(self.source), "stack"))[1]

    def test_admin_before_any_read_and_no_writes(self):
        self.assertEqual(self.stack[:2], ("function.run", '"Quick Start/enforce_role"'))
        self.assertIn('"admin"', list(flatten(self.stack[2][1])))
        flat = list(flatten(self.stack))
        self.assertLess(flat.index('"admin"'), flat.index("db.query"))
        for statement in ("db.add", "db.edit", "db.del", "db.transaction"):
            self.assertEqual(list(calls(self.stack, statement)), [], statement)
        self.assertNotIn("XANO_RENTAL_WRITES_ENABLED", self.source)

    def test_period_validation_and_no_personal_data(self):
        self.assertTrue(predicate_exists(self.stack, "$input.from > 0 && $input.to > $input.from && $input.to - $input.from <= 31622400000"))
        for personal in ("cpf", "customer_name", "email", "telefone"):
            self.assertNotIn(personal, self.source)


if __name__ == "__main__":
    unittest.main()
