// Cria um Checkout Asaas avulso para o saldo integral de uma multa aberta.
function "Asaas/create_checkout" {
  input {
    int fine_id
    int requested_by
    uuid operation_key
  }

  stack {
    db.query asaas_checkout {
      where = $db.asaas_checkout.requested_by == $input.requested_by && $db.asaas_checkout.operation_key == $input.operation_key
      return = {type: "single"}
    } as $existing
    precondition ($existing == null || $existing.fine_id == $input.fine_id) {
      error_type = "inputerror"
      error = "Chave já utilizada para outra operação."
    }
    var $checkout { value = $existing }
    conditional {
      if ($existing == null) {
        precondition (($env.ASAAS_CHECKOUT_ENABLED ?? "false") == "true") {
          error_type = "accessdenied"
          error = "Cobrança via cartão ainda não está habilitada."
        }
        precondition ((($env.ASAAS_API_KEY ?? "")|trim) != "") {
          error_type = "standard"
          error = "Integração de cobrança não configurada."
        }
        precondition ((($env.ASAAS_API_BASE_URL ?? "")|trim) != "") {
          error_type = "standard"
          error = "URL da integração de cobrança não configurada."
        }
        db.get fine {
          field_name = "id"
          field_value = $input.fine_id
          lock = true
          output = ["id", "customer_id", "amount_cents", "paid_cents", "waived_cents", "status", "film_title", "exemplar_identifier"]
        } as $fine
        precondition ($fine != null) {
          error_type = "notfound"
          error = "Multa não encontrada."
        }
        precondition ($fine.status == "open") {
          error_type = "inputerror"
          error = "Multa não está em aberto."
        }
        var $balance { value = $fine.amount_cents - $fine.paid_cents - $fine.waived_cents }
        precondition ($balance > 0) {
          error_type = "inputerror"
          error = "Multa não possui saldo para cobrança."
        }
        function.run "Asaas/find_or_create_customer" {
          input = {customer_id: $fine.customer_id}
        } as $asaas_customer
        var $callback_base { value = (($env.ASAAS_CALLBACK_BASE_URL ?? $env.FRONTEND_BASE_URL) ?? "")|trim }
        precondition ($callback_base != "") {
          error_type = "standard"
          error = "URL de retorno da cobrança não configurada."
        }
        var $external_reference { value = "locadora-fine-" ~ ($fine.id|to_text) ~ "-" ~ ($input.operation_key|to_text) }
        var $checkout_payload {
          value = {
            customer: $asaas_customer.asaas_customer_id
            billingTypes: ["CREDIT_CARD"]
            chargeTypes: ["DETACHED"]
            minutesToExpire: 60
            externalReference: $external_reference
            callback: {
              successUrl: $callback_base ~ "/multas/" ~ ($fine.id|to_text) ~ "?asaas=success"
              cancelUrl: $callback_base ~ "/multas/" ~ ($fine.id|to_text) ~ "?asaas=cancelled"
              expiredUrl: $callback_base ~ "/multas/" ~ ($fine.id|to_text) ~ "?asaas=expired"
            }
            items: [{
              name: "Multa da locação #" ~ ($fine.id|to_text)
              description: "" ~ $fine.film_title ~ " / " ~ $fine.exemplar_identifier
              quantity: 1
              value: $balance / 100
            }]
          }
        }
        // A reserva precede a chamada externa: timeout não pode autorizar novo POST.
        db.add asaas_checkout {
          data = {
            fine_id: $fine.id
            customer_id: $fine.customer_id
            requested_by: $input.requested_by
            operation_key: $input.operation_key
            external_reference: $external_reference
            checkout_id: null
            checkout_url: null
            amount_cents: $balance
            status: "unknown"
          }
        } as $reserved
        var.update $checkout { value = $reserved }
        api.request {
          url = ($env.ASAAS_API_BASE_URL|trim) ~ "/checkouts"
          method = "POST"
          params = $checkout_payload
          headers = ["User-Agent: ProjetoLocadora/1.0", "Content-Type: application/json", "accept: application/json", "access_token: " ~ $env.ASAAS_API_KEY]
          timeout = 30
        } as $asaas_response
        precondition ($asaas_response.response.status == 200 || $asaas_response.response.status == 201) {
          error_type = "standard"
          error = "Não foi possível criar a cobrança no Asaas."
        }
        precondition ($asaas_response.response.result.id != null) {
          error_type = "standard"
          error = "O Asaas não retornou o identificador da cobrança."
        }
        db.edit asaas_checkout {
          field_name = "id"
          field_value = $reserved.id
          data = {
            checkout_id: $asaas_response.response.result.id
            checkout_url: "https://asaas.com/checkoutSession/show?id=" ~ $asaas_response.response.result.id
            status: "pending"
            updated_at: now
          }
        } as $created
        var.update $checkout { value = $created }
      }
    }
  }

  response = {checkout: $checkout}
  tags = ["asaas", "payments"]
  guid = "E9gP2tU6vR3wX8zB1cD5fO4qH7"
}
