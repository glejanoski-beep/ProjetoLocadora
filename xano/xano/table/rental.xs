// Histórico permanente. Não remover para liberar exemplar.
table rental {
  auth = false
  schema {
    int id
    int customer_id { table = "customer" }
    int exemplar_id { table = "exemplar" }
    int registered_by { table = "user" }
    timestamp rented_at
    timestamp due_at
    // "returned" somente pela devolução (POST locacoes/{id}/devolucao).
    enum status { values = ["active", "returned"] }
    uuid operation_key
    text customer_name
    text exemplar_identifier
    int film_id { table = "film" }
    text film_title
    // Cópias de leitura do registro em rental_return, gravadas na mesma transação.
    timestamp? returned_at
    int? returned_by { table = "user" }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "registered_by"}, {name: "operation_key"}]}
    {type: "btree", field: [{name: "exemplar_id"}]}
    {type: "btree", field: [{name: "customer_id"}]}
  ]
  guid = "Rd-wyIaDjgv3T_lqRaZgzY4qEfg"
}
