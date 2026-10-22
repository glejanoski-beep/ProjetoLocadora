// Individual physical copy linked to one catalog film.
table exemplar {
  auth = false

  schema {
    int id
    text identificador
    int filme_id {
      table = "film"
    }
    enum operational_condition?=unverified {
      values = ["unverified", "available", "unavailable"]
    }
    timestamp? condition_confirmed_at
    int? condition_confirmed_by { table = "user" }
    text? condition_reason filters=trim|max:500
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "identificador", op: "asc"}]}
    {type: "btree", field: [{name: "filme_id", op: "asc"}]}
  ]
  guid = "8vzM3sxxeTHrTxaJGPUfK1JI8ZA"
}
