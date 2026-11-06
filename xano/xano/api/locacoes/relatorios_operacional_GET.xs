// Relatório consolidado por período [from, to), em ms UTC (change gerar-relatorios).
// Somente admin; leitura sem efeitos, sem dados pessoais nem nomes de clientes.
// Definições dos indicadores no design.md da change.
query "relatorios/operacional" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
    int from
    int to
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check
    precondition ($input.from > 0 && $input.to > $input.from && $input.to - $input.from <= 31622400000) {
      error_type = "inputerror"
      error = "Período inválido."
    }
    var $now { value = now }

    // Locações no período e situação atual
    db.query rental {
      where = $db.rental.rented_at >= $input.from && $db.rental.rented_at < $input.to
      return = {type: "count"}
    } as $checkouts
    db.query rental {
      where = $db.rental.returned_at >= $input.from && $db.rental.returned_at < $input.to
      return = {type: "list"}
      output = ["returned_at", "due_at"]
    } as $returned
    var $late_returns { value = 0 }
    foreach ($returned) {
      each as $item {
        conditional {
          if ($item.returned_at > $item.due_at) {
            var.update $late_returns { value = $late_returns + 1 }
          }
        }
      }
    }
    db.query rental {
      where = $db.rental.status == "active"
      return = {type: "count"}
    } as $active_now
    db.query rental {
      where = $db.rental.status == "active" && $db.rental.due_at < $now
      return = {type: "count"}
    } as $overdue_now

    // Multas
    db.query fine {
      where = $db.fine.created_at >= $input.from && $db.fine.created_at < $input.to
      return = {type: "list"}
      output = ["amount_cents"]
    } as $generated
    var $generated_cents { value = 0 }
    foreach ($generated) {
      each as $item {
        var.update $generated_cents { value = $generated_cents + $item.amount_cents }
      }
    }
    db.query fine {
      where = $db.fine.waived_at >= $input.from && $db.fine.waived_at < $input.to
      return = {type: "list"}
      output = ["waived_cents"]
    } as $waived
    var $waived_cents { value = 0 }
    foreach ($waived) {
      each as $item {
        var.update $waived_cents { value = $waived_cents + $item.waived_cents }
      }
    }
    db.query fine {
      where = $db.fine.status == "open"
      return = {type: "list"}
      output = ["amount_cents", "paid_cents", "waived_cents"]
    } as $open_fines
    var $open_balance { value = 0 }
    foreach ($open_fines) {
      each as $item {
        var.update $open_balance { value = $open_balance + $item.amount_cents - $item.paid_cents - $item.waived_cents }
      }
    }

    // Pagamentos: recebidos = registrados no período e ainda confirmados.
    db.query payment {
      where = $db.payment.paid_at >= $input.from && $db.payment.paid_at < $input.to && $db.payment.status == "confirmed"
      return = {type: "list"}
      output = ["amount_cents", "method"]
    } as $received
    var $received_cents { value = 0 }
    var $cash { value = 0 }
    var $pix { value = 0 }
    var $debit_card { value = 0 }
    var $credit_card { value = 0 }
    foreach ($received) {
      each as $item {
        var.update $received_cents { value = $received_cents + $item.amount_cents }
        conditional {
          if ($item.method == "cash") {
            var.update $cash { value = $cash + $item.amount_cents }
          }
          elseif ($item.method == "pix") {
            var.update $pix { value = $pix + $item.amount_cents }
          }
          elseif ($item.method == "debit_card") {
            var.update $debit_card { value = $debit_card + $item.amount_cents }
          }
          else {
            var.update $credit_card { value = $credit_card + $item.amount_cents }
          }
        }
      }
    }
    db.query payment {
      where = $db.payment.reversed_at >= $input.from && $db.payment.reversed_at < $input.to
      return = {type: "list"}
      output = ["amount_cents"]
    } as $reversed
    var $reversed_cents { value = 0 }
    foreach ($reversed) {
      each as $item {
        var.update $reversed_cents { value = $reversed_cents + $item.amount_cents }
      }
    }

    // Filmes mais alugados: retiradas por filme (todas as cópias) e cópias cadastradas.
    db.query film {
      return = {type: "list"}
      output = ["id", "titulo"]
    } as $catalog
    var $films { value = [] }
    foreach ($catalog) {
      each as $film {
        db.query rental {
          where = $db.rental.film_id == $film.id && $db.rental.rented_at >= $input.from && $db.rental.rented_at < $input.to
          return = {type: "count"}
        } as $film_rentals
        conditional {
          if ($film_rentals > 0) {
            db.query exemplar {
              where = $db.exemplar.filme_id == $film.id
              return = {type: "count"}
            } as $film_exemplars
            var.update $films { value = $films|push:{film_id: $film.id, film_title: $film.titulo, rentals: $film_rentals, exemplars: $film_exemplars} }
          }
        }
      }
    }
  }
  response = {
    from: $input.from
    to: $input.to
    generated_at: $now
    rentals: {checkouts: $checkouts, returns: ($returned|count), late_returns: $late_returns, active_now: $active_now, overdue_now: $overdue_now}
    fines: {generated_count: ($generated|count), generated_cents: $generated_cents, waived_count: ($waived|count), waived_cents: $waived_cents, open_balance_cents: $open_balance}
    payments: {received_cents: $received_cents, received_count: ($received|count), by_method: {cash: $cash, pix: $pix, debit_card: $debit_card, credit_card: $credit_card}, reversed_count: ($reversed|count), reversed_cents: $reversed_cents}
    films: $films
  }
  tags = []
  guid = "x0-4_IvW0gDjks4g-0_0zk27foA"
}
