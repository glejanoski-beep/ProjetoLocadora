// Resumo para o dashboard: quantidade de multas em aberto e saldo total.
query "multas/resumo" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    db.query fine {
      where = $db.fine.status == "open"
      return = {type: "list"}
      output = ["amount_cents", "paid_cents", "waived_cents"]
    } as $open_fines
    var $count { value = 0 }
    var $balance { value = 0 }
    foreach ($open_fines) {
      each as $item {
        var.update $count { value = $count + 1 }
        var.update $balance { value = $balance + $item.amount_cents - $item.paid_cents - $item.waived_cents }
      }
    }
  }
  response = {open_count: $count, open_balance_cents: $balance}
  tags = []
  guid = "JyGOcehaLN9CULNE1Gvf5Re4qqI"
}
