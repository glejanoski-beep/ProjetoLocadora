// Vínculo entre cliente interno e cliente criado no Asaas.
table asaas_customer {
  auth = false
  schema {
    int id
    int customer_id { table = "customer" }
    text asaas_customer_id filters=trim|max:100
    timestamp created_at?=now
    timestamp updated_at?=now
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "customer_id"}]}
    {type: "btree|unique", field: [{name: "asaas_customer_id"}]}
  ]
  guid = "A5cL7pQ2rN8sT4vX6yZ1bK9mD3"
}
