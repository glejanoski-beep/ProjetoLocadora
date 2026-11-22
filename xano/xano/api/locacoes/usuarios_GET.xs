// Lista de contas internas (change gerenciar-usuarios). Somente admin.
// output explícito: senha e password_reset nunca são lidos. Até 500 contas.
query usuarios verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    db.query user {
      return = {type: "list", paging: {page: 1, per_page: 500, totals: true, metadata: true}}
      output = ["items.id", "items.name", "items.email", "items.role", "items.is_active", "items.created_at"]
    } as $users
  }
  response = {items: $users.items}
  tags = []
  guid = "YB1TCj5oEEp_RgEJfYeBPD-QyQk"
}
