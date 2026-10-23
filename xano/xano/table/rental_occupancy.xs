// Restrição de exclusividade; alterações somente pelo ciclo de locação.
table rental_occupancy {
  auth = false
  schema {
    int id
    int exemplar_id { table = "exemplar" }
    int rental_id { table = "rental" }
  }
  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "exemplar_id"}]}
    {type: "btree|unique", field: [{name: "rental_id"}]}
  ]
  guid = "vDxgG8RtuUmgXnPCli16NVEzdHA"
}
