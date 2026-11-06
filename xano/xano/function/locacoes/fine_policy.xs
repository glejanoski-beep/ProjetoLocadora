// Parâmetros vigentes da política de multa, em inteiros.
// Variável ausente ou vazia usa o padrão (300 centavos, 120 minutos, 9000 centavos);
// preenchida com valor inválido falha (fail-closed): melhor recusar do que cobrar errado.
function "Locacoes/fine_policy" {
  input {
  }
  stack {
    var $daily_raw { value = ($env.XANO_FINE_DAILY_CENTS ?? "")|trim }
    var $grace_raw { value = ($env.XANO_FINE_GRACE_MINUTES ?? "")|trim }
    var $cap_raw { value = ($env.XANO_FINE_CAP_CENTS ?? "")|trim }
    precondition (($daily_raw == "" || ("/^[0-9]{1,7}$/"|regex_matches:$daily_raw)) && ($grace_raw == "" || ("/^[0-9]{1,7}$/"|regex_matches:$grace_raw)) && ($cap_raw == "" || ("/^[0-9]{1,7}$/"|regex_matches:$cap_raw))) {
      error_type = "standard"
      error = "Política de multa mal configurada."
    }
    var $daily { value = ($daily_raw == "") ? 300 : ($daily_raw|to_int) }
    var $grace { value = ($grace_raw == "") ? 120 : ($grace_raw|to_int) }
    var $cap { value = ($cap_raw == "") ? 9000 : ($cap_raw|to_int) }
    precondition ($daily > 0 && $grace >= 0 && $cap >= $daily) {
      error_type = "standard"
      error = "Política de multa mal configurada."
    }
  }
  response = {daily_cents: $daily, grace_minutes: $grace, cap_cents: $cap}
  guid = "6l4ijjyQ8sHe5e2mXPcUPgcu_AY"
}
