// Baixa de exemplar (admin): perdido, danificado, descartado ou outro, com motivo.
// Recusada com locação ativa. Também marca a condição como unavailable, de modo
// que a cópia sai das opções de locação pelas regras existentes. Nada é apagado.
query "exemplares/{id}/baixa" verb=POST {
  api_group = "Exemplares"
  auth = "user"
  input {
    int id
    text retire_kind filters=trim
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
    precondition ($input.retire_kind == "lost" || $input.retire_kind == "damaged" || $input.retire_kind == "discarded" || $input.retire_kind == "other") {
      error_type = "inputerror"
      error = "Informe o tipo da baixa."
    }
    precondition ($input.reason != null && ($input.reason|strlen) > 0 && ($input.reason|strlen) <= 500) {
      error_type = "inputerror"
      error = "Informe o motivo da baixa (até 500 caracteres)."
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
        output = ["id", "identificador", "filme_id", "retired_at"]
      } as $current
      precondition ($current != null) {
        error_type = "notfound"
        error = "Exemplar não encontrado."
      }
      precondition ($current.retired_at == null) {
        error_type = "inputerror"
        error = "Exemplar já está baixado."
      }
      // Depois do bloqueio do exemplar: uma locação concorrente já terá gravado a ocupação.
      db.has rental_occupancy {
        field_name = "exemplar_id"
        field_value = $current.id
      } as $occupied
      precondition ($occupied == false) {
        error_type = "inputerror"
        error = "Exemplar alugado: registre a devolução antes da baixa."
      }
      var $now { value = now }
      db.edit exemplar {
        field_name = "id"
        field_value = $current.id
        data = {retired_at: $now, retired_by: $auth.id, retire_kind: $input.retire_kind, retire_reason: $input.reason, operational_condition: "unavailable", condition_confirmed_at: $now, condition_confirmed_by: $auth.id, condition_reason: ("Baixa: " ~ $input.reason)|substr:0:500}
        output = ["id", "identificador", "filme_id"]
      } as $retired
    } }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: "retire_exemplar", result: "success: " ~ $input.retire_kind, resource_type: "exemplar", resource_id: $retired.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
    db.get film {
      field_name = "id"
      field_value = $retired.filme_id
      output = ["id", "titulo"]
    } as $film
    var $exemplar {
      value = {}|set:"id":$retired.id|set:"identificador":$retired.identificador|set:"filme_id":$retired.filme_id|set:"filme_titulo":(($film == null) ? ("Filme removido (#" ~ $retired.filme_id ~ ")") : $film.titulo)|set:"baixado":true|set:"baixa_tipo":$input.retire_kind|set:"baixa_motivo":$input.reason
    }
  }
  response = {exemplar: $exemplar, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "ils53gOd6O2C3px-mYCxV1E13yI"
}
