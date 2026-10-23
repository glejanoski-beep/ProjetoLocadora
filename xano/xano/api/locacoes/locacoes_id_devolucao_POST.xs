query "locacoes/{id}/devolucao" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int id
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
    precondition ($input.id > 0) {
      error_type = "inputerror"
      error = "Locação inválida."
    }
    var $returned { value = null }
    var $created { value = false }
    var $transaction_failed { value = false }
    try_catch {
      try {
        db.transaction { stack {
          // Ordem de bloqueios: conta, locação, ocupação. Não bloqueia exemplar,
          // cliente ou filme: sem ciclo com a criação (conta, cliente, exemplar, filme).
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
          // Bloquear a conta serializa repetições da mesma conta/chave.
          db.query rental_return {
            where = $db.rental_return.returned_by == $auth.id && $db.rental_return.operation_key == $input.operation_key
            return = {type: "single"}
          } as $existing
          conditional {
            if ($existing != null) {
              var.update $returned { value = $existing }
            }
            else {
              db.get rental {
                field_name = "id"
                field_value = $input.id
                lock = true
                output = ["id", "exemplar_id", "status"]
              } as $rental
              precondition ($rental != null) {
                error_type = "notfound"
                error = "Locação não encontrada."
              }
              precondition ($rental.status == "active") {
                error_type = "inputerror"
                error = "Locação já devolvida."
              }
              // A ocupação é localizada pela locação, nunca apenas pelo exemplar.
              db.get rental_occupancy {
                field_name = "rental_id"
                field_value = $rental.id
                lock = true
                output = ["id", "exemplar_id", "rental_id"]
              } as $occupancy
              precondition ($occupancy != null && $occupancy.exemplar_id == $rental.exemplar_id) {
                error_type = "standard"
                error = "Ocupação inconsistente; devolução não registrada."
              }
              var $returned_at { value = now }
              db.add rental_return {
                data = {
                  rental_id: $rental.id
                  returned_at: $returned_at
                  returned_by: $auth.id
                  operation_key: $input.operation_key
                }
              } as $inserted
              // Status e cópias de leitura na mesma unidade; retirada e vencimento intactos.
              db.edit rental {
                field_name = "id"
                field_value = $rental.id
                data = {status: "returned", returned_at: $returned_at, returned_by: $auth.id}
              } as $closed
              // Libera somente esta ocupação. Não altera a condição do exemplar.
              db.del rental_occupancy {
                field_name = "id"
                field_value = $occupancy.id
              }
              var.update $returned { value = $inserted }
              var.update $created { value = true }
            }
          }
        } }
      }
      catch {
        // Não continuar com variáveis da transação abortada.
        var.update $returned { value = null }
        var.update $created { value = false }
        var.update $transaction_failed { value = true }
        // Motivo interno só na auditoria (nunca na resposta), para diagnóstico.
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "return_rental", result: "failed: " ~ ($error.message|substr:0:300), resource_type: "rental", resource_id: $input.id}
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
        db.query rental_return {
          where = $db.rental_return.returned_by == $auth.id && $db.rental_return.operation_key == $input.operation_key
          return = {type: "single"}
        } as $committed
        conditional {
          if ($committed != null) {
            var.update $returned { value = $committed }
          }
          else {
            // A corrida pode terminar como falha de índice único em rental_return.rental_id.
            db.has rental_return {
              field_name = "rental_id"
              field_value = $input.id
            } as $already_returned
            // Inexistência decidida pelo banco: no runtime, a mensagem do notfound
            // capturada na transação não era igual e a resposta virava HTTP 500.
            db.has rental {
              field_name = "id"
              field_value = $input.id
            } as $rental_exists
            conditional {
              if ($already_returned) {
                precondition (false) {
                  error_type = "inputerror"
                  error = "Locação já devolvida."
                }
              }
              else {
                conditional {
                  if ($rental_exists == false) {
                    precondition (false) {
                      error_type = "notfound"
                      error = "Locação não encontrada."
                    }
                  }
                  else {
                    // Erro HTTP explícito: throw customizado pode encerrar como HTTP 200.
                    // Não devolver detalhes internos de falha do banco.
                    precondition (false) {
                      error_type = "standard"
                      error = "Não foi possível confirmar a devolução. Consulte a locação antes de repetir."
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    conditional {
      if ($returned.rental_id != $input.id) {
        precondition (false) {
          error_type = "inputerror"
          error = "Chave já utilizada para outra operação."
        }
      }
    }
    // Auditoria posterior ao commit; não alegar rollback se o log falhar.
    var $audit_succeeded { value = false }
    conditional {
      if ($created) {
        try_catch {
          try {
            function.run "Quick Start/log_event" {
              input = {user_id: $auth.id, action: "return_rental", result: "success", resource_type: "rental", resource_id: $returned.rental_id}
            } as $event_log
            var.update $audit_succeeded { value = true }
          }
          catch {
            var.update $audit_succeeded { value = false }
          }
        }
      }
      else {
        // Repetição: não presumir que o evento da requisição original foi confirmado.
        // Só eventos posteriores a esta devolução: ids de locação podem ser reutilizados.
        db.query event_log {
          where = $db.event_log.user_id == $auth.id && $db.event_log.action == "return_rental" && $db.event_log.metadata.resource_id == $returned.rental_id && $db.event_log.metadata.resource_type == "rental" && $db.event_log.metadata.result == "success" && $db.event_log.created_at >= $returned.returned_at
          return = {type: "exists"}
        } as $audit_exists
        var.update $audit_succeeded { value = $audit_exists }
      }
    }
    db.get rental {
      field_name = "id"
      field_value = $returned.rental_id
      output = ["id", "customer_id", "exemplar_id", "registered_by", "rented_at", "due_at", "status", "customer_name", "exemplar_identifier", "film_id", "film_title", "returned_at", "returned_by"]
    } as $result
  }
  response = {rental: $result, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "y4kNz1qCYPoAKxMqdUNuCTMUFuM"
}
