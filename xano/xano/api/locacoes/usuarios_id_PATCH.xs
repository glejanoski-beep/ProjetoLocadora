// Alteração de papel e situação de outra conta (change gerenciar-usuarios).
// Somente admin, com motivo; nunca a própria conta, o que mantém ao menos um
// admin ativo. As duas contas são bloqueadas em ordem crescente de id para que
// alterações cruzadas entre admins não entrem em impasse. Nada é excluído.
query "usuarios/{id}" verb=PATCH {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    enum role {
      values = ["admin", "member"]
    }
    bool is_active
    text reason filters=trim
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.id > 0) {
      error_type = "inputerror"
      error = "Usuário inválido."
    }
    precondition ($input.id != $auth.id) {
      error_type = "inputerror"
      error = "Você não pode alterar a própria conta."
    }
    precondition ($input.reason != null && ($input.reason|strlen) > 0 && ($input.reason|strlen) <= 500) {
      error_type = "inputerror"
      error = "Informe o motivo da alteração (até 500 caracteres)."
    }
    var $actor_first { value = $auth.id < $input.id }
    var $low_id { value = $actor_first ? $auth.id : $input.id }
    var $high_id { value = $actor_first ? $input.id : $auth.id }
    db.transaction { stack {
      db.get user {
        field_name = "id"
        field_value = $low_id
        lock = true
        output = ["id", "role", "is_active"]
      } as $low_row
      db.get user {
        field_name = "id"
        field_value = $high_id
        lock = true
        output = ["id", "role", "is_active"]
      } as $high_row
      var $actor { value = $actor_first ? $low_row : $high_row }
      var $target { value = $actor_first ? $high_row : $low_row }
      precondition ($actor != null && $actor.is_active != false && $actor.role == "admin") {
        error_type = "accessdenied"
        error = "Conta sem autorização atual."
      }
      precondition ($target != null) {
        error_type = "notfound"
        error = "Usuário não encontrado."
      }
      var $previous_active { value = $target.is_active != false }
      precondition ($target.role != $input.role || $previous_active != $input.is_active) {
        error_type = "inputerror"
        error = "Nenhuma alteração informada."
      }
      db.edit user {
        field_name = "id"
        field_value = $target.id
        data = {role: $input.role, is_active: $input.is_active}
        output = ["id"]
      } as $edited
    } }
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {user_id: $auth.id, action: "update_user", result: ("success: role " ~ ($target.role ?? "") ~ "->" ~ $input.role ~ "; active " ~ ($previous_active ? "true" : "false") ~ "->" ~ ($input.is_active ? "true" : "false") ~ "; reason: " ~ $input.reason)|substr:0:500, resource_type: "user", resource_id: $target.id}
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
    db.get user {
      field_name = "id"
      field_value = $target.id
      output = ["id", "name", "email", "role", "is_active", "created_at"]
    } as $row
    var $user {
      value = {}|set:"id":$row.id|set:"name":($row.name ?? "")|set:"email":($row.email ?? "")|set:"role":($row.role ?? "")|set:"is_active":($row.is_active != false)|set:"created_at":$row.created_at
    }
  }
  response = {user: $user, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "jRFbWWplQ5LiI1iztHULBJEMcLQ"
}
