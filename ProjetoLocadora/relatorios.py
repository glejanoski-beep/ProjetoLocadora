"""Relatórios por período: datas de Brasília, contrato da resposta e ranking.

O backend só compara instantes; a conversão de fuso fica aqui, num único lugar.
"""

from datetime import date, datetime, time, timedelta
from typing import TypedDict

from ProjetoLocadora.locacoes import BRASILIA, data_brasilia

DAY_MS = 24 * 60 * 60 * 1000
MAX_DAYS = 366
TOP_FILMS = 10
SHORTCUTS = {"7d": "Últimos 7 dias", "30d": "Últimos 30 dias", "month": "Este mês", "last_month": "Mês anterior"}
METHODS = ("cash", "pix", "debit_card", "credit_card")


class FilmRank(TypedDict):
    film_id: int
    film_title: str
    rentals: int
    exemplars: int


def intervalo_ms(inicio: date, fim: date) -> tuple[int, int]:
    """[00:00 de `inicio`, 00:00 do dia seguinte a `fim`) em Brasília, como ms UTC."""
    start = datetime.combine(inicio, time(0), tzinfo=BRASILIA)
    end = datetime.combine(fim + timedelta(days=1), time(0), tzinfo=BRASILIA)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def validar_periodo(inicio_texto: str, fim_texto: str) -> tuple[date, date]:
    """Datas `AAAA-MM-DD` inclusivas; início ≤ fim e no máximo 366 dias."""
    try:
        inicio, fim = date.fromisoformat(inicio_texto), date.fromisoformat(fim_texto)
    except (TypeError, ValueError):
        raise ValueError("Informe datas de início e fim válidas.") from None
    if inicio > fim:
        raise ValueError("A data de início deve ser igual ou anterior à data de fim.")
    if (fim - inicio).days + 1 > MAX_DAYS:
        raise ValueError(f"O período pode ter no máximo {MAX_DAYS} dias.")
    return inicio, fim


def atalho(chave: str, hoje: date) -> tuple[date, date]:
    """Períodos prontos, todos terminando hoje (exceto o mês anterior, completo)."""
    if chave == "7d":
        return hoje - timedelta(days=6), hoje
    if chave == "30d":
        return hoje - timedelta(days=29), hoje
    if chave == "month":
        return hoje.replace(day=1), hoje
    if chave == "last_month":
        fim = hoje.replace(day=1) - timedelta(days=1)
        return fim.replace(day=1), fim
    raise ValueError("Atalho de período desconhecido.")


def hoje_brasilia() -> date:
    return datetime.now(BRASILIA).date()


def rotulo_periodo(inicio: date, fim: date) -> str:
    return f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y} (horário de Brasília)"


def _count(value: object) -> bool:
    return type(value) is int and value >= 0


def _block(value: object, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys or not all(_count(value[k]) for k in keys):
        raise ValueError("Relatório inválido")
    return value


def validar_relatorio(value: object, from_ms: int, to_ms: int) -> dict:
    """Contrato de `GET /relatorios/operacional`: inteiros ≥ 0 e somas coerentes."""
    if type(value) is not dict or set(value) != {"from", "to", "generated_at", "rentals", "fines", "payments", "films"}:
        raise ValueError("Relatório inválido")
    if value["from"] != from_ms or value["to"] != to_ms:
        raise ValueError("Relatório inválido")
    if type(value["generated_at"]) is not int or data_brasilia(value["generated_at"]) == "Data indisponível":
        raise ValueError("Relatório inválido")
    rentals = _block(value["rentals"], {"checkouts", "returns", "late_returns", "active_now", "overdue_now"})
    fines = _block(value["fines"], {"generated_count", "generated_cents", "waived_count", "waived_cents", "open_balance_cents"})
    payments = value["payments"]
    if type(payments) is not dict or set(payments) != {"received_cents", "received_count", "by_method", "reversed_count", "reversed_cents"}:
        raise ValueError("Relatório inválido")
    _block({k: v for k, v in payments.items() if k != "by_method"}, {"received_cents", "received_count", "reversed_count", "reversed_cents"})
    by_method = _block(payments["by_method"], set(METHODS))
    if rentals["late_returns"] > rentals["returns"] or rentals["overdue_now"] > rentals["active_now"]:
        raise ValueError("Relatório inválido")
    if sum(by_method.values()) != payments["received_cents"]:
        raise ValueError("Relatório inválido")
    films = value["films"]
    if type(films) is not list:
        raise ValueError("Relatório inválido")
    seen = set()
    for film in films:
        if type(film) is not dict or set(film) != {"film_id", "film_title", "rentals", "exemplars"}:
            raise ValueError("Relatório inválido")
        if type(film["film_id"]) is not int or film["film_id"] < 1 or film["film_id"] in seen:
            raise ValueError("Relatório inválido")
        if not isinstance(film["film_title"], str) or not film["film_title"].strip():
            raise ValueError("Relatório inválido")
        if not _count(film["exemplars"]) or type(film["rentals"]) is not int or film["rentals"] < 1:
            raise ValueError("Relatório inválido")
        seen.add(film["film_id"])
    if sum(film["rentals"] for film in films) > rentals["checkouts"]:
        raise ValueError("Relatório inválido")
    return value


def ranking(films: list[FilmRank], limite: int = TOP_FILMS) -> list[FilmRank]:
    """Mais retiradas primeiro; empate por título, sem diferenciar maiúsculas."""
    return sorted(films, key=lambda f: (-f["rentals"], f["film_title"].casefold()))[:limite]


def percentual(parte: int, total: int) -> str:
    """Percentual inteiro, ou "—" quando não há base (sem divisão por zero)."""
    if total <= 0:
        return "—"
    return f"{round(parte * 100 / total)}%"
