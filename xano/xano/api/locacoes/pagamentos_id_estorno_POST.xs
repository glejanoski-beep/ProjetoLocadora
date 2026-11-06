// Estorno de pagamento (somente admin, com motivo). O pagamento fica "reversed",
// nunca apagado; a multa volta a "open". Recusado para multa abonada.
query "pagamentos/{id}/estorno" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int id
    text reason filters=trim
    uuid operation_key
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($env.XANO_RENTAL_WRITES_ENABLED == "true") {
      error_type = "accessdenied"
      error = "Registro de locação ainda não habilitado."
    }
    precondition ($input.id > 0) {
      error_type = "inputerror"
      error = "Pagamento inválido."
    }
    precondition ($input.reason != null && ($input.reason|strlen) > 0 && ($input.reason|strlen) <= 500) {
      error_type = "inputerror"
      error = "Informe o motivo do estorno (até 500 caracteres)."
    }
    // fine_id é imutável: lido antes para respeitar a ordem conta, multa, pagamento.
    db.get payment {
      field_name = "id"
      field_value = $input.id
      output = ["id", "fine_id"]
    } as $target
    precondition ($target != null) {
      error_type = "notfound"
      error = "Pagamento não encontrado."
    }
    var $created { value = false }
    var $transaction_failed { value = false }
    try_catch {
      try {
        db.transaction { stack {
          db.get user {
            field_name = "id"
            field_value = $auth.id
            lock = true
            output = ["id", "role", "is_active"]
          } as $actor
          precondition ($actor != null && $actor.is_active != false && $actor.role == "admin") {
            error_type = "accessdenied"
            error = "Conta sem autorização atual."
          }
          db.get fine {
            field_name = "id"
            field_value = $target.fine_id
            lock = true
            output = ["id", "paid_cents", "status"]
          } as $fine_row
          db.get payment {
            field_name = "id"
            field_value = $target.id
            lock = true
            output = ["id", "amount_cents", "status", "reversed_by", "reversal_operation_key"]
          } as $payment_row
          conditional {
            if ($payment_row.status == "reversed" && $payment_row.reversed_by == $auth.id && $payment_row.reversal_operation_key == $input.operation_key) {
              var.update $created { value = false }
            }
            else {
              precondition ($payment_row.status == "confirmed") {
                error_type = "inputerror"
                error = "Pagamento já estornado."
              }
              precondition ($fine_row.status != "waived") {
                error_type = "inputerror"
                error = "Multa abonada: estorno não permitido."
              }
              db.edit payment {
                field_name = "id"
                field_value = $payment_row.id
                data = {status: "reversed", reversed_at: now, reversed_by: $auth.id, reversal_reason: $input.reason, reversal_operation_key: $input.operation_key}
              } as $payment_updated
              db.edit fine {
                field_name = "id"
                field_value = $fine_row.id
                data = {paid_cents: $fine_row.paid_cents - $payment_row.amount_cents, status: "open"}
              } as $fine_updated
              var.update $created { value = true }
            }
          }
        } }
      }
      catch {
        var.update $created { value = false }
        var.update $transaction_failed { value = true }
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "reverse_payment", result: "failed: " ~ ($error.message|substr:0:300), resource_type: "payment", resource_id: $input.id}
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
        function.run "Quick Start/enforce_role" {
          input = {user_id: $auth.id, required_role: "admin"}
        } as $retry_role_check
        db.get payment {
          field_name = "id"
          field_value = $input.id
          output = ["id", "fine_id", "status", "reversed_by", "reversal_operation_key"]
        } as $current
        db.get fine {
          field_name = "id"
          field_value = $current.fine_id
          output = ["id", "status"]
        } as $current_fine
        conditional {
          if ($current.status == "reversed" && $current.reversed_by == $auth.id && $current.reversal_operation_key == $input.operation_key) {
            var.update $created { value = false }
          }
          else {
            precondition ($current.status == "confirmed") {
              error_type = "inputerror"
              error = "Pagamento já estornado."
            }
            precondition ($current_fine.status != "waived") {
              error_type = "inputerror"
              error = "Multa abonada: estorno não permitido."
            }
            precondition (false) {
              error_type = "standard"
              error = "Não foi possível confirmar o estorno. Consulte a multa antes de repetir."
            }
          }
        }
      }
    }
    var $audit_succeeded { value = false }
    conditional {
      if ($created) {
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "reverse_payment", result: "success", resource_type: "payment", resource_id: $input.id}
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
          where = $db.event_log.user_id == $auth.id && $db.event_log.action == "reverse_payment" && $db.event_log.metadata.resource_id == $input.id && $db.event_log.metadata.resource_type == "payment" && $db.event_log.metadata.result == "success"
          return = {type: "exists"}
        } as $audit_exists
        var.update $audit_succeeded { value = $audit_exists }
      }
    }
    db.get payment {
      field_name = "id"
      field_value = $input.id
      output = ["id", "fine_id", "customer_id", "amount_cents", "method", "paid_at", "registered_by", "status", "reversed_at", "reversed_by", "reversal_reason"]
    } as $payment_result
    db.get fine {
      field_name = "id"
      field_value = $target.fine_id
      output = ["id", "rental_id", "customer_id", "customer_name", "film_title", "exemplar_identifier", "due_at", "returned_at", "late_days", "daily_cents", "grace_minutes", "cap_cents", "amount_cents", "paid_cents", "waived_cents", "status", "created_at", "created_by", "waived_at", "waived_by", "waive_reason"]
    } as $fine_result
  }
  response = {payment: $payment_result, fine: $fine_result, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "GHOyNBbhQ_HvZEdw6_7K9ymvrkY"
}
