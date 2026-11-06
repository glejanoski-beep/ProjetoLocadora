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
      sort = {user.name: "asc"}
      output = ["id", "name", "email", "role", "is_active", "created_at"]
      return = {type: "list", paging: {page: 1, per_page: 500}}
    } as $users
    var $items { value = [] }
    foreach ($users.items) {
      each as $row {
        var $item {
          value = {}|set:"id":$row.id|set:"name":($row.name ?? "")|set:"email":($row.email ?? "")|set:"role":($row.role ?? "")|set:"is_active":($row.is_active != false)|set:"created_at":$row.created_at
        }
        var.update $items { value = $items|push:$item }
      }
    }
  }
  response = {items: $items}
  tags = []
  guid = "YB1TCj5oEEp_RgEJfYeBPD-QyQk"
}
