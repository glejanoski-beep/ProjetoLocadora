// Removes the cover image of an existing film; administrators only.
query "catalogo-filmes/filmes/{id}/capa" verb=DELETE {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    int id
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "admin"
      }
    } as $role_check

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
        capa: null
        capa_link: null
      }
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status", "capa", "capa_link"]
    } as $film

    // The film no longer references the file; a failed vault delete leaves only an orphan file.
    var $file_removed { value = true }
    conditional {
      if ($existing_film.capa != null && $existing_film.capa.path != null) {
        try_catch {
          try {
            storage.delete_file {
              pathname = $existing_film.capa.path
            }
          }
          catch {
            var.update $file_removed { value = false }
          }
        }
      }
    }

    var $audit_succeeded { value = true }

    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {
            user_id: $auth.id
            action: "remove_film_cover"
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
  guid = "MC-o-98K0BM1tJwoY9H2_VdgQDc"
}
