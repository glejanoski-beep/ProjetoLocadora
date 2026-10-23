query "locacoes" verb=POST {
  api_group = "Locações"
  auth = "user"
  input {
    int customer_id
    int exemplar_id
    text due_at
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
    precondition ($input.customer_id > 0 && $input.exemplar_id > 0) {
      error_type = "inputerror"
      error = "Cliente e exemplar são obrigatórios."
    }
    function.run "Locacoes/parse_due_at" {
      input = {due_at: $input.due_at}
    } as $due_at
    var $rental { value = null }
    var $created { value = false }
    var $transaction_failed { value = false }
    try_catch {
      try {
        db.transaction { stack {
          // Ordem de bloqueios: conta, cliente, exemplar, filme.
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
          // Bloquear a conta também serializa tentativas da mesma conta/chave.
          db.query rental {
            where = $db.rental.registered_by == $auth.id && $db.rental.operation_key == $input.operation_key
            return = {type: "single"}
          } as $existing
          conditional {
            if ($existing != null) {
              var.update $rental { value = $existing }
            }
            else {
              db.get customer {
                field_name = "id"
                field_value = $input.customer_id
                lock = true
                output = ["id", "nome", "status", "bloqueio_manual_ativo"]
              } as $customer
              precondition ($customer != null && $customer.status == "active" && $customer.bloqueio_manual_ativo != true) {
                error_type = "inputerror"
                error = "Cliente não elegível para locação."
              }
              db.get exemplar {
                field_name = "id"
                field_value = $input.exemplar_id
                lock = true
                output = ["id", "identificador", "filme_id", "operational_condition"]
              } as $exemplar
              precondition ($exemplar != null && $exemplar.operational_condition == "available") {
                error_type = "inputerror"
                error = "Exemplar não disponível para locação."
              }
              db.get film {
                field_name = "id"
                field_value = $exemplar.filme_id
                lock = true
                output = ["id", "titulo", "status"]
              } as $film
              precondition ($film != null && $film.status == "active") {
                error_type = "inputerror"
                error = "Filme não disponível para locação."
              }
              db.has rental_occupancy {
                field_name = "exemplar_id"
                field_value = $exemplar.id
              } as $occupied
              conditional {
                if ($occupied) {
                  precondition (false) {
                    error_type = "inputerror"
                    error = "Exemplar já possui locação ativa."
                  }
                }
              }
              var $rented_at { value = now }
              precondition ($due_at > $rented_at) {
                error_type = "inputerror"
                error = "Vencimento deve ser posterior à retirada."
              }
              db.add rental {
                data = {
                  customer_id: $customer.id
                  exemplar_id: $exemplar.id
                  registered_by: $auth.id
                  rented_at: $rented_at
                  due_at: $due_at
                  status: "active"
                  operation_key: $input.operation_key
                  customer_name: $customer.nome
                  exemplar_identifier: $exemplar.identificador
                  film_id: $film.id
                  film_title: $film.titulo
                }
              } as $inserted
              db.add rental_occupancy {
                data = {exemplar_id: $exemplar.id, rental_id: $inserted.id}
              } as $occupancy
              var.update $rental { value = $inserted }
              var.update $created { value = true }
            }
          }
        } }
      }
      catch {
        // Não continuar com variáveis da transação abortada.
        var.update $rental { value = null }
        var.update $created { value = false }
        var.update $transaction_failed { value = true }
        var $failure_message { value = $error.message }
      }
    }
    conditional {
      if ($transaction_failed) {
        // Revalidar antes de reconciliar dados, inclusive após falha de permissão.
        function.run "Quick Start/enforce_role" {
          input = {user_id: $auth.id, required_role: "member"}
        } as $retry_role_check
        db.query rental {
          where = $db.rental.registered_by == $auth.id && $db.rental.operation_key == $input.operation_key
          return = {type: "single"}
        } as $committed
        conditional {
          if ($committed != null) {
            var.update $rental { value = $committed }
          }
          else {
            // A corrida pode terminar como falha de índice, não como validação
            // explícita. Classificar somente depois do rollback/reconciliação.
            db.has rental_occupancy {
              field_name = "exemplar_id"
              field_value = $input.exemplar_id
            } as $now_occupied
            conditional {
              if ($now_occupied) {
                precondition (false) {
                  error_type = "inputerror"
                  error = "Exemplar já possui locação ativa."
                }
              }
              else {
                conditional {
                  if ($failure_message == "Cliente não elegível para locação." || $failure_message == "Exemplar não disponível para locação." || $failure_message == "Filme não disponível para locação." || $failure_message == "Vencimento deve ser posterior à retirada.") {
                    precondition (false) {
                      error_type = "inputerror"
                      error = $failure_message
                    }
                  }
                  else {
                    // Erro HTTP explícito: throw customizado pode encerrar como HTTP 200.
                    // Não devolver detalhes internos de falha do banco.
                    precondition (false) {
                      error_type = "standard"
                      error = "Não foi possível confirmar a operação. Consulte a tentativa antes de repetir."
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
      if ($rental.customer_id != $input.customer_id || $rental.exemplar_id != $input.exemplar_id || $rental.due_at != $due_at) {
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
              input = {user_id: $auth.id, action: "create_rental", result: "success", resource_type: "rental", resource_id: $rental.id}
            } as $event_log
            var.update $audit_succeeded { value = true }
          }
          catch {
            var.update $audit_succeeded { value = false }
          }
        }
      }
      else {
        // Não presumir que o evento da requisição original foi confirmado.
        // Só eventos posteriores a esta locação: ids de locação podem ser reutilizados.
        db.query event_log {
          where = $db.event_log.user_id == $auth.id && $db.event_log.action == "create_rental" && $db.event_log.metadata.resource_id == $rental.id && $db.event_log.metadata.resource_type == "rental" && $db.event_log.metadata.result == "success" && $db.event_log.created_at >= $rental.rented_at
          return = {type: "exists"}
        } as $audit_exists
        var.update $audit_succeeded { value = $audit_exists }
      }
    }
    db.get rental {
      field_name = "id"
      field_value = $rental.id
      output = ["id", "customer_id", "exemplar_id", "registered_by", "rented_at", "due_at", "status", "customer_name", "exemplar_identifier", "film_id", "film_title", "returned_at", "returned_by"]
    } as $result
  }
  response = {rental: $result, audit_succeeded: $audit_succeeded}
  tags = []
  guid = "tax4PENi7VLhtE7GRIqECDtdYZo"
}
