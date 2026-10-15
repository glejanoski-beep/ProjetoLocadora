// Lists customers with paging and a deliberately minimal projection.
query "clientes" verb=GET {
  api_group = "Clientes"
  auth = "user"

  input {
    text nome? filters=trim
    text cpf? filters=trim
    int page?=1
    int per_page?=20
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check

    precondition ($input.page >= 1) {
      error_type = "inputerror"
      error = "Página inválida."
    }

    var $per_page { value = $input.per_page|min:50|max:1 }
    var $cpf_filter { value = "" }
    conditional {
      if ($input.cpf != null && $input.cpf != "") {
        function.run "Clientes/validate_cpf" {
          input = {cpf: $input.cpf}
        } as $cpf_validation

        precondition ($cpf_validation.valid) {
          error_type = "inputerror"
          error = "CPF inválido."
        }
        var.update $cpf_filter { value = $cpf_validation.cpf }
      }
    }

    db.query customer {
      where = (
        ($input.nome == null || $input.nome == "" || ($db.customer.nome|to_lower|includes:($input.nome|to_lower)))
        && ($cpf_filter == "" || $db.customer.cpf == $cpf_filter)
      )
      sort = {customer.nome: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $per_page, totals: true, metadata: true}}
      output = ["items.id", "items.nome", "items.cpf", "items.status", "items.bloqueio_manual_ativo", "curPage", "itemsTotal"]
    } as $customers

    var $items { value = [] }
    foreach ($customers.items) {
      each as $customer {
        function.run "Clientes/mask_cpf" {
          input = {cpf: $customer.cpf}
        } as $cpf_mascarado

        var $item {
          value = {}|set:"id":$customer.id|set:"nome":$customer.nome|set:"cpf_mascarado":$cpf_mascarado|set:"status":$customer.status|set:"bloqueio_manual_ativo":$customer.bloqueio_manual_ativo
        }
        var.update $items { value = $items|push:$item }
      }
    }
  }

  response = {items: $items, page: $customers.curPage, per_page: $per_page, total: $customers.itemsTotal}
  tags = []
  guid = "TD1dmxGz77L1gtuJ46TiPJBIgDo"
}
