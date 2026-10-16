from __future__ import annotations

from typing import TypedDict


class Exemplar(TypedDict):
    id: int
    identificador: str
    filme_id: int
    filme_titulo: str


class ExemplarCadastro(TypedDict):
    identificador: str
    filme_id: int


def validar_exemplar(
    *,
    identificador: str,
    filme_id: int | None,
) -> tuple[dict[str, str], ExemplarCadastro]:
    errors: dict[str, str] = {}

    if identificador == "":
        errors["identificador"] = "Informe o identificador do exemplar."
    if filme_id is None or filme_id < 1:
        errors["filme_id"] = "Selecione um filme cadastrado."

    return errors, {
        "identificador": identificador,
        "filme_id": filme_id if filme_id is not None and filme_id > 0 else 0,
    }
