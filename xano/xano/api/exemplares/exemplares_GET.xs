// Lists physical copies with the catalog film each copy belongs to.
query "exemplares" verb=GET {
  api_group = "Exemplares"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check

    db.query exemplar {
      sort = {exemplar.id: "asc"}
      output = ["id", "identificador", "filme_id"]
      return = {type: "list"}
    } as $exemplares

    var $items { value = [] }
    foreach ($exemplares) {
      each as $exemplar {
        db.get film {
          field_name = "id"
          field_value = $exemplar.filme_id
          output = ["id", "titulo"]
        } as $film

        // A copy whose film was removed outside the app must not break the whole listing.
        var $film_title { value = "Filme removido (#" ~ $exemplar.filme_id ~ ")" }
        conditional {
          if ($film != null) {
            var.update $film_title { value = $film.titulo }
          }
        }

        var $item {
          value = {}|set:"id":$exemplar.id|set:"identificador":$exemplar.identificador|set:"filme_id":$exemplar.filme_id|set:"filme_titulo":$film_title
        }
        var.update $items { value = $items|push:$item }
      }
    }
  }

  response = $items
  tags = []
  guid = "cibR9mTZjK6TcHgKx8MHCcznTXA"
}
