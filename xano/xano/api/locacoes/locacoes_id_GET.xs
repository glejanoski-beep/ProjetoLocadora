query "locacoes/{id}" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int id
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    db.get rental {
      field_name = "id"
      field_value = $input.id
      output = ["id", "customer_id", "exemplar_id", "registered_by", "rented_at", "due_at", "status", "customer_name", "exemplar_identifier", "film_id", "film_title"]
    } as $rental
    precondition ($rental != null) {
      error_type = "notfound"
      error = "Locação não encontrada."
    }
  }
  response = $rental
  tags = []
  guid = "M7R-IzDnnv9sEEDeAlBOlQF17po"
}
