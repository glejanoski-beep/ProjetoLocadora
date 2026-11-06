// Listagem paginada de multas, mais recentes primeiro. Sem CPF nem contatos.
query "multas" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int page?=1
    int per_page?=10
    // Opcional: "open", "paid" ou "waived". Vazio lista todas.
    text status? filters=trim
    int customer_id?
    int rental_id?
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
    precondition ($status == "" || $status == "open" || $status == "paid" || $status == "waived") {
      error_type = "inputerror"
      error = "Situação inválida."
    }
    var $customer_id { value = ($input.customer_id == null) ? 0 : $input.customer_id }
    var $rental_id { value = ($input.rental_id == null) ? 0 : $input.rental_id }
    precondition ($customer_id >= 0 && $rental_id >= 0) {
      error_type = "inputerror"
      error = "Filtro inválido."
    }
    db.query fine {
      where = ($status == "" || $db.fine.status == $status) && ($customer_id == 0 || $db.fine.customer_id == $customer_id) && ($rental_id == 0 || $db.fine.rental_id == $rental_id)
      sort = {fine.id: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true, metadata: true}}
      output = ["items.id", "items.rental_id", "items.customer_id", "items.customer_name", "items.film_title", "items.exemplar_identifier", "items.due_at", "items.returned_at", "items.late_days", "items.daily_cents", "items.grace_minutes", "items.cap_cents", "items.amount_cents", "items.paid_cents", "items.waived_cents", "items.status", "items.created_at", "items.created_by", "items.waived_at", "items.waived_by", "items.waive_reason", "curPage", "itemsTotal"]
    } as $fines
  }
  response = {items: $fines.items, page: $fines.curPage, per_page: $input.per_page, total: $fines.itemsTotal}
  tags = []
  guid = "fBRc-O8yJ9weT9GdrRAPiE19eP0"
}
