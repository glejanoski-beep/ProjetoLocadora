// Forma fechada ISO 8601; não aceita expressões relativas do to_timestamp.
function "Locacoes/parse_due_at" {
  input {
    text due_at
  }
  stack {
    precondition ("/^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$/"|regex_matches:$input.due_at) {
      error_type = "inputerror"
      error = "Informe vencimento ISO 8601 com horário e offset explícito."
    }
    var $timezone { value = "UTC" }
    conditional {
      if (($input.due_at|strlen) == 25) {
        var.update $timezone { value = $input.due_at|substr:19:6 }
      }
    }
    var $timestamp { value = $input.due_at|to_timestamp }
    // Roundtrip também recusa datas de calendário normalizadas pelo parser.
    precondition (($timestamp|format_timestamp:"Y-m-d":"UTC") != "") {
      error_type = "inputerror"
      error = "Vencimento inválido."
    }
    var $local_date { value = ($timestamp|format_timestamp:"Y-m-d":$timezone) ~ "T" ~ ($timestamp|format_timestamp:"H:i:s":$timezone) }
    precondition ($local_date == ($input.due_at|substr:0:19)) {
      error_type = "inputerror"
      error = "Vencimento inválido."
    }
  }
  response = $timestamp
}
