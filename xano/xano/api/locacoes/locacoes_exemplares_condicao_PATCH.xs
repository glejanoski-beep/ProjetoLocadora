query "locacoes/exemplares/{id}/condicao" verb=PATCH {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    enum operational_condition { values = ["unverified", "available", "unavailable"] }
    text reason filters=trim|max:500
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($env.XANO_RENTAL_WRITES_ENABLED == "true") {
      error_type = "accessdenied"
      error = "Registro de locação ainda não habilitado."
    }
    precondition ($input.reason != "" && $input.id > 0) {
      error_type = "inputerror"
      error = "Informe exemplar e motivo da confirmação."
    }
    db.transaction { stack {
      db.get user {
        field_name = "id"
        field_value = $auth.id
        lock = true
        output = ["id", "role", "is_active"]
      } as $actor
      precondition ($actor != null && $actor.is_active != false && $actor.role == "admin") {
        error_type = "accessdenied"
        error = "Conta sem autorização atual."
      }
      db.get exemplar {
        field_name = "id"
        field_value = $input.id
        lock = true
        output = ["id"]
      } as $exemplar
      precondition ($exemplar != null) {
        error_type = "notfound"
        error = "Exemplar não encontrado."
      }
      db.edit exemplar {
        field_name = "id"
        field_value = $exemplar.id
        data = {operational_condition: $input.operational_condition, condition_confirmed_at: now, condition_confirmed_by: $auth.id, condition_reason: $input.reason}
        output = ["id", "operational_condition", "condition_confirmed_at", "condition_confirmed_by"]
      } as $confirmed
    } }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: "confirm_exemplar_condition", result: "success", resource_type: "exemplar", resource_id: $confirmed.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
  }
  response = {exemplar: $confirmed, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "lyn1YVo93KWn_EMpqXPWCjv1XSU"
}
