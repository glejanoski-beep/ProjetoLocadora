// Listagem paginada das locações registradas, mais recentes primeiro.
// Mesma projeção de 13 campos do detalhe; sem CPF nem dados de contato.
query "locacoes" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int page?=1
    int per_page?=10
    // Opcional: "active" ou "returned". Vazio lista todas, como antes.
    text status? filters=trim
    // Opcional: locações de um cliente (histórico no detalhe do cliente).
    int customer_id?
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    precondition ($input.page >= 1 && $input.per_page >= 1 && $input.per_page <= 50) {
      error_type = "inputerror"
      error = "Paginação inválida."
    }
    var $status { value = ($input.status == null) ? "" : $input.status }
    precondition ($status == "" || $status == "active" || $status == "returned") {
      error_type = "inputerror"
      error = "Situação inválida."
    }
    var $customer_id { value = ($input.customer_id == null) ? 0 : $input.customer_id }
    precondition ($customer_id >= 0) {
      error_type = "inputerror"
      error = "Cliente inválido."
    }
    db.query rental {
      where = ($status == "" || $db.rental.status == $status) && ($customer_id == 0 || $db.rental.customer_id == $customer_id)
      sort = {rental.id: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true, metadata: true}}
      output = ["items.id", "items.customer_id", "items.exemplar_id", "items.registered_by", "items.rented_at", "items.due_at", "items.status", "items.customer_name", "items.exemplar_identifier", "items.film_id", "items.film_title", "items.returned_at", "items.returned_by", "curPage", "itemsTotal"]
    } as $rentals
  }
  response = {items: $rentals.items, page: $rentals.curPage, per_page: $input.per_page, total: $rentals.itemsTotal}
  tags = []
  guid = "eL1WCa_SmXv8Vd18clhuIzvSdyc"
}
