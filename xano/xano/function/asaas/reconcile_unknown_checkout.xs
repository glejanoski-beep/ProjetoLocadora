// Associa manualmente um Checkout localizado no painel Asaas a uma reserva ambígua.
// Esta função nunca confirma pagamento; isso continua restrito ao webhook autenticado.
function "Asaas/reconcile_unknown_checkout" {
  input {
    int checkout_attempt_id
    int reconciled_by
    text checkout_id filters=trim|max:100
    text external_reference filters=trim|max:200
    int verified_amount_cents
    text reason filters=trim|min:10|max:500
  }

  stack {
    db.get asaas_checkout {
      field_name = "id"
      field_value = $input.checkout_attempt_id
      lock = true
    } as $checkout
    precondition ($checkout != null && $checkout.status == "unknown" && $checkout.checkout_id == null) {
      error_type = "inputerror"
      error = "Tentativa não está aguardando reconciliação."
    }
    precondition ($checkout.external_reference == $input.external_reference) {
      error_type = "inputerror"
      error = "Referência externa não corresponde à tentativa."
    }
    precondition ($checkout.amount_cents == $input.verified_amount_cents) {
      error_type = "inputerror"
      error = "Valor verificado não corresponde à tentativa."
    }
    db.query asaas_checkout {
      where = $db.asaas_checkout.checkout_id == $input.checkout_id
      return = {type: "single"}
    } as $checkout_id_match
    precondition ($checkout_id_match == null && $input.checkout_id != "") {
      error_type = "inputerror"
      error = "Checkout já vinculado ou identificador inválido."
    }
    db.edit asaas_checkout {
      field_name = "id"
      field_value = $checkout.id
      data = {
        checkout_id: $input.checkout_id
        checkout_url: "https://asaas.com/checkoutSession/show?id=" ~ $input.checkout_id
        status: "pending"
        updated_at: now
      }
    } as $reconciled
    db.add event_log {
      data = {
        created_at: now
        user_id: $input.reconciled_by
        action: "asaas_checkout_manual_reconciliation"
        metadata: {
          result: "success"
          resource_type: "asaas_checkout"
          resource_id: $checkout.id
          checkout_id: $input.checkout_id
          external_reference: $checkout.external_reference
          reason: $input.reason
          payment_confirmation: "webhook_required"
        }
      }
    } as $event_log
  }

  response = {checkout: $reconciled}
  tags = ["asaas", "payments"]
  guid = "A5qJ2nM8rT4wX9cD1eF6gH3kL7"
}
