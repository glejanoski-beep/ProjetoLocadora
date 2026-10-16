import unittest

from ProjetoLocadora.exemplares import validar_exemplar


class TestExemplarValidation(unittest.TestCase):
    def test_accepts_literal_identifier_without_normalizing_it(self):
        errors, payload = validar_exemplar(
            identificador="  A-01 ",
            filme_id=42,
        )

        self.assertEqual(errors, {})
        self.assertEqual(
            payload,
            {"identificador": "  A-01 ", "filme_id": 42},
        )

    def test_requires_identifier_and_existing_film_selection(self):
        errors, _ = validar_exemplar(identificador="", filme_id=None)

        self.assertEqual(set(errors), {"identificador", "filme_id"})

    def test_rejects_non_positive_film_id(self):
        errors, _ = validar_exemplar(identificador="A-01", filme_id=0)

        self.assertIn("filme_id", errors)


if __name__ == "__main__":
    unittest.main()
