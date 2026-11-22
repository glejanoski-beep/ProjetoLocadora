// Eventos de Checkout recebidos do Asaas; usado para idempotência de webhook.
table asaas_checkout_event {
  auth = false
  schema {
    int id
    text event_id filters=trim|max:200
    text? checkout_id filters=trim|max:100
    text? provider_payment_id filters=trim|max:100
    text event filters=trim|max:100
    timestamp received_at?=now
    timestamp? processed_at
    enum status { values = ["received", "processed", "ignored", "failed"] }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "event_id"}]}
    {type: "btree", field: [{name: "checkout_id"}]}
  ]
  guid = "C7eN9rS4tP1uV6xZ8aB3dM2oF5"
}
