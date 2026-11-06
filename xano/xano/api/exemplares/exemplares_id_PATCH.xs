// Edição de exemplar (admin): identificador sempre corrigível; filme só sem
// locações registradas, para o histórico não ficar contraditório.
query "exemplares/{id}" verb=PATCH {
  api_group = "Exemplares"
  auth = "user"
  input {
    int id
    text identificador
    int filme_id
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.id > 0 && $input.filme_id > 0) {
      error_type = "inputerror"
      error = "Informe exemplar e filme."
    }
    precondition ($input.identificador != "" && ($input.identificador|strlen) <= 100) {
      error_type = "inputerror"
      error = "Informe o identificador do exemplar."
    }
    db.transaction { stack {
      // Ordem de bloqueios: conta, exemplar (a criação de locação também bloqueia o exemplar).
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
        error = "Exemplar baixado: reative antes de editar."
      }
      db.query exemplar {
        where = $db.exemplar.identificador == $input.identificador && $db.exemplar.id != $current.id
        return = {type: "count"}
      } as $duplicate_count
      precondition ($duplicate_count == 0) {
        error_type = "inputerror"
        error = "Já existe um exemplar com este identificador."
      }
      db.get film {
        field_name = "id"
        field_value = $input.filme_id
        output = ["id", "titulo"]
      } as $film
      precondition ($film != null) {
        error_type = "notfound"
        error = "Filme não encontrado."
      }
      conditional {
        if ($input.filme_id != $current.filme_id) {
          db.has rental {
            field_name = "exemplar_id"
            field_value = $current.id
          } as $has_history
          precondition ($has_history == false) {
            error_type = "inputerror"
            error = "Exemplar com locações registradas não pode trocar de filme."
          }
        }
      }
      db.edit exemplar {
        field_name = "id"
        field_value = $current.id
        data = {identificador: $input.identificador, filme_id: $film.id}
        output = ["id", "identificador", "filme_id"]
      } as $updated
    } }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: "update_exemplar", result: "success", resource_type: "exemplar", resource_id: $updated.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
    var $exemplar {
      value = {}|set:"id":$updated.id|set:"identificador":$updated.identificador|set:"filme_id":$film.id|set:"filme_titulo":$film.titulo|set:"baixado":false|set:"baixa_tipo":""|set:"baixa_motivo":""
    }
  }
  response = {exemplar: $exemplar, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "oL9rIiG5wuSDYyjSrgNQR41Rv8U"
}
