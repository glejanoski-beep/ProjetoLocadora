// Updates the approved catalog fields for an existing film.
query "catalogo-filmes/filmes/{id}" verb=PATCH {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    int id
    text titulo filters=trim|max:200
    text genero filters=trim|max:100
    int ano_lancamento
    enum classificacao {
      values = ["Livre", "10 anos", "12 anos", "14 anos", "16 anos", "18 anos"]
    }
    int valor_locacao_centavos
    enum status {
      values = ["active", "inactive"]
    }
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "admin"
      }
    } as $role_check

    precondition ($input.titulo != "" && ($input.titulo|strlen) <= 200) {
      error_type = "inputerror"
      error = "Título obrigatório, com até 200 caracteres."
    }

    precondition ($input.genero != "" && ($input.genero|strlen) <= 100) {
      error_type = "inputerror"
      error = "Gênero obrigatório, com até 100 caracteres."
    }

    precondition (
      $input.ano_lancamento >= 1888
      && $input.ano_lancamento <= (now|format_timestamp:"Y":"UTC"|to_int)
    ) {
      error_type = "inputerror"
      error = "Ano de lançamento fora do intervalo permitido."
    }

    precondition ($input.valor_locacao_centavos >= 0) {
      error_type = "inputerror"
      error = "Valor de locação não pode ser negativo."
    }

    db.get film {
      field_name = "id"
      field_value = $input.id
    } as $existing_film

    precondition ($existing_film != null) {
      error_type = "notfound"
      error = "Filme não encontrado."
    }

    db.edit film {
      field_name = "id"
      field_value = $input.id
      data = {
        titulo: $input.titulo
        genero: $input.genero
        ano_lancamento: $input.ano_lancamento
        classificacao: $input.classificacao
        valor_locacao_centavos: $input.valor_locacao_centavos
        status: $input.status
      }
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status"]
    } as $film

    var $audit_succeeded { value = true }

    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {
            user_id: $auth.id
            action: "edit_film"
            result: "success"
            resource_type: "film"
            resource_id: $film.id
          }
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
  }

  response = {film: $film, audit_succeeded: $audit_succeeded}
  tags = []
}
