// Sets or replaces the public cover image of an existing film; administrators only.
query "catalogo-filmes/filmes/{id}/capa" verb=POST {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    int id
    // Must be `file?`: only `file` populates `.path` on a multipart upload.
    file? capa
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "admin"
      }
    } as $role_check

    precondition ($input.capa != null) {
      error_type = "inputerror"
      error = "Envie a imagem da capa."
    }

    db.get film {
      field_name = "id"
      field_value = $input.id
    } as $existing_film

    precondition ($existing_film != null) {
      error_type = "notfound"
      error = "Filme não encontrado."
    }

    // create_attachment accepts any type; the real MIME and size are checked below,
    // so an unsupported file gets a clean input error instead of a fatal one.
    storage.create_attachment {
      value = $input.capa
      access = "public"
      filename = $input.capa.name
    } as $stored_cover

    var $cover_valid {
      value = (["image/jpeg", "image/png", "image/webp"]|in:$stored_cover.mime) && $stored_cover.size <= 2097152
    }

    conditional {
      if ($cover_valid == false) {
        storage.delete_file {
          pathname = $stored_cover.path
        }
      }
    }

    precondition ($cover_valid) {
      error_type = "inputerror"
      error = "A capa deve ser uma imagem JPEG, PNG ou WebP com até 2 MB."
    }

    db.edit film {
      field_name = "id"
      field_value = $input.id
      data = {
        capa: $stored_cover
      }
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status", "capa", "capa_link"]
    } as $film

    // The previous file is removed only after the film references the new one.
    var $previous_removed { value = true }
    conditional {
      if ($existing_film.capa != null && $existing_film.capa.path != null && $existing_film.capa.path != $stored_cover.path) {
        try_catch {
          try {
            storage.delete_file {
              pathname = $existing_film.capa.path
            }
          }
          catch {
            var.update $previous_removed { value = false }
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
            action: "update_film_cover"
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
  guid = "9sZYWfDZlbx65UiPs_LtJWMvlKQ"
}
