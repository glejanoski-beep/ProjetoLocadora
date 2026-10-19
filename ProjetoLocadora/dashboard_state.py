"""Estado isolado do resumo integrado à revisão privada da sessão."""

import reflex as rx

from ProjetoLocadora.dashboard_client import (
    DashboardErrorCategory,
    XanoDashboardError,
    get_dashboard_summary_xano,
)
from ProjetoLocadora.xano_client import get_me_xano, is_authorized_employee


class DashboardState(rx.State):
    status: str = "initial"
    loading: bool = False
    total_filmes: int | None = None
    total_exemplares: int | None = None
    generated_at: str = ""
    message: str = ""
    _revision: int = 0
    _request_id: int = 0

    def _clear_values(self) -> None:
        self.total_filmes = None
        self.total_exemplares = None
        self.generated_at = ""
        self.message = ""

    def _invalidate(self) -> None:
        """Ponto de integração futuro para transições locais da sessão."""
        self._revision += 1
        self._request_id += 1
        self._clear_values()
        self.loading = False
        self.status = "initial"

    def _show_error(self, category: DashboardErrorCategory) -> None:
        # Não usar str(error): somente mensagens públicas controladas aqui.
        self._clear_values()
        if category == DashboardErrorCategory.AUTHENTICATION:
            self.status = "unauthenticated"
            self.message = "Entre novamente para consultar o resumo do acervo."
        elif category == DashboardErrorCategory.AUTHORIZATION:
            self.status = "forbidden"
            self.message = "Resumo do acervo restrito a administradores."
        elif category == DashboardErrorCategory.INVALID_RESPONSE:
            self.status = "invalid_response"
            self.message = "O serviço retornou um resumo inválido. Tente atualizar."
        elif category in {
            DashboardErrorCategory.CONNECTION, DashboardErrorCategory.TIMEOUT,
            DashboardErrorCategory.SERVICE,
        }:
            self.status = "unavailable"
            self.message = "Não foi possível consultar o resumo. Tente atualizar."
        else:
            self.status = "error"
            self.message = "A consulta do resumo não está disponível."

    async def _load_summary(self):
        # Antes do primeiro await: bloqueia eventos simultâneos na mesma instância.
        if self.loading:
            return
        self._request_id += 1
        request_id, revision = self._request_id, self._revision
        self._clear_values()
        self.loading = True
        self.status = "loading"
        yield

        # Importação localizada evita que o módulo principal importe a si próprio
        # quando os eventos da Dashboard forem integrados futuramente.
        from ProjetoLocadora.ProjetoLocadora import State

        session = None
        snapshot = None

        def current():
            return (
                request_id == self._request_id and revision == self._revision
                and session is not None and snapshot == (
                    session._user_id, session._user_role, session._xano_auth_token, session._session_revision,
                )
            )

        try:
            session = await self.get_state(State)
            # Token existe somente na sessão original e em variáveis locais
            # durante a requisição; não vira campo de DashboardState.
            snapshot = (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)
            identity, role, token, _ = snapshot
            if not token or not identity:
                self._show_error(DashboardErrorCategory.AUTHENTICATION)
                return
            if role != "admin":
                self._show_error(DashboardErrorCategory.AUTHORIZATION)
                return

            me = await get_me_xano(token)
            if not current():
                return
            if not me or not is_authorized_employee(me) or str(me.get("id", "")) != identity:
                session._clear_session()
                await session._sync_dashboard_session()
                self._show_error(DashboardErrorCategory.AUTHENTICATION)
                yield rx.redirect("/login")
                return
            if me.get("role") != "admin":
                session._set_user(me)
                await session._sync_dashboard_session()
                self._show_error(DashboardErrorCategory.AUTHORIZATION)
                return

            summary = await get_dashboard_summary_xano(token)
            if not current():
                return
            self.total_filmes = summary["total_filmes"]
            self.total_exemplares = summary["total_exemplares"]
            self.generated_at = summary["generated_at"]
            self.status = "success"
        except XanoDashboardError as error:
            if current():
                if error.category == DashboardErrorCategory.AUTHENTICATION:
                    session._clear_session()
                    await session._sync_dashboard_session()
                self._show_error(error.category)
                if error.category == DashboardErrorCategory.AUTHENTICATION:
                    yield rx.redirect("/login")
        except Exception:
            if request_id == self._request_id and revision == self._revision:
                if session is None or current():
                    self._show_error(DashboardErrorCategory.UNEXPECTED_STATUS)
        finally:
            if request_id == self._request_id and revision == self._revision:
                if snapshot is not None and not current():
                    self._clear_values()
                    self.status = "initial"
                self.loading = False

    @rx.event
    async def load_summary(self):
        async for update in self._load_summary():
            yield update

    @rx.event
    async def refresh_summary(self):
        # A mesma rotina sempre revalida a sessão; não usa resultado em cache.
        async for update in self._load_summary():
            yield update
