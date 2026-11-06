"""Estados de multas, pagamentos e histórico financeiro do cliente.

Isolados pela revisão privada da sessão, como em locações: respostas que chegam
depois de logout, troca de conta ou perda de autorização são descartadas.
"""

import math
import re
import time
from typing import Any
from uuid import uuid4

import reflex as rx

from ProjetoLocadora.config import rental_writes_enabled
from ProjetoLocadora.locacoes import data_brasilia
from ProjetoLocadora.locacoes_client import RentalError, list_rentals
from ProjetoLocadora.multas import (
    FINE_STATUS, PAYMENT_METHODS, PAYMENT_STATUS, Fine, centavos, dias, reais, saldo,
)
from ProjetoLocadora.multas_client import (
    MESSAGES, FineError, get_fine, list_fines, list_payments, pay_fine, reverse_payment, waive_fine,
)
from ProjetoLocadora.xano_client import XanoSessionUnavailable, get_me_xano, is_authorized_employee

PAGE_SIZE = 10
FINE_NUMBER = re.compile(r"[1-9][0-9]{0,9}")
TABS = {"open": "Em aberto", "paid": "Quitadas", "waived": "Abonadas", "all": "Todas"}
EMPTY = {
    "open": "Nenhuma multa em aberto.", "paid": "Nenhuma multa quitada.",
    "waived": "Nenhuma multa abonada.", "all": "Nenhuma multa registrada.",
}
METHOD_BY_LABEL = {label: key for key, label in PAYMENT_METHODS.items()}


def _fine_label(fine: Fine) -> str:
    if fine["status"] == "open" and fine["paid_cents"] > 0:
        return "Parcial"
    return FINE_STATUS[fine["status"]]


def fine_row(fine: Fine) -> dict[str, str]:
    return {
        "number": f"#{fine['id']}",
        "href": f"/multas/{fine['id']}",
        "customer": fine["customer_name"],
        "film": fine["film_title"],
        "exemplar": fine["exemplar_identifier"],
        "returned_at": data_brasilia(fine["returned_at"]),
        "days": dias(fine["late_days"]),
        "amount": reais(fine["amount_cents"]),
        "paid": reais(fine["paid_cents"]),
        "balance": reais(saldo(fine)),
        "status": _fine_label(fine),
        "status_key": "partial" if _fine_label(fine) == "Parcial" else fine["status"],
    }


def payment_row(payment: dict) -> dict[str, str]:
    return {
        "id": str(payment["id"]),
        "amount": reais(payment["amount_cents"]),
        "method": PAYMENT_METHODS[payment["method"]],
        "paid_at": data_brasilia(payment["paid_at"]),
        "registered_by": str(payment["registered_by"]),
        "status": PAYMENT_STATUS[payment["status"]],
        "reversed": "1" if payment["status"] == "reversed" else "",
        "reversal": (
            f"Estornado em {data_brasilia(payment['reversed_at'])} pelo funcionário nº {payment['reversed_by']}: {payment['reversal_reason']}"
            if payment["status"] == "reversed" else ""
        ),
        "fine_href": f"/multas/{payment['fine_id']}",
        "fine_number": f"#{payment['fine_id']}",
    }


class _SessionBound:
    """Conferência de sessão compartilhada pelos estados desta página (mixin sem estado)."""

    def _snapshot(self, session):
        return (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)

    def _current(self, session, snapshot, revision):
        return revision == self._revision and snapshot == self._snapshot(session)

    async def _authorize(self, fresh: bool = False):
        """Leituras podem reaproveitar um auth/me recente; escritas sempre conferem agora."""
        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        snapshot, revision = self._snapshot(session), self._revision
        if not snapshot[0] or not snapshot[2]:
            raise FineError("authentication")
        if not fresh and session._recently_verified():
            return session, snapshot, revision
        try:
            me = await get_me_xano(snapshot[2])
        except XanoSessionUnavailable as error:
            if error.retry_after:
                raise FineError("ratelimited", retry_after=error.retry_after) from None
            raise FineError("unavailable") from None
        if not self._current(session, snapshot, revision):
            return None
        if not me or not is_authorized_employee(me) or str(me.get("id", "")) != snapshot[0]:
            session._clear_session()
            await session._sync_dashboard_session()
            self.message = MESSAGES["authentication"]
            return None
        if me.get("role") != snapshot[1]:
            session._set_user(me)
            await session._sync_dashboard_session()
            self.message = "A permissão da conta mudou. Abra novamente a página."
            return None
        session._mark_session_verified()
        return session, snapshot, revision

    def _cooling_down(self) -> bool:
        remaining = self._cooldown_until - time.monotonic()
        if remaining <= 0:
            return False
        self.message = f"Limite de requisições do Xano: aguarde mais {math.ceil(remaining)} s antes de tentar novamente."
        return True

    async def _show_error(self, error: FineError | RentalError):
        if error.category == "ratelimited":
            wait = error.retry_after or 20
            self._cooldown_until = time.monotonic() + wait
            self.message = f"O Xano atingiu o limite de requisições do plano (10 a cada 20 s). Aguarde {wait} s e use “Tentar novamente”."
            return
        if error.category in {"authentication", "authorization"}:
            from ProjetoLocadora.ProjetoLocadora import State

            session = await self.get_state(State)
            if error.category == "authentication":
                session._clear_session()
                await session._sync_dashboard_session()
            else:
                session._forget_session_check()
        detail = getattr(error, "detail", "")
        self.message = detail or MESSAGES.get(error.category, str(error))


class MultasState(_SessionBound, rx.State):
    message: str = ""
    notice: str = ""
    loading: bool = False
    _revision: int = 0
    _busy: bool = False
    _cooldown_until: float = 0.0
    writes_blocked: bool = False
    # Lista
    tab: str = "open"
    list_state: str = "idle"
    _items: list[dict] = []
    _page: int = 1
    _total: int = 0
    # Detalhe
    detail_state: str = "idle"
    detail_id: str = ""
    _fine: dict = {}
    _payments: list[dict] = []
    # Pagamento
    amount_text: str = ""
    method: str = "cash"
    pay_confirming: bool = False
    _pay_pending: dict = {}
    # Ajustes administrativos
    admin_action: str = ""
    admin_target: int = 0
    admin_reason: str = ""
    _admin_pending: dict = {}

    def _invalidate(self) -> None:
        self._revision += 1
        self._busy = self.loading = False
        self._cooldown_until = 0.0
        self.message = self.notice = ""
        self.writes_blocked = False
        self.tab, self.list_state = "open", "idle"
        self._items, self._page, self._total = [], 1, 0
        self.detail_state, self.detail_id = "idle", ""
        self._fine, self._payments = {}, []
        self._reset_forms()

    def _reset_forms(self) -> None:
        self.amount_text = ""
        self.method = "cash"
        self.pay_confirming = False
        self._pay_pending = {}
        self.admin_action = ""
        self.admin_target = 0
        self.admin_reason = ""
        self._admin_pending = {}

    # ---------- Lista ----------

    @rx.var
    def rows(self) -> list[dict[str, str]]:
        return [fine_row(item) for item in self._items]

    @rx.var
    def tabs(self) -> list[dict[str, str]]:
        return [{"key": key, "label": label} for key, label in TABS.items()]

    @rx.var
    def empty_text(self) -> str:
        return EMPTY.get(self.tab, "")

    @rx.var
    def paging(self) -> str:
        if not self._total:
            return ""
        first = (self._page - 1) * PAGE_SIZE + 1
        return f"{first}–{min(self._page * PAGE_SIZE, self._total)} de {self._total}"

    @rx.var
    def has_previous(self) -> bool:
        return self._page > 1

    @rx.var
    def has_next(self) -> bool:
        return self._page * PAGE_SIZE < self._total

    @rx.event
    async def load_list(self):
        if self._busy or self._cooling_down():
            if self.list_state in ("idle", "loading"):
                self.list_state = "error"
            return
        self._busy = self.loading = True
        self.list_state = "loading"
        revision, context = self._revision, None
        yield
        try:
            context = await self._authorize()
            if context is None:
                self.list_state = "error"
                return
            status = "" if self.tab == "all" else self.tab
            page = await list_fines(context[1][2], self._page, PAGE_SIZE, status=status)
            if self._current(*context):
                self._items, self._total = page["items"], page["total"]
                self.list_state = "ready" if page["items"] else "empty"
        except FineError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
                self.list_state = "error"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def open_list(self):
        self.message = self.notice = ""
        self._page = 1
        async for update in self.load_list():
            yield update

    @rx.event
    async def set_tab(self, tab: str):
        if tab not in TABS or self._busy:
            return
        self.tab, self._page = tab, 1
        async for update in self.load_list():
            yield update

    @rx.event
    async def change_page(self, direction: int):
        target = self._page + direction
        if self._busy or target < 1 or (direction > 0 and not self.has_next):
            return
        self._page = target
        async for update in self.load_list():
            yield update

    # ---------- Detalhe ----------

    @rx.var
    def has_fine(self) -> bool:
        return bool(self._fine)

    @rx.var
    def fine_view(self) -> dict[str, str]:
        fine = self._fine
        if not fine:
            return {}
        view = fine_row(fine)
        view.update({
            "title": f"Multa #{fine['id']}",
            "rental_href": f"/locacoes/{fine['rental_id']}",
            "rental": f"Locação #{fine['rental_id']}",
            "customer_href": f"/clientes/{fine['customer_id']}",
            "due_at": data_brasilia(fine["due_at"]),
            "waived": reais(fine["waived_cents"]),
            "policy": (
                f"{dias(fine['late_days'])} × {reais(fine['daily_cents'])} por dia, "
                f"tolerância de {fine['grace_minutes']} min, teto de {reais(fine['cap_cents'])}"
            ),
            "created_by": str(fine["created_by"]),
            "waive_note": (
                f"Saldo de {reais(fine['waived_cents'])} abonado em {data_brasilia(fine['waived_at'])} "
                f"pelo funcionário nº {fine['waived_by']}: {fine['waive_reason']}"
                if fine["status"] == "waived" else ""
            ),
        })
        return view

    @rx.var
    def payment_rows(self) -> list[dict[str, str]]:
        return [payment_row(item) for item in self._payments]

    @rx.var
    def is_open(self) -> bool:
        return bool(self._fine) and self._fine["status"] == "open"

    @rx.var
    def can_reverse(self) -> bool:
        return bool(self._fine) and self._fine["status"] != "waived"

    @rx.var
    def method_options(self) -> list[str]:
        return list(PAYMENT_METHODS.values())

    @rx.var
    def method_label(self) -> str:
        return PAYMENT_METHODS.get(self.method, "")

    def _route_fine_id(self) -> str:
        return str(self.router.page.params.get("fine_id", "")).strip()

    @rx.event
    async def load_detail(self):
        if self._busy:
            return
        raw = self._route_fine_id()
        self.detail_id = raw[:20]
        if not self._pay_pending and not self._admin_pending:
            self._fine, self._payments = {}, []
            self._reset_forms()
        self.message = ""
        if not FINE_NUMBER.fullmatch(raw):
            self.detail_state = "invalid"
            self.message = "Número de multa inválido."
            return
        if self._cooling_down():
            self.detail_state = "error"
            return
        self.detail_state = "loading"
        self._busy = self.loading = True
        revision, context = self._revision, None
        yield
        try:
            context = await self._authorize()
            if context is None:
                self.detail_state = "error"
                return
            fine, payments = await get_fine(context[1][2], int(raw))
            if self._current(*context):
                self._fine, self._payments = fine, payments
                self.detail_state = "ready"
                self.writes_blocked = not rental_writes_enabled()
                if not self.amount_text and fine["status"] == "open":
                    self.amount_text = reais(saldo(fine)).replace("R$ ", "")
                if self._pay_pending and any(p["status"] == "confirmed" and p["amount_cents"] == self._pay_pending["amount_cents"] for p in payments):
                    self.notice = "Confira a lista: um pagamento com esse valor consta no registro. Repita a mesma tentativa só se ele não for o seu."
        except FineError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "notfound":
                    self.detail_state = "notfound"
                    self.message = f"A multa nº {raw} não foi encontrada."
                else:
                    await self._show_error(error)
                    self.detail_state = "error"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    # ---------- Pagamento ----------

    @rx.event
    def capture_amount(self, value: str):
        if not self._busy and not self._pay_pending:
            self.amount_text = value[:20]

    @rx.event
    def capture_method(self, value: str):
        if not self._busy and not self._pay_pending:
            self.method = METHOD_BY_LABEL.get(value, value if value in PAYMENT_METHODS else self.method)

    def _amount_issue(self) -> str:
        if not self._fine:
            return "Multa não carregada."
        cents = centavos(self.amount_text)
        if cents is None or cents <= 0:
            return "Informe um valor positivo, como 9,00."
        if cents > saldo(self._fine):
            return f"O valor não pode passar do saldo ({reais(saldo(self._fine))})."
        return ""

    @rx.var
    def amount_issue(self) -> str:
        return self._amount_issue() if self.amount_text else ""

    @rx.var
    def pay_pending(self) -> bool:
        return bool(self._pay_pending)

    @rx.var
    def can_pay(self) -> bool:
        return self.is_open and rental_writes_enabled() and not self._busy and not self._pay_pending and not self._amount_issue()

    @rx.var
    def pay_summary(self) -> str:
        cents = centavos(self.amount_text)
        if cents is None or not self._fine:
            return ""
        return f"Registrar pagamento de {reais(cents)} em {PAYMENT_METHODS.get(self.method, '')} para a multa #{self._fine['id']}?"

    @rx.event
    def ask_pay(self):
        if self.can_pay:
            self.pay_confirming = True
            self.message = self.notice = ""

    @rx.event
    def cancel_pay(self):
        if not self._busy:
            self.pay_confirming = False

    async def _send_pay(self, repeat: bool = False):
        if self._busy:
            return
        if repeat and not self._pay_pending:
            return
        # Novo pagamento só a partir da confirmação explícita; ela some após o sucesso.
        if not repeat and (not self.pay_confirming or self._pay_pending or self._amount_issue() or not self.is_open):
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
        revision, context = self._revision, None
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                return
            if not rental_writes_enabled():
                raise FineError("disabled")
            if not repeat:
                self._pay_pending = {
                    "fine_id": self._fine["id"], "amount_cents": centavos(self.amount_text),
                    "method": self.method, "operation_key": str(uuid4()),
                }
            pending = dict(self._pay_pending)
            payment, fine, audit = await pay_fine(context[1][2], pending["fine_id"], pending["amount_cents"], pending["method"], pending["operation_key"])
            if not self._current(*context):
                return
            if payment["registered_by"] != int(context[1][0]):
                raise FineError("unknown")
            self._fine = fine
            self._payments = [p for p in self._payments if p["id"] != payment["id"]] + [payment]
            self._pay_pending = {}
            self.pay_confirming = False
            self.amount_text = reais(saldo(fine)).replace("R$ ", "") if fine["status"] == "open" else ""
            done = "Multa quitada." if fine["status"] == "paid" else f"Saldo restante: {reais(saldo(fine))}."
            self.notice = f"Pagamento de {reais(payment['amount_cents'])} registrado. {done}" + (
                "" if audit else " A auditoria não foi confirmada; não repita o pagamento."
            )
        except FineError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "unknown" or (repeat and error.category in {"configuration", "disabled", "unavailable", "invalid"}):
                    self.message = "Resultado do pagamento ainda desconhecido. Use “Atualizar detalhes” ou repita a mesma tentativa."
                elif error.category in {"authentication", "authorization", "ratelimited"}:
                    await self._show_error(error)
                else:
                    self._pay_pending = {}
                    self.pay_confirming = False
                    await self._show_error(error)
                    if error.category == "conflict":
                        await self._refresh(context)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    async def _refresh(self, context) -> None:
        """Releitura após conflito (saldo ou situação alterados por outra pessoa)."""
        try:
            fine, payments = await get_fine(context[1][2], self._fine["id"])
            if self._current(*context):
                self._fine, self._payments = fine, payments
                self.amount_text = reais(saldo(fine)).replace("R$ ", "") if fine["status"] == "open" else ""
        except FineError:
            self.message += " Use “Atualizar detalhes”."

    @rx.event
    async def submit_pay(self):
        async for update in self._send_pay():
            yield update

    @rx.event
    async def repeat_pay(self):
        async for update in self._send_pay(repeat=True):
            yield update

    # ---------- Estorno e abono (admin) ----------

    @rx.event
    def ask_reverse(self, payment_id: str):
        if self._busy or self._admin_pending:
            return
        target = int(payment_id) if str(payment_id).isdigit() else 0
        if any(p["id"] == target and p["status"] == "confirmed" for p in self._payments) and self.can_reverse:
            self.admin_action, self.admin_target, self.admin_reason = "reverse", target, ""
            self.message = self.notice = ""

    @rx.event
    def ask_waive(self):
        if not self._busy and not self._admin_pending and self.is_open:
            self.admin_action, self.admin_target, self.admin_reason = "waive", self._fine["id"], ""
            self.message = self.notice = ""

    @rx.event
    def cancel_admin(self):
        if not self._busy and not self._admin_pending:
            self.admin_action, self.admin_target, self.admin_reason = "", 0, ""

    @rx.event
    def capture_admin_reason(self, value: str):
        if not self._busy and not self._admin_pending:
            self.admin_reason = value[:500]

    @rx.var
    def admin_pending(self) -> bool:
        return bool(self._admin_pending)

    @rx.var
    def can_confirm_admin(self) -> bool:
        return bool(self.admin_action) and bool(self.admin_reason.strip()) and rental_writes_enabled() and not self._busy

    @rx.var
    def admin_title(self) -> str:
        if self.admin_action == "reverse":
            payment = next((p for p in self._payments if p["id"] == self.admin_target), None)
            return f"Estornar o pagamento nº {self.admin_target}" + (f" ({reais(payment['amount_cents'])})" if payment else "")
        if self.admin_action == "waive" and self._fine:
            return f"Abonar o saldo de {reais(saldo(self._fine))} da multa #{self._fine['id']}"
        return ""

    async def _send_admin(self, repeat: bool = False):
        if self._busy:
            return
        if repeat and not self._admin_pending:
            return
        if not repeat and (not self.admin_action or not self.admin_reason.strip()):
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
        revision, context = self._revision, None
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                return
            if context[1][1] != "admin":
                raise FineError("authorization")
            if not rental_writes_enabled():
                raise FineError("disabled")
            if not repeat:
                self._admin_pending = {
                    "action": self.admin_action, "target": self.admin_target,
                    "reason": self.admin_reason.strip(), "operation_key": str(uuid4()),
                }
            pending = dict(self._admin_pending)
            token = context[1][2]
            if pending["action"] == "reverse":
                payment, fine, audit = await reverse_payment(token, pending["target"], pending["reason"], pending["operation_key"])
                if not self._current(*context):
                    return
                self._payments = [payment if p["id"] == payment["id"] else p for p in self._payments]
                done = f"Pagamento nº {payment['id']} estornado. Saldo da multa: {reais(saldo(fine))}."
            else:
                fine, audit = await waive_fine(token, pending["target"], pending["reason"], pending["operation_key"])
                if not self._current(*context):
                    return
                done = f"Saldo de {reais(fine['waived_cents'])} abonado."
            self._fine = fine
            self.amount_text = reais(saldo(fine)).replace("R$ ", "") if fine["status"] == "open" else ""
            self._admin_pending = {}
            self.admin_action, self.admin_target, self.admin_reason = "", 0, ""
            self.notice = done + ("" if audit else " A auditoria não foi confirmada; não repita a operação.")
        except FineError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "unknown" or (repeat and error.category in {"configuration", "disabled", "unavailable", "invalid"}):
                    self.message = "Resultado ainda desconhecido. Use “Atualizar detalhes” ou repita a mesma tentativa."
                elif error.category in {"authentication", "authorization", "ratelimited"}:
                    await self._show_error(error)
                else:
                    self._admin_pending = {}
                    self.admin_action, self.admin_target, self.admin_reason = "", 0, ""
                    await self._show_error(error)
                    if error.category == "conflict":
                        await self._refresh(context)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def confirm_admin(self):
        async for update in self._send_admin():
            yield update

    @rx.event
    async def repeat_admin(self):
        async for update in self._send_admin(repeat=True):
            yield update


class ClienteHistoricoState(_SessionBound, rx.State):
    """Abas "Locações", "Multas" e "Pagamentos" do detalhe do cliente."""

    message: str = ""
    tab: str = "rentals"
    state: str = "idle"
    loading: bool = False
    _revision: int = 0
    _busy: bool = False
    _cooldown_until: float = 0.0
    _customer_id: int = 0
    _items: list[dict] = []
    _page: int = 1
    _total: int = 0
    # Saldo em aberto do cliente (multas open), lido junto com a primeira aba.
    balance_state: str = "idle"
    _open_count: int = 0
    _open_balance: int = 0

    def _invalidate(self) -> None:
        self._revision += 1
        self._busy = self.loading = False
        self._cooldown_until = 0.0
        self.message = ""
        self.tab, self.state = "rentals", "idle"
        self._customer_id, self._items, self._page, self._total = 0, [], 1, 0
        self.balance_state, self._open_count, self._open_balance = "idle", 0, 0

    @rx.var
    def rows(self) -> list[dict[str, str]]:
        if self.tab == "fines":
            return [fine_row(item) for item in self._items]
        if self.tab == "payments":
            return [payment_row(item) for item in self._items]
        return [
            {
                "number": f"#{item['id']}", "href": f"/locacoes/{item['id']}", "film": item["film_title"],
                "exemplar": item["exemplar_identifier"], "rented_at": data_brasilia(item["rented_at"]),
                "due_at": data_brasilia(item["due_at"]),
                "status": "Ativa" if item["status"] == "active" else "Devolvida",
            }
            for item in self._items
        ]

    @rx.var
    def balance_text(self) -> str:
        return reais(self._open_balance)

    @rx.var
    def has_open_fine(self) -> bool:
        return self._open_count > 0

    @rx.var
    def paging(self) -> str:
        if self._total <= PAGE_SIZE:
            return ""
        first = (self._page - 1) * PAGE_SIZE + 1
        return f"{first}–{min(self._page * PAGE_SIZE, self._total)} de {self._total}"

    @rx.var
    def has_previous(self) -> bool:
        return self._page > 1

    @rx.var
    def has_next(self) -> bool:
        return self._page * PAGE_SIZE < self._total

    @rx.var
    def empty_text(self) -> str:
        return {
            "rentals": "Nenhuma locação registrada para este cliente.",
            "fines": "Nenhuma multa registrada para este cliente.",
            "payments": "Nenhum pagamento registrado para este cliente.",
        }.get(self.tab, "")

    async def _load(self, with_balance: bool = False):
        if self._busy or not self._customer_id or self._cooling_down():
            if self.state in ("idle", "loading"):
                self.state = "error"
            return
        self._busy = self.loading = True
        self.state = "loading"
        self.message = ""
        if with_balance:
            self.balance_state = "loading"
        revision, context, customer_id = self._revision, None, self._customer_id
        yield
        try:
            context = await self._authorize()
            if context is None:
                self.state = "error"
                return
            token = context[1][2]
            if with_balance:
                # Saldo do cliente: soma das multas em aberto (até 50 é suficiente para o balcão).
                open_page = await list_fines(token, 1, 50, status="open", customer_id=customer_id)
                if self._current(*context) and customer_id == self._customer_id:
                    self._open_count = open_page["total"]
                    self._open_balance = sum(saldo(item) for item in open_page["items"])
                    self.balance_state = "ready"
            if self.tab == "fines":
                page = await list_fines(token, self._page, PAGE_SIZE, customer_id=customer_id)
            elif self.tab == "payments":
                page = await list_payments(token, self._page, PAGE_SIZE, customer_id=customer_id)
            else:
                page = await list_rentals(token, self._page, PAGE_SIZE, customer_id=customer_id)
            if self._current(*context) and customer_id == self._customer_id:
                self._items, self._total = page["items"], page["total"]
                self.state = "ready" if page["items"] else "empty"
        except (FineError, RentalError) as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
                self.state = "error"
                if self.balance_state == "loading":
                    self.balance_state = "error"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    def _route_customer_id(self) -> str:
        return str(self.router.page.params.get("customer_id", "")).strip()

    @rx.event
    async def open_customer(self):
        """Chamado ao abrir /clientes/{id}: descarta o histórico de outro cliente."""
        raw = self._route_customer_id()
        customer_id = int(raw) if FINE_NUMBER.fullmatch(raw) else 0
        if customer_id != self._customer_id:
            self._revision += 1
            self._busy = self.loading = False
            self._customer_id, self._items, self._page, self._total = customer_id, [], 1, 0
            self.tab, self.state = "rentals", "idle"
            self.balance_state, self._open_count, self._open_balance = "idle", 0, 0
        if not customer_id:
            return
        self._page = 1
        async for update in self._load(with_balance=True):
            yield update

    @rx.event
    async def set_tab(self, tab: str):
        if tab not in ("rentals", "fines", "payments") or self._busy:
            return
        self.tab, self._page, self._items, self._total = tab, 1, [], 0
        async for update in self._load():
            yield update

    @rx.event
    async def change_page(self, direction: int):
        target = self._page + direction
        if self._busy or target < 1 or (direction > 0 and not self.has_next):
            return
        self._page = target
        async for update in self._load():
            yield update

    @rx.event
    async def retry(self):
        async for update in self._load(with_balance=self.balance_state != "ready"):
            yield update
