// Creates one physical copy after checking administrator access and its film reference.
query "exemplares" verb=POST {
  api_group = "Exemplares"
  auth = "user"

  input {
    text identificador
    int filme_id
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    precondition ($input.identificador != "") {
      error_type = "inputerror"
      error = "Informe o identificador do exemplar."
    }

    db.get film {
      field_name = "id"
      field_value = $input.filme_id
      output = ["id", "titulo"]
    } as $film

    precondition ($film != null) {
      error_type = "notfound"
      error = "Filme não encontrado."
    }

    db.query exemplar {
      where = $db.exemplar.identificador == $input.identificador
      return = {type: "count"}
    } as $duplicate_count

    precondition ($duplicate_count == 0) {
      error_type = "inputerror"
      error = "Já existe um exemplar com este identificador."
    }

    db.add exemplar {
      data = {
        identificador: $input.identificador
        filme_id: $film.id
      }
      output = ["id", "identificador", "filme_id"]
    } as $created

    var $exemplar {
      value = {}|set:"id":$created.id|set:"identificador":$created.identificador|set:"filme_id":$film.id|set:"filme_titulo":$film.titulo
    }

    var $audit_succeeded { value = true }
    try_catch {
      try {
        function.run "Quick Start/log_event" {
          input = {
            user_id: $auth.id
            action: "create_exemplar"
            result: "success"
            resource_type: "exemplar"
            resource_id: $created.id
          }
        } as $event_log
      }
      catch {
        var.update $audit_succeeded { value = false }
      }
    }
  }

  response = {exemplar: $exemplar, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "R0GbjN4_QRwBqlq-cs6-8w4rpxY"
}
