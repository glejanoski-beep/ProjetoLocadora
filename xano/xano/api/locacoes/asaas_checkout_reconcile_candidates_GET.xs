// Lista tentativas sem identificador externo para reconciliação manual por admin.
query "asaas/checkouts/reconcile/candidates" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int page?=1
    int per_page?=20
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.page >= 1 && $input.per_page >= 1 && $input.per_page <= 50) {
      error_type = "inputerror"
      error = "Paginação inválida."
    }
    db.query asaas_checkout {
      where = $db.asaas_checkout.status == "unknown" && $db.asaas_checkout.checkout_id == null
      sort = {asaas_checkout.created_at: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true, metadata: true}}
      output = ["items.id", "items.fine_id", "items.customer_id", "items.requested_by", "items.external_reference", "items.amount_cents", "items.created_at", "curPage", "itemsTotal"]
    } as $attempts
  }
  response = {items: $attempts.items, page: $attempts.curPage, per_page: $input.per_page, total: $attempts.itemsTotal}
  tags = ["asaas", "payments"]
  guid = "P8sL5wR2qN9tY3cD6eF1gH4kJ7"
}
