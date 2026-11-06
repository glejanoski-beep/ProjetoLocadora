// Detalhe da multa com todos os pagamentos, inclusive estornados.
query "multas/{id}" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int id
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    db.get fine {
      field_name = "id"
      field_value = $input.id
      output = ["id", "rental_id", "customer_id", "customer_name", "film_title", "exemplar_identifier", "due_at", "returned_at", "late_days", "daily_cents", "grace_minutes", "cap_cents", "amount_cents", "paid_cents", "waived_cents", "status", "created_at", "created_by", "waived_at", "waived_by", "waive_reason"]
    } as $fine
    precondition ($fine != null) {
      error_type = "notfound"
      error = "Multa não encontrada."
    }
    db.query payment {
      where = $db.payment.fine_id == $fine.id
      sort = {payment.id: "asc"}
      return = {type: "list"}
      output = ["id", "fine_id", "customer_id", "amount_cents", "method", "paid_at", "registered_by", "status", "reversed_at", "reversed_by", "reversal_reason"]
    } as $payments
  }
  response = {fine: $fine, payments: $payments}
  tags = []
  guid = "ShyUOYPOzch_C5CHzDeEq-mRkjg"
}
