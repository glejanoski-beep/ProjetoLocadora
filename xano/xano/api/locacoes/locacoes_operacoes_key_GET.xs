query "locacoes/operacoes/{operation_key}" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    uuid operation_key
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    db.query rental {
      where = $db.rental.registered_by == $auth.id && $db.rental.operation_key == $input.operation_key
      return = {type: "single"}
      output = ["id", "customer_id", "exemplar_id", "registered_by", "rented_at", "due_at", "status", "customer_name", "exemplar_identifier", "film_id", "film_title"]
    } as $rental
    precondition ($rental != null) {
      error_type = "notfound"
      error = "Locação não encontrada."
    }
  }
  response = $rental
  tags = []
  guid = "gpU1Bg4kThKTTd3fXfq9aH1aHSI"
}
