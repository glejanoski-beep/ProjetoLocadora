"""Estado da página de usuários: lista única, filtro local e diálogo de alteração."""

from typing import TypedDict

import reflex as rx

from ProjetoLocadora.locacoes import data_brasilia
from ProjetoLocadora.multas_client import FineError
from ProjetoLocadora.multas_state import _SessionBound
from ProjetoLocadora.usuarios import MAX_USERS, ROLE_BY_LABEL, ROLES, STATUS_FILTERS, filtrar, validar_motivo
from ProjetoLocadora.usuarios_client import MESSAGES, UserError, list_users, update_user


class UserRow(TypedDict):
    id: int
    name: str
    email: str
    role_label: str
    active: bool
    created: str
    is_self: bool


UNCERTAIN = "Não foi possível confirmar a alteração. A lista foi recarregada: confira a conta antes de repetir."


class UsuariosState(_SessionBound, rx.State):
    message: str = ""
    notice: str = ""
    state: str = "idle"  # idle | loading | ready | error | forbidden
    loading: bool = False
    search: str = ""
    status_filter: str = "all"
    _users: list[dict] = []
    _me: int = 0
    _revision: int = 0
    _busy: bool = False
    _cooldown_until: float = 0.0
    # Diálogo
    edit_open: bool = False
    edit_id: int = 0
    edit_role: str = "member"
    edit_active: bool = True
    edit_reason: str = ""
    edit_error: str = ""
    confirming: bool = False
    saving: bool = False

    def _invalidate(self) -> None:
        self._revision += 1
        self._busy = self.loading = self.saving = False
        self._cooldown_until = 0.0
        self.message = self.notice = ""
        self.state = "idle"
        self.search, self.status_filter = "", "all"
        self._users, self._me = [], 0
        self._close()

    def _close(self) -> None:
        self.edit_open = self.confirming = False
        self.edit_id, self.edit_role, self.edit_active = 0, "member", True
        self.edit_reason = self.edit_error = ""

    # ---------- Lista ----------

    async def _load(self):
        if self._busy or self._cooling_down():
            return
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
                self.state, self._users = "forbidden", []
                return
            users = await list_users(context[1][2])
            if self._current(*context):
                self._users = users
                self._me = int(context[1][0])
                self.state = "ready"
        except (UserError, FineError) as error:
            if revision == self._revision and (context is None or self._current(*context)):
                await self._show_user_error(error)
                self.state = "forbidden" if error.category == "authorization" else "error"
        finally:
            if revision == self._revision:
                self._busy = self.loading = False

    async def _show_user_error(self, error) -> None:
        await self._show_error(error)
        if error.category != "ratelimited":
            self.message = getattr(error, "detail", "") or MESSAGES.get(error.category, MESSAGES["unavailable"])

    @rx.event
    async def open_page(self):
        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        if session._user_role != "admin":
            self.state, self._users = "forbidden", []
            return
        async for update in self._load():
            yield update

    @rx.event
    async def reload(self):
        async for update in self._load():
            yield update

    @rx.event
    def capture_search(self, value: str):
        self.search = value[:120]

    @rx.event
    def set_status_filter(self, key: str):
        if key in STATUS_FILTERS:
            self.status_filter = key

    @rx.var
    def status_filters(self) -> list[dict[str, str]]:
        return [{"key": key, "label": label} for key, label in STATUS_FILTERS.items()]

    @rx.var
    def rows(self) -> list[UserRow]:
        return [
            {
                "id": u["id"],
                "name": u["name"] or "(sem nome)",
                "email": u["email"],
                "role_label": ROLES[u["role"]],
                "active": u["is_active"],
                "created": data_brasilia(u["created_at"]),
                "is_self": u["id"] == self._me,
            }
            for u in filtrar(self._users, self.search, self.status_filter)
        ]

    @rx.var
    def summary(self) -> str:
        total = len(self._users)
        active = sum(1 for u in self._users if u["is_active"])
        return f"{total} {'conta' if total == 1 else 'contas'} · {active} {'ativa' if active == 1 else 'ativas'}"

    @rx.var
    def truncated(self) -> bool:
        return len(self._users) >= MAX_USERS

    # ---------- Diálogo ----------

    def _find(self, user_id: int) -> dict | None:
        return next((u for u in self._users if u["id"] == user_id), None)

    @rx.event
    def open_edit(self, user_id: int):
        user = self._find(user_id)
        if user is None or user_id == self._me or self.saving:
            return
        self.edit_open, self.confirming = True, False
        self.edit_id, self.edit_role, self.edit_active = user_id, user["role"], user["is_active"]
        self.edit_reason = self.edit_error = ""
        self.notice = ""

    @rx.event
    def set_edit_open(self, value: bool):
        if not value and not self.saving:
            self._close()

    @rx.event
    def capture_role(self, label: str):
        if label in ROLE_BY_LABEL and not self.saving:
            self.edit_role, self.confirming = ROLE_BY_LABEL[label], False

    @rx.event
    def capture_active(self, value: bool):
        if not self.saving:
            self.edit_active, self.confirming = bool(value), False

    @rx.event
    def capture_reason(self, value: str):
        if not self.saving:
            self.edit_reason = value[:500]

    @rx.var
    def edit_user(self) -> dict[str, str]:
        user = self._find(self.edit_id)
        if user is None:
            return {"name": "", "email": "", "role_label": "", "active_label": ""}
        return {
            "name": user["name"] or "(sem nome)",
            "email": user["email"],
            "role_label": ROLES[user["role"]],
            "active_label": "Ativa" if user["is_active"] else "Desativada",
        }

    @rx.var
    def edit_role_label(self) -> str:
        return ROLES.get(self.edit_role, "")

    @rx.var
    def role_options(self) -> list[str]:
        return list(ROLES.values())

    @rx.event
    async def submit_edit(self):
        if self.saving or not self.edit_open:
            return
        user = self._find(self.edit_id)
        if user is None:
            self._close()
            return
        if (user["role"], user["is_active"]) == (self.edit_role, self.edit_active):
            self.edit_error = "Nenhuma alteração informada."
            return
        try:
            reason = validar_motivo(self.edit_reason)
        except ValueError as error:
            self.edit_error = str(error)
            return
        if user["is_active"] and not self.edit_active and not self.confirming:
            self.confirming, self.edit_error = True, ""
            return
        self.saving, self.edit_error = True, ""
        revision, context, uncertain = self._revision, None, False
        target, role, active = self.edit_id, self.edit_role, self.edit_active
        yield
        try:
            context = await self._authorize(fresh=True)
            if context is None:
                self._close()
                return
            updated = await update_user(context[1][2], target, role, active, reason)
            if self._current(*context):
                self._users = [updated if u["id"] == target else u for u in self._users]
                self._close()
                self.notice = "Conta atualizada."
        except (UserError, FineError) as error:
            if revision != self._revision or (context is not None and not self._current(*context)):
                return
            if error.category in {"authentication", "authorization"}:
                self._close()
                await self._show_user_error(error)
                if error.category == "authorization":
                    self.state, self._users = "forbidden", []
                return
            self.confirming = False
            self.edit_error = getattr(error, "detail", "") or MESSAGES.get(error.category, MESSAGES["unavailable"])
            if error.category == "unknown":
                # Resultado incerto: fecha e relê a lista em vez de repetir a escrita.
                self._close()
                uncertain = True
        finally:
            if revision == self._revision:
                self.saving = False
        if uncertain and revision == self._revision:
            async for update in self._load():
                yield update
            if self.state == "ready":
                self.notice = UNCERTAIN

    @rx.event
    def cancel_confirm(self):
        if not self.saving:
            self.confirming = False
