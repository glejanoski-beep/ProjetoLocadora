// Criação administrativa de conta interna sem senha inicial.
// O usuário define a senha pelo fluxo existente de recuperação de senha.
query usuarios verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    text name filters=trim
    email email filters=trim|lower
    enum role {
      values = ["admin", "member"]
    }
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.name != null && ($input.name|strlen) > 0 && ($input.name|strlen) <= 200) {
      error_type = "inputerror"
      error = "Informe o nome com até 200 caracteres."
    }
    precondition ($input.email != null) {
      error_type = "inputerror"
      error = "Informe um e-mail válido."
    }
    db.query user {
      where = $db.user.email == $input.email
      return = {type: "exists"}
    } as $existing
    precondition (!$existing) {
      error_type = "badrequest"
      error = "Já existe uma conta com este e-mail."
    }
    db.add user {
      data = {
        created_at: "now"
        name: $input.name
        email: $input.email
        role: $input.role
        is_active: true
      }
      output = ["id"]
    } as $created
    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {
            user_id: $auth.id
            action: "create_user"
            result: ("success: role " ~ $input.role ~ "; active true")|substr:0:500
            resource_type: "user"
            resource_id: $created.id
          }
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
    db.get user {
      field_name = "id"
      field_value = $created.id
      output = ["id", "name", "email", "role", "is_active", "created_at"]
    } as $row
    var $user {
      value = {}|set:"id":$row.id|set:"name":($row.name ?? "")|set:"email":($row.email ?? "")|set:"role":($row.role ?? "")|set:"is_active":($row.is_active != false)|set:"created_at":$row.created_at
    }
  }
  response = {user: $user, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "cadastrar-novo-usuario-usuarios-post"
}
