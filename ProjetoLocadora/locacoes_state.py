"""Estado de locações isolado, vinculado à revisão privada da sessão."""

from uuid import uuid4

import reflex as rx

from ProjetoLocadora.config import get_xano_rental_api_url, rental_writes_enabled
from ProjetoLocadora.locacoes import Rental, data_brasilia, vencimento_utc
from ProjetoLocadora.locacoes_client import (
    MESSAGES, RentalError, available_exemplars, confirm_condition,
    create_rental, get_rental, reconcile_rental,
)
from ProjetoLocadora.xano_client import (
    XanoCustomerError, XanoExemplarError, get_me_xano, is_authorized_employee,
    list_customers_xano, list_exemplares_xano,
)


def _customer_label(row: dict) -> str:
    condition = " · inativo" if row["status"] != "active" else ""
    if row["bloqueio_manual_ativo"]:
        condition += " · bloqueado"
    return f"{row['id']} | {row['nome']} · {row['cpf_mascarado']}{condition}"


def _exemplar_label(row: dict) -> str:
    return f"{row['id']} | {row['identificador']} · {row['filme_titulo']}"


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
    _options_ready: bool = False
    _customers: list[dict] = []
    _exemplars: list[dict] = []
    _admin_exemplars: list[dict] = []
    _customer_page: int = 1
    _customer_total: int = 0
    _exemplar_page: int = 1
    _exemplar_total: int = 0
    _pending: dict = {}
    _rental: dict = {}

    @rx.var
    def customer_options(self) -> list[str]:
        return [_customer_label(row) for row in self._customers]

    @rx.var
    def exemplar_options(self) -> list[str]:
        return [_exemplar_label(row) for row in self._exemplars]

    @rx.var
    def admin_exemplar_options(self) -> list[str]:
        return [_exemplar_label(row) for row in self._admin_exemplars]

    @rx.var
    def has_pending(self) -> bool:
        return bool(self._pending)

    @rx.var
    def uncertain(self) -> bool:
        return self._unknown

    @rx.var
    def can_create(self) -> bool:
        return self._configured and self._options_ready and bool(self._customers) and bool(self._exemplars) and rental_writes_enabled() and not self._busy and not self._pending and not self._rental

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
        return self._customer_page * 20 < self._customer_total and not self._busy

    @rx.var
    def exemplar_previous(self) -> bool:
        return self._exemplar_page > 1 and not self._busy

    @rx.var
    def exemplar_next(self) -> bool:
        return self._exemplar_page * 20 < self._exemplar_total and not self._busy

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
            f"Status: ativa · Responsável: {rental['registered_by']}"
        )

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
        self._pending = {}
        self._rental = {}
        self._customer_page = self._exemplar_page = 1
        self._customer_total = self._exemplar_total = 0
        self.customer_search = self.customer_choice = self.exemplar_choice = ""
        self.due_local = self.condition_exemplar = self.condition_reason = ""
        self.condition_value = "unverified"
        self.message = self.notice = ""

    def _snapshot(self, session):
        return (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)

    def _current(self, session, snapshot, revision):
        return revision == self._revision and snapshot == self._snapshot(session)

    async def _authorize(self):
        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        snapshot, revision = self._snapshot(session), self._revision
        if not snapshot[0] or not snapshot[2]:
            raise RentalError("authentication")
        me = await get_me_xano(snapshot[2])
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
        return session, snapshot, revision

    async def _show_error(self, error: RentalError):
        if error.category in {"authentication", "authorization"}:
            from ProjetoLocadora.ProjetoLocadora import State

            session = await self.get_state(State)
            if error.category == "authentication":
                session._clear_session()
                await session._sync_dashboard_session()
            else:
                self._invalidate()
        self.message = MESSAGES[error.category]

    @rx.event
    def capture_customer_search(self, value: str):
        if not self._busy and not self._pending:
            self.customer_search = value[:200]

    @rx.event
    def capture_customer(self, value: str):
        if not self._busy and not self._pending:
            self.customer_choice = value if value in self.customer_options else ""

    @rx.event
    def capture_exemplar(self, value: str):
        if not self._busy and not self._pending:
            self.exemplar_choice = value if value in self.exemplar_options else ""

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

    async def _load_options(self):
        if self._busy or self._pending:
            return
        self._busy = self.loading = True
        self._customers = []
        self._exemplars = []
        self._admin_exemplars = []
        self.customer_choice = self.exemplar_choice = self.condition_exemplar = ""
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
            customers = await list_customers_xano(snapshot[2], nome=self.customer_search, page=self._customer_page, per_page=20)
            if not self._current(*context):
                return
            exemplars = await available_exemplars(snapshot[2], self._exemplar_page)
            if not self._current(*context):
                return
            admin = []
            if snapshot[1] == "admin":
                admin = await list_exemplares_xano(snapshot[2])
                if not self._current(*context):
                    return
            self._customers = customers["items"]
            self._customer_total = customers["total"]
            self._exemplars = exemplars["items"]
            self._exemplar_total = exemplars["total"]
            self._admin_exemplars = admin
            self._options_ready = True
            if not rental_writes_enabled():
                self.notice = MESSAGES["disabled"]
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        except (XanoCustomerError, XanoExemplarError):
            if revision == self._revision and (context is None or self._current(*context)):
                self.message = "Não foi possível carregar clientes e exemplares. Tente atualizar."
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

    @rx.event
    async def search_customers(self):
        if not self._busy and not self._pending:
            self._customer_page = 1
            async for update in self._load_options():
                yield update

    @rx.event
    async def customer_page(self, direction: int):
        if direction not in (-1, 1) or self._busy or self._pending:
            return
        page = self._customer_page + direction
        if page < 1 or (direction == 1 and self._customer_page * 20 >= self._customer_total):
            return
        self._customer_page = page
        async for update in self._load_options():
            yield update

    @rx.event
    async def exemplar_page(self, direction: int):
        if direction not in (-1, 1) or self._busy or self._pending:
            return
        page = self._exemplar_page + direction
        if page < 1 or (direction == 1 and self._exemplar_page * 20 >= self._exemplar_total):
            return
        self._exemplar_page = page
        async for update in self._load_options():
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
            context = await self._authorize()
            if context is None:
                return
            session, snapshot, revision = context
            if not rental_writes_enabled():
                raise RentalError("disabled")
            if not repeat:
                customer = next((r for r in self._customers if _customer_label(r) == self.customer_choice), None)
                exemplar = next((r for r in self._exemplars if _exemplar_label(r) == self.exemplar_choice), None)
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
                        self.exemplar_choice = ""
                await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def submit(self):
        async for update in self._send():
            yield update

    @rx.event
    async def repeat_pending(self):
        async for update in self._send(repeat=True):
            yield update

    @rx.event
    async def reconcile(self):
        if self._busy or not self._pending:
            return
        self._busy = self.loading = True
        self.message = ""
        context = None
        revision = self._revision
        yield
        try:
            context = await self._authorize()
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
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                if error.category == "notfound":
                    self.message = "A tentativa ainda não foi localizada. Ela pode estar em processamento; consulte novamente ou repita a mesma tentativa."
                else:
                    await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def load_detail(self):
        if self._busy:
            return
        self._rental = {}
        self.message = self.notice = ""
        self._busy = self.loading = True
        revision = self._revision
        context = None
        yield
        try:
            context = await self._authorize()
            if context is None:
                return
            _, snapshot, revision = context
            try:
                rental_id = int(self.router.page.params.get("rental_id", ""))
            except ValueError:
                raise RentalError("notfound") from None
            rental = await get_rental(snapshot[2], rental_id)
            if self._current(*context):
                self._rental = rental
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    @rx.event
    async def save_condition(self):
        if self._busy or self._pending:
            return
        self._busy = self.loading = True
        self.message = self.notice = ""
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
            exemplar = next((r for r in self._admin_exemplars if _exemplar_label(r) == self.condition_exemplar), None)
            if exemplar is None:
                raise RentalError("input")
            audit = await confirm_condition(snapshot[2], exemplar["id"], self.condition_value, self.condition_reason)
            if self._current(*context):
                self._exemplars = []
                self._options_ready = False
                self.exemplar_choice = ""
                self.notice = "Condição confirmada. Atualize as opções de locação." if audit else "Condição gravada; auditoria não confirmada. Atualize as opções de locação."
        except RentalError as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_error(error)
        finally:
            if revision == self._revision:
                self._busy = self.loading = False
