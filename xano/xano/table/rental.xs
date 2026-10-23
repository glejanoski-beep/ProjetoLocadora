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
    enum status { values = ["active"] }
    uuid operation_key
    text customer_name
    text exemplar_identifier
    int film_id { table = "film" }
    text film_title
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "registered_by"}, {name: "operation_key"}]}
    {type: "btree", field: [{name: "exemplar_id"}]}
    {type: "btree", field: [{name: "customer_id"}]}
  ]
  guid = "Rd-wyIaDjgv3T_lqRaZgzY4qEfg"
}
