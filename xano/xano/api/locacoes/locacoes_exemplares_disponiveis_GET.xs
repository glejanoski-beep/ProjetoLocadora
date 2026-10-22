query "locacoes/exemplares-disponiveis" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int page?=1
    int per_page?=20
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    precondition ($input.page >= 1 && $input.per_page >= 1 && $input.per_page <= 50) {
      error_type = "inputerror"
      error = "Paginação inválida."
    }
    db.query exemplar {
      join = {
        film: {table: "film", type: "inner", where: $db.exemplar.filme_id == $db.film.id}
        rental_occupancy: {table: "rental_occupancy", type: "left", where: $db.exemplar.id == $db.rental_occupancy.exemplar_id}
      }
      where = $db.exemplar.operational_condition == "available" && $db.film.status == "active" && $db.rental_occupancy.id == null
      sort = {exemplar.id: "asc"}
      eval = {filme_titulo: $db.film.titulo}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true, metadata: true}}
      output = ["items.id", "items.identificador", "items.filme_id", "items.filme_titulo", "curPage", "itemsTotal"]
    } as $available
  }
  response = {items: $available.items, page: $available.curPage, per_page: $input.per_page, total: $available.itemsTotal}
  tags = []
}
