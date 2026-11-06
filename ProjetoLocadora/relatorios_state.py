"""Estado da página de relatórios: período, consulta única e descarte por sessão."""

import reflex as rx

from ProjetoLocadora.locacoes import data_brasilia
from ProjetoLocadora.multas import reais
from ProjetoLocadora.multas_client import FineError
from ProjetoLocadora.multas_state import _SessionBound
from ProjetoLocadora.relatorios import (
    METHODS, SHORTCUTS, atalho, hoje_brasilia, intervalo_ms, percentual, ranking, rotulo_periodo, validar_periodo,
)
from ProjetoLocadora.relatorios_client import MESSAGES, ReportError, operational_report

METHOD_LABELS = {"cash": "Dinheiro", "pix": "Pix", "debit_card": "Cartão de débito", "credit_card": "Cartão de crédito"}


class RelatoriosState(_SessionBound, rx.State):
    message: str = ""
    state: str = "idle"  # idle | loading | ready | error | forbidden
    loading: bool = False
    shortcut: str = "30d"
    start_text: str = ""
    end_text: str = ""
    period_label: str = ""
    _revision: int = 0
    _busy: bool = False
    _cooldown_until: float = 0.0
    _report: dict = {}

    def _invalidate(self) -> None:
        self._revision += 1
        self._busy = self.loading = False
        self._cooldown_until = 0.0
        self.message = ""
        self.state = "idle"
        self.shortcut = "30d"
        self.start_text = self.end_text = self.period_label = ""
        self._report = {}

    # ---------- Período ----------

    @rx.var
    def shortcuts(self) -> list[dict[str, str]]:
        return [{"key": key, "label": label} for key, label in SHORTCUTS.items()]

    def _apply_shortcut(self, key: str) -> None:
        inicio, fim = atalho(key, hoje_brasilia())
        self.shortcut = key
        self.start_text, self.end_text = inicio.isoformat(), fim.isoformat()

    @rx.event
    def capture_start(self, value: str):
        if not self._busy:
            self.start_text, self.shortcut = value[:10], ""

    @rx.event
    def capture_end(self, value: str):
        if not self._busy:
            self.end_text, self.shortcut = value[:10], ""

    # ---------- Consulta ----------

    async def _load(self):
        if self._busy or self._cooling_down():
            return
        try:
            inicio, fim = validar_periodo(self.start_text, self.end_text)
        except ValueError as error:
            self.message = str(error)
            return
        from_ms, to_ms = intervalo_ms(inicio, fim)
        self._busy = self.loading = True
        self.state, self.message = "loading", ""
        revision, context = self._revision, None
        yield
        try:
            context = await self._authorize()
            if context is None:
                self.state = "error"
                return
            if context[1][1] != "admin":
                self.state, self._report = "forbidden", {}
                return
            report = await operational_report(context[1][2], from_ms, to_ms)
            if self._current(*context):
                self._report = report
                self.period_label = rotulo_periodo(inicio, fim)
                self.state = "ready"
        except (ReportError, FineError) as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_report_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    async def _show_report_error(self, error) -> None:
        category = error.category
        if category == "authorization":
            # Recusa do backend: papel mudou; a próxima abertura confere de novo.
            from ProjetoLocadora.ProjetoLocadora import State

            (await self.get_state(State))._forget_session_check()
            self.state, self._report = "forbidden", {}
            return
        await self._show_error(error)
        self.state = "error"
        self.message = (
            self.message if category == "ratelimited" else MESSAGES.get(category, MESSAGES["unavailable"])
        )

    @rx.event
    async def open_page(self):
        """Entrada da página: últimos 30 dias, como na spec."""
        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        if session._user_role != "admin":
            self.state, self._report = "forbidden", {}
            return
        if not self._report:
            self._apply_shortcut("30d")
        async for update in self._load():
            yield update

    @rx.event
    async def set_shortcut(self, key: str):
        if key not in SHORTCUTS or self._busy:
            return
        self._apply_shortcut(key)
        async for update in self._load():
            yield update

    @rx.event
    async def generate(self):
        async for update in self._load():
            yield update

    # ---------- Apresentação ----------

    @rx.var
    def has_report(self) -> bool:
        return bool(self._report)

    @rx.var
    def generated_label(self) -> str:
        if not self._report:
            return ""
        return "Gerado em " + data_brasilia(self._report["generated_at"]) + " (horário de Brasília)"

    @rx.var
    def rental_cards(self) -> list[dict[str, str]]:
        if not self._report:
            return []
        r = self._report["rentals"]
        return [
            {"label": "Retiradas", "value": str(r["checkouts"]), "note": "locações iniciadas no período"},
            {"label": "Devoluções", "value": str(r["returns"]), "note": "locações encerradas no período"},
            {
                "label": "Devoluções com atraso",
                "value": str(r["late_returns"]),
                "note": percentual(r["late_returns"], r["returns"]) + " das devoluções",
            },
        ]

    @rx.var
    def finance_cards(self) -> list[dict[str, str]]:
        if not self._report:
            return []
        f, p = self._report["fines"], self._report["payments"]
        return [
            {"label": "Multas geradas", "value": reais(f["generated_cents"]), "note": _plural(f["generated_count"], "multa", "multas")},
            {"label": "Pagamentos recebidos", "value": reais(p["received_cents"]), "note": _plural(p["received_count"], "pagamento", "pagamentos")},
            {"label": "Estornos", "value": reais(p["reversed_cents"]), "note": _plural(p["reversed_count"], "estorno", "estornos")},
            {"label": "Abonos", "value": reais(f["waived_cents"]), "note": _plural(f["waived_count"], "multa abonada", "multas abonadas")},
        ]

    @rx.var
    def method_rows(self) -> list[dict[str, str]]:
        if not self._report:
            return []
        by_method = self._report["payments"]["by_method"]
        return [{"label": METHOD_LABELS[m], "value": reais(by_method[m])} for m in METHODS]

    @rx.var
    def current_cards(self) -> list[dict[str, str]]:
        if not self._report:
            return []
        r, f = self._report["rentals"], self._report["fines"]
        return [
            {"label": "Locações ativas", "value": str(r["active_now"]), "note": "neste momento"},
            {"label": "Vencidas", "value": str(r["overdue_now"]), "note": "ativas com vencimento ultrapassado"},
            {"label": "Multas em aberto", "value": reais(f["open_balance_cents"]), "note": "saldo a receber"},
        ]

    @rx.var
    def film_rows(self) -> list[dict[str, str]]:
        if not self._report:
            return []
        top = ranking(self._report["films"])
        leader = top[0]["rentals"] if top else 1
        return [
            {
                "position": f"{index}º",
                "title": film["film_title"],
                "detail": f"{_plural(film['rentals'], 'locação', 'locações')} · {_plural(film['exemplars'], 'exemplar', 'exemplares')}",
                "width": f"{max(4, round(film['rentals'] * 100 / leader))}%",
            }
            for index, film in enumerate(top, start=1)
        ]


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"
