// Webhook público do Asaas. O segredo é lido do header HTTP asaas-access-token.
// O payload bruto nunca é devolvido nem gravado em auditoria.
query "asaas/webhook" verb=POST {
  api_group = "Locações"
  input {
    json payload
  }
  stack {
    var $webhook_token { value = $env.httpHeaders["asaas-access-token"] }
    precondition ((($env.ASAAS_WEBHOOK_TOKEN ?? "")|trim) != "") {
      error_type = "accessdenied"
      error = "Webhook não configurado."
    }
    precondition ($webhook_token != null && $webhook_token == $env.ASAAS_WEBHOOK_TOKEN) {
      error_type = "accessdenied"
      error = "Webhook não autorizado."
    }
    var $event_id { value = $input.payload.id }
    var $event_name { value = $input.payload.event }
    var $checkout_id { value = $input.payload.checkout.id }
    var $payment_id { value = $input.payload.payment.id }
    var $external_reference { value = $input.payload.payment.externalReference }
    precondition ($event_id != null && $event_name != null && ($checkout_id != null || ($event_name == "PAYMENT_REFUNDED" && $payment_id != null))) {
      error_type = "inputerror"
      error = "Evento do Asaas inválido."
    }
    db.query asaas_checkout_event {
      where = $db.asaas_checkout_event.event_id == $event_id
      return = {type: "single"}
    } as $existing_event
    var $event_row { value = $existing_event }
    var $should_process { value = ($existing_event == null || $existing_event.status == "failed" || $existing_event.status == "received") }
    conditional {
      if ($existing_event == null) {
        db.add asaas_checkout_event {
          data = {event_id: $event_id, checkout_id: $checkout_id, provider_payment_id: $payment_id, event: $event_name, received_at: now, status: "received"}
        } as $event_row
      }
      elseif ($should_process) {
        db.edit asaas_checkout_event {
          field_name = "id"
          field_value = $existing_event.id
          data = {status: "received"}
        } as $event_row
      }
    }
    conditional {
      if ($should_process) {
        var $processing_failed { value = false }
        try_catch {
          try {
            conditional {
              if ($event_name == "CHECKOUT_PAID") {
                function.run "Asaas/confirm_paid_checkout" {
                  input = {checkout_id: $checkout_id, provider_payment_id: $payment_id, event_id: $event_id}
                } as $confirmed
                db.edit asaas_checkout_event {
                  field_name = "id"
                  field_value = $event_row.id
                  data = {status: "processed", processed_at: now}
                } as $event_processed
              }
              elseif ($event_name == "PAYMENT_REFUNDED") {
                function.run "Asaas/reverse_paid_checkout" {
                  input = {provider_payment_id: $payment_id, external_reference: $external_reference, event_id: $event_id}
                } as $reversed
                db.edit asaas_checkout_event {
                  field_name = "id"
                  field_value = $event_row.id
                  data = {checkout_id: $reversed.checkout.checkout_id, status: "processed", processed_at: now}
                } as $event_processed
              }
              elseif ($event_name == "CHECKOUT_CANCELED" || $event_name == "CHECKOUT_EXPIRED") {
                db.get asaas_checkout {
                  field_name = "checkout_id"
                  field_value = $checkout_id
                  lock = true
                } as $checkout
                conditional {
                  if ($checkout != null && $checkout.status == "pending") {
                    db.edit asaas_checkout {
                      field_name = "id"
                      field_value = $checkout.id
                      data = {status: ($event_name == "CHECKOUT_CANCELED") ? "cancelled" : "expired", last_event_id: $event_id}
                    } as $checkout_updated
                  }
                }
                db.edit asaas_checkout_event {
                  field_name = "id"
                  field_value = $event_row.id
                  data = {status: "processed", processed_at: now}
                } as $event_processed
              }
              else {
                db.edit asaas_checkout_event {
                  field_name = "id"
                  field_value = $event_row.id
                  data = {status: "ignored", processed_at: now}
                } as $event_ignored
              }
            }
          }
          catch {
            var.update $processing_failed { value = true }
          }
        }
        conditional {
          if ($processing_failed) {
            db.edit asaas_checkout_event {
              field_name = "id"
              field_value = $event_row.id
              data = {status: "failed"}
            } as $event_failed
            precondition (false) {
              error_type = "standard"
              error = "Evento não processado. O Asaas pode tentar novamente."
            }
          }
        }
      }
    }
  }
  response = {received: true, duplicate: ($existing_event != null && !$should_process)}
  guid = "AtW9SpIpd2IMMyZssN_GI5HIeoQ"
}
