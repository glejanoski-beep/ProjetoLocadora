// Listagem paginada de pagamentos de multas, inclusive estornados.
query "pagamentos" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int page?=1
    int per_page?=10
    int customer_id?
    int fine_id?
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    precondition ($input.page >= 1 && $input.per_page >= 1 && $input.per_page <= 50) {
      error_type = "inputerror"
      error = "Paginação inválida."
    }
    var $customer_id { value = ($input.customer_id == null) ? 0 : $input.customer_id }
    var $fine_id { value = ($input.fine_id == null) ? 0 : $input.fine_id }
    precondition ($customer_id >= 0 && $fine_id >= 0) {
      error_type = "inputerror"
      error = "Filtro inválido."
    }
    db.query payment {
      where = ($customer_id == 0 || $db.payment.customer_id == $customer_id) && ($fine_id == 0 || $db.payment.fine_id == $fine_id)
      sort = {payment.id: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true, metadata: true}}
      output = ["items.id", "items.fine_id", "items.customer_id", "items.amount_cents", "items.method", "items.paid_at", "items.registered_by", "items.status", "items.reversed_at", "items.reversed_by", "items.reversal_reason", "curPage", "itemsTotal"]
    } as $payments
  }
  response = {items: $payments.items, page: $payments.curPage, per_page: $input.per_page, total: $payments.itemsTotal}
  tags = []
  guid = "B3ro3YMIKYgdZYtMTD3E-6xMvEc"
}
