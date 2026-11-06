// Pagamento de multa. Nunca apagado nem com valor alterado; ajuste só por estorno.
table payment {
  auth = false
  schema {
    int id
    int fine_id { table = "fine" }
    int customer_id { table = "customer" }
    int amount_cents
    enum method { values = ["cash", "pix", "debit_card", "credit_card"] }
    timestamp paid_at
    int registered_by { table = "user" }
    uuid operation_key
    enum status { values = ["confirmed", "reversed"] }
    timestamp? reversed_at
    int? reversed_by { table = "user" }
    text? reversal_reason filters=trim|max:500
    uuid? reversal_operation_key
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "registered_by"}, {name: "operation_key"}]}
    {type: "btree", field: [{name: "fine_id"}]}
    {type: "btree", field: [{name: "customer_id"}]}
  ]
  guid = "UN_lWRIGiCM12dK8wAG4Rhc5ly0"
}
