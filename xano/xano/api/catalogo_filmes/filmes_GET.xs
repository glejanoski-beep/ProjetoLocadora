// Lists persisted films and applies optional title and genre filters.
query "catalogo-filmes/filmes" verb=GET {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    text titulo? filters=trim
    text genero? filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "member"
      }
    } as $role_check

    db.query film {
      where = (
        ($input.titulo == null || $input.titulo == "" || ($db.film.titulo|to_lower|includes:($input.titulo|to_lower)))
        && ($input.genero == null || $input.genero == "" || $db.film.genero == $input.genero)
      )
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status"]
      return = {type: "list"}
    } as $films
  }

  response = $films
  tags = []
}
