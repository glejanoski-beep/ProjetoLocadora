// Updates only approved customer registration fields.
query "clientes/{id}" verb=PATCH {
  api_group = "Clientes"
  auth = "user"

  input {
    int id
    text nome filters=trim|max:200
    text cpf filters=trim
    email email? filters=trim|lower
    text telefone? filters=trim
    enum status {
      values = ["active", "inactive"]
    }
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

    function.run "Clientes/validate_cpf" {
      input = {cpf: $input.cpf}
    } as $cpf_validation
    precondition ($input.nome != "" && ($input.nome|strlen) <= 200) {
      error_type = "inputerror"
      error = "Nome obrigatório, com até 200 caracteres."
    }
    precondition ($cpf_validation.valid) {
      error_type = "inputerror"
      error = "CPF inválido."
    }

    var $telefone { value = "" }
    conditional {
      if ($input.telefone != null && $input.telefone != "") {
        var.update $telefone {
          value = $input.telefone|replace:"(":""|replace:")":""|replace:"-":""|replace:" ":""
        }
      }
    }
    var $telefone_resto {
      value = $telefone|replace:"0":""|replace:"1":""|replace:"2":""|replace:"3":""|replace:"4":""|replace:"5":""|replace:"6":""|replace:"7":""|replace:"8":""|replace:"9":""
    }
    precondition (
      $input.telefone == null || $input.telefone == ""
      || ($telefone_resto == "" && (($telefone|strlen) == 10 || ($telefone|strlen) == 11))
    ) {
      error_type = "inputerror"
      error = "Telefone brasileiro inválido."
    }
    precondition (($input.email != null && $input.email != "") || $telefone != "") {
      error_type = "inputerror"
      error = "Informe ao menos um contato: e-mail ou telefone."
    }

    db.query customer {
      where = $db.customer.cpf == $cpf_validation.cpf && $db.customer.id != $input.id
      return = {type: "count"}
    } as $duplicate_count
    precondition ($duplicate_count == 0) {
      error_type = "inputerror"
      error = "Já existe um cliente cadastrado com este CPF."
    }

    try_catch {
      try {
        db.edit customer {
          field_name = "id"
          field_value = $input.id
          data = {
            updated_at: "now"
            nome: $input.nome
            cpf: $cpf_validation.cpf
            email: $input.email
            telefone: ($telefone == "" ? null : $telefone)
            status: $input.status
          }
          output = ["id", "created_at", "updated_at", "nome", "cpf", "email", "telefone", "status", "bloqueio_manual_ativo", "motivo_bloqueio_manual", "bloqueado_em", "bloqueado_por"]
        } as $customer
      }
      catch {
        precondition (false) {
          error_type = "inputerror"
          error = "Já existe um cliente cadastrado com este CPF."
        }
      }
    }

    var $audit_action { value = "update_customer" }
    conditional {
      if ($existing_customer.status != $input.status) {
        var.update $audit_action { value = "change_customer_status" }
      }
    }
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
  guid = "qdA8Jacs5CR4pwVEdD_5WYXbbOA"
}
