// Inicia uma cobrança de cartão via Checkout Asaas para o saldo integral da multa.
query "multas/{id}/cobranca-cartao" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    uuid operation_key
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    precondition ($env.XANO_RENTAL_WRITES_ENABLED == "true") {
      error_type = "accessdenied"
      error = "Registro de locação ainda não habilitado."
    }
    function.run "Asaas/create_checkout" {
      input = {fine_id: $input.id, requested_by: $auth.id, operation_key: $input.operation_key}
    } as $checkout_result
    function.run "Quick Start/log_event" {
      input = {
        user_id: $auth.id
        action: "create_card_checkout"
        result: "success"
        resource_type: "asaas_checkout"
        resource_id: $checkout_result.checkout.id
      }
    } as $event_log
  }
  response = {checkout: $checkout_result.checkout}
  tags = []
  guid = "F1hQ3uV7wS4xY9aC2dE6gP5rI8"
}
