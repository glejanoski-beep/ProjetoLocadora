// Multa por atraso: no máximo uma por locação. Histórico permanente.
// amount_cents e o retrato da política nunca são alterados após a criação.
table fine {
  auth = false
  schema {
    int id
    int rental_id { table = "rental" }
    int customer_id { table = "customer" }
    // Cópias de leitura da locação, como em rental.
    text customer_name
    text film_title
    text exemplar_identifier
    timestamp due_at
    timestamp returned_at
    // Retrato da política aplicada no instante da devolução.
    int late_days
    int daily_cents
    int grace_minutes
    int cap_cents
    int amount_cents
    // Soma dos pagamentos confirmed; saldo = amount - paid - waived.
    int paid_cents?=0
    int waived_cents?=0
    enum status { values = ["open", "paid", "waived"] }
    timestamp created_at
    int created_by { table = "user" }
    timestamp? waived_at
    int? waived_by { table = "user" }
    text? waive_reason filters=trim|max:500
    uuid? waive_operation_key
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "rental_id"}]}
    {type: "btree", field: [{name: "customer_id"}, {name: "status"}]}
    {type: "btree", field: [{name: "status"}]}
  ]
  guid = "RQZ7kk4NGyYjYZGvs0mlVBC4Nek"
}
