from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict


CLASSIFICACOES = ("Livre", "10 anos", "12 anos", "14 anos", "16 anos", "18 anos")
STATUS_FILME = ("active", "inactive")


class Filme(TypedDict):
    id: int
    titulo: str
    genero: str
    ano_lancamento: int
    classificacao: str
    valor_locacao_centavos: int
    status: str


class FilmeCatalogo(TypedDict):
    id: int
    titulo: str
    genero: str
    ano_lancamento: int
    classificacao: str
    valor_locacao_centavos: int
    valor_locacao_display: str
    status: str


def reais_para_centavos(value: str) -> int:
    amount = value.strip().replace("R$", "").strip()
    if not amount:
        raise ValueError("Informe o valor da locação.")

    if "," in amount:
        if "." in amount and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{1,2}", amount):
            raise ValueError("Informe um valor em reais válido, com até duas casas decimais.")
        amount = amount.replace(".", "").replace(",", ".")
    elif not re.fullmatch(r"\d+(?:\.\d{1,2})?", amount):
        raise ValueError("Informe um valor em reais válido, com até duas casas decimais.")

    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation as err:
        raise ValueError("Informe um valor em reais válido, com até duas casas decimais.") from err

    if not decimal_amount.is_finite() or decimal_amount < 0:
        raise ValueError("O valor da locação não pode ser negativo.")

    centavos = decimal_amount * 100
    if centavos != centavos.to_integral_value():
        raise ValueError("Informe no máximo duas casas decimais.")
    return int(centavos)


def centavos_para_reais(value: int) -> str:
    reais, centavos = divmod(value, 100)
    reais_formatados = f"{reais:,}".replace(",", ".")
    return f"R$ {reais_formatados},{centavos:02d}"


def validar_filme(
    *,
    titulo: str,
    genero: str,
    ano_lancamento: str,
    classificacao: str,
    valor_locacao: str,
    status: str,
    current_year: int | None = None,
) -> tuple[dict[str, str], dict[str, str | int]]:
    errors: dict[str, str] = {}
    clean_title = titulo.strip()
    clean_genre = genero.strip()

    if not clean_title:
        errors["titulo"] = "Informe o título."
    elif len(clean_title) > 200:
        errors["titulo"] = "O título deve ter no máximo 200 caracteres."

    if not clean_genre:
        errors["genero"] = "Informe o gênero."
    elif len(clean_genre) > 100:
        errors["genero"] = "O gênero deve ter no máximo 100 caracteres."

    try:
        year = int(ano_lancamento.strip())
        max_year = current_year if current_year is not None else datetime.now().year
        if str(year) != ano_lancamento.strip() or not 1888 <= year <= max_year:
            raise ValueError
    except ValueError:
        errors["ano_lancamento"] = "Informe um ano entre 1888 e o ano atual."
        year = 0

    if classificacao not in CLASSIFICACOES:
        errors["classificacao"] = "Selecione uma classificação indicativa válida."

    try:
        rent_centavos = reais_para_centavos(valor_locacao)
    except ValueError as err:
        errors["valor_locacao"] = str(err)
        rent_centavos = 0

    if status not in STATUS_FILME:
        errors["status"] = "Selecione um status válido."

    return errors, {
        "titulo": clean_title,
        "genero": clean_genre,
        "ano_lancamento": year,
        "classificacao": classificacao,
        "valor_locacao_centavos": rent_centavos,
        "status": status,
    }
