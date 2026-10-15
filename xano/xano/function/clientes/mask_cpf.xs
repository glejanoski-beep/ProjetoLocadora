// Masks a normalized CPF while preserving the final check digits for identification.
function "Clientes/mask_cpf" {
  input {
    text cpf filters=trim
  }

  stack {
    function.run "Clientes/validate_cpf" {
      input = {cpf: $input.cpf}
    } as $validation

    precondition ($validation.valid) {
      error_type = "inputerror"
      error = "CPF inválido."
    }

    var $masked { value = "***.***.***-" ~ ($validation.cpf|substr:9:2) }
  }

  response = $masked
  guid = "Ic-WLme1mG9I3SVqzUTs2iJX4wU"
}
