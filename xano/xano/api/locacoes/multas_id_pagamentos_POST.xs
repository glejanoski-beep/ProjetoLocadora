// Registro de pagamento de multa (total ou parcial), nunca acima do saldo.
// Idempotente por (registered_by, operation_key). Sem integração com meios de pagamento.
query "multas/{id}/pagamentos" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    int amount_cents
    text method filters=trim
    uuid operation_key
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    precondition ($env.XANO_RENTAL_WRITES_ENABLED == "true") {
      error_type = "accessdenied"
      error = "Registro de locação ainda não habilitado."
    }
    precondition ($input.id > 0 && $input.amount_cents > 0) {
      error_type = "inputerror"
      error = "Multa e valor são obrigatórios."
    }
    precondition ($input.method == "cash" || $input.method == "pix" || $input.method == "debit_card" || $input.method == "credit_card") {
      error_type = "inputerror"
      error = "Meio de pagamento inválido."
    }
    var $payment { value = null }
    var $created { value = false }
    var $transaction_failed { value = false }
    try_catch {
      try {
        db.transaction { stack {
          // Ordem de bloqueios: conta, multa. Não bloqueia cliente: sem ciclo com a criação de locação.
          db.get user {
            field_name = "id"
            field_value = $auth.id
            lock = true
            output = ["id", "role", "is_active"]
          } as $actor
          precondition ($actor != null && $actor.is_active != false && ($actor.role == "member" || $actor.role == "admin")) {
            error_type = "accessdenied"
            error = "Conta sem autorização atual."
          }
          db.query payment {
            where = $db.payment.registered_by == $auth.id && $db.payment.operation_key == $input.operation_key
            return = {type: "single"}
          } as $existing
          conditional {
            if ($existing != null) {
              var.update $payment { value = $existing }
            }
            else {
              db.get fine {
                field_name = "id"
                field_value = $input.id
                lock = true
                output = ["id", "customer_id", "amount_cents", "paid_cents", "waived_cents", "status"]
              } as $fine_row
              precondition ($fine_row != null) {
                error_type = "notfound"
                error = "Multa não encontrada."
              }
              precondition ($fine_row.status == "open") {
                error_type = "inputerror"
                error = "Multa não está em aberto."
              }
              var $balance { value = $fine_row.amount_cents - $fine_row.paid_cents - $fine_row.waived_cents }
              precondition ($input.amount_cents <= $balance) {
                error_type = "inputerror"
                error = "Valor acima do saldo da multa."
              }
              var $paid_at { value = now }
              db.add payment {
                data = {
                  fine_id: $fine_row.id
                  customer_id: $fine_row.customer_id
                  amount_cents: $input.amount_cents
                  method: $input.method
                  paid_at: $paid_at
                  registered_by: $auth.id
                  operation_key: $input.operation_key
                  status: "confirmed"
                }
              } as $inserted
              var $new_paid { value = $fine_row.paid_cents + $input.amount_cents }
              db.edit fine {
                field_name = "id"
                field_value = $fine_row.id
                data = {paid_cents: $new_paid, status: ($new_paid + $fine_row.waived_cents >= $fine_row.amount_cents) ? "paid" : "open"}
              } as $fine_updated
              var.update $payment { value = $inserted }
              var.update $created { value = true }
            }
          }
        } }
      }
      catch {
        var.update $payment { value = null }
        var.update $created { value = false }
        var.update $transaction_failed { value = true }
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "register_payment", result: "failed: " ~ ($error.message|substr:0:300), resource_type: "fine", resource_id: $input.id}
            } as $failure_log
          }
          catch {
            var.update $transaction_failed { value = true }
          }
        }
      }
    }
    conditional {
      if ($transaction_failed) {
        // Revalidar antes de reconciliar, inclusive após falha de permissão.
        function.run "Quick Start/enforce_role" {
          input = {user_id: $auth.id, required_role: "member"}
        } as $retry_role_check
        db.query payment {
          where = $db.payment.registered_by == $auth.id && $db.payment.operation_key == $input.operation_key
          return = {type: "single"}
        } as $committed
        conditional {
          if ($committed != null) {
            var.update $payment { value = $committed }
          }
          else {
            // Mensagens de negócio decididas pelo estado atual: dentro da transação
            // a precondition vira exceção capturada e perderia o código HTTP.
            db.get fine {
              field_name = "id"
              field_value = $input.id
              output = ["id", "amount_cents", "paid_cents", "waived_cents", "status"]
            } as $current
            precondition ($current != null) {
              error_type = "notfound"
              error = "Multa não encontrada."
            }
            precondition ($current.status == "open") {
              error_type = "inputerror"
              error = "Multa não está em aberto."
            }
            precondition ($input.amount_cents <= $current.amount_cents - $current.paid_cents - $current.waived_cents) {
              error_type = "inputerror"
              error = "Valor acima do saldo da multa."
            }
            precondition (false) {
              error_type = "standard"
              error = "Não foi possível confirmar o pagamento. Consulte a multa antes de repetir."
            }
          }
        }
      }
    }
    conditional {
      if ($payment.fine_id != $input.id) {
        precondition (false) {
          error_type = "inputerror"
          error = "Chave já utilizada para outra operação."
        }
      }
    }
    var $audit_succeeded { value = false }
    conditional {
      if ($created) {
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "register_payment", result: "success", resource_type: "payment", resource_id: $payment.id}
            } as $event_log
            var.update $audit_succeeded { value = true }
          }
          catch {
            var.update $audit_succeeded { value = false }
          }
        }
      }
      else {
        db.query event_log {
          where = $db.event_log.user_id == $auth.id && $db.event_log.action == "register_payment" && $db.event_log.metadata.resource_id == $payment.id && $db.event_log.metadata.resource_type == "payment" && $db.event_log.metadata.result == "success" && $db.event_log.created_at >= $payment.paid_at
          return = {type: "exists"}
        } as $audit_exists
        var.update $audit_succeeded { value = $audit_exists }
      }
    }
    db.get payment {
      field_name = "id"
      field_value = $payment.id
      output = ["id", "fine_id", "customer_id", "amount_cents", "method", "paid_at", "registered_by", "status", "reversed_at", "reversed_by", "reversal_reason"]
    } as $payment_result
    db.get fine {
      field_name = "id"
      field_value = $payment.fine_id
      output = ["id", "rental_id", "customer_id", "customer_name", "film_title", "exemplar_identifier", "due_at", "returned_at", "late_days", "daily_cents", "grace_minutes", "cap_cents", "amount_cents", "paid_cents", "waived_cents", "status", "created_at", "created_by", "waived_at", "waived_by", "waive_reason"]
    } as $fine_result
  }
  response = {payment: $payment_result, fine: $fine_result, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "9oBMQNwsiDlikbOdEPr8zpsw4wY"
}
