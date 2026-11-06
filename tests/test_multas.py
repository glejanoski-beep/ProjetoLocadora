"""Multas e pagamentos (registrar-multa-e-pagamento).

HTTP simulado localmente e contratos estáticos: NÃO consulta nem grava no Xano.
Bloqueios, rollback e corrida reais continuam sujeitos à homologação.
"""

import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import reflex as rx

from ProjetoLocadora import multas_client as client
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.multas import (
    centavos, estimar_multa, reais, saldo, validar_fine, validar_payment, validar_policy,
)
from ProjetoLocadora.multas_state import ClienteHistoricoState, MultasState
from tests.test_locacoes_client import RETURNED
from tests.test_locacoes_devolucao import POLICY, fine_for
from tests.test_locacoes_xano_contract import ROOT, body, calls, flatten, predicate_exists, unique_assignment

HOUR = 3600 * 1000
KEY = "0b3b5a8e-7c1d-4e2f-9a6b-1c2d3e4f5a6b"
DUE = RETURNED["due_at"]
FINE = fine_for({**RETURNED, "returned_at": DUE + 49 * HOUR})  # 3 dias, 900 centavos
PAYMENT = {
    "id": 11, "fine_id": FINE["id"], "customer_id": FINE["customer_id"], "amount_cents": 300,
    "method": "pix", "paid_at": FINE["returned_at"] + HOUR, "registered_by": 9, "status": "confirmed",
    "reversed_at": None, "reversed_by": None, "reversal_reason": None,
}
ME = {"id": 9, "role": "member", "is_active": True}


async def consume(event):
    async for _ in event:
        pass


class TestFinePolicy(unittest.TestCase):
    """Mesmos exemplos do design.md; a função Xano segue a mesma regra."""

    def test_design_examples(self):
        cases = (
            (90 * 60 * 1000, (0, 0)),           # 1 h 30: tolerância
            (120 * 60 * 1000, (0, 0)),          # exatamente na tolerância
            (120 * 60 * 1000 + 1, (1, 300)),    # 1 ms além da tolerância já conta o 1º dia
            (3 * HOUR, (1, 300)),
            (24 * HOUR, (1, 300)),
            (47 * HOUR, (2, 600)),
            (49 * HOUR, (3, 900)),
            (45 * 24 * HOUR, (45, 9000)),       # teto
            (-HOUR, (0, 0)),                    # no prazo
        )
        for late, expected in cases:
            with self.subTest(late=late):
                self.assertEqual(estimar_multa(DUE, DUE + late, POLICY), expected)

    def test_money_format_and_parse(self):
        self.assertEqual(reais(0), "R$ 0,00")
        self.assertEqual(reais(900), "R$ 9,00")
        self.assertEqual(reais(123456), "R$ 1.234,56")
        for text, cents in (("9", 900), ("9,5", 950), ("9,50", 950), ("1.234,56", 123456), ("R$ 3,00", 300)):
            self.assertEqual(centavos(text), cents, text)
        for bad in ("", "abc", "9,999", "-3", "1e3", "9.5.1,0", "99999999"):
            self.assertIsNone(centavos(bad), bad)

    def test_policy_contract(self):
        self.assertEqual(validar_policy(POLICY), POLICY)
        for bad in ({**POLICY, "daily_cents": 0}, {**POLICY, "cap_cents": 100}, {**POLICY, "grace_minutes": -1},
                    {**POLICY, "daily_cents": "300"}, {**POLICY, "extra": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validar_policy(bad)


class TestFineContract(unittest.TestCase):
    def test_coherent_states_are_accepted(self):
        self.assertEqual(validar_fine(FINE), FINE)
        partial = {**FINE, "paid_cents": 300}
        self.assertEqual(saldo(validar_fine(partial)), 600)
        self.assertEqual(validar_fine({**FINE, "paid_cents": 900, "status": "paid"})["status"], "paid")
        waived = {**partial, "status": "waived", "waived_cents": 600, "waived_at": FINE["created_at"] + HOUR, "waived_by": 1, "waive_reason": "Cortesia"}
        self.assertEqual(saldo(validar_fine(waived)), 0)

    def test_incoherent_or_personal_data_is_rejected(self):
        variants = [
            {**FINE, "cpf": "x"}, {**FINE, "amount_cents": "900"}, {**FINE, "paid_cents": 1000},
            {**FINE, "status": "paid"}, {**FINE, "paid_cents": 900},  # status e saldo incoerentes
            {**FINE, "status": "waived"}, {**FINE, "waived_cents": 100},
            {**FINE, "amount_cents": 9001, "cap_cents": 9000}, {**FINE, "returned_at": DUE},
            {**FINE, "late_days": 0}, {**FINE, "status": "cancelled"}, {**FINE, "id": True},
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validar_fine(value)

    def test_payment_contract(self):
        self.assertEqual(validar_payment(PAYMENT), PAYMENT)
        reversed_ = {**PAYMENT, "status": "reversed", "reversed_at": PAYMENT["paid_at"] + 1, "reversed_by": 1, "reversal_reason": "Erro de digitação"}
        self.assertEqual(validar_payment(reversed_)["status"], "reversed")
        for bad in ({**PAYMENT, "method": "boleto"}, {**PAYMENT, "amount_cents": 0}, {**PAYMENT, "status": "reversed"},
                    {**PAYMENT, "reversed_by": 1}, {**PAYMENT, "operation_key": KEY}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validar_payment(bad)


class TestFineTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.requests = []

    async def call(self, operation, response):
        def handler(request):
            self.requests.append(request)
            return response

        real = httpx.AsyncClient

        def fake(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return real(*args, **kwargs)

        with patch("ProjetoLocadora.multas_client.httpx.AsyncClient", side_effect=fake):
            return await operation()

    async def test_pay_posts_once_and_validates_the_result(self):
        paid = {**FINE, "paid_cents": 300}
        result = await self.call(lambda: client.pay_fine("tok", 7, 300, "pix", KEY), httpx.Response(200, json={"payment": PAYMENT, "fine": paid, "audit_succeeded": True}))
        self.assertEqual(result, (PAYMENT, paid, True))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].url.path, "/api:rentals/multas/7/pagamentos")
        self.assertEqual(json.loads(self.requests[0].content), {"amount_cents": 300, "method": "pix", "operation_key": KEY})

    async def test_pay_input_and_gate_send_nothing(self):
        for args in ((0, 300, "pix", KEY), (7, 0, "pix", KEY), (7, 300, "boleto", KEY), (7, 300, "pix", "x"), (7, 3.0, "pix", KEY)):
            with self.subTest(args=args), self.assertRaises(client.FineError) as error:
                await self.call(lambda: client.pay_fine("tok", *args), httpx.Response(200, json={}))
            self.assertEqual(error.exception.category, "input")
        with patch.dict(os.environ, {"XANO_RENTAL_WRITES_ENABLED": "false"}), self.assertRaises(client.FineError) as error:
            await self.call(lambda: client.pay_fine("tok", 7, 300, "pix", KEY), httpx.Response(200, json={}))
        self.assertEqual(error.exception.category, "disabled")
        self.assertEqual(self.requests, [])

    async def test_business_refusals_keep_their_message(self):
        for message in ("Valor acima do saldo da multa.", "Multa não está em aberto.", "Chave já utilizada para outra operação."):
            with self.subTest(message=message), self.assertRaises(client.FineError) as error:
                await self.call(lambda: client.pay_fine("tok", 7, 300, "pix", KEY), httpx.Response(400, json={"message": message}))
            self.assertEqual((error.exception.category, error.exception.detail), ("conflict", message))

    async def test_write_errors_never_claim_success(self):
        cases = (
            (httpx.Response(200, json={"payment": {**PAYMENT, "amount_cents": 200}, "fine": FINE, "audit_succeeded": True}), "unknown"),
            (httpx.Response(200, json={"payment": PAYMENT, "fine": FINE, "audit_succeeded": True}), "unknown"),  # pago incoerente
            (httpx.Response(500, json={}), "unknown"),
            (httpx.Response(404, json={"message": "Unable to locate request."}), "unknown"),
            (httpx.Response(404, json={"message": "Multa não encontrada."}), "notfound"),
            (httpx.Response(403, json={}), "authorization"),
        )
        for response, category in cases:
            with self.subTest(status=response.status_code, category=category), self.assertRaises(client.FineError) as error:
                await self.call(lambda: client.pay_fine("tok", 7, 300, "pix", KEY), response)
            self.assertEqual(error.exception.category, category)

    async def test_detail_requires_paid_total_to_match_confirmed_payments(self):
        paid = {**FINE, "paid_cents": 300}
        reversed_ = {**PAYMENT, "id": 12, "status": "reversed", "reversed_at": PAYMENT["paid_at"] + 1, "reversed_by": 1, "reversal_reason": "Erro"}
        result = await self.call(lambda: client.get_fine("tok", 7), httpx.Response(200, json={"fine": paid, "payments": [PAYMENT, reversed_]}))
        self.assertEqual(result, (paid, [PAYMENT, reversed_]))
        with self.assertRaises(client.FineError) as error:
            await self.call(lambda: client.get_fine("tok", 7), httpx.Response(200, json={"fine": FINE, "payments": [PAYMENT]}))
        self.assertEqual(error.exception.category, "invalid")

    async def test_list_filters_are_sent_and_enforced(self):
        page = {"items": [FINE], "page": 1, "per_page": 10, "total": 1}
        result = await self.call(lambda: client.list_fines("tok", status="open", customer_id=FINE["customer_id"]), httpx.Response(200, json=page))
        self.assertEqual(result["total"], 1)
        self.assertEqual(dict(self.requests[0].url.params), {"page": "1", "per_page": "10", "status": "open", "customer_id": str(FINE["customer_id"])})
        with self.assertRaises(client.FineError) as error:
            await self.call(lambda: client.list_fines("tok", status="paid"), httpx.Response(200, json=page))
        self.assertEqual(error.exception.category, "invalid")

    async def test_summary_and_admin_operations(self):
        summary = await self.call(lambda: client.fines_summary("tok"), httpx.Response(200, json={"open_count": 2, "open_balance_cents": 900}))
        self.assertEqual(summary, {"open_count": 2, "open_balance_cents": 900})
        for bad in ({"open_count": 0, "open_balance_cents": 5}, {"open_count": -1, "open_balance_cents": 0}):
            with self.subTest(bad=bad), self.assertRaises(client.FineError):
                await self.call(lambda: client.fines_summary("tok"), httpx.Response(200, json=bad))
        for reason in ("", "   ", "x" * 501):
            with self.subTest(reason=len(reason)), self.assertRaises(client.FineError) as error:
                await self.call(lambda: client.waive_fine("tok", 7, reason, KEY), httpx.Response(200, json={}))
            self.assertEqual(error.exception.category, "input")
        waived = {**FINE, "status": "waived", "waived_cents": 900, "waived_at": FINE["created_at"] + HOUR, "waived_by": 1, "waive_reason": "Cortesia"}
        result = await self.call(lambda: client.waive_fine("tok", 7, " Cortesia ", KEY), httpx.Response(200, json={"fine": waived, "audit_succeeded": True}))
        self.assertEqual(result, (waived, True))
        self.assertEqual(json.loads(self.requests[-1].content)["reason"], "Cortesia")


class TestFineState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(MultasState)
        self.session = await self.root.get_state(State)
        self.session._user_id, self.session._user_role, self.session._xano_auth_token = "9", "member", "private-token"
        self.env = patch.dict(os.environ, {"XANO_RENTAL_API_URL": "https://api.test/api:rentals", "XANO_RENTAL_WRITES_ENABLED": "true"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.me = patch("ProjetoLocadora.multas_state.get_me_xano", new=AsyncMock(return_value=ME)).start()
        self.get = patch("ProjetoLocadora.multas_state.get_fine", new=AsyncMock(return_value=(FINE, []))).start()
        self.pay = patch("ProjetoLocadora.multas_state.pay_fine", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)

    async def open(self, raw="7"):
        with patch.object(MultasState, "_route_fine_id", return_value=raw):
            await consume(self.state.load_detail())

    async def test_detail_suggests_the_balance_and_shows_policy(self):
        await self.open()
        self.assertEqual(self.state.amount_text, "9,00")
        self.assertEqual(self.state.fine_view["balance"], "R$ 9,00")
        self.assertIn("3 dias × R$ 3,00 por dia", self.state.fine_view["policy"])
        self.assertTrue(self.state.can_pay)

    async def test_invalid_number_does_not_reach_the_service(self):
        await self.open("abc")
        self.assertEqual(self.state.detail_state, "invalid")
        self.get.assert_not_awaited()

    async def test_amount_above_balance_is_blocked_before_sending(self):
        await self.open()
        self.state.capture_amount("10,00")
        self.assertIn("saldo", self.state.amount_issue)
        self.assertFalse(self.state.can_pay)
        self.state.ask_pay()
        self.assertFalse(self.state.pay_confirming)

    async def test_partial_payment_keys_once_and_updates_balance(self):
        await self.open()
        self.state.capture_amount("3,00")
        self.state.capture_method("Pix")
        self.pay.return_value = (PAYMENT, {**FINE, "paid_cents": 300}, True)
        self.state.ask_pay()
        await consume(self.state.submit_pay())
        await consume(self.state.submit_pay())  # segundo clique: nada pendente nem confirmado
        self.assertEqual(self.pay.await_count, 1)
        args = self.pay.await_args.args
        self.assertEqual(args[1:4], (7, 300, "pix"))
        self.assertIn("Saldo restante: R$ 6,00.", self.state.notice)
        self.assertEqual(self.state.fine_view["status"], "Parcial")
        self.assertEqual(self.state.amount_text, "6,00")

    async def test_unknown_result_keeps_the_key_for_repeat(self):
        await self.open()
        self.pay.side_effect = client.FineError("unknown")
        self.state.ask_pay()
        await consume(self.state.submit_pay())
        self.assertTrue(self.state.pay_pending)
        key = self.pay.await_args.args[4]
        self.pay.side_effect = None
        self.pay.return_value = ({**PAYMENT, "amount_cents": 900}, {**FINE, "paid_cents": 900, "status": "paid"}, True)
        await consume(self.state.repeat_pay())
        self.assertEqual(self.pay.await_args.args[4], key)
        self.assertFalse(self.state.pay_pending)
        self.assertIn("Multa quitada.", self.state.notice)

    async def test_conflict_shows_backend_message_and_reloads(self):
        await self.open()
        self.pay.side_effect = client.FineError("conflict", detail="Valor acima do saldo da multa.")
        self.get.return_value = ({**FINE, "paid_cents": 600}, [{**PAYMENT, "amount_cents": 600}])
        self.state.ask_pay()
        await consume(self.state.submit_pay())
        self.assertEqual(self.state.message, "Valor acima do saldo da multa.")
        self.assertEqual(self.state.amount_text, "3,00")
        self.assertFalse(self.state.pay_pending)

    async def test_logout_discards_late_payment_response(self):
        await self.open()

        async def late(*args):
            await self.session.logout()
            return PAYMENT, {**FINE, "paid_cents": 300}, True

        self.pay.side_effect = late
        self.state.ask_pay()
        await consume(self.state.submit_pay())
        self.assertFalse(self.state.has_fine)
        self.assertEqual(self.state.notice, "")

    async def test_member_cannot_run_admin_adjustments(self):
        await self.open()
        self.state.ask_waive()
        self.state.capture_admin_reason("Cortesia")
        with patch("ProjetoLocadora.multas_state.waive_fine", new=AsyncMock()) as waive:
            await consume(self.state.confirm_admin())
            waive.assert_not_awaited()
        self.assertEqual(self.state.message, client.MESSAGES["authorization"])


class TestCustomerHistoryState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(ClienteHistoricoState)
        self.session = await self.root.get_state(State)
        self.session._user_id, self.session._user_role, self.session._xano_auth_token = "9", "member", "private-token"
        patch("ProjetoLocadora.multas_state.get_me_xano", new=AsyncMock(return_value=ME)).start()
        self.fines = patch("ProjetoLocadora.multas_state.list_fines", new=AsyncMock(return_value={"items": [{**FINE, "paid_cents": 300}], "page": 1, "per_page": 50, "total": 1})).start()
        self.rentals = patch("ProjetoLocadora.multas_state.list_rentals", new=AsyncMock(return_value={"items": [RETURNED], "page": 1, "per_page": 10, "total": 1})).start()
        self.addCleanup(patch.stopall)

    async def test_opening_loads_rentals_and_open_balance_for_that_customer(self):
        with patch.object(ClienteHistoricoState, "_route_customer_id", return_value="1"):
            await consume(self.state.open_customer())
        self.assertEqual(self.fines.await_args.kwargs, {"status": "open", "customer_id": 1})
        self.assertEqual(self.rentals.await_args.kwargs, {"customer_id": 1})
        self.assertEqual(self.state.balance_text, "R$ 6,00")
        self.assertTrue(self.state.has_open_fine)
        self.assertEqual(self.state.state, "ready")
        self.assertEqual(self.state.rows[0]["status"], "Devolvida")


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def stack_of(text: str):
    return next(calls(body(text), "stack"))[1]


class TestFineXanoContract(unittest.TestCase):
    """Estrutura de segurança dos endpoints; não comprova o runtime do Xano."""

    WRITES = {
        "api/locacoes/multas_id_pagamentos_POST.xs": ("member", [("user",), ("fine",)]),
        "api/locacoes/multas_id_abono_POST.xs": ("admin", [("user",), ("fine",)]),
        "api/locacoes/pagamentos_id_estorno_POST.xs": ("admin", [("user",), ("fine",), ("payment",)]),
    }

    def test_writes_authorize_gate_and_lock_in_order(self):
        for path, (role, locks) in self.WRITES.items():
            with self.subTest(path=path):
                stack = stack_of(source(path))
                self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
                self.assertIn(f'"{role}"', list(flatten(stack[2][1])))
                self.assertTrue(predicate_exists(stack, '$env.XANO_RENTAL_WRITES_ENABLED == "true"'))
                transactions = list(calls(stack, "db.transaction"))
                self.assertEqual(len(transactions), 1)
                gets = list(calls(transactions[0][1], "db.get"))
                self.assertEqual([args for args, _ in gets], locks)
                for args, operation in gets:
                    self.assertEqual(unique_assignment(operation, "lock"), "true", args)
                # Histórico financeiro: nunca apagar; escritas só dentro da transação.
                self.assertEqual(list(calls(stack, "db.del")), [])
                for statement in ("db.add", "db.edit"):
                    self.assertEqual(len(list(calls(stack, statement))), len(list(calls(transactions[0][1], statement))))
                self.assertEqual(list(calls(stack, "throw")), [])

    def test_payment_never_exceeds_balance(self):
        stack = stack_of(source("api/locacoes/multas_id_pagamentos_POST.xs"))
        self.assertTrue(predicate_exists(stack, "$input.amount_cents <= $balance"))
        self.assertTrue(predicate_exists(stack, '$fine_row.status == "open"'))
        self.assertEqual([args for args, _ in calls(stack, "db.add")], [("payment",)])
        flat = list(flatten(stack))
        self.assertNotIn("$input.registered_by", flat)
        self.assertNotIn("$input.paid_at", flat)

    def test_rental_creation_refuses_open_fine(self):
        stack = stack_of(source("api/locacoes/locacoes_POST.xs"))
        self.assertTrue(predicate_exists(stack, "$open_fine == false"))
        flat = list(flatten(stack))
        # Depois do bloqueio do cliente, antes do exemplar: ordem de bloqueios inalterada.
        self.assertLess(flat.index("$customer.bloqueio_manual_ativo"), flat.index("$open_fine"))
        self.assertLess(flat.index("$open_fine"), flat.index("exemplar"))

    def test_policy_defaults_and_fail_closed(self):
        text = source("function/locacoes/fine_policy.xs")
        for default in ("300", "120", "9000"):
            self.assertIn(f"? {default} :", text)
        self.assertIn("$daily > 0 && $grace >= 0 && $cap >= $daily", text)
        calc = source("function/locacoes/calculate_late_fine.xs")
        self.assertIn("$late_ms > $policy.grace_minutes * 60000", calc)
        self.assertIn("(($late_ms / 86400000)|ceil)|to_int", calc)

    def test_reads_require_member_before_data(self):
        for path in ("multas_GET.xs", "multas_id_GET.xs", "multas_resumo_GET.xs", "multas_politica_GET.xs", "pagamentos_GET.xs"):
            with self.subTest(path=path):
                stack = stack_of(source("api/locacoes/" + path))
                self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
                for statement in ("db.add", "db.edit", "db.del", "db.transaction"):
                    self.assertEqual(list(calls(stack, statement)), [], statement)
                self.assertNotIn("cpf", source("api/locacoes/" + path))


if __name__ == "__main__":
    unittest.main()
