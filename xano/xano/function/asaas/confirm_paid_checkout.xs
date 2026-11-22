// Confirma um Checkout pago dentro de uma transação local.
// A confirmação é idempotente pelo provider_checkout_id.
function "Asaas/confirm_paid_checkout" {
  input {
    text checkout_id filters=trim|max:100
    text provider_payment_id? filters=trim|max:100
    text event_id filters=trim|max:150
  }
  stack {
    db.transaction { stack {
      db.get asaas_checkout {
        field_name = "checkout_id"
        field_value = $input.checkout_id
        lock = true
      } as $checkout
      precondition ($checkout != null) {
        error_type = "notfound"
        error = "Tentativa de Checkout não encontrada."
      }
      db.query payment {
        where = $db.payment.provider_checkout_id == $input.checkout_id
        return = {type: "single"}
      } as $existing_payment
      conditional {
        if ($existing_payment == null) {
          db.get fine {
            field_name = "id"
            field_value = $checkout.fine_id
            lock = true
            output = ["id", "customer_id", "amount_cents", "paid_cents", "waived_cents", "status"]
          } as $fine
          precondition ($fine != null) {
            error_type = "notfound"
            error = "Multa não encontrada."
          }
          var $balance { value = $fine.amount_cents - $fine.paid_cents - $fine.waived_cents }
          precondition ($fine.status == "open" && $balance == $checkout.amount_cents) {
            error_type = "inputerror"
            error = "Saldo da multa mudou; confirmação automática recusada."
          }
          db.add payment {
            data = {
              fine_id: $fine.id
              customer_id: $fine.customer_id
              amount_cents: $checkout.amount_cents
              method: "credit_card"
              origin: "asaas_checkout"
              provider_checkout_id: $checkout.checkout_id
              provider_payment_id: $input.provider_payment_id
              paid_at: now
              registered_by: $checkout.requested_by
              operation_key: $checkout.operation_key
              status: "confirmed"
            }
          } as $payment
          db.edit fine {
            field_name = "id"
            field_value = $fine.id
            data = {paid_cents: $fine.paid_cents + $checkout.amount_cents, status: "paid"}
          } as $fine_updated
        }
        else {
          var.update $payment { value = $existing_payment }
        }
      }
      db.edit asaas_checkout {
        field_name = "id"
        field_value = $checkout.id
        data = {status: "confirmed", last_event_id: $input.event_id, external_payment_id: $input.provider_payment_id, confirmed_at: now}
      } as $checkout_updated
    } }
    db.get asaas_checkout {
      field_name = "checkout_id"
      field_value = $input.checkout_id
    } as $result
  }
  response = {checkout: $result, payment: $payment}
  guid = "3YodCv88ZJflnmcv4lOBPvqSIaY"
}
