import unittest

from ProjetoLocadora.clientes import (
    cpf_valido,
    mascarar_cpf,
    normalizar_cpf,
    normalizar_telefone,
    validar_bloqueio_manual,
    validar_cliente,
)


class TestClientes(unittest.TestCase):
    def test_normaliza_e_mascara_cpf_com_zero_a_esquerda(self):
        self.assertEqual(normalizar_cpf("012.345.678-90"), "01234567890")
        self.assertTrue(cpf_valido("012.345.678-90"))
        self.assertEqual(mascarar_cpf("01234567890"), "***.***.***-90")

    def test_rejeita_cpf_parcial_repetido_invalido_e_com_letras(self):
        for value in ("123.456.789", "111.111.111-11", "123.456.789-00", "abc01234567890"):
            with self.subTest(value=value):
                self.assertFalse(cpf_valido(value))

    def test_valida_cadastro_com_email_normalizado(self):
        errors, payload = validar_cliente(
            nome="  Maria da Silva  ",
            cpf="012.345.678-90",
            email="  MARIA@EXAMPLE.COM ",
            telefone="",
            status="active",
        )
        self.assertEqual(errors, {})
        self.assertEqual(
            payload,
            {
                "nome": "Maria da Silva",
                "cpf": "01234567890",
                "email": "maria@example.com",
                "telefone": None,
                "status": "active",
            },
        )

    def test_valida_cadastro_com_telefone(self):
        errors, payload = validar_cliente(
            nome="João Souza",
            cpf="52998224725",
            email="",
            telefone="(41) 99999-1234",
            status="inactive",
        )
        self.assertEqual(errors, {})
        self.assertEqual(payload["telefone"], "41999991234")
        self.assertEqual(normalizar_telefone("41 3333-4444"), "4133334444")

    def test_rejeita_nome_cpf_email_telefone_status_e_ausencia_de_contato(self):
        errors, _ = validar_cliente(
            nome=" ",
            cpf="11111111111",
            email="inválido",
            telefone="123",
            status="blocked",
        )
        self.assertEqual(
            set(errors),
            {"nome", "cpf", "email", "telefone", "status"},
        )

        errors, _ = validar_cliente(
            nome="Cliente sem contato",
            cpf="52998224725",
            email="",
            telefone="",
        )
        self.assertEqual(errors, {"contato": "Informe ao menos um contato: e-mail ou telefone."})

    def test_bloqueio_exige_motivo_e_desbloqueio_limpa_motivo(self):
        errors, _ = validar_bloqueio_manual(bloqueado=True, motivo="  ")
        self.assertIn("motivo", errors)

        errors, payload = validar_bloqueio_manual(
            bloqueado=True, motivo="  Documento em análise  "
        )
        self.assertEqual(errors, {})
        self.assertEqual(payload["motivo"], "Documento em análise")

        errors, payload = validar_bloqueio_manual(
            bloqueado=False, motivo="não deve ser enviado"
        )
        self.assertEqual(errors, {})
        self.assertIsNone(payload["motivo"])


if __name__ == "__main__":
    unittest.main()
