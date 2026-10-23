from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "xano" / "xano" / "table" / "exemplar.xs"
API_DIR = ROOT / "xano" / "xano" / "api" / "exemplares"


class TestExemplaresXanoContract(unittest.TestCase):
    def test_table_has_only_identity_and_film_reference_with_unique_index(self):
        source = TABLE.read_text(encoding="utf-8")

        self.assertIn("text identificador", source)
        self.assertIn('int filme_id {\n      table = "film"', source)
        self.assertIn(
            '{type: "btree|unique", field: [{name: "identificador", op: "asc"}]}',
            source,
        )
        self.assertNotIn("status", source)
        self.assertNotIn("estoque", source)
        self.assertNotIn("disponibilidade", source)
        self.assertNotIn("localizacao", source)

    def test_creation_checks_role_and_film_before_persisting(self):
        source = (API_DIR / "exemplares_POST.xs").read_text(encoding="utf-8")
        role_check = source.index('required_role: "admin"')
        film_lookup = source.index("db.get film")
        film_guard = source.index('error = "Filme não encontrado."')
        unique_index_check = source.index("db.query exemplar")
        insert = source.index("db.add exemplar")

        self.assertLess(role_check, film_lookup)
        self.assertLess(film_lookup, film_guard)
        self.assertLess(film_guard, unique_index_check)
        self.assertLess(unique_index_check, insert)
        self.assertIn("$input.identificador", source)
        self.assertNotIn("filters=trim", source)
        self.assertIn('return = {type: "count"}', source)
        self.assertIn("$duplicate_count == 0", source)
        self.assertIn("Já existe um exemplar com este identificador.", source)

    def test_listing_checks_member_and_resolves_the_associated_film(self):
        source = (API_DIR / "exemplares_GET.xs").read_text(encoding="utf-8")

        self.assertIn('required_role: "member"', source)
        self.assertIn("db.query exemplar", source)
        self.assertIn("db.get film", source)
        # Filme removido fora do app não derruba a listagem: mantém o id do exemplar
        # e usa o título real quando o filme existe.
        self.assertIn('set:"filme_id":$exemplar.filme_id', source)
        self.assertIn('set:"filme_titulo":$film_title', source)
        self.assertIn('"Filme removido (#" ~ $exemplar.filme_id ~ ")"', source)
        self.assertIn("var.update $film_title { value = $film.titulo }", source)
        self.assertIn("response = $items", source)

    def test_create_audits_only_resource_metadata_and_returns_partial_status(self):
        source = (API_DIR / "exemplares_POST.xs").read_text(encoding="utf-8")

        audit = source[source.index('function.run "Quick Start/log_event"') :]
        self.assertIn('action: "create_exemplar"', audit)
        self.assertIn('result: "success"', audit)
        self.assertIn('resource_type: "exemplar"', audit)
        self.assertIn("resource_id: $created.id", audit)
        self.assertNotIn("identificador:", audit)
        self.assertNotIn("filme_titulo:", audit)
        self.assertIn("var.update $audit_succeeded { value = false }", source)
        self.assertIn(
            "response = {exemplar: $exemplar, audit_succeeded: $audit_succeeded}",
            source,
        )


if __name__ == "__main__":
    unittest.main()
