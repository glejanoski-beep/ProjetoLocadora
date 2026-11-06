// Reativação de exemplar baixado (admin, com motivo). A cópia volta como
// "não conferida" (unverified): só é alugada após nova conferência available.
query "exemplares/{id}/reativacao" verb=POST {
  api_group = "Exemplares"
  auth = "user"
  input {
    int id
    text reason filters=trim
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.id > 0) {
      error_type = "inputerror"
      error = "Exemplar inválido."
    }
    precondition ($input.reason != null && ($input.reason|strlen) > 0 && ($input.reason|strlen) <= 500) {
      error_type = "inputerror"
      error = "Informe o motivo da reativação (até 500 caracteres)."
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
        output = ["id", "retired_at"]
      } as $current
      precondition ($current != null) {
        error_type = "notfound"
        error = "Exemplar não encontrado."
      }
      precondition ($current.retired_at != null) {
        error_type = "inputerror"
        error = "Exemplar não está baixado."
      }
      db.edit exemplar {
        field_name = "id"
        field_value = $current.id
        data = {retired_at: null, retired_by: null, retire_kind: null, retire_reason: null, operational_condition: "unverified", condition_confirmed_at: now, condition_confirmed_by: $auth.id, condition_reason: ("Reativação: " ~ $input.reason)|substr:0:500}
        output = ["id", "identificador", "filme_id"]
      } as $reactivated
    } }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: "reactivate_exemplar", result: "success", resource_type: "exemplar", resource_id: $reactivated.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
    db.get film {
      field_name = "id"
      field_value = $reactivated.filme_id
      output = ["id", "titulo"]
    } as $film
    var $exemplar {
      value = {}|set:"id":$reactivated.id|set:"identificador":$reactivated.identificador|set:"filme_id":$reactivated.filme_id|set:"filme_titulo":(($film == null) ? ("Filme removido (#" ~ $reactivated.filme_id ~ ")") : $film.titulo)|set:"baixado":false|set:"baixa_tipo":""|set:"baixa_motivo":""
    }
  }
  response = {exemplar: $exemplar, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "dW_C-RoKCGY5YsYpicafP6ngS6Q"
}
