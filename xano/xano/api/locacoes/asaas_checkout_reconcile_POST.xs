// Reconciliação administrativa: vincula um Checkout encontrado no painel Asaas.
query "asaas/checkouts/reconcile" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int checkout_attempt_id
    text checkout_id filters=trim|max:100
    text external_reference filters=trim|max:200
    int verified_amount_cents
    text reason filters=trim|min:10|max:500
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    function.run "Asaas/reconcile_unknown_checkout" {
      input = {
        checkout_attempt_id: $input.checkout_attempt_id
        checkout_id: $input.checkout_id
        external_reference: $input.external_reference
        verified_amount_cents: $input.verified_amount_cents
        reason: $input.reason
        reconciled_by: $auth.id
      }
    } as $result
  }
  response = $result
  tags = ["asaas", "payments"]
  guid = "D7mK4pQ1sV8xZ2aB5cE9fG3hJ6"
}
