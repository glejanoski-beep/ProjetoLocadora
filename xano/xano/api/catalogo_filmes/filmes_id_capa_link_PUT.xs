// Sets or clears an external https cover link for an existing film; administrators only.
query "catalogo-filmes/filmes/{id}/capa-link" verb=PUT {
  api_group = "Catálogo de Filmes"
  auth = "user"

  input {
    int id
    // Empty clears the link.
    text capa_link? filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $auth.id
        required_role: "admin"
      }
    } as $role_check

    var $link {
      value = ($input.capa_link == null) ? "" : $input.capa_link
    }

    // Only https links without spaces, quotes or angle brackets, up to 500 characters.
    // Slashes are removed before the regex so the pattern needs no escaped "/".
    var $link_chars {
      value = $link|replace:"/":""
    }

    var $link_valid {
      value = $link == "" || (($link|strlen) <= 500 && ($link|starts_with:"https://") && ("/^https:[A-Za-z0-9._~:?#@!&()*+,;=%-]+$/"|regex_matches:$link_chars))
    }

    precondition ($link_valid) {
      error_type = "inputerror"
      error = "Informe um link https válido para a imagem da capa."
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
        capa_link: ($link == "") ? null : $link
      }
      output = ["id", "titulo", "genero", "ano_lancamento", "classificacao", "valor_locacao_centavos", "status", "capa", "capa_link"]
    } as $film

    var $audit_succeeded { value = true }

    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {
            user_id: $auth.id
            action: "update_film_cover_link"
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
  guid = "3HwZ1inVNRlW_MquTTyF1tIkSuM"
}
