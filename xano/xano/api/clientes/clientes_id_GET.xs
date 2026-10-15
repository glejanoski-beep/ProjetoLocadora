// Returns the protected customer detail for internal service.
query "clientes/{id}" verb=GET {
  api_group = "Clientes"
  auth = "user"

  input {
    int id
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check

    db.get customer {
      field_name = "id"
      field_value = $input.id
      output = ["id", "created_at", "updated_at", "nome", "cpf", "email", "telefone", "status", "bloqueio_manual_ativo", "motivo_bloqueio_manual", "bloqueado_em", "bloqueado_por"]
    } as $customer

    precondition ($customer != null) {
      error_type = "notfound"
      error = "Cliente não encontrado."
    }
  }

  response = $customer
  tags = []
  guid = "iEYNwJxaHAd2MbPJxe_ZkF637Uk"
}
