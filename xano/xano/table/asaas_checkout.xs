// Tentativa de Checkout Asaas; não confirma o pagamento por si só.
table asaas_checkout {
  auth = false
  schema {
    int id
    int fine_id { table = "fine" }
    int customer_id { table = "customer" }
    int requested_by { table = "user" }
    uuid operation_key
    text external_reference filters=trim|max:200
    text? checkout_id filters=trim|max:100
    text? checkout_url filters=trim|max:1000
    int amount_cents
    enum status { values = ["unknown", "pending", "confirmed", "rejected", "cancelled", "expired", "reversed"] }
    text? last_event_id filters=trim|max:200
    text? external_payment_id filters=trim|max:100
    timestamp created_at?=now
    timestamp updated_at?=now
    timestamp? confirmed_at
    timestamp? reversed_at
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "requested_by"}, {name: "operation_key"}]}
    {type: "btree|unique", field: [{name: "checkout_id"}]}
    {type: "btree|unique", field: [{name: "external_reference"}]}
    {type: "btree", field: [{name: "fine_id"}, {name: "status"}]}
    {type: "btree", field: [{name: "customer_id"}]}
  ]
  guid = "B6dM8qR3sO9tU5wY7zA2cL1nE4"
}
