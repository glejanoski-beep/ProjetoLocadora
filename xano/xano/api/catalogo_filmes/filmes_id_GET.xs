// Loads one persisted film for the administrator edit form.
query "catalogo-filmes/filmes/{id}" verb=GET {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    int id
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "member"
      }
    } as $role_check

    db.get film {
      field_name = "id"
      field_value = $input.id
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status"]
    } as $film

    precondition ($film != null) {
      error_type = "notfound"
      error = "Filme não encontrado."
    }
  }

  response = $film
  tags = []
}
