from __future__ import annotations

from typing import TypedDict


class Exemplar(TypedDict):
    id: int
    identificador: str
    filme_id: int
    filme_titulo: str
    # Baixa (editar-e-baixar-exemplares); a listagem antiga é normalizada como ativa.
    baixado: bool
    baixa_tipo: str
    baixa_motivo: str


RETIRE_KINDS = {"lost": "Perdido", "damaged": "Danificado", "discarded": "Descartado", "other": "Outro"}
RETIRE_KIND_BY_LABEL = {label: kind for kind, label in RETIRE_KINDS.items()}


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


def validar_motivo(motivo: str, acao: str) -> str:
    """Motivo obrigatório (até 500 caracteres) para baixa e reativação."""
    clean = motivo.strip()
    if not clean:
        raise ValueError(f"Informe o motivo da {acao}.")
    if len(clean) > 500:
        raise ValueError(f"O motivo da {acao} pode ter no máximo 500 caracteres.")
    return clean


def validar_baixa(*, tipo: str, motivo: str) -> tuple[str, str]:
    if tipo not in RETIRE_KINDS:
        raise ValueError("Selecione o tipo da baixa.")
    return tipo, validar_motivo(motivo, "baixa")


def normalizar_exemplar(value: dict) -> dict:
    """Listagem anterior (sem campos de baixa) é tratada como exemplar ativo."""
    item = dict(value)
    item.setdefault("baixado", False)
    item.setdefault("baixa_tipo", "")
    item.setdefault("baixa_motivo", "")
    if type(item["baixado"]) is not bool or not isinstance(item["baixa_tipo"], str) or not isinstance(item["baixa_motivo"], str):
        raise ValueError("Exemplar inválido")
    if item["baixado"] and item["baixa_tipo"] not in RETIRE_KINDS:
        raise ValueError("Exemplar inválido")
    return item
