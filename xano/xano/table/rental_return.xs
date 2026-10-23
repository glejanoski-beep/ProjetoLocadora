// Registro da devolução: no máximo um por locação. Histórico permanente.
table rental_return {
  auth = false
  schema {
    int id
    int rental_id { table = "rental" }
    timestamp returned_at
    int returned_by { table = "user" }
    uuid operation_key
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "rental_id"}]}
    {type: "btree|unique", field: [{name: "returned_by"}, {name: "operation_key"}]}
  ]
  guid = "QBDC9KftLiV9AA20EoaR3N0mqJs"
}
