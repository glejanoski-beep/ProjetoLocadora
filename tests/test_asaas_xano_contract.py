"""Contratos estruturais da integração Asaas mantida como exportação Xano."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class TestAsaasWebhookContract(unittest.TestCase):
    def test_webhook_authenticates_before_persisting_and_never_logs_raw_payload(self):
        webhook = source("xano/xano/api/locacoes/asaas_webhook_POST.xs")
        self.assertLess(webhook.index("$webhook_token == $env.ASAAS_WEBHOOK_TOKEN"), webhook.index("db.add asaas_checkout_event"))
        self.assertIn("$event_id", webhook)
        self.assertIn('event_name == "PAYMENT_REFUNDED"', webhook)
        self.assertIn('data = {status: "failed"}', webhook)
        self.assertIn("$existing_event.status == \"failed\"", webhook)
        self.assertNotIn("$input.payload}", webhook)
        self.assertNotIn("payload: $input.payload", webhook)

    def test_event_and_checkout_keys_are_unique_for_idempotency(self):
        events = source("xano/xano/table/asaas_checkout_event.xs")
        checkout = source("xano/xano/table/asaas_checkout.xs")
        payments = source("xano/xano/table/payment.xs")
        self.assertIn('{type: "btree|unique", field: [{name: "event_id"}]}', events)
        self.assertIn('{type: "btree|unique", field: [{name: "external_reference"}]}', checkout)
        self.assertIn('{type: "btree|unique", field: [{name: "provider_checkout_id"}]}', payments)

    def test_external_refund_preserves_payment_value_and_reopens_fine(self):
        refund = source("xano/xano/function/asaas/reverse_paid_checkout.xs")
        self.assertIn('status: "reversed"', refund)
        self.assertIn('reversal_reason: "Estorno confirmado pelo Asaas"', refund)
        self.assertIn("paid_cents: $fine.paid_cents - $payment.amount_cents", refund)
        self.assertIn('status: "open"', refund)
        self.assertNotIn("amount_cents:", refund)

    def test_checkout_creation_and_reads_remain_authorized_and_checkout_only(self):
        start = source("xano/xano/api/locacoes/multas_id_cobranca_cartao_POST.xs")
        read = source("xano/xano/api/locacoes/multas_id_cobranca_cartao_GET.xs")
        create = source("xano/xano/function/asaas/create_checkout.xs")
        self.assertIn('auth = "user"', start)
        self.assertIn('required_role: "member"', start)
        self.assertIn('required_role: "member"', read)
        self.assertIn('"CREDIT_CARD"', create)
        self.assertIn("external_reference: $external_reference", create)
        self.assertIn("$input.operation_key == null", read)

    def test_checkout_requires_open_fine_integral_balance_and_sandbox_configuration(self):
        create = source("xano/xano/function/asaas/create_checkout.xs")
        self.assertIn('status == "open"', create)
        self.assertIn("$balance > 0", create)
        self.assertIn("amount_cents: $balance", create)
        self.assertIn("ASAAS_API_KEY", create)
        self.assertIn("ASAAS_CHECKOUT_ENABLED", create)
        self.assertNotIn("db.add payment", create)

    def test_ambiguous_create_reserves_unknown_before_network_and_does_not_repeat_post(self):
        create = source("xano/xano/function/asaas/create_checkout.xs")
        table = source("xano/xano/table/asaas_checkout.xs")
        self.assertLess(create.index('status: "unknown"'), create.index("api.request"))
        self.assertLess(create.index('if ($existing == null)'), create.index("api.request"))
        self.assertIn('values = ["unknown", "pending"', table)
        self.assertIn("text? checkout_id", table)

    def test_manual_reconciliation_is_admin_audited_and_never_confirms_payment(self):
        endpoint = source("xano/xano/api/locacoes/asaas_checkout_reconcile_POST.xs")
        candidates = source("xano/xano/api/locacoes/asaas_checkout_reconcile_candidates_GET.xs")
        function = source("xano/xano/function/asaas/reconcile_unknown_checkout.xs")
        self.assertIn('required_role: "admin"', endpoint)
        self.assertIn('required_role: "admin"', candidates)
        self.assertIn('status == "unknown"', candidates)
        self.assertIn("verified_amount_cents", endpoint)
        self.assertIn('$checkout.external_reference == $input.external_reference', function)
        self.assertIn("db.add event_log", function)
        self.assertIn('status: "pending"', function)
        self.assertNotIn('status: "confirmed"', function)

    def test_paid_confirmation_is_transactional_idempotent_and_checks_current_balance(self):
        confirm = source("xano/xano/function/asaas/confirm_paid_checkout.xs")
        self.assertIn("db.transaction", confirm)
        self.assertIn("$db.payment.provider_checkout_id == $input.checkout_id", confirm)
        self.assertIn("$balance == $checkout.amount_cents", confirm)
        self.assertIn('method: "credit_card"', confirm)
        self.assertIn('origin: "asaas_checkout"', confirm)
        self.assertIn("paid_cents: $fine.paid_cents + $checkout.amount_cents", confirm)

    def test_state_machine_ignores_late_cancel_and_reprocesses_failed_event(self):
        webhook = source("xano/xano/api/locacoes/asaas_webhook_POST.xs")
        self.assertIn('$existing_event.status == "failed"', webhook)
        self.assertIn('$existing_event.status == "received"', webhook)
        self.assertIn('$checkout.status == "pending"', webhook)
        self.assertIn('status: ($event_name == "CHECKOUT_CANCELED") ? "cancelled" : "expired"', webhook)


if __name__ == "__main__":
    unittest.main()
