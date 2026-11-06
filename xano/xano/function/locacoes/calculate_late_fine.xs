// Multa por atraso (change registrar-multa-e-pagamento).
// Devolução sem atraso não lê a configuração. Com atraso, a política vem de
// Locacoes/fine_policy (falha com configuração inválida, desfazendo a devolução).
// dias = ceil((returned_at - due_at) / 24 h) quando o atraso passa da tolerância;
// valor = min(dias * diária, teto). Somente inteiros em centavos.
function "Locacoes/calculate_late_fine" {
  input {
    int due_at
    int returned_at
  }
  stack {
    var $late_ms { value = $input.returned_at - $input.due_at }
    var $result { value = {late_days: 0, amount_cents: 0, daily_cents: 0, grace_minutes: 0, cap_cents: 0} }
    conditional {
      if ($late_ms > 0) {
        function.run "Locacoes/fine_policy" {
          input = {}
        } as $policy
        conditional {
          if ($late_ms > $policy.grace_minutes * 60000) {
            var $days { value = (($late_ms / 86400000)|ceil)|to_int }
            var $amount { value = $days * $policy.daily_cents }
            var.update $result {
              value = {late_days: $days, amount_cents: ($amount > $policy.cap_cents) ? $policy.cap_cents : $amount, daily_cents: $policy.daily_cents, grace_minutes: $policy.grace_minutes, cap_cents: $policy.cap_cents}
            }
          }
        }
      }
    }
  }
  response = $result
  guid = "V-gChLcRL_VDBLe1VFZOoULaD4o"
}
