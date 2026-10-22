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
    // Validar o calendário no relógio informado, sem depender de suporte
    // do runtime a nomes de timezone numéricos como -03:00.
    var $calendar_text { value = ($input.due_at|substr:0:19) ~ "Z" }
    var $calendar_timestamp { value = $calendar_text|to_timestamp }
    var $timestamp { value = $input.due_at|to_timestamp }
    // Roundtrip também recusa datas de calendário normalizadas pelo parser.
    precondition (($calendar_timestamp|format_timestamp:"Y-m-d":"UTC") != "") {
      error_type = "inputerror"
      error = "Vencimento inválido."
    }
    var $local_date { value = ($calendar_timestamp|format_timestamp:"Y-m-d":"UTC") ~ "T" ~ ($calendar_timestamp|format_timestamp:"H:i:s":"UTC") }
    precondition ($local_date == ($input.due_at|substr:0:19)) {
      error_type = "inputerror"
      error = "Vencimento inválido."
    }
  }
  response = $timestamp
  guid = "rI7lKRcdG90_BLPywGd5rVhZOms"
}
