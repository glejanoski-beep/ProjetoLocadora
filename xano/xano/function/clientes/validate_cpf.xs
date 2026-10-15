// Normalizes a Brazilian CPF and validates its check digits.
function "Clientes/validate_cpf" {
  input {
    text cpf filters=trim
  }

  stack {
    var $cpf {
      value = $input.cpf|replace:".":""|replace:"-":""|replace:"/":""|replace:" ":""
    }
    var $cpf_resto {
      value = $cpf|replace:"0":""|replace:"1":""|replace:"2":""|replace:"3":""|replace:"4":""|replace:"5":""|replace:"6":""|replace:"7":""|replace:"8":""|replace:"9":""
    }
    var $allowed { value = $cpf_resto == "" && ($cpf|strlen) == 11 }
    var $valid {
      value = $allowed && $cpf != "00000000000" && $cpf != "11111111111" && $cpf != "22222222222" && $cpf != "33333333333" && $cpf != "44444444444" && $cpf != "55555555555" && $cpf != "66666666666" && $cpf != "77777777777" && $cpf != "88888888888" && $cpf != "99999999999"
    }

    var $first_sum {
      value = (($cpf|substr:0:1|to_int) * 10) + (($cpf|substr:1:1|to_int) * 9) + (($cpf|substr:2:1|to_int) * 8) + (($cpf|substr:3:1|to_int) * 7) + (($cpf|substr:4:1|to_int) * 6) + (($cpf|substr:5:1|to_int) * 5) + (($cpf|substr:6:1|to_int) * 4) + (($cpf|substr:7:1|to_int) * 3) + (($cpf|substr:8:1|to_int) * 2)
    }
    var $first_digit { value = ($first_sum|multiply:10|modulus:11) }
    conditional {
      if ($first_digit == 10) {
        var.update $first_digit { value = 0 }
      }
    }
    var.update $valid {
      value = $valid && $first_digit == ($cpf|substr:9:1|to_int)
    }

    var $second_sum {
      value = (($cpf|substr:0:1|to_int) * 11) + (($cpf|substr:1:1|to_int) * 10) + (($cpf|substr:2:1|to_int) * 9) + (($cpf|substr:3:1|to_int) * 8) + (($cpf|substr:4:1|to_int) * 7) + (($cpf|substr:5:1|to_int) * 6) + (($cpf|substr:6:1|to_int) * 5) + (($cpf|substr:7:1|to_int) * 4) + (($cpf|substr:8:1|to_int) * 3) + (($cpf|substr:9:1|to_int) * 2)
    }
    var $second_digit { value = ($second_sum|multiply:10|modulus:11) }
    conditional {
      if ($second_digit == 10) {
        var.update $second_digit { value = 0 }
      }
    }
    var.update $valid {
      value = $valid && $second_digit == ($cpf|substr:10:1|to_int)
    }
  }

  response = {cpf: $cpf, valid: $valid}
  guid = "MrzZRTyVU4aDW6tiTe5pD2McjjE"
}
