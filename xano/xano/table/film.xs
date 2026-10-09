// Catalog record for a film; physical copies and stock are modeled separately.
table film {
  auth = false

  schema {
    int id
    text titulo filters=trim|max:200
    text genero filters=trim|max:100
    int ano_lancamento
    enum classificacao {
      values = ["Livre", "10 anos", "12 anos", "14 anos", "16 anos", "18 anos"]
    }
    int valor_locacao_centavos
    enum status?=active {
      values = ["active", "inactive"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "titulo", op: "asc"}]}
    {type: "btree", field: [{name: "genero", op: "asc"}]}
  ]
}
