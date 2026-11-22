// Reverte o pagamento local após PAYMENT_REFUNDED autenticado.
// externalReference associa o evento de pagamento ao Checkout sem payload bruto.
function "Asaas/reverse_paid_checkout" {
  input {
    text provider_payment_id filters=trim|max:100
    text external_reference filters=trim|max:200
    text event_id filters=trim|max:150
  }
  stack {
    db.transaction { stack {
      db.get asaas_checkout {
        field_name = "external_reference"
        field_value = $input.external_reference
        lock = true
      } as $checkout
      precondition ($checkout != null) {
        error_type = "notfound"
        error = "Checkout associado ao estorno não encontrado."
      }
      db.query payment {
        where = $db.payment.provider_checkout_id == $checkout.checkout_id
        return = {type: "single"}
      } as $payment_match
      precondition ($payment_match != null && $payment_match.origin == "asaas_checkout" && ($payment_match.provider_payment_id == null || $payment_match.provider_payment_id == $input.provider_payment_id)) {
        error_type = "inputerror"
        error = "Pagamento externo não corresponde ao Checkout."
      }
      db.get payment {
        field_name = "id"
        field_value = $payment_match.id
        lock = true
      } as $payment
      conditional {
        if ($checkout.status == "reversed" && $payment.status == "reversed") {
          var.update $payment { value = $payment }
        }
        else {
          precondition ($checkout.status == "confirmed" && $payment.status == "confirmed") {
            error_type = "inputerror"
            error = "Somente Checkout confirmado pode ser estornado."
          }
          db.get fine {
            field_name = "id"
            field_value = $checkout.fine_id
            lock = true
            output = ["id", "paid_cents", "status"]
          } as $fine
          precondition ($fine != null && $fine.status != "waived" && $fine.paid_cents >= $payment.amount_cents) {
            error_type = "inputerror"
            error = "Saldo financeiro incompatível com o estorno externo."
          }
          db.edit payment {
            field_name = "id"
            field_value = $payment.id
            data = {status: "reversed", provider_payment_id: $input.provider_payment_id, reversed_at: now, reversed_by: null, reversal_reason: "Estorno confirmado pelo Asaas", reversal_operation_key: null}
          } as $payment_reversed
          db.edit fine {
            field_name = "id"
            field_value = $fine.id
            data = {paid_cents: $fine.paid_cents - $payment.amount_cents, status: "open"}
          } as $fine_updated
          db.edit asaas_checkout {
            field_name = "id"
            field_value = $checkout.id
            data = {status: "reversed", last_event_id: $input.event_id, reversed_at: now}
          } as $checkout_reversed
          var.update $payment { value = $payment_reversed }
        }
      }
    } }
    db.get payment {
      field_name = "id"
      field_value = $payment.id
    } as $payment_result
    db.get asaas_checkout {
      field_name = "id"
      field_value = $checkout.id
    } as $checkout_result
  }
  response = {checkout: $checkout_result, payment: $payment_result}
  guid = "9wX2aK4mP7rT1vB6cD3fH8jL5q"
}
