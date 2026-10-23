"""Estado de locações isolado, vinculado à revisão privada da sessão."""

from datetime import datetime, timezone
import math
import re
import time
from typing import Any
from uuid import uuid4

import reflex as rx

from ProjetoLocadora.config import get_xano_rental_api_url, rental_writes_enabled
from ProjetoLocadora.locacoes import Rental, data_brasilia, vencimento_utc
from ProjetoLocadora.locacoes_client import (
    MESSAGES, RentalError, available_exemplars, confirm_condition,
    create_rental, get_rental, list_rentals, reconcile_rental, return_rental,
)
from ProjetoLocadora.xano_client import (
    XanoCustomerError, XanoExemplarError, XanoSessionUnavailable, get_me_xano, is_authorized_employee,
    list_customers_xano, list_exemplares_xano,
)


PAGE_SIZE = 10
# Número de locação: inteiro positivo, como o `int id` do endpoint de detalhe.
RENTAL_NUMBER = re.compile(r"[1-9][0-9]{0,9}")
STATUS_LABELS = {"active": "Ativa", "returned": "Devolvida"}


def _customer_label(row: dict) -> str:
    condition = " · inativo" if row["status"] != "active" else ""
    if row["bloqueio_manual_ativo"]:
        condition += " · bloqueado"
    return f"{row['id']} | {row['nome']} · {row['cpf_mascarado']}{condition}"


def _exemplar_label(row: dict) -> str:
    return f"{row['id']} | {row['identificador']} · {row['filme_titulo']}"


def _with_selected(rows: list[dict], selected: dict) -> list[dict]:
    """Mantém a escolha visível quando ela está em outra página da lista."""
    if selected and all(row["id"] != selected["id"] for row in rows):
        return [selected, *rows]
    return rows


class LocacoesState(rx.State):
    loading: bool = False
    message: str = ""
    notice: str = ""
    customer_search: str = ""
    customer_choice: str = ""
    exemplar_choice: str = ""
    due_local: str = ""
    condition_exemplar: str = ""
    condition_value: str = "unverified"
    condition_reason: str = ""
    _revision: int = 0
    _busy: bool = False
    _unknown: bool = False
    _configured: bool = False
    writes_blocked: bool = False
    admin_loaded: bool = False
    # Detalhe: idle | loading | ready | invalid | notfound | error
    detail_state: str = "idle"
    detail_id: str = ""
    lookup_error: str = ""
    _cooldown_until: float = 0.0
    _options_ready: bool = False
    _customers: list[dict] = []
    _exemplars: list[dict] = []
    _customer_sel: dict = {}
    _customer_sel_page: int = 0
    _exemplar_sel: dict = {}
    _exemplar_sel_page: int = 0
    _admin_exemplars: list[dict] = []
    _customer_page: int = 1
    _customer_total: int = 0
    _exemplar_page: int = 1
    _exemplar_total: int = 0
    _pending: dict = {}
    # Devolução: tentativa com chave própria, preservada até resultado conhecido.
    _return_pending: dict = {}
    return_confirming: bool = False
    _rental: dict = {}
    # Locações registradas: idle | loading | ready | empty | error. Carga própria,
    # sem `_busy`, para não bloquear o formulário de registro.
    list_state: str = "idle"
    list_message: str = ""
    _list_busy: bool = False
    _list_items: list[dict] = []
    _list_page: int = 1
    _list_total: int = 0
    # Abas da lista: "active" | "returned"; o filtro é aplicado pelo Xano.
    list_tab: str = "active"
    list_notice: str = ""
    _tab_totals: dict[str, int] = {}

    @rx.var
    def tab_active_label(self) -> str:
        total = self._tab_totals.get("active")
        return "Ativas" if total is None else f"Ativas ({total})"

    @rx.var
    def tab_returned_label(self) -> str:
        total = self._tab_totals.get("returned")
        return "Devolvidas" if total is None else f"Devolvidas ({total})"

    @rx.var
    def customer_options(self) -> list[str]:
        return [_customer_label(row) for row in _with_selected(self._customers, self._customer_sel)]

    @rx.var
    def exemplar_options(self) -> list[str]:
        return [_exemplar_label(row) for row in _with_selected(self._exemplars, self._exemplar_sel)]

    @rx.var
    def admin_exemplar_options(self) -> list[str]:
        return [_exemplar_label(row) for row in self._admin_exemplars]

    @rx.var
    def has_pending(self) -> bool:
        return bool(self._pending)

    @rx.var
    def uncertain(self) -> bool:
        return self._unknown

    def _customer_issue(self) -> str:
        customer = self._customer_sel
        if not customer or _customer_label(customer) != self.customer_choice:
            return "Selecione um cliente."
        if customer["status"] != "active":
            return "O cliente selecionado está inativo."
        if customer["bloqueio_manual_ativo"]:
            return "O cliente selecionado está bloqueado."
        return ""

    def _exemplar_issue(self) -> str:
        if not self._exemplar_sel or _exemplar_label(self._exemplar_sel) != self.exemplar_choice:
            return "Selecione um exemplar disponível."
        return ""

    def _due_issue(self) -> str:
        if not self.due_local:
            return "Informe a data e hora de vencimento."
        try:
            due = datetime.fromisoformat(vencimento_utc(self.due_local).replace("Z", "+00:00"))
        except ValueError as error:
            return str(error)
        if due <= datetime.now(timezone.utc):
            return "O vencimento deve ser posterior ao momento atual."
        return ""

    @rx.var
    def form_issues(self) -> list[str]:
        """Pendências do formulário; a decisão final continua sendo do backend."""
        return [issue for issue in (self._customer_issue(), self._exemplar_issue(), self._due_issue()) if issue]

    @rx.var
    def can_create(self) -> bool:
        return self._configured and self._options_ready and rental_writes_enabled() and not self._busy and not self._pending and not self._rental and not self.form_issues

    @rx.var
    def editing_disabled(self) -> bool:
        return self._busy or bool(self._pending) or bool(self._rental)

    @rx.var
    def writes_available(self) -> bool:
        return self._configured and rental_writes_enabled()

    @rx.var
    def condition_label(self) -> str:
        return {"unverified": "Não conferido", "available": "Apto para locação", "unavailable": "Indisponível"}.get(self.condition_value, "Não conferido")

    @rx.var
    def customer_paging(self) -> str:
        if not self._options_ready:
            return "Clientes ainda não carregados."
        return f"Página {self._customer_page} · {self._customer_total} cliente(s)"

    @rx.var
    def exemplar_paging(self) -> str:
        if not self._options_ready:
            return "Disponibilidade ainda não consultada."
        return f"Página {self._exemplar_page} · {self._exemplar_total} exemplar(es) disponível(is)"

    @rx.var
    def customer_previous(self) -> bool:
        return self._customer_page > 1 and not self._busy

    @rx.var
    def customer_next(self) -> bool:
        return self._customer_page * PAGE_SIZE < self._customer_total and not self._busy

    @rx.var
    def exemplar_previous(self) -> bool:
        return self._exemplar_page > 1 and not self._busy

    @rx.var
    def exemplar_next(self) -> bool:
        return self._exemplar_page * PAGE_SIZE < self._exemplar_total and not self._busy

    @rx.var
    def customer_paginated(self) -> bool:
        return self._customer_total > PAGE_SIZE

    @rx.var
    def exemplar_paginated(self) -> bool:
        return self._exemplar_total > PAGE_SIZE

    @rx.var
    def customer_cards(self) -> list[dict[str, Any]]:
        cards = []
        for row in self._customers:
            reasons = []
            if row["status"] != "active":
                reasons.append("Inativo")
            if row["bloqueio_manual_ativo"]:
                reasons.append("Bloqueado")
            label = _customer_label(row)
            cards.append({
                "label": label, "name": row["nome"], "cpf": row["cpf_mascarado"],
                "reason": " e ".join(reasons), "disabled": bool(reasons),
                "selected": label == self.customer_choice,
            })
        return cards

    @rx.var
    def exemplar_cards(self) -> list[dict[str, Any]]:
        return [
            {"label": _exemplar_label(row), "code": row["identificador"], "film": row["filme_titulo"],
             "selected": _exemplar_label(row) == self.exemplar_choice}
            for row in self._exemplars
        ]

    @rx.var
    def customer_summary(self) -> str:
        row = self._customer_sel
        return f"{row['nome']} · {row['cpf_mascarado']}" if row and not self._customer_issue() else ""

    @rx.var
    def exemplar_summary(self) -> str:
        row = self._exemplar_sel
        return f"{row['identificador']} · {row['filme_titulo']}" if row and not self._exemplar_issue() else ""

    @rx.var
    def due_summary(self) -> str:
        """Vencimento válido no formato dd/mm/aaaa às hh:mm, em horário de Brasília."""
        if self._due_issue():
            return ""
        return datetime.fromisoformat(self.due_local).strftime("%d/%m/%Y às %H:%M")

    @rx.var
    def steps(self) -> list[dict[str, str]]:
        """Progresso derivado das mesmas pendências que governam o botão."""
        done = bool(self._rental)
        flags = [not self._customer_issue(), not self._exemplar_issue(), not self._due_issue()]
        current = next((i for i, ok in enumerate(flags) if not ok), -1)
        names = ("Cliente", "Exemplar", "Vencimento")
        return [
            {"number": str(i + 1), "label": names[i],
             "state": "done" if (ok or done) else ("current" if i == current else "todo")}
            for i, ok in enumerate(flags)
        ]

    @rx.var
    def confirmation(self) -> str:
        if not self._rental:
            return ""
        rental: Rental = self._rental
        return (
            f"Locação #{rental['id']} · {rental['customer_name']} · "
            f"Exemplar {rental['exemplar_identifier']} · {rental['film_title']} · "
            f"Retirada: {data_brasilia(rental['rented_at'])} · "
            f"Vencimento: {data_brasilia(rental['due_at'])} (horário de Brasília) · "
            f"Status: {STATUS_LABELS.get(rental['status'], rental['status']).lower()} · Responsável: {rental['registered_by']}"
        )

    @rx.var
    def options_loaded(self) -> bool:
        return self._options_ready

    @rx.var
    def has_rental(self) -> bool:
        return bool(self._rental)

    @rx.var
    def rental_view(self) -> dict[str, str]:
        """Campos da locação já formatados para a tela de detalhes."""
        if not self._rental:
            return {}
        rental: Rental = self._rental
        return {
            "title": f"Locação #{rental['id']}",
            "status": STATUS_LABELS.get(rental["status"], rental["status"]),
            # Atraso pela regra do domínio: vencimento comparado ao momento da consulta.
            "overdue": "1" if rental["status"] == "active" and rental["due_at"] < time.time() * 1000 else "",
            "customer": rental["customer_name"],
            "customer_href": f"/clientes/{rental['customer_id']}",
            "exemplar": rental["exemplar_identifier"],
            "film": rental["film_title"],
            "rented_at": data_brasilia(rental["rented_at"]),
            "due_at": data_brasilia(rental["due_at"]),
            "registered_by": str(rental["registered_by"]),
            "returned_at": data_brasilia(rental["returned_at"]) if rental.get("returned_at") else "",
            "returned_by": str(rental["returned_by"]) if rental.get("returned_by") else "",
            # Atraso derivado: devolução posterior ao vencimento. Sem multa nem valor.
            "returned_late": "1" if rental.get("returned_at") and rental["returned_at"] > rental["due_at"] else "",
        }

    @rx.var
    def rental_rows(self) -> list[dict[str, str]]:
        now_ms = time.time() * 1000
        return [
            {
                "number": f"#{rental['id']}",
                "film": rental["film_title"],
                "exemplar": rental["exemplar_identifier"],
                "customer": rental["customer_name"],
                "status": STATUS_LABELS.get(rental["status"], rental["status"]),
                "done": "1" if rental["status"] != "active" else "",
                "overdue": "1" if rental["status"] == "active" and rental["due_at"] < now_ms else "",
                "rented_at": data_brasilia(rental["rented_at"]),
                # Linha compacta: a data que importa em cada aba.
                "when": (
                    "Devolvida " + data_brasilia(rental["returned_at"])
                    if rental["status"] != "active" and rental.get("returned_at")
                    else "Retirada " + data_brasilia(rental["rented_at"])
                ),
                "href": f"/locacoes/{rental['id']}",
            }
            for rental in self._list_items
        ]

    @rx.var
    def list_paging(self) -> str:
        return f"Página {self._list_page} · {self._list_total} locação(ões)"

    @rx.var
    def list_previous(self) -> bool:
        return self._list_page > 1 and not self._list_busy

    @rx.var
    def list_next(self) -> bool:
        return self._list_page * PAGE_SIZE < self._list_total and not self._list_busy

    @rx.var
    def list_paginated(self) -> bool:
        return self._list_total > PAGE_SIZE

    @rx.var
    def confirmation_link(self) -> str:
        return f"/locacoes/{self._rental['id']}" if self._rental else "/locacoes/nova"

    def _invalidate(self) -> None:
        self._revision += 1
        self._busy = False
        self.loading = False
        self._unknown = False
        self._configured = False
        self._options_ready = False
        self._customers = []
        self._exemplars = []
        self._admin_exemplars = []
        self._customer_sel = self._exemplar_sel = {}
        self._pending = {}
        self._rental = {}
        self._customer_page = self._exemplar_page = 1
        self._customer_total = self._exemplar_total = 0
        self.customer_search = self.customer_choice = self.exemplar_choice = ""
        self.due_local = self.condition_exemplar = self.condition_reason = ""
        self.condition_value = "unverified"
        self.message = self.notice = ""
        self.writes_blocked = False
        self.admin_loaded = False
        self.detail_state = "idle"
        self.detail_id = self.lookup_error = ""
        self._return_pending = {}
        self.return_confirming = False
        self._cooldown_until = 0.0
        self.list_state = "idle"
        self.list_message = ""
        self._list_busy = False
        self._list_items = []
        self._list_page = 1
        self._list_total = 0
        self.list_tab = "active"
        self.list_notice = ""
        self._tab_totals = {}

    def _snapshot(self, session):
        return (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)

    def _current(self, session, snapshot, revision):
        return revision == self._revision and snapshot == self._snapshot(session)

    async def _authorize(self, fresh: bool = False):
        """Confere a sessão; leituras podem reaproveitar um auth/me recente.

        `fresh=True` (escritas e reconciliação) sempre consulta auth/me agora.
        """
        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        snapshot, revision = self._snapshot(session), self._revision
        if not snapshot[0] or not snapshot[2]:
            raise RentalError("authentication")
        if not fresh and session._recently_verified():
            return session, snapshot, revision
        try:
            me = await get_me_xano(snapshot[2])
        except XanoSessionUnavailable as error:
            # Não prova que o token é inválido: manter a sessão e permitir nova tentativa.
            if error.retry_after:
                raise RentalError("ratelimited", retry_after=error.retry_after) from None
            raise RentalError("unavailable") from None
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

    def _rate_limited(self, wait: int) -> None:
        """Registra o Retry-After; nenhuma leitura nova é enviada antes dele."""
        self._cooldown_until = time.monotonic() + wait
        self.message = (
            "O Xano atingiu o limite de requisições do plano (10 a cada 20 s). "
            f"Aguarde {wait} s e use “Tentar novamente”."
        )

    def _cooling_down(self) -> bool:
        remaining = self._cooldown_until - time.monotonic()
        if remaining <= 0:
            return False
        self.message = (
            "Limite de requisições do Xano: aguarde mais "
            f"{math.ceil(remaining)} s antes de tentar novamente."
        )
        return True

    async def _show_error(self, error: RentalError):
        if error.category == "ratelimited":
            self._rate_limited(error.retry_after or 20)
            return
        if error.category in {"authentication", "authorization"}:
            from ProjetoLocadora.ProjetoLocadora import State

            session = await self.get_state(State)
            if error.category == "authentication":
                session._clear_session()
                await session._sync_dashboard_session()
            else:
                # Recusa do backend: a próxima operação confere a sessão de novo.
                session._forget_session_check()
                self._invalidate()
        self.message = MESSAGES[error.category]

    @rx.event
    def capture_customer_search(self, value: str):
        if not self._busy and not self._pending:
            self.customer_search = value[:200]

    @rx.event
    def capture_customer(self, value: str):
        if not self._busy and not self._pending:
            row = next((r for r in _with_selected(self._customers, self._customer_sel) if _customer_label(r) == value), None)
            self._customer_sel = row or {}
            self._customer_sel_page = self._customer_page
            self.customer_choice = _customer_label(row) if row else ""

    @rx.event
    def capture_exemplar(self, value: str):
        if not self._busy and not self._pending:
            row = next((r for r in _with_selected(self._exemplars, self._exemplar_sel) if _exemplar_label(r) == value), None)
            self._exemplar_sel = row or {}
            self._exemplar_sel_page = self._exemplar_page
            self.exemplar_choice = _exemplar_label(row) if row else ""

    @rx.event
    def capture_due(self, value: str):
        if not self._busy and not self._pending:
            self.due_local = value

    @rx.event
    def capture_condition_exemplar(self, value: str):
        if not self._busy:
            self.condition_exemplar = value if value in self.admin_exemplar_options else ""

    @rx.event
    def capture_condition(self, value: str):
        value = {"Não conferido": "unverified", "Apto para locação": "available", "Indisponível": "unavailable"}.get(value, value)
        if not self._busy and value in {"unverified", "available", "unavailable"}:
            self.condition_value = value

    @rx.event
    def capture_reason(self, value: str):
        if not self._busy:
            self.condition_reason = value[:500]

    def _revalidate_selection(self) -> None:
        """Atualiza a escolha com a lista recarregada, sem apagar a da outra lista.

        Se a escolha estava na página recarregada e não aparece mais, ela deixou de
        existir ou de estar disponível. Em outra página, não há como saber sem nova
        consulta: ela é mantida e o backend continua sendo a validação final.
        """
        for sel, rows, page, sel_page, label, field in (
            (self._customer_sel, self._customers, self._customer_page, self._customer_sel_page, _customer_label, "customer_choice"),
            (self._exemplar_sel, self._exemplars, self._exemplar_page, self._exemplar_sel_page, _exemplar_label, "exemplar_choice"),
        ):
            if not sel:
                continue
            fresh = next((r for r in rows if r["id"] == sel["id"]), None)
            if fresh is not None:
                chosen = fresh
            elif sel_page == page:
                chosen = {}
            else:
                chosen = sel
            if field == "customer_choice":
                self._customer_sel = chosen
            else:
                self._exemplar_sel = chosen
            setattr(self, field, label(chosen) if chosen else "")

    async def _load_options(self, customers: bool = True, exemplars: bool = True):
        if self._busy or self._pending or self._cooling_down():
            return
        self._busy = self.loading = True
        full = customers and exemplars
        if full:
            self._customers = []
            self._exemplars = []
            self._customer_sel = self._exemplar_sel = {}
            self.customer_choice = self.exemplar_choice = ""
            self._options_ready = False
        self.message = ""
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize()
            if context is None:
                return
            session, snapshot, revision = context
            try:
                get_xano_rental_api_url()
            except (RuntimeError, ValueError):
                raise RentalError("configuration") from None
            self._configured = True
            loaded_customers = loaded_exemplars = None
            if customers:
                loaded_customers = await list_customers_xano(snapshot[2], nome=self.customer_search, page=self._customer_page, per_page=PAGE_SIZE)
                if not self._current(*context):
                    return
            if exemplars:
                loaded_exemplars = await available_exemplars(snapshot[2], self._exemplar_page, PAGE_SIZE)
                if not self._current(*context):
                    return
            if loaded_customers is not None:
                self._customers = loaded_customers["items"]
                self._customer_total = loaded_customers["total"]
            if loaded_exemplars is not None:
                self._exemplars = loaded_exemplars["items"]
                self._exemplar_total = loaded_exemplars["total"]
            self._revalidate_selection()
            self._options_ready = True
            self.writes_blocked = not rental_writes_enabled()
            if self.writes_blocked:
                self.notice = MESSAGES["disabled"]
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        except XanoCustomerError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.status in (401, 403) and context is not None:
                    context[0]._forget_session_check()
                if error.retry_after:
                    self._rate_limited(error.retry_after)
                else:
                    self.message = f"Não foi possível carregar os clientes. {error.user_message}"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def load_admin_exemplars(self):
        """Lista completa só para a conferência do admin, sob demanda.

        Carregá-la em toda abertura da tela consumia uma requisição a mais da cota
        do Xano e uma falha dela impedia clientes e exemplares de aparecerem.
        """
        if self._busy or self._cooling_down():
            return
        self._busy = self.loading = True
        self.message = ""
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize()
            if context is None:
                return
            _, snapshot, revision = context
            if snapshot[1] != "admin":
                raise RentalError("authorization")
            rows = await list_exemplares_xano(snapshot[2])
            if self._current(*context):
                self._admin_exemplars = rows
                self.condition_exemplar = ""
                self.admin_loaded = True
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        except XanoExemplarError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.status in (401, 403) and context is not None:
                    context[0]._forget_session_check()
                if error.retry_after:
                    self._rate_limited(error.retry_after)
                else:
                    self.message = f"Não foi possível carregar os exemplares para conferência. {error.user_message}"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def load_new(self):
        # Navegação não descarta tentativa de resultado ainda desconhecido.
        if not self._pending and not self._busy:
            self._rental = {}
            self.notice = ""
        async for update in self._load_options():
            yield update
        async for update in self._load_list():
            yield update

    @rx.event
    async def search_customers(self):
        if not self._busy and not self._pending:
            self._customer_page = 1
            # Novo filtro de busca: a ausência do cliente escolhido nos resultados não
            # indica que ele deixou de existir; a escolha só é revalidada se reaparecer.
            self._customer_sel_page = 0
            async for update in self._load_options(exemplars=False):
                yield update

    @rx.event
    async def customer_page(self, direction: int):
        if direction not in (-1, 1) or self._busy or self._pending:
            return
        page = self._customer_page + direction
        if page < 1 or (direction == 1 and self._customer_page * PAGE_SIZE >= self._customer_total):
            return
        self._customer_page = page
        async for update in self._load_options(exemplars=False):
            yield update

    @rx.event
    async def exemplar_page(self, direction: int):
        if direction not in (-1, 1) or self._busy or self._pending:
            return
        page = self._exemplar_page + direction
        if page < 1 or (direction == 1 and self._exemplar_page * PAGE_SIZE >= self._exemplar_total):
            return
        self._exemplar_page = page
        async for update in self._load_options(customers=False):
            yield update

    async def _load_list(self):
        """Página de locações registradas; falha aqui não afeta o formulário."""
        if self._list_busy:
            return
        remaining = self._cooldown_until - time.monotonic()
        if remaining > 0:
            self.list_state = "error"
            self.list_message = f"Limite de requisições do Xano: aguarde mais {math.ceil(remaining)} s antes de atualizar a lista."
            return
        self._list_busy = True
        self.list_state = "loading"
        self.list_message = ""
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize()
            if context is None:
                if revision == self._revision:
                    self.list_state = "idle"
                return
            _, snapshot, revision = context
            tab = self.list_tab
            page = await list_rentals(snapshot[2], self._list_page, PAGE_SIZE, status=tab)
            # set_list_tab é bloqueado durante a carga: a aba não muda no meio dela.
            if not self._current(*context):
                return
            self._list_items = page["items"]
            self._list_total = page["total"]
            self._tab_totals = {**self._tab_totals, tab: page["total"]}
            self.list_state = "ready" if page["items"] else "empty"
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                self.list_state = "error"
                if error.category == "ratelimited":
                    wait = error.retry_after or 20
                    self._cooldown_until = time.monotonic() + wait
                    self.list_message = f"O Xano atingiu o limite de requisições do plano. Aguarde {wait} s e atualize a lista."
                elif error.category == "notfound":
                    # GET sem rota: o endpoint de listagem ainda não foi aplicado no Xano.
                    self.list_message = "A listagem de locações ainda não está disponível no serviço."
                elif error.category in {"authentication", "authorization"}:
                    await self._show_error(error)
                    self.list_message = MESSAGES[error.category]
                else:
                    self.list_message = f"Não foi possível carregar as locações. {MESSAGES[error.category]}"
        finally:
            if revision == self._revision:
                self._list_busy = False

    @rx.event
    async def load_rentals(self):
        async for update in self._load_list():
            yield update

    @rx.event
    async def rentals_page(self, direction: int):
        if direction not in (-1, 1) or self._list_busy:
            return
        page = self._list_page + direction
        if page < 1 or (direction == 1 and self._list_page * PAGE_SIZE >= self._list_total):
            return
        self._list_page = page
        async for update in self._load_list():
            yield update

    @rx.event
    async def set_list_tab(self, tab: str):
        if tab not in ("active", "returned") or self._list_busy or tab == self.list_tab:
            return
        self.list_tab = tab
        self.list_notice = ""
        self._list_page = 1
        self._list_items = []
        async for update in self._load_list():
            yield update

    async def _refresh_list_after_registration(self):
        # A locação nova é ativa e a mais recente: aba "Ativas", primeira página.
        self.list_tab = "active"
        self._list_page = 1
        async for update in self._load_list():
            yield update

    async def _send(self, repeat: bool = False):
        if self._busy or self._rental:
            return
        if repeat:
            if not self._pending:
                return
        elif self._pending:
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
        context = None
        revision = self._revision
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                return
            session, snapshot, revision = context
            if not rental_writes_enabled():
                raise RentalError("disabled")
            if not repeat:
                customer = next((r for r in _with_selected(self._customers, self._customer_sel) if _customer_label(r) == self.customer_choice), None)
                exemplar = next((r for r in _with_selected(self._exemplars, self._exemplar_sel) if _exemplar_label(r) == self.exemplar_choice), None)
                if customer is None or exemplar is None or customer["status"] != "active" or customer["bloqueio_manual_ativo"]:
                    raise RentalError("input")
                try:
                    due_at = vencimento_utc(self.due_local)
                except ValueError as error:
                    self.message = str(error)
                    return
                self._pending = {"customer_id": customer["id"], "exemplar_id": exemplar["id"], "due_at": due_at, "operation_key": str(uuid4())}
            rental, audit = await create_rental(snapshot[2], dict(self._pending))
            if not self._current(*context):
                return
            if rental["registered_by"] != int(snapshot[0]):
                raise RentalError("unknown")
            self._rental = rental
            self._pending = {}
            self._unknown = False
            self._exemplars = []
            self.notice = "Locação registrada." if audit else "Locação registrada; a auditoria não foi confirmada. Não repita o registro."
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                # Sem certeza de rollback, conservar a chave e impedir outro payload.
                if error.category == "unknown" or (repeat and error.category in {"configuration", "disabled", "unavailable", "invalid"}):
                    self._unknown = True
                elif error.category not in {"authentication", "authorization"}:
                    self._pending = {}
                    self._unknown = False
                    if error.category == "conflict":
                        self._exemplars = []
                        self._exemplar_sel = {}
                        self.exemplar_choice = ""
                await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def submit(self):
        registered_before = bool(self._rental)
        async for update in self._send():
            yield update
        if self._rental and not registered_before:
            async for update in self._refresh_list_after_registration():
                yield update

    @rx.event
    async def repeat_pending(self):
        registered_before = bool(self._rental)
        async for update in self._send(repeat=True):
            yield update
        if self._rental and not registered_before:
            async for update in self._refresh_list_after_registration():
                yield update

    @rx.event
    async def reconcile(self):
        if self._busy or not self._pending:
            return
        self._busy = self.loading = True
        self.message = ""
        context = None
        revision = self._revision
        confirmed = False
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                return
            _, snapshot, revision = context
            rental = await reconcile_rental(snapshot[2], self._pending["operation_key"])
            if not self._current(*context):
                return
            expected_due = self._pending["due_at"]
            from datetime import datetime

            expected_ms = int(datetime.fromisoformat(expected_due.replace("Z", "+00:00")).timestamp() * 1000)
            if (rental["customer_id"], rental["exemplar_id"], rental["registered_by"], rental["due_at"]) != (self._pending["customer_id"], self._pending["exemplar_id"], int(snapshot[0]), expected_ms):
                raise RentalError("invalid")
            self._rental = rental
            self._pending = {}
            self._unknown = False
            self.notice = "Locação confirmada pelo registro persistido. A auditoria deve ser verificada separadamente."
            confirmed = True
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "notfound":
                    self.message = "A tentativa ainda não foi localizada. Ela pode estar em processamento; consulte novamente ou repita a mesma tentativa."
                else:
                    await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False
        if confirmed:
            async for update in self._refresh_list_after_registration():
                yield update

    def _route_rental_id(self) -> str:
        return str(self.router.page.params.get("rental_id", "")).strip()

    @rx.event
    def open_rental(self, form_data: dict):
        """Abre o detalhe pelo número; o backend continua sendo quem confirma a existência."""
        raw = str(form_data.get("rental_number", "")).strip()
        if not RENTAL_NUMBER.fullmatch(raw):
            self.lookup_error = "Informe o número da locação (inteiro positivo)."
            return
        self.lookup_error = ""
        return rx.redirect(f"/locacoes/{raw}")

    @rx.event
    async def load_detail(self):
        if self._busy:
            return
        raw = self._route_rental_id()
        self.detail_id = raw[:20]
        self._rental = {}
        self.message = self.notice = self.lookup_error = ""
        # Identificador inválido não chega ao Xano nem consome a cota do plano.
        if not RENTAL_NUMBER.fullmatch(raw):
            self.detail_state = "invalid"
            self.message = "Número de locação inválido. Use um número inteiro positivo, como 1 ou 25."
            return
        if self._cooling_down():
            self.detail_state = "error"
            return
        self.detail_state = "loading"
        self._busy = self.loading = True
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize()
            if context is None:
                self.detail_state = "error"
                return
            _, snapshot, revision = context
            rental = await get_rental(snapshot[2], int(raw))
            if self._current(*context):
                self._rental = rental
                self.detail_state = "ready"
                self.writes_blocked = not rental_writes_enabled()
                pending = self._return_pending
                if pending and pending["rental_id"] == rental["id"] and rental["status"] == "returned":
                    # Resultado desconhecido resolvido pelo registro persistido.
                    self._return_pending = {}
                    self.notice = "Devolução confirmada pelo registro persistido."
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "notfound":
                    self.detail_state = "notfound"
                    self.message = f"A locação nº {raw} não foi encontrada."
                else:
                    await self._show_error(error)
                    self.detail_state = "error"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.var
    def is_active_rental(self) -> bool:
        return bool(self._rental) and self._rental["status"] == "active"

    @rx.var
    def return_pending_here(self) -> bool:
        return bool(self._return_pending) and bool(self._rental) and self._return_pending["rental_id"] == self._rental["id"]

    @rx.var
    def can_return(self) -> bool:
        return (
            bool(self._rental) and self._rental["status"] == "active" and rental_writes_enabled()
            and not self._busy and not self._return_pending
        )

    @rx.event
    def ask_return(self):
        if self.can_return:
            self.return_confirming = True
            self.message = self.notice = ""

    @rx.event
    def cancel_return(self):
        if not self._busy:
            self.return_confirming = False

    async def _send_return(self, repeat: bool = False):
        if self._busy:
            return
        rental = self._rental
        if repeat:
            if not self._return_pending:
                return
        elif self._return_pending or not rental or rental["status"] != "active":
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
        context = None
        revision = self._revision
        yield
        try:
            # Escrita: auth/me atual, nunca a conferência reaproveitada.
            context = await self._authorize(fresh=True)
            if context is None:
                return
            _, snapshot, revision = context
            if not rental_writes_enabled():
                raise RentalError("disabled")
            if not repeat:
                self._return_pending = {"rental_id": rental["id"], "operation_key": str(uuid4())}
            pending = dict(self._return_pending)
            returned, audit = await return_rental(snapshot[2], pending["rental_id"], pending["operation_key"])
            if not self._current(*context):
                return
            if returned["returned_by"] != int(snapshot[0]):
                raise RentalError("unknown")
            self._rental = returned
            self._return_pending = {}
            self.return_confirming = False
            self.detail_state = "ready"
            self.notice = "Devolução registrada." if audit else "Devolução registrada; a auditoria não foi confirmada. Não repita a devolução."
            # Volta à lista já na aba "Devolvidas", com a locação recém-devolvida no topo.
            self.list_tab = "returned"
            self._list_page = 1
            self.list_notice = f"Locação #{returned['id']} devolvida." + (
                "" if audit else " A auditoria não foi confirmada; não repita a devolução."
            )
            yield rx.redirect("/locacoes/nova")
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "unknown" or (repeat and error.category in {"configuration", "disabled", "unavailable", "invalid", "ratelimited"}):
                    # Sem certeza do resultado: manter a chave para repetir ou conferir o detalhe.
                    if error.category == "ratelimited":
                        await self._show_error(error)
                    else:
                        self.message = "Resultado da devolução ainda desconhecido. Use “Atualizar detalhes” ou repita a mesma tentativa."
                elif error.category in {"authentication", "authorization"}:
                    await self._show_error(error)
                else:
                    self._return_pending = {}
                    self.return_confirming = False
                    if error.category == "conflict":
                        self.message = "Esta locação já foi devolvida ou a chave pertence a outra operação. Os dados abaixo foram atualizados."
                        try:
                            refreshed = await get_rental(context[1][2], rental["id"])
                            if self._current(*context):
                                self._rental = refreshed
                        except RentalError:
                            self.message = "Esta locação já foi devolvida ou a chave pertence a outra operação. Use “Atualizar detalhes”."
                    else:
                        await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def submit_return(self):
        async for update in self._send_return():
            yield update

    @rx.event
    async def repeat_return(self):
        async for update in self._send_return(repeat=True):
            yield update

    def _condition_issue(self) -> str:
        """Campos da conferência; o erro genérico de locação não se aplica aqui."""
        if not any(_exemplar_label(r) == self.condition_exemplar for r in self._admin_exemplars):
            return "Selecione o exemplar conferido."
        if not self.condition_reason.strip():
            return "Informe o motivo da confirmação (ex.: disco conferido, sem riscos)."
        return ""

    @rx.event
    async def save_condition(self):
        if self._busy or self._pending:
            return
        self.notice = ""
        # Validação local antes de qualquer requisição: o Xano exige os mesmos campos.
        self.message = self._condition_issue()
        if self.message:
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                return
            _, snapshot, revision = context
            if snapshot[1] != "admin":
                raise RentalError("authorization")
            exemplar = next((r for r in self._admin_exemplars if _exemplar_label(r) == self.condition_exemplar), None)
            if exemplar is None:
                raise RentalError("input")
            audit = await confirm_condition(snapshot[2], exemplar["id"], self.condition_value, self.condition_reason)
            if self._current(*context):
                self._exemplars = []
                self._exemplar_sel = {}
                self._options_ready = False
                self.exemplar_choice = ""
                self.notice = "Condição confirmada. Atualize as opções de locação." if audit else "Condição gravada; auditoria não confirmada. Atualize as opções de locação."
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False
