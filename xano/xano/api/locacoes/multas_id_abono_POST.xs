// Abono do saldo restante (somente admin, com motivo). Preserva pagamentos e valor original.
// Idempotente: a mesma conta e chave sobre a multa já abonada devolve o estado atual.
query "multas/{id}/abono" verb=POST {
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
      error = "Multa inválida."
    }
    precondition ($input.reason != null && ($input.reason|strlen) > 0 && ($input.reason|strlen) <= 500) {
      error_type = "inputerror"
      error = "Informe o motivo do abono (até 500 caracteres)."
    }
    var $created { value = false }
    var $already_done { value = false }
    var $transaction_failed { value = false }
    try_catch {
      try {
        db.transaction { stack {
          // Ordem de bloqueios: conta, multa.
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
            field_value = $input.id
            lock = true
            output = ["id", "amount_cents", "paid_cents", "waived_cents", "status", "waived_by", "waive_operation_key"]
          } as $fine_row
          precondition ($fine_row != null) {
            error_type = "notfound"
            error = "Multa não encontrada."
          }
          conditional {
            if ($fine_row.status == "waived" && $fine_row.waived_by == $auth.id && $fine_row.waive_operation_key == $input.operation_key) {
              var.update $already_done { value = true }
            }
            else {
              precondition ($fine_row.status == "open") {
                error_type = "inputerror"
                error = "Multa não está em aberto."
              }
              db.edit fine {
                field_name = "id"
                field_value = $fine_row.id
                data = {waived_cents: $fine_row.amount_cents - $fine_row.paid_cents - $fine_row.waived_cents, status: "waived", waived_at: now, waived_by: $auth.id, waive_reason: $input.reason, waive_operation_key: $input.operation_key}
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
              input = {user_id: $auth.id, action: "waive_fine", result: "failed: " ~ ($error.message|substr:0:300), resource_type: "fine", resource_id: $input.id}
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
        db.get fine {
          field_name = "id"
          field_value = $input.id
          output = ["id", "status", "waived_by", "waive_operation_key"]
        } as $current
        precondition ($current != null) {
          error_type = "notfound"
          error = "Multa não encontrada."
        }
        conditional {
          if ($current.status == "waived" && $current.waived_by == $auth.id && $current.waive_operation_key == $input.operation_key) {
            var.update $already_done { value = true }
          }
          else {
            precondition ($current.status == "open") {
              error_type = "inputerror"
              error = "Multa não está em aberto."
            }
            precondition (false) {
              error_type = "standard"
              error = "Não foi possível confirmar o abono. Consulte a multa antes de repetir."
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
              input = {user_id: $auth.id, action: "waive_fine", result: "success", resource_type: "fine", resource_id: $input.id}
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
          where = $db.event_log.user_id == $auth.id && $db.event_log.action == "waive_fine" && $db.event_log.metadata.resource_id == $input.id && $db.event_log.metadata.resource_type == "fine" && $db.event_log.metadata.result == "success"
          return = {type: "exists"}
        } as $audit_exists
        var.update $audit_succeeded { value = $audit_exists }
      }
    }
    db.get fine {
      field_name = "id"
      field_value = $input.id
      output = ["id", "rental_id", "customer_id", "customer_name", "film_title", "exemplar_identifier", "due_at", "returned_at", "late_days", "daily_cents", "grace_minutes", "cap_cents", "amount_cents", "paid_cents", "waived_cents", "status", "created_at", "created_by", "waived_at", "waived_by", "waive_reason"]
    } as $fine_result
  }
  response = {fine: $fine_result, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "3K6qjiJ-UeiRscccgcoBKXumdhs"
}
