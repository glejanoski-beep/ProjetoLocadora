"""Contrato estrutural local; não interpreta nem executa XanoScript.

O leitor abaixo reconhece tokens e delimitadores aninhados, ignorando comentários.
Não é um parser completo da linguagem. Mutações existem somente em memória.

Risco conhecido: o filtro to_int faz coerção (a documentação inclui texto,
decimal e bool), portanto não prova que o resultado original era inteiro.
A guarda >= 0 também não detecta um valor positivo truncado/coagido. Estes
testes verificam a consulta count, não simulam sua resposta nem a coerção Xano.
"""

import json
from pathlib import Path
import re
import unittest


ENDPOINT = (
    Path(__file__).resolve().parents[1]
    / "xano/xano/api/dashboard/dashboard_resumo_acervo_GET.xs"
)
TOKEN = re.compile(
    r'(?P<space>\s+)|(?P<comment>//[^\n]*|/\*.*?\*/)|'
    r'(?P<string>"(?:\\.|[^"\\])*")|'
    r'(?P<atom>\$?[A-Za-z_][\w.]*|\d+)|(?P<symbol>[^\s])',
    re.DOTALL,
)


def read_tree(source):
    """Preserva limites de blocos e strings sem depender da indentação."""
    tokens = [
        m.group() for m in TOKEN.finditer(source)
        if m.lastgroup not in {"space", "comment"}
    ]
    pairs = {"{": "}", "[": "]", "(": ")"}

    def group(index, closing=None):
        result = []
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token in pairs:
                children, index = group(index, pairs[token])
                result.append((token, children))
            elif token in pairs.values():
                if token != closing:
                    raise AssertionError("Delimitador incompatível")
                return tuple(result), index
            else:
                result.append(token)
        if closing:
            raise AssertionError("Bloco não encerrado")
        return tuple(result), index

    return group(0)[0]


def block(node):
    assert isinstance(node, tuple) and node[0] == "{", "Bloco esperado"
    return node[1]


def unique_assignment(nodes, name):
    values = [nodes[i + 2] for i in range(len(nodes) - 2)
              if nodes[i:i + 2] == (name, "=")]
    assert len(values) == 1, f"Atribuição única esperada: {name}"
    return values[0]


def fields(nodes):
    """Objeto de campos escalares; rejeita campos repetidos e expressões extras."""
    result = {}
    index = 0
    while index < len(nodes):
        key, colon, value = nodes[index:index + 3]
        assert colon == ":" and isinstance(key, str)
        assert key not in result, f"Campo repetido: {key}"
        result[key] = value
        index += 3
        if index < len(nodes) and nodes[index] == ",":
            index += 1
    return result


def check_contract(source):
    root = read_tree(source)
    assert root[:5] == ('query', '"dashboard/resumo-acervo"', 'verb', '=', 'GET')
    assert len(root) == 6
    endpoint = block(root[5])
    assert unique_assignment(endpoint, "api_group") == '"Dashboard"'
    assert unique_assignment(endpoint, "auth") == '"user"'
    inputs = [block(endpoint[i + 1]) for i, item in enumerate(endpoint[:-1])
              if item == "input"]
    assert inputs == [()], "Endpoint não deve aceitar parâmetros de cliente"
    stacks = [block(endpoint[i + 1]) for i, item in enumerate(endpoint[:-1])
              if item == "stack"]
    assert len(stacks) == 1
    stack = stacks[0]
    # Exige guarda incondicional no início do stack, não dentro de conditional.
    assert stack[:2] == ('function.run', '"Quick Start/enforce_role"')
    guard = block(stack[2])
    assert fields(block(unique_assignment(guard, "input"))) == {
        "user_id": "$auth.id", "required_role": '"admin"',
    }
    assert stack[3] == "as"
    # Leitura tokenizada de todas as operações, inclusive em blocos aninhados.
    def walk(nodes):
        for item in nodes:
            if isinstance(item, tuple):
                yield from walk(item[1])
            else:
                yield item

    operations = [t for t in walk(stack) if t.startswith("db.")]
    assert operations == ["db.query", "db.query"]
    queries = []
    for index, item in enumerate(stack):
        if item != "db.query":
            continue
        table = stack[index + 1]
        if table.startswith('"'):
            table = json.loads(table)
        body = block(stack[index + 2])
        # Allowlist integral: nenhum where, join, paginação, eval ou lista.
        assert len(body) == 3 and body[:2] == ("return", "=")
        assert fields(block(body[2])) == {"type": '"count"'}
        assert stack[index + 3] == "as"
        queries.append((table, stack[index + 4]))
    assert queries == [("film", "$film_count"), ("exemplar", "$exemplar_count")]
    # Captura única e incondicional após o término das duas consultas.
    captures = [i for i in range(len(stack) - 2)
                if stack[i:i + 2] == ("var", "$generated_timestamp")]
    assert len(captures) == 1
    capture = captures[0]
    assert block(stack[capture + 2]) == ("value", "=", "now")
    assert list(walk(endpoint)).count("now") == 1
    assert all(capture > i + 4 for i, token in enumerate(stack) if token == "db.query")
    generated = [i for i in range(len(stack) - 2)
                 if stack[i:i + 2] == ("var", "$generated_at")]
    assert len(generated) == 1 and generated[0] > capture + 2
    # Compara a expressão tokenizada completa: mesma captura, UTC em ambas
    # as partes, ordem data/T/horário/Z, sem executar formatação Xano.
    expected_format = read_tree(
        'value = ($generated_timestamp|format_timestamp:"Y-m-d":"UTC")'
        ' ~ "T" ~ ($generated_timestamp|format_timestamp:"H:i:s":"UTC") ~ "Z"'
    )
    assert block(stack[generated[0] + 2]) == expected_format
    # Impede reatribuições ou usos adicionais que invalidem a derivação acima.
    flattened = list(walk(endpoint))
    assert flattened.count("$generated_timestamp") == 3
    assert flattened.count("$generated_at") == 2
    assert fields(block(unique_assignment(endpoint, "response"))) == {
        "total_filmes": "$total_filmes",
        "total_exemplares": "$total_exemplares",
        "generated_at": "$generated_at",
    }


class TestDashboardXanoContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ENDPOINT.read_text(encoding="utf-8")

    def test_endpoint_contract(self):
        check_contract(self.source)

    def test_formatting_comments_and_quoted_tables_do_not_change_structure(self):
        source = self.source.replace("db.query film", 'db.query "film"')
        source = source.replace("return =", "/* where = fake { } */ return\n=")
        source = '// auth = "public"; db.query fake { }\n' + source
        check_contract(source)

    def test_rejects_authorization_after_queries(self):
        start = self.source.index('    function.run "Quick Start/enforce_role"')
        end = self.source.index("\n\n", start)
        guard = self.source[start:end]
        source = self.source[:start] + self.source[end:]
        source = source.replace("    var $total_filmes", guard + "\n    var $total_filmes")
        with self.assertRaises(AssertionError):
            check_contract(source)

    def test_rejects_filtered_counts_including_active_only_films(self):
        for table, condition in [("film", '$db.film.status == "active"'),
                                 ("exemplar", "$db.exemplar.id > 1")]:
            with self.subTest(table=table):
                source = self.source.replace(
                    f"db.query {table} {{", f"db.query {table} {{\n where = {condition}",
                )
                with self.assertRaises(AssertionError):
                    check_contract(source)

    def test_rejects_joins_and_list_results(self):
        mutations = [
            self.source.replace("db.query exemplar {", "db.query exemplar {\n join = {}"),
            self.source.replace('type: "count"', 'type: "list"', 1),
        ]
        for source in mutations:
            with self.subTest(source=source), self.assertRaises(AssertionError):
                check_contract(source)

    def test_rejects_missing_auth_member_role_and_client_identity(self):
        for source in [
            self.source.replace('auth = "user"', 'auth = "other"'),
            self.source.replace('required_role: "admin"', 'required_role: "member"'),
            self.source.replace("user_id: $auth.id", "user_id: $input.user_id"),
            self.source.replace("input {\n  }", "input { int user_id text role }"),
        ]:
            with self.subTest(source=source), self.assertRaises(AssertionError):
                check_contract(source)

    def test_rejects_extra_missing_or_duplicate_response_fields(self):
        for source in [
            self.source.replace("total_filmes: $total_filmes", "user_id: $auth.id"),
            self.source.replace("response = {", "response = { extra: 0"),
            self.source.replace("response = {", "response = { total_filmes: 0"),
        ]:
            with self.subTest(source=source), self.assertRaises(AssertionError):
                check_contract(source)

    def assert_rejected_mutation(self, source):
        self.assertNotEqual(source, self.source, "A mutação deve alterar a fonte")
        with self.assertRaises(AssertionError):
            check_contract(source)

    def authorization_call_source(self):
        """Obtém a chamada real para mutações; a validação usa a árvore."""
        start = self.source.index('function.run "Quick Start/enforce_role"')
        end = self.source.index("as $role_check", start) + len("as $role_check")
        call = self.source[start:end]
        self.assertEqual(self.source.count(call), 1)
        return call

    def test_rejects_removed_auth_declaration(self):
        self.assert_rejected_mutation(self.source.replace('auth = "user"', ""))

    def test_rejects_removed_authorization_call(self):
        call = self.authorization_call_source()
        self.assert_rejected_mutation(self.source.replace(call, ""))

    def test_rejects_authorization_inside_skippable_condition(self):
        call = self.authorization_call_source()
        conditional = "conditional { if (false) {\n" + call + "\n} }"
        self.assert_rejected_mutation(self.source.replace(call, conditional))

    def test_rejects_authorization_inside_catch_that_allows_continuation(self):
        call = self.authorization_call_source()
        swallowed = (
            "try_catch { try {\n" + call + "\n} catch {\n"
            "var $ignored_denial { value = true }\n} }"
        )
        # As duas consultas permanecem fora do tratamento, após ele.
        self.assert_rejected_mutation(self.source.replace(call, swallowed))

    def test_rejects_timestamp_capture_before_either_count(self):
        capture = "    var $generated_timestamp { value = now }"
        without_capture = self.source.replace(capture, "")
        for table in ("film", "exemplar"):
            with self.subTest(table=table):
                self.assert_rejected_mutation(without_capture.replace(
                    f"    db.query {table}", capture + f"\n    db.query {table}",
                ))

    def test_rejects_missing_or_multiple_now_captures(self):
        for source in [
            self.source.replace("value = now", "value = 0"),
            self.source.replace("value = now", "value = now|add:now"),
            self.source.replace("var $generated_at {", "var $extra { value = now }\n    var $generated_at {"),
        ]:
            with self.subTest(source=source):
                self.assert_rejected_mutation(source)

    def test_rejects_missing_or_non_utc_date_and_time_formatting(self):
        for fmt in ("Y-m-d", "H:i:s"):
            for replacement in (f'"{fmt}"', f'"{fmt}":"America/Sao_Paulo"'):
                with self.subTest(format=fmt, replacement=replacement):
                    self.assert_rejected_mutation(self.source.replace(
                        f'"{fmt}":"UTC"', replacement,
                    ))

    def test_rejects_changed_timestamp_composition_or_source(self):
        mutations = [
            ('"Y-m-d"', '"d-m-Y"'),
            ('"H:i:s"', '"H:i"'),
            ('~ "T" ~', '~ " " ~'),
            ('~ "Z"', '~ "+00:00"'),
            ('~ "Z"', ''),
            ('$generated_timestamp|format_timestamp', '$other_timestamp|format_timestamp'),
            ('~ "T" ~', '~ "Z" ~'),
            ('generated_at: $generated_at', 'generated_at: $generated_timestamp'),
            ('var $generated_at {', 'var $generated_at { value = "fixed" }\n    var $generated_at {'),
        ]
        for old, new in mutations:
            with self.subTest(old=old, new=new):
                self.assert_rejected_mutation(self.source.replace(old, new))


if __name__ == "__main__":
    unittest.main()
