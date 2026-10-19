// Consulta administrativa dos totais cadastrados, sem inferir disponibilidade.
// Grupo Dashboard confirmado na Metadata API: workspace 149184, grupo 437089, branch v1.
query "dashboard/resumo-acervo" verb=GET {
  api_group = "Dashboard"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    db.query film {
      return = {type: "count"}
    } as $film_count

    db.query exemplar {
      return = {type: "count"}
    } as $exemplar_count

    var $total_filmes { value = $film_count|to_int }
    var $total_exemplares { value = $exemplar_count|to_int }

    precondition ($total_filmes >= 0 && $total_exemplares >= 0) {
      error_type = "standard"
      error = "Não foi possível gerar os totais do acervo."
    }

    // Captura única após as contagens; ambos os formatos usam UTC explícito.
    var $generated_timestamp { value = now }
    var $generated_at {
      value = ($generated_timestamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($generated_timestamp|format_timestamp:"H:i:s":"UTC") ~ "Z"
    }
  }

  response = {
    total_filmes: $total_filmes
    total_exemplares: $total_exemplares
    generated_at: $generated_at
  }
  tags = []
}
