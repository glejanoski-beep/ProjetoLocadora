// Customer master data. Rentals and financial obligations are modeled separately.
table customer {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    text nome filters=trim|max:200
    text cpf filters=trim|max:11
    email? email filters=trim|lower
    text? telefone filters=trim|max:11
    enum status?=active {
      values = ["active", "inactive"]
    }
    bool bloqueio_manual_ativo?=false
    text? motivo_bloqueio_manual filters=trim|max:500
    timestamp? bloqueado_em
    int? bloqueado_por {
      table = "user"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cpf", op: "asc"}]}
    {type: "btree", field: [{name: "nome", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
  ]
  guid = "GfhUdgyg0rVV1K3uQU-CX2w1suQ"
}
