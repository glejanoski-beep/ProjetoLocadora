"""Contratos estáticos de segurança; NÃO executam transações Xano.

Reconhecem blocos/tokenização e exercitam mutações inseguras. Rollback,
bloqueios reais e corrida permanecem sujeitos à homologação do workspace.
"""

from pathlib import Path
import unittest

from tests.test_dashboard_xano_contract import read_tree, block, unique_assignment

ROOT = Path(__file__).resolve().parents[1] / "xano/xano"


def flatten(nodes):
    for node in nodes:
        if isinstance(node, tuple):
            yield from flatten(node[1])
        else:
            yield node


def calls(nodes, name):
    for i, node in enumerate(nodes):
        if node == name:
            j = i + 1
            arguments = []
            while j < len(nodes) and not (isinstance(nodes[j], tuple) and nodes[j][0] == "{"):
                arguments.append(nodes[j])
                j += 1
            assert j < len(nodes)
            yield tuple(arguments), block(nodes[j])
        if isinstance(node, tuple):
            yield from calls(node[1], name)


def body(source):
    return block(read_tree(source)[-1])


def predicate_exists(nodes, expression):
    expected = read_tree("(" + expression + ")")[0]
    return any(args == (expected,) for args, _ in calls(nodes, "precondition"))


def check_create(source):
    endpoint = body(source)
    assert unique_assignment(endpoint, "auth") == '"user"'
    stack = next(calls(endpoint, "stack"))[1]
    assert stack[:2] == ("function.run", '"Quick Start/enforce_role"')
    assert predicate_exists(stack, '$env.XANO_RENTAL_WRITES_ENABLED == "true"')
    transactions = list(calls(stack, "db.transaction"))
    assert len(transactions) == 1
    transaction = transactions[0][1]
    locks = list(calls(transaction, "db.get"))
    assert [args for args, _ in locks] == [("user",), ("customer",), ("exemplar",), ("film",)]
    for args, operation in locks:
        assert unique_assignment(operation, "lock") == "true", f"Sem lock em {args}"
    assert predicate_exists(transaction, '$actor != null && $actor.is_active != false && ($actor.role == "member" || $actor.role == "admin")')
    assert predicate_exists(transaction, '$customer != null && $customer.status == "active" && $customer.bloqueio_manual_ativo != true')
    assert predicate_exists(transaction, '$exemplar != null && $exemplar.operational_condition == "available"')
    assert predicate_exists(transaction, '$film != null && $film.status == "active"')
    assert predicate_exists(transaction, '$due_at > $rented_at')
    writes = list(calls(transaction, "db.add"))
    assert [args for args, _ in writes] == [("rental",), ("rental_occupancy",)]
    assert len(list(calls(stack, "db.add"))) == len(writes)
    assert not list(calls(transaction, "try_catch")), "Não engolir falha dentro da transação"
    flat = list(flatten(transaction))
    assert flat.index("$due_at") < flat.index("db.add")
    assert not any(t in flat for t in ("db.edit", "db.patch", "db.del"))
    # Nada potencialmente falível entre a primeira e a segunda inserção.
    assert flat[flat.index("db.add") + 1] == "rental"
    assert not list(calls(transaction, "function.run"))
    assert "$auth.id" in flat and "$input.registered_by" not in flat
    assert len(list(calls(stack, "db.query"))) >= 3  # chave inicial, reconciliação externa, auditoria
    # No runtime, throw customizado encerrou conflito como HTTP 200.
    assert not list(calls(stack, "throw")), "Usar precondition com erro HTTP explícito"
    for _, operation in calls(stack, "precondition"):
        try:
            message = unique_assignment(operation, "error")
        except AssertionError:
            continue
        if message in ('"Exemplar já possui locação ativa."', '"Chave já utilizada para outra operação."'):
            assert unique_assignment(operation, "error_type") == '"inputerror"'



RETURN_FIELDS_13 = '["id", "customer_id", "exemplar_id", "registered_by", "rented_at", "due_at", "status", "customer_name", "exemplar_identifier", "film_id", "film_title", "returned_at", "returned_by"]'


def check_return(source):
    """Devolução: autorização e trava antes de dados, bloqueios, unidade atômica e liberação exata."""
    endpoint = body(source)
    assert unique_assignment(endpoint, "auth") == '"user"'
    stack = next(calls(endpoint, "stack"))[1]
    assert stack[:2] == ("function.run", '"Quick Start/enforce_role"')
    assert '"member"' in list(flatten(block(unique_assignment(block(stack[2]), "input"))))
    assert predicate_exists(stack, '$env.XANO_RENTAL_WRITES_ENABLED == "true"')
    transactions = list(calls(stack, "db.transaction"))
    assert len(transactions) == 1
    transaction = transactions[0][1]
    locks = list(calls(transaction, "db.get"))
    assert [args for args, _ in locks] == [("user",), ("rental",), ("rental_occupancy",)]
    for args, operation in locks:
        assert unique_assignment(operation, "lock") == "true", f"Sem lock em {args}"
    # A ocupação é encontrada pela locação, nunca apenas pelo exemplar.
    assert unique_assignment(locks[2][1], "field_name") == '"rental_id"'
    assert predicate_exists(transaction, '$actor != null && $actor.is_active != false && ($actor.role == "member" || $actor.role == "admin")')
    assert predicate_exists(transaction, '$rental != null')
    assert predicate_exists(transaction, '$rental.status == "active"')
    assert predicate_exists(transaction, '$occupancy != null && $occupancy.exemplar_id == $rental.exemplar_id')
    assert [args for args, _ in calls(transaction, "db.add")] == [("rental_return",)]
    edits = list(calls(transaction, "db.edit"))
    assert [args for args, _ in edits] == [("rental",)]
    data = list(flatten(block(unique_assignment(edits[0][1], "data"))))
    for protected in ("rented_at", "due_at", "customer_id", "exemplar_id", "registered_by", "operation_key"):
        assert protected not in data, f"Devolução não pode alterar {protected}"
    dels = list(calls(transaction, "db.del"))
    assert [args for args, _ in dels] == [("rental_occupancy",)]
    assert unique_assignment(dels[0][1], "field_name") == '"id"'
    assert unique_assignment(dels[0][1], "field_value") == "$occupancy.id"
    # Escritas fora da transação seriam efeitos sem atomicidade.
    for statement in ("db.add", "db.edit", "db.del"):
        assert len(list(calls(stack, statement))) == len(list(calls(transaction, statement)))
    # Inapto continua inapto: a devolução nunca toca a condição do exemplar.
    flat = list(flatten(stack))
    assert "exemplar" not in [args[0] for args, _ in calls(stack, "db.edit")]
    assert not any("operational_condition" in str(token) for token in flat)
    assert "$auth.id" in flat and "$input.returned_by" not in flat and "$input.returned_at" not in flat
    # Inexistência após falha decidida pelo banco; a mensagem capturada não é confiável (HTTP 500 no runtime).
    assert ("rental",) in [args for args, _ in calls(stack, "db.has")]
    assert "$failure_message" not in flat
    assert not list(calls(stack, "throw")), "Usar precondition com erro HTTP explícito"
    for _, operation in calls(stack, "precondition"):
        try:
            message = unique_assignment(operation, "error")
        except AssertionError:
            continue
        if message in ('"Locação já devolvida."', '"Chave já utilizada para outra operação."'):
            assert unique_assignment(operation, "error_type") == '"inputerror"'
        if message == '"Locação não encontrada."':
            assert unique_assignment(operation, "error_type") == '"notfound"'


class TestRentalXanoContract(unittest.TestCase):
    def source(self, path):
        return (ROOT / path).read_text()

    def test_creation_security_and_atomic_unit(self):
        check_create(self.source("api/locacoes/locacoes_POST.xs"))

    def test_rejects_custom_throw_that_can_return_http_200(self):
        source = self.source("api/locacoes/locacoes_POST.xs")
        unsafe = source.replace('error_type = "standard"', 'error_type = "standard"\n                    throw { name = "RentalConflict" value = "conflito" }', 1)
        with self.assertRaises(AssertionError):
            check_create(unsafe)

    def test_rejects_missing_lock_on_each_related_record(self):
        source = self.source("api/locacoes/locacoes_POST.xs")
        # Muta separadamente cada uma das quatro leituras protegidas.
        offsets = [i for i in range(len(source)) if source.startswith("lock = true", i)]
        self.assertEqual(len(offsets), 4)
        for offset in offsets:
            with self.subTest(offset=offset), self.assertRaises(AssertionError):
                check_create(source[:offset] + source[offset:].replace("lock = true", "lock = false", 1))

    def test_rejects_weakened_eligibility_or_removed_authorization(self):
        source = self.source("api/locacoes/locacoes_POST.xs")
        mutations = [
            ('auth = "user"', 'auth = "public"'),
            ('$customer.bloqueio_manual_ativo != true', 'true'),
            ('$customer.status == "active"', 'true'),
            ('$exemplar.operational_condition == "available"', 'true'),
            ('$film.status == "active"', 'true'),
            ('$due_at > $rented_at', '$due_at >= 0'),
            ('$env.XANO_RENTAL_WRITES_ENABLED == "true"', 'true'),
            ('$actor.is_active != false', 'true'),
        ]
        for before, after in mutations:
            with self.subTest(before=before), self.assertRaises(AssertionError):
                check_create(source.replace(before, after))

    def test_unique_keys_and_required_occupancy_references(self):
        rental = self.source("table/rental.xs")
        occupancy = self.source("table/rental_occupancy.xs")
        self.assertIn('{type: "btree|unique", field: [{name: "registered_by"}, {name: "operation_key"}]}', rental)
        for field in ("exemplar_id", "rental_id"):
            self.assertIn(f'int {field} {{ table =', occupancy)
            self.assertNotIn(f'int? {field}', occupancy)
            self.assertIn(f'{{type: "btree|unique", field: [{{name: "{field}"}}]}}', occupancy)

    def test_new_queries_have_explicit_auth_and_guard_before_any_data(self):
        for path in (ROOT / "api/locacoes").glob("*.xs"):
            if path.name == "locacoes.xs":
                continue
            with self.subTest(path=path.name):
                endpoint = body(path.read_text())
                self.assertEqual(unique_assignment(endpoint, "auth"), '"user"')
                stack = next(calls(endpoint, "stack"))[1]
                self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
                if path.name.endswith("PATCH.xs"):
                    self.assertIn('"admin"', list(flatten(block(unique_assignment(block(stack[2]), "input")))))

    def test_legacy_copies_not_automatically_available(self):
        source = self.source("table/exemplar.xs")
        self.assertIn("operational_condition?=unverified", source)
        self.assertNotIn("operational_condition?=available", source)
        self.assertIn('guid = "8vzM3sxxeTHrTxaJGPUfK1JI8ZA"', source)

    def test_available_query_filters_occupation_and_active_film(self):
        source = self.source("api/locacoes/locacoes_exemplares_disponiveis_GET.xs")
        for expression in ('$db.exemplar.operational_condition == "available"', '$db.film.status == "active"', '$db.rental_occupancy.id == null'):
            self.assertIn(expression, source)
        self.assertIn('type: "left"', source)
        self.assertIn('paging:', source)

    def test_condition_cannot_release_occupancy_or_create_rental(self):
        source = self.source("api/locacoes/locacoes_exemplares_condicao_PATCH.xs")
        self.assertIn('required_role: "admin"', source)
        self.assertIn('lock = true', source)
        self.assertNotIn("db.del", source)
        self.assertNotIn("db.add rental", source)
        writes = list(calls(body(source), "db.edit"))
        self.assertEqual([args for args, _ in writes], [("exemplar",)])
        data = block(unique_assignment(writes[0][1], "data"))
        self.assertNotIn("identificador", list(flatten(data)))
        self.assertNotIn("filme_id", list(flatten(data)))

    def test_read_projections_and_reconciliation_minimize_data(self):
        for path in ("api/locacoes/locacoes_id_GET.xs", "api/locacoes/locacoes_operacoes_key_GET.xs"):
            source = self.source(path)
            for prohibited in ("cpf", "email", "telefone", "condition_reason"):
                self.assertNotIn(prohibited, source)
            self.assertNotIn("db.add", source)
        key_source = self.source("api/locacoes/locacoes_operacoes_key_GET.xs")
        self.assertIn("$db.rental.registered_by == $auth.id", key_source)
        self.assertNotIn("$input.user_id", key_source)

    def test_backend_due_validation_requires_explicit_offset_and_roundtrip(self):
        source = self.source("function/locacoes/parse_due_at.xs")
        self.assertIn("regex_matches:$input.due_at", source)
        self.assertIn('$local_date == ($input.due_at|substr:0:19)', source)
        self.assertIn('$calendar_timestamp|format_timestamp:"H:i:s":"UTC"', source)
        self.assertIn('($input.due_at|substr:0:19) ~ "Z"', source)
        self.assertIn('$input.due_at|to_timestamp', source)
        self.assertNotIn("$timezone", source)

    # --- devolução ---------------------------------------------------------
    def test_return_security_and_atomic_unit(self):
        check_return(self.source("api/locacoes/locacoes_id_devolucao_POST.xs"))

    def test_return_rejects_unsafe_mutations(self):
        source = self.source("api/locacoes/locacoes_id_devolucao_POST.xs")
        mutations = [
            ('field_name = "rental_id"\n                field_value = $rental.id', 'field_name = "exemplar_id"\n                field_value = $rental.exemplar_id'),
            ('field_value = $occupancy.id', 'field_value = $rental.exemplar_id'),
            ('precondition ($rental.status == "active")', 'precondition (true)'),
            ('$env.XANO_RENTAL_WRITES_ENABLED == "true"', 'true'),
            ('data = {status: "returned", returned_at: $returned_at, returned_by: $auth.id}', 'data = {status: "returned", returned_at: $returned_at, returned_by: $auth.id, due_at: $returned_at}'),
            ('db.del rental_occupancy {', 'db.del rental_occupancy {\n                operational_condition = "available"'),
            ('db.has rental {', 'db.has rental_return {'),
        ]
        for before, after in mutations:
            self.assertIn(before, source)
            with self.subTest(before=before), self.assertRaises(AssertionError):
                check_return(source.replace(before, after, 1))
        offsets = [i for i in range(len(source)) if source.startswith("lock = true", i)]
        self.assertEqual(len(offsets), 3)
        for offset in offsets:
            with self.subTest(offset=offset), self.assertRaises(AssertionError):
                check_return(source[:offset] + source[offset:].replace("lock = true", "lock = false", 1))
        unsafe = source.replace('error_type = "standard"', 'error_type = "standard"\n                    throw { name = "ReturnConflict" value = "conflito" }', 1)
        with self.assertRaises(AssertionError):
            check_return(unsafe)

    def test_audit_on_replay_ignores_events_of_reused_rental_ids(self):
        # A tabela rental foi recriada e os ids recomeçaram; eventos antigos com o mesmo
        # resource_id não podem confirmar a auditoria de uma operação nova.
        clauses = {
            "api/locacoes/locacoes_POST.xs": "$db.event_log.created_at >= $rental.rented_at",
            "api/locacoes/locacoes_id_devolucao_POST.xs": "$db.event_log.created_at >= $returned.returned_at",
        }
        for path, clause in clauses.items():
            with self.subTest(path=path):
                queries = [op for args, op in calls(body(self.source(path)), "db.query") if args == ("event_log",)]
                self.assertEqual(len(queries), 1)
                self.assertIn(clause.replace(" ", ""), "".join(flatten(queries[0])))

    def test_return_is_unique_per_rental_and_key(self):
        table = self.source("table/rental_return.xs")
        self.assertIn('{type: "btree|unique", field: [{name: "rental_id"}]}', table)
        self.assertIn('{type: "btree|unique", field: [{name: "returned_by"}, {name: "operation_key"}]}', table)
        self.assertIn('int rental_id { table = "rental" }', table)
        self.assertNotIn("int? rental_id", table)
        rental = self.source("table/rental.xs")
        self.assertIn('enum status { values = ["active", "returned"] }', rental)
        self.assertIn("timestamp? returned_at", rental)
        self.assertIn('int? returned_by { table = "user" }', rental)

    def test_responses_use_the_13_field_projection(self):
        for path in ("api/locacoes/locacoes_id_GET.xs", "api/locacoes/locacoes_operacoes_key_GET.xs",
                     "api/locacoes/locacoes_POST.xs", "api/locacoes/locacoes_id_devolucao_POST.xs"):
            with self.subTest(path=path):
                self.assertIn(f"output = {RETURN_FIELDS_13}", self.source(path))

    def test_inapt_copy_stays_out_of_new_rentals_after_return(self):
        # A devolução não altera a condição; criação e consulta de disponíveis exigem "available".
        self.assertNotIn("operational_condition", self.source("api/locacoes/locacoes_id_devolucao_POST.xs"))
        self.assertIn('$exemplar.operational_condition == "available"', self.source("api/locacoes/locacoes_POST.xs"))
        self.assertIn('$db.exemplar.operational_condition == "available"', self.source("api/locacoes/locacoes_exemplares_disponiveis_GET.xs"))
