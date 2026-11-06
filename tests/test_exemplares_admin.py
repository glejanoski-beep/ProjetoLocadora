"""Edição, baixa e reativação de exemplares (editar-e-baixar-exemplares).

HTTP simulado localmente e contratos estáticos; NÃO consulta nem grava no Xano.
"""

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from ProjetoLocadora import xano_client
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.exemplares import normalizar_exemplar, validar_baixa, validar_motivo
from ProjetoLocadora.xano_client import XanoExemplarError
from tests.test_locacoes_xano_contract import ROOT, body, calls, flatten, predicate_exists, unique_assignment

ACTIVE = {"id": 8, "identificador": "A-01", "filme_id": 42, "filme_titulo": "Filme de teste", "baixado": False, "baixa_tipo": "", "baixa_motivo": ""}
OTHER = {**ACTIVE, "id": 9, "identificador": "A-02"}
RETIRED = {**ACTIVE, "id": 10, "identificador": "A-03", "baixado": True, "baixa_tipo": "lost", "baixa_motivo": "Cliente perdeu"}
FILM = {"id": 42, "titulo": "Filme de teste", "genero": "Drama", "ano_lancamento": 2020, "classificacao": "Livre", "valor_locacao_centavos": 1000, "status": "active"}


def admin_state(role: str = "admin") -> State:
    state = State(_reflex_internal_init=True)
    state._xano_auth_token = "private-token"
    state._user_id = "1"
    state._user_role = role
    state.exemplares = [ACTIVE, OTHER, RETIRED]
    state.exemplar_films = [FILM]
    return state


class TestExemplarRules(unittest.TestCase):
    def test_old_listing_is_normalized_as_active(self):
        old = {k: ACTIVE[k] for k in ("id", "identificador", "filme_id", "filme_titulo")}
        self.assertEqual(normalizar_exemplar(old), ACTIVE)
        self.assertEqual(normalizar_exemplar(RETIRED), RETIRED)
        for bad in ({**RETIRED, "baixa_tipo": "stolen"}, {**ACTIVE, "baixado": "false"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalizar_exemplar(bad)

    def test_retire_and_reactivation_require_kind_and_reason(self):
        self.assertEqual(validar_baixa(tipo="damaged", motivo="  Disco riscado "), ("damaged", "Disco riscado"))
        for tipo, motivo in (("", "x"), ("stolen", "x"), ("lost", "   "), ("lost", "x" * 501)):
            with self.subTest(tipo=tipo, motivo=len(motivo)), self.assertRaises(ValueError):
                validar_baixa(tipo=tipo, motivo=motivo)
        with self.assertRaises(ValueError):
            validar_motivo("", "reativação")


class TestExemplarListing(unittest.TestCase):
    def test_retired_hidden_by_default_and_never_counted(self):
        state = admin_state()
        group = next(g for g in state.exemplar_groups if g["filme_id"] == 42)
        self.assertEqual([e["identificador"] for e in group["exemplares"]], ["A-01", "A-02"])
        self.assertEqual(group["count"], 2)
        self.assertTrue(state.exemplar_summary.startswith("2 exemplares"))
        self.assertEqual(state.exemplar_retired_count, 1)
        state.toggle_exemplar_show_retired(True)
        group = next(g for g in state.exemplar_groups if g["filme_id"] == 42)
        self.assertEqual(len(group["exemplares"]), 3)
        self.assertEqual(group["count"], 2)


class TestExemplarAdminState(unittest.IsolatedAsyncioTestCase):
    async def test_member_cannot_open_the_dialog(self):
        state = admin_state("member")
        state.open_exemplar_admin(8)
        self.assertFalse(state.exemplar_admin_open)

    async def test_edit_prefills_and_replaces_with_backend_result(self):
        state = admin_state()
        state.open_exemplar_admin(8)
        self.assertEqual((state.exemplar_edit_identifier, state.exemplar_edit_film_selection), ("A-01", "42 | Filme de teste"))
        state.capture_exemplar_edit_identifier("A-01b")
        updated = {**ACTIVE, "identificador": "A-01b"}
        with patch("ProjetoLocadora.ProjetoLocadora.update_exemplar_xano", new=AsyncMock(return_value=updated)) as api:
            await state.submit_exemplar_edit()
        api.assert_awaited_once_with("private-token", 8, {"identificador": "A-01b", "filme_id": 42})
        self.assertEqual(state.exemplares[0]["identificador"], "A-01b")
        self.assertFalse(state.exemplar_admin_open)
        self.assertEqual(state.exemplares_success, "Exemplar atualizado.")

    async def test_backend_refusal_keeps_dialog_open_with_message(self):
        state = admin_state()
        state.open_exemplar_admin(8)
        message = "Exemplar com locações registradas não pode trocar de filme."
        with patch("ProjetoLocadora.ProjetoLocadora.update_exemplar_xano", new=AsyncMock(side_effect=XanoExemplarError(message))):
            await state.submit_exemplar_edit()
        self.assertTrue(state.exemplar_admin_open)
        self.assertEqual(state.exemplar_admin_error, message)

    async def test_retire_requires_confirmation_then_hides_the_copy(self):
        state = admin_state()
        state.open_exemplar_admin(8)
        state.ask_exemplar_retire()
        self.assertIn("tipo", state.exemplar_admin_error)
        self.assertFalse(state.exemplar_retire_confirming)
        state.capture_exemplar_retire_kind("Danificado")
        state.capture_exemplar_admin_reason("Disco quebrado")
        state.ask_exemplar_retire()
        self.assertTrue(state.exemplar_retire_confirming)
        retired = {**ACTIVE, "baixado": True, "baixa_tipo": "damaged", "baixa_motivo": "Disco quebrado"}
        with patch("ProjetoLocadora.ProjetoLocadora.retire_exemplar_xano", new=AsyncMock(return_value=retired)) as api:
            await state.submit_exemplar_retire()
        api.assert_awaited_once_with("private-token", 8, "damaged", "Disco quebrado")
        self.assertEqual(state.exemplares_success, "Baixa registrada.")
        group = next(g for g in state.exemplar_groups if g["filme_id"] == 42)
        self.assertEqual([e["identificador"] for e in group["exemplares"]], ["A-02"])

    async def test_reactivation_of_retired_copy(self):
        state = admin_state()
        state.open_exemplar_admin(10)
        self.assertEqual(state.exemplar_admin_item["baixa_tipo"], "Perdido")
        state.capture_exemplar_admin_reason("Encontrado na prateleira")
        with patch("ProjetoLocadora.ProjetoLocadora.reactivate_exemplar_xano", new=AsyncMock(return_value={**RETIRED, "baixado": False, "baixa_tipo": "", "baixa_motivo": ""})) as api:
            await state.submit_exemplar_reactivate()
        api.assert_awaited_once_with("private-token", 10, "Encontrado na prateleira")
        self.assertIn("Confira a condição", state.exemplares_success)
        self.assertEqual(state.exemplar_retired_count, 0)


class TestExemplarAdminTransport(unittest.IsolatedAsyncioTestCase):
    async def test_retire_posts_kind_and_reason(self):
        retired = {**ACTIVE, "baixado": True, "baixa_tipo": "lost", "baixa_motivo": "Perdido"}
        with patch("ProjetoLocadora.xano_client._exemplar_request", return_value=httpx.Response(200, json={"exemplar": retired, "audit_succeeded": True})) as request:
            result = await xano_client.retire_exemplar_xano("tok", 8, "lost", "Perdido")
        self.assertEqual(result, retired)
        self.assertEqual(request.call_args.args, ("POST", "/8/baixa", "tok"))
        self.assertEqual(request.call_args.kwargs, {"json_body": {"retire_kind": "lost", "reason": "Perdido"}})

    async def test_edit_and_reactivation_paths(self):
        response = httpx.Response(200, json={"exemplar": ACTIVE, "audit_succeeded": True})
        with patch("ProjetoLocadora.xano_client._exemplar_request", return_value=response) as request:
            await xano_client.update_exemplar_xano("tok", 8, {"identificador": "A-01", "filme_id": 42})
            self.assertEqual(request.call_args.args, ("PATCH", "/8", "tok"))
        with patch("ProjetoLocadora.xano_client._exemplar_request", return_value=httpx.Response(200, json={"exemplar": ACTIVE, "audit_succeeded": True})) as request:
            await xano_client.reactivate_exemplar_xano("tok", 8, "Encontrado")
            self.assertEqual(request.call_args.args, ("POST", "/8/reativacao", "tok"))

    async def test_business_messages_are_shown_as_returned(self):
        for message in ("Exemplar alugado: registre a devolução antes da baixa.",
                        "Exemplar com locações registradas não pode trocar de filme.",
                        "Já existe um exemplar com este identificador."):
            with self.subTest(message=message), patch(
                "ProjetoLocadora.xano_client._exemplar_request",
                return_value=httpx.Response(400, json={"message": message}),
            ), self.assertRaises(XanoExemplarError) as error:
                await xano_client.update_exemplar_xano("tok", 8, {"identificador": "A", "filme_id": 42})
            self.assertEqual(error.exception.user_message, message)

    async def test_invalid_write_response_is_not_success(self):
        with patch("ProjetoLocadora.xano_client._exemplar_request", return_value=httpx.Response(200, json={"exemplar": {"id": 8}, "audit_succeeded": True})), self.assertRaises(XanoExemplarError):
            await xano_client.retire_exemplar_xano("tok", 8, "lost", "x")


def stack_of(relative: str):
    source = (ROOT / relative).read_text(encoding="utf-8")
    return source, next(calls(body(source), "stack"))[1]


class TestExemplarXanoContract(unittest.TestCase):
    WRITES = ("api/exemplares/exemplares_id_PATCH.xs", "api/exemplares/exemplares_id_baixa_POST.xs", "api/exemplares/exemplares_id_reativacao_POST.xs")

    def test_admin_first_and_exemplar_locked_without_deletes(self):
        for path in self.WRITES:
            with self.subTest(path=path):
                source, stack = stack_of(path)
                self.assertEqual(stack[:2], ("function.run", '"Quick Start/enforce_role"'))
                self.assertIn('"admin"', list(flatten(stack[2][1])))
                transaction = next(calls(stack, "db.transaction"))[1]
                locks = [(args, op) for args, op in calls(transaction, "db.get") if args in (("user",), ("exemplar",))]
                self.assertEqual([args for args, _ in locks], [("user",), ("exemplar",)])
                for _, op in locks:
                    self.assertEqual(unique_assignment(op, "lock"), "true")
                self.assertEqual(list(calls(stack, "db.del")), [])
                self.assertEqual(list(calls(stack, "db.add")), [])

    def test_retire_refuses_rented_copy_and_marks_unavailable(self):
        source, stack = stack_of("api/exemplares/exemplares_id_baixa_POST.xs")
        self.assertTrue(predicate_exists(stack, "$occupied == false"))
        self.assertIn('operational_condition: "unavailable"', source)

    def test_edit_refuses_film_change_with_history(self):
        source, stack = stack_of("api/exemplares/exemplares_id_PATCH.xs")
        self.assertTrue(predicate_exists(stack, "$has_history == false"))
        self.assertTrue(predicate_exists(stack, "$duplicate_count == 0"))

    def test_reactivation_requires_new_check_and_condition_refuses_retired(self):
        source, _ = stack_of("api/exemplares/exemplares_id_reativacao_POST.xs")
        self.assertIn('operational_condition: "unverified"', source)
        _, stack = stack_of("api/locacoes/locacoes_exemplares_condicao_PATCH.xs")
        self.assertTrue(predicate_exists(stack, "$exemplar.retired_at == null"))


if __name__ == "__main__":
    unittest.main()
