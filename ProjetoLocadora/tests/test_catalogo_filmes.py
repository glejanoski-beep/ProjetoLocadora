import unittest

from ProjetoLocadora.catalogo_filmes import (
    CLASSIFICACOES,
    centavos_para_reais,
    reais_para_centavos,
    validar_filme,
)


class TestCatalogoFilmesValidation(unittest.TestCase):
    def test_parses_brazilian_and_plain_reais_without_float_rounding(self):
        self.assertEqual(reais_para_centavos("R$ 1.234,56"), 123456)
        self.assertEqual(reais_para_centavos("12.34"), 1234)
        self.assertEqual(reais_para_centavos("0,01"), 1)

    def test_formats_centavos_as_brazilian_reais(self):
        self.assertEqual(centavos_para_reais(123456), "R$ 1.234,56")
        self.assertEqual(centavos_para_reais(0), "R$ 0,00")

    def test_rejects_invalid_currency_values(self):
        for value in ("", "-1,00", "1,234", "1.23,45", "NaN"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                reais_para_centavos(value)

    def test_accepts_valid_catalog_data(self):
        errors, payload = validar_filme(
            titulo="  Filme  ",
            genero="Drama",
            ano_lancamento="1888",
            classificacao=CLASSIFICACOES[0],
            valor_locacao="0,00",
            status="active",
            current_year=2025,
        )
        self.assertEqual(errors, {})
        self.assertEqual(payload["titulo"], "Filme")
        self.assertEqual(payload["valor_locacao_centavos"], 0)
        self.assertEqual(payload["ano_lancamento"], 1888)

    def test_reports_title_genre_year_classification_and_status_errors(self):
        errors, _ = validar_filme(
            titulo=" " * 201,
            genero=" " * 101,
            ano_lancamento="2026",
            classificacao="XX",
            valor_locacao="1,00",
            status="deleted",
            current_year=2025,
        )
        self.assertEqual(
            set(errors),
            {"titulo", "genero", "ano_lancamento", "classificacao", "status"},
        )

    def test_rejects_fractional_or_invalid_year(self):
        for year in ("1887", "2025.0", "not-a-year"):
            with self.subTest(year=year):
                errors, _ = validar_filme(
                    titulo="Filme",
                    genero="Drama",
                    ano_lancamento=year,
                    classificacao="Livre",
                    valor_locacao="1,00",
                    status="active",
                    current_year=2025,
                )
                self.assertIn("ano_lancamento", errors)


if __name__ == "__main__":
    unittest.main()
