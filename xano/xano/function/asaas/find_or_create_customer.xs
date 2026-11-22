// Localiza ou cria o cliente correspondente no Asaas, serializado pela linha local.
function "Asaas/find_or_create_customer" {
  input {
    int customer_id
  }

  stack {
    precondition (($env.ASAAS_CHECKOUT_ENABLED ?? "false") == "true") {
      error_type = "accessdenied"
      error = "Cobrança via cartão ainda não está habilitada."
    }
    precondition ((($env.ASAAS_API_KEY ?? "")|trim) != "") {
      error_type = "standard"
      error = "Integração de cobrança não configurada."
    }
    precondition ((($env.ASAAS_API_BASE_URL ?? "")|trim) != "") {
      error_type = "standard"
      error = "URL da integração de cobrança não configurada."
    }
    var $asaas_id { value = null }
    db.transaction { stack {
      db.get customer {
        field_name = "id"
        field_value = $input.customer_id
        lock = true
        output = ["id", "nome", "cpf", "email", "telefone", "status"]
      } as $customer
      precondition ($customer != null && $customer.status == "active") {
        error_type = "inputerror"
        error = "Cliente não está disponível para cobrança."
      }
      db.query asaas_customer {
        where = $db.asaas_customer.customer_id == $input.customer_id
        return = {type: "single"}
      } as $mapping
      conditional {
        if ($mapping != null) {
          var.update $asaas_id { value = $mapping.asaas_customer_id }
        }
        else {
          var $external_reference { value = "locadora-customer-" ~ ($customer.id|to_text) }
          api.request {
            url = ($env.ASAAS_API_BASE_URL|trim) ~ "/customers?externalReference=" ~ $external_reference
            method = "GET"
            headers = ["User-Agent: ProjetoLocadora/1.0", "accept: application/json", "access_token: " ~ $env.ASAAS_API_KEY]
            timeout = 20
          } as $search
          precondition ($search.response.status == 200) {
            error_type = "standard"
            error = "Não foi possível reconciliar o cliente de cobrança (Asaas HTTP " ~ ($search.response.status|to_text) ~ ")."
          }
          conditional {
            if (($search.response.result.data|count) > 0) {
              var.update $asaas_id { value = ($search.response.result.data|first).id }
            }
            else {
              var $customer_payload {
                value = {
                  name: $customer.nome
                  cpfCnpj: $customer.cpf
                  externalReference: $external_reference
                }
              }
              conditional {
                if ($customer.email != null && ($customer.email|trim) != "") {
                  var.update $customer_payload { value = $customer_payload|set:"email":$customer.email }
                }
              }
              conditional {
                if ($customer.telefone != null && ($customer.telefone|trim) != "") {
                  var.update $customer_payload { value = $customer_payload|set:"mobilePhone":$customer.telefone }
                }
              }
              api.request {
                url = ($env.ASAAS_API_BASE_URL|trim) ~ "/customers"
                method = "POST"
                params = $customer_payload
                headers = ["User-Agent: ProjetoLocadora/1.0", "Content-Type: application/json", "accept: application/json", "access_token: " ~ $env.ASAAS_API_KEY]
                timeout = 20
              } as $created_customer
              precondition (($created_customer.response.status == 200 || $created_customer.response.status == 201) && $created_customer.response.result.id != null) {
                error_type = "standard"
                error = "Não foi possível criar o cliente de cobrança (Asaas HTTP " ~ ($created_customer.response.status|to_text) ~ ")."
              }
              var.update $asaas_id { value = $created_customer.response.result.id }
            }
          }
          db.add asaas_customer {
            data = {customer_id: $customer.id, asaas_customer_id: $asaas_id}
          } as $new_mapping
        }
      }
    } }
  }

  response = {asaas_customer_id: $asaas_id}
  tags = ["asaas", "payments"]
  guid = "D8fO1sT5uQ2vW7yA9bC4eN3pG6"
}
