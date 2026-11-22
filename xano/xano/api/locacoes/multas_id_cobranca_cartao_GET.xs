// Consulta idempotente de uma tentativa de Checkout iniciada pelo usuário.
query "multas/{id}/cobranca-cartao" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    uuid operation_key?
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    var $checkout { value = null }
    conditional {
      if ($input.operation_key == null) {
        db.query asaas_checkout {
          where = $db.asaas_checkout.fine_id == $input.id && $db.asaas_checkout.requested_by == $auth.id
          sort = {asaas_checkout.id: "desc"}
          return = {type: "single"}
        } as $latest_checkout
        var.update $checkout { value = $latest_checkout }
      }
      else {
        db.query asaas_checkout {
          where = $db.asaas_checkout.fine_id == $input.id && $db.asaas_checkout.requested_by == $auth.id && $db.asaas_checkout.operation_key == $input.operation_key
          return = {type: "single"}
        } as $keyed_checkout
        var.update $checkout { value = $keyed_checkout }
      }
    }
  }
  response = {checkout: $checkout}
  guid = "Ir5b_Tt2IzhZ4-muqxlxRdeFE3k"
}
