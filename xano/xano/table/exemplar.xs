// Individual physical copy linked to one catalog film.
table exemplar {
  auth = false

  schema {
    int id
    text identificador
    int filme_id {
      table = "film"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "identificador", op: "asc"}]}
    {type: "btree", field: [{name: "filme_id", op: "asc"}]}
  ]
  guid = "7R9-qJX04Jtpd64Y87VGGbrI2-I"
}
