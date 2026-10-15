// Controls the current manual block without changing registration status.
query "clientes/{id}/bloqueio-manual" verb=PATCH {
  api_group = "Clientes"
  auth = "user"

  input {
    int id
    bool bloqueado
    text motivo? filters=trim|max:500
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.get customer {
      field_name = "id"
      field_value = $input.id
    } as $existing_customer
    precondition ($existing_customer != null) {
      error_type = "notfound"
      error = "Cliente não encontrado."
    }
    precondition (!$input.bloqueado || ($input.motivo != null && $input.motivo != "" && ($input.motivo|strlen) <= 500)) {
      error_type = "inputerror"
      error = "Informe o motivo do bloqueio manual."
    }

    db.edit customer {
      field_name = "id"
      field_value = $input.id
      data = {
        updated_at: "now"
        bloqueio_manual_ativo: $input.bloqueado
        motivo_bloqueio_manual: ($input.bloqueado ? $input.motivo : null)
        bloqueado_em: ($input.bloqueado ? "now" : null)
        bloqueado_por: ($input.bloqueado ? $auth.id : null)
      }
      output = ["id", "created_at", "updated_at", "nome", "cpf", "email", "telefone", "status", "bloqueio_manual_ativo", "motivo_bloqueio_manual", "bloqueado_em", "bloqueado_por"]
    } as $customer

    var $audit_action { value = ($input.bloqueado ? "block_customer" : "unblock_customer") }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: $audit_action, result: "success", resource_type: "customer", resource_id: $customer.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
  }

  response = {customer: $customer, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "yRDawazMF9GgQb9bsPNuQ5IwqOs"
}
