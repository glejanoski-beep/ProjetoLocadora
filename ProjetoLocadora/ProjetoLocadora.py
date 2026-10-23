"""Aplicação principal da locadora com login de funcionários em Reflex."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, TypedDict

import reflex as rx

from ProjetoLocadora.dashboard_state import DashboardState
from ProjetoLocadora.dashboard import (
    customer_list_panel,
    customer_metric_card,
    customer_situation_panel,
    empty_metric_card,
    genre_panel,
    movement_panel,
    overdue_panel,
    rental_metric_card,
    top_customers_panel,
    render_acervo_summary,
    render_summary_toolbar,
    user_initials,
)
from ProjetoLocadora.locacoes_state import LocacoesState
from ProjetoLocadora.locacoes_ui import (
    registration as render_rental_registration,
    detail as render_rental_detail,
)
from ProjetoLocadora.catalogo_filmes import (
    CAPA_ACCEPT,
    CAPA_MAX_BYTES,
    CLASSIFICACOES,
    STATUS_FILME,
    Filme,
    FilmeCatalogo,
    centavos_para_reais,
    validar_capa,
    validar_filme,
    validar_link_capa,
)
from ProjetoLocadora.clientes import (
    ClienteDetalhe,
    ClienteResumo,
    validar_bloqueio_manual,
    validar_cliente,
)
from ProjetoLocadora.exemplares import Exemplar, validar_exemplar
from ProjetoLocadora.xano_client import (
    GENERIC_AUTH_ERROR,
    XanoCatalogError,
    XanoCustomerError,
    XanoExemplarError,
    consume_password_reset_token,
    create_film_xano,
    create_customer_xano,
    create_exemplar_xano,
    get_customer_xano,
    get_film_xano,
    XanoSessionUnavailable,
    get_me_xano,
    is_authorized_employee,
    list_films_xano,
    list_customers_xano,
    list_exemplares_xano,
    login_xano,
    remove_film_cover_xano,
    request_password_reset,
    set_film_cover_link_xano,
    update_film_xano,
    upload_film_cover_xano,
    update_customer_xano,
    update_password_xano,
    set_customer_manual_block_xano,
)

LOGIN_REQUIRED_ERROR = "Informe login e senha para continuar."
RESET_EMAIL_ERROR = "Informe um e-mail válido."
RESET_GENERIC_MESSAGE = (
    "Se o e-mail estiver cadastrado, enviaremos um link para redefinição."
)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


EXEMPLAR_FILTER_ALL = "Todos os filmes"


class ExemplarGrupo(TypedDict):
    """Exemplares de um filme, para apresentação agrupada."""

    filme_id: int
    titulo: str
    detalhe: str
    count: int
    unidade: str
    exemplares: list[Exemplar]
    opcao: str
    tom: int
    pode_adicionar: bool
    # Mesma capa do catálogo de filmes; vazia mantém o gradiente.
    capa_url: str


class ClienteLinha(ClienteResumo):
    """Linha da lista: resumo do servidor mais as iniciais para o avatar."""

    iniciais: str


# Plano do Xano: 10 requisições a cada 20 s. Leituras reaproveitam auth/me recente.
SESSION_CHECK_REUSE_SECONDS = 15


class State(rx.State):
    """Estado de autenticação do backoffice e sessão do funcionário."""

    is_loading: bool = False
    login_submitting: bool = False
    error_message: str = ""
    password_visible: bool = False
    reset_dialog_open: bool = False
    reset_loading: bool = False
    _login_email: str = ""
    _login_password: str = ""
    _session_revision: int = 0
    # Última conferência bem-sucedida de auth/me, presa a esta sessão.
    _me_verified_at: float = 0.0
    _me_verified_key: str = ""
    _dashboard_synced_revision: int = 0
    _xano_auth_token: str = ""
    _user_id: str = ""
    _user_name: str = ""
    _user_email: str = ""
    _user_role: str = ""
    _reset_request_email: str = ""
    _reset_email: str = ""
    _reset_auth_token: str = ""
    _new_password: str = ""
    _confirm_new_password: str = ""
    reset_link_ready: bool = False
    reset_message: str = ""
    reset_message_is_error: bool = False
    films: list[FilmeCatalogo] = []
    films_loading: bool = False
    films_error: str = ""
    films_success: str = ""
    title_search: str = ""
    genre_filter: str = ""
    film_status_filter: str = "all"
    form_loading: bool = False
    form_error: str = ""
    form_title: str = ""
    form_genre: str = ""
    form_year: str = ""
    form_classification: str = CLASSIFICACOES[0]
    form_rent_price: str = ""
    form_status: str = "active"
    editing_film_id: int = 0
    editing_film: bool = False
    # Capa do filme em edição: gravada direto no Xano, independente de "Salvar alterações".
    form_cover_url: str = ""
    form_cover_link: str = ""
    cover_loading: bool = False
    cover_error: str = ""
    cover_success: str = ""
    customers: list[ClienteResumo] = []
    customers_loading: bool = False
    customers_error: str = ""
    customers_success: str = ""
    customer_name_search: str = ""
    customer_cpf_search: str = ""
    customers_page: int = 1
    customers_per_page: int = 20
    customers_total: int = 0
    customer_form_loading: bool = False
    customer_form_error: str = ""
    customer_form_name: str = ""
    customer_form_cpf: str = ""
    customer_form_email: str = ""
    customer_form_phone: str = ""
    customer_form_status: str = "active"
    editing_customer_id: int = 0
    editing_customer: bool = False
    customer_detail: ClienteDetalhe | None = None
    customer_detail_loading: bool = False
    customer_detail_error: str = ""
    customer_block_reason: str = ""
    customer_block_loading: bool = False
    exemplares: list[Exemplar] = []
    exemplares_loading: bool = False
    exemplares_error: str = ""
    exemplares_success: str = ""
    exemplar_identifier: str = ""
    exemplar_film_selection: str = ""
    exemplar_films: list[Filme] = []
    # Capa por id do filme, para todos os perfis; não altera a apresentação do member.
    exemplar_covers: dict[int, str] = {}
    exemplar_films_error: str = ""
    exemplar_form_error: str = ""
    exemplar_form_loading: bool = False
    exemplar_search: str = ""
    exemplar_film_filter: str = EXEMPLAR_FILTER_ALL
    exemplar_dialog_open: bool = False

    @rx.var
    def visible_films(self) -> list[FilmeCatalogo]:
        if self.film_status_filter == "all":
            return self.films
        return [film for film in self.films if film["status"] == self.film_status_filter]

    @rx.var
    def has_films(self) -> bool:
        return bool(self.films)

    @rx.var
    def has_customers(self) -> bool:
        return bool(self.customers)

    @rx.var
    def has_exemplares(self) -> bool:
        return bool(self.exemplares)

    @rx.var
    def exemplar_film_options(self) -> list[str]:
        return [
            f"{film['id']} | {film['titulo']}"
            for film in self.exemplar_films
        ]

    def _exemplar_film_entries(self) -> list[tuple[int, str, Filme | None]]:
        """Filmes na ordem de exibição: lista de filmes (admin) e, depois, só os com exemplares."""
        films = {film["id"]: film for film in self.exemplar_films}
        titles: dict[int, str] = {}
        for exemplar in self.exemplares:
            titles.setdefault(exemplar["filme_id"], exemplar["filme_titulo"])
        entries: list[tuple[int, str, Filme | None]] = [
            (film["id"], film["titulo"], film) for film in self.exemplar_films
        ]
        entries += [
            (film_id, title, None)
            for film_id, title in titles.items()
            if film_id not in films
        ]
        return entries

    @rx.var
    def exemplar_filter_options(self) -> list[str]:
        return [
            EXEMPLAR_FILTER_ALL,
            *[
                f"{film_id} | {title}"
                for film_id, title, _ in self._exemplar_film_entries()
            ],
        ]

    @rx.var
    def exemplar_groups(self) -> list[ExemplarGrupo]:
        search = self.exemplar_search.strip().lower()
        by_film: dict[int, list[Exemplar]] = {}
        for exemplar in self.exemplares:
            by_film.setdefault(exemplar["filme_id"], []).append(exemplar)

        groups: list[ExemplarGrupo] = []
        for film_id, title, film in self._exemplar_film_entries():
            option = f"{film_id} | {title}"
            if self.exemplar_film_filter != EXEMPLAR_FILTER_ALL and (
                self.exemplar_film_filter != option
            ):
                continue
            items = by_film.get(film_id, [])
            if search:
                items = [
                    item for item in items if search in item["identificador"].lower()
                ]
                if not items:
                    continue
            groups.append(
                {
                    "filme_id": film_id,
                    "titulo": title,
                    "detalhe": (
                        f"{film['genero']} · {film['ano_lancamento']}" if film else ""
                    ),
                    "count": len(items),
                    "unidade": "exemplar" if len(items) == 1 else "exemplares",
                    "exemplares": items,
                    "opcao": option,
                    "tom": film_id % 5,
                    "pode_adicionar": film is not None,
                    "capa_url": self.exemplar_covers.get(film_id, ""),
                }
            )
        return groups

    @rx.var
    def exemplar_summary(self) -> str:
        total = len(self.exemplares)
        text = f"{total} {'exemplar' if total == 1 else 'exemplares'}"
        if self.exemplar_films:
            film_ids = {film["id"] for film in self.exemplar_films}
            with_copy = len({item["filme_id"] for item in self.exemplares} & film_ids)
            films_total = len(film_ids)
            text += (
                f" · {with_copy} de {films_total} "
                f"{'filme' if films_total == 1 else 'filmes'} com cópia"
            )
        return text

    @rx.var
    def customers_view(self) -> list[ClienteLinha]:
        return [
            {**customer, "iniciais": user_initials(customer["nome"]) or "?"}
            for customer in self.customers
        ]

    @rx.var
    def customer_detail_initials(self) -> str:
        if self.customer_detail is None:
            return ""
        return user_initials(self.customer_detail["nome"]) or "?"

    @rx.var
    def customers_has_previous_page(self) -> bool:
        return self.customers_page > 1

    @rx.var
    def customers_has_next_page(self) -> bool:
        return self.customers_page * self.customers_per_page < self.customers_total

    @rx.var
    def customer_detail_loaded(self) -> bool:
        return self.customer_detail is not None

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(self._xano_auth_token and self._user_id)

    @rx.var
    def user_id(self) -> str:
        return self._user_id

    @rx.var
    def user_name(self) -> str:
        return self._user_name

    @rx.var
    def user_email(self) -> str:
        return self._user_email

    @rx.var
    def user_role(self) -> str:
        return self._user_role

    @rx.var
    def user_role_label(self) -> str:
        return "Administrador" if self._user_role == "admin" else "Funcionário"

    @rx.var
    def user_initials(self) -> str:
        return user_initials(self._user_name)

    @rx.var
    def password_input_type(self) -> str:
        return "text" if self.password_visible else "password"

    @rx.var
    def password_toggle_label(self) -> str:
        return "Ocultar senha" if self.password_visible else "Mostrar senha"

    def capture_login_email(self, value: str) -> None:
        self._login_email = value

    def capture_login_password(self, value: str) -> None:
        self._login_password = value

    def toggle_password_visibility(self) -> None:
        self.password_visible = not self.password_visible

    def set_reset_dialog_open(self, is_open: bool) -> None:
        self.reset_dialog_open = is_open
        if not is_open:
            self._reset_request_email = ""
            self.reset_message = ""
            self.reset_message_is_error = False

    def capture_reset_request_email(self, value: str) -> None:
        self._reset_request_email = value

    def capture_new_password(self, value: str) -> None:
        self._new_password = value

    def capture_confirm_new_password(self, value: str) -> None:
        self._confirm_new_password = value

    def capture_title_search(self, value: str) -> None:
        self.title_search = value

    def capture_genre_filter(self, value: str) -> None:
        self.genre_filter = value

    def capture_film_status_filter(self, value: str) -> None:
        if value in ("all", *STATUS_FILME):
            self.film_status_filter = value

    async def apply_film_filters(self):
        self.films_success = ""
        return await self.load_films()

    def capture_film_title(self, value: str) -> None:
        self.form_title = value

    def capture_film_genre(self, value: str) -> None:
        self.form_genre = value

    def capture_film_year(self, value: str) -> None:
        self.form_year = value

    def capture_film_classification(self, value: str) -> None:
        self.form_classification = value

    def capture_film_rent_price(self, value: str) -> None:
        self.form_rent_price = value

    def capture_film_status(self, value: str) -> None:
        self.form_status = value

    def capture_customer_name_search(self, value: str) -> None:
        self.customer_name_search = value

    def capture_customer_cpf_search(self, value: str) -> None:
        self.customer_cpf_search = value

    def capture_customer_name(self, value: str) -> None:
        self.customer_form_name = value

    def capture_customer_cpf(self, value: str) -> None:
        self.customer_form_cpf = value

    def capture_customer_email(self, value: str) -> None:
        self.customer_form_email = value

    def capture_customer_phone(self, value: str) -> None:
        self.customer_form_phone = value

    def capture_customer_status(self, value: str) -> None:
        self.customer_form_status = value

    def capture_customer_block_reason(self, value: str) -> None:
        self.customer_block_reason = value

    def capture_exemplar_identifier(self, value: str) -> None:
        self.exemplar_identifier = value

    def capture_exemplar_film_selection(self, value: str) -> None:
        self.exemplar_film_selection = value

    def capture_exemplar_search(self, value: str) -> None:
        self.exemplar_search = value

    def capture_exemplar_film_filter(self, value: str) -> None:
        self.exemplar_film_filter = value

    def set_exemplar_dialog_open(self, is_open: bool) -> None:
        if is_open and self._user_role != "admin":
            return
        self.exemplar_dialog_open = is_open
        self.exemplar_form_error = ""
        if not is_open:
            self.exemplar_identifier = ""
            self.exemplar_film_selection = ""

    def _session_check_key(self) -> str:
        """Identidade exata da sessão: token, conta, papel e revisão."""
        if not self._xano_auth_token or not self._user_id:
            return ""
        digest = hashlib.sha256(self._xano_auth_token.encode("utf-8")).hexdigest()
        return f"{digest}:{self._user_id}:{self._user_role}:{self._session_revision}"

    def _mark_session_verified(self) -> None:
        self._me_verified_key = self._session_check_key()
        self._me_verified_at = time.monotonic() if self._me_verified_key else 0.0

    def _forget_session_check(self) -> None:
        self._me_verified_at = 0.0
        self._me_verified_key = ""

    def _recently_verified(self) -> bool:
        """Leituras podem reaproveitar um auth/me de até 15 s desta mesma sessão.

        Não substitui a autorização do Xano, que confere token e papel em cada
        endpoint; escritas sempre fazem uma conferência nova.
        """
        key = self._session_check_key()
        age = time.monotonic() - self._me_verified_at
        return bool(key) and key == self._me_verified_key and 0 <= age < SESSION_CHECK_REUSE_SECONDS

    def _clear_session(self) -> None:
        self._forget_session_check()
        self._session_revision += 1
        self._login_email = ""
        self._login_password = ""
        self._xano_auth_token = ""
        self._user_id = ""
        self._user_name = ""
        self._user_email = ""
        self._user_role = ""
        self.error_message = ""

    async def _sync_dashboard_session(self) -> None:
        if self._dashboard_synced_revision != self._session_revision:
            dashboard = await self.get_state(DashboardState)
            dashboard._invalidate()
            rentals = await self.get_state(LocacoesState)
            rentals._invalidate()
            self._dashboard_synced_revision = self._session_revision

    def _set_user(self, me: dict[str, object]) -> None:
        if (self._user_id, self._user_role) != (
            str(me.get("id", "")), str(me.get("role", "")),
        ):
            self._forget_session_check()
            self._session_revision += 1
        self._user_id = str(me.get("id", ""))
        self._user_name = str(me.get("name", ""))
        self._user_email = str(me.get("email", ""))
        self._user_role = str(me.get("role", ""))

    def _clear_film_form(self) -> None:
        self.form_error = ""
        self.form_title = ""
        self.form_genre = ""
        self.form_year = ""
        self.form_classification = CLASSIFICACOES[0]
        self.form_rent_price = ""
        self.form_status = "active"
        self.editing_film_id = 0
        self.form_cover_url = ""
        self.form_cover_link = ""
        self.cover_loading = False
        self.cover_error = ""
        self.cover_success = ""

    def _clear_customer_form(self) -> None:
        self.customer_form_error = ""
        self.customer_form_name = ""
        self.customer_form_cpf = ""
        self.customer_form_email = ""
        self.customer_form_phone = ""
        self.customer_form_status = "active"
        self.editing_customer_id = 0

    def _require_customer_admin(self):
        if not self._xano_auth_token:
            self._clear_session()
            return rx.redirect("/login")
        if self._user_role != "admin":
            return rx.redirect("/clientes")
        return None

    def _require_exemplar_admin(self):
        if not self._xano_auth_token:
            self._clear_session()
            return rx.redirect("/login")
        if self._user_role != "admin":
            return rx.redirect("/exemplares")
        return None

    async def load_exemplares(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")

        self.exemplares_loading = True
        self.exemplares_error = ""
        self.exemplares_success = ""
        try:
            self.exemplares = await list_exemplares_xano(self._xano_auth_token)
        except XanoExemplarError as err:
            self.exemplares_error = err.user_message
            self.exemplares = []
        finally:
            self.exemplares_loading = False

        # O catálogo traz as capas para todos; a lista de manutenção (gênero, ano,
        # filmes sem cópia) continua só para administradores.
        is_admin = self._user_role == "admin"
        self.exemplar_films_error = ""
        self.exemplar_films = []
        self.exemplar_covers = {}
        try:
            films = await list_films_xano(self._xano_auth_token)
        except XanoCatalogError as err:
            if is_admin:
                self.exemplar_films_error = err.user_message
            # Para member, sem catálogo a lista segue apenas sem capas.
        else:
            self.exemplar_covers = {
                film["id"]: film.get("capa_url", "") for film in films if film.get("capa_url")
            }
            if is_admin:
                self.exemplar_films = films

    async def submit_exemplar(self):
        redirect = self._require_exemplar_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect

        self.exemplar_form_error = ""
        selected_film_id: int | None = None
        try:
            selected_film_id = int(self.exemplar_film_selection.split(" | ", 1)[0])
        except (ValueError, IndexError):
            pass

        errors, payload = validar_exemplar(
            identificador=self.exemplar_identifier,
            filme_id=selected_film_id,
        )
        if errors:
            self.exemplar_form_error = next(iter(errors.values()))
            return

        self.exemplar_form_loading = True
        try:
            exemplar = await create_exemplar_xano(
                self._xano_auth_token,
                payload,
            )
        except XanoExemplarError as err:
            self.exemplar_form_error = err.user_message
        else:
            self.exemplares = [exemplar, *self.exemplares]
            self.exemplares_success = "Exemplar cadastrado com sucesso."
            self.exemplar_identifier = ""
            self.exemplar_film_selection = ""
            self.exemplar_dialog_open = False
        finally:
            self.exemplar_form_loading = False

    async def load_customers(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")
        self.customers_loading = True
        self.customers_error = ""
        try:
            result = await list_customers_xano(
                self._xano_auth_token,
                nome=self.customer_name_search,
                cpf=self.customer_cpf_search,
                page=self.customers_page,
                per_page=self.customers_per_page,
            )
        except XanoCustomerError as err:
            self.customers_error = err.user_message
            self.customers = []
            self.customers_total = 0
        else:
            self.customers = result["items"]
            self.customers_page = result["page"]
            self.customers_per_page = result["per_page"]
            self.customers_total = result["total"]
        finally:
            self.customers_loading = False

    async def apply_customer_filters(self):
        self.customers_page = 1
        self.customers_success = ""
        return await self.load_customers()

    async def previous_customers_page(self):
        if self.customers_page > 1:
            self.customers_page -= 1
            return await self.load_customers()

    async def next_customers_page(self):
        if self.customers_page * self.customers_per_page < self.customers_total:
            self.customers_page += 1
            return await self.load_customers()

    async def load_new_customer(self):
        redirect = self._require_customer_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        self._clear_customer_form()
        self.editing_customer = False
        self.customers_success = ""

    def _route_customer_id(self) -> int:
        value = self.router.page.params.get("customer_id", "")
        return int(value) if value.isdecimal() else 0

    async def load_customer_detail(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")
        customer_id = self._route_customer_id()
        self.customer_detail = None
        self.customer_detail_error = ""
        self.customer_block_reason = ""
        if not customer_id:
            self.customer_detail_error = "Identificador do cliente inválido."
            return
        self.customer_detail_loading = True
        try:
            self.customer_detail = await get_customer_xano(
                self._xano_auth_token, customer_id
            )
        except XanoCustomerError as err:
            self.customer_detail_error = err.user_message
        finally:
            self.customer_detail_loading = False

    async def load_customer_for_edit(self):
        redirect = self._require_customer_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        self._clear_customer_form()
        self.editing_customer = True
        self.customers_success = ""
        customer_id = self._route_customer_id()
        if not customer_id:
            self.customer_form_error = "Identificador do cliente inválido."
            return
        self.customer_form_loading = True
        try:
            customer = await get_customer_xano(self._xano_auth_token, customer_id)
        except XanoCustomerError as err:
            self.customer_form_error = err.user_message
        else:
            self.editing_customer_id = customer["id"]
            self.customer_form_name = customer["nome"]
            self.customer_form_cpf = customer["cpf"]
            self.customer_form_email = customer["email"] or ""
            self.customer_form_phone = customer["telefone"] or ""
            self.customer_form_status = customer["status"]
        finally:
            self.customer_form_loading = False

    async def submit_customer(self):
        redirect = self._require_customer_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        self.customer_form_error = ""
        errors, payload = validar_cliente(
            nome=self.customer_form_name,
            cpf=self.customer_form_cpf,
            email=self.customer_form_email,
            telefone=self.customer_form_phone,
            status=self.customer_form_status,
        )
        if errors:
            self.customer_form_error = next(iter(errors.values()))
            return
        self.customer_form_loading = True
        try:
            if self.editing_customer:
                await update_customer_xano(
                    self._xano_auth_token, self.editing_customer_id, payload
                )
                self.customers_success = "Cliente atualizado com sucesso."
            else:
                payload.pop("status")
                await create_customer_xano(self._xano_auth_token, payload)
                self.customers_success = "Cliente cadastrado com sucesso."
        except XanoCustomerError as err:
            self.customer_form_error = err.user_message
        else:
            self._clear_customer_form()
            return rx.redirect("/clientes")
        finally:
            self.customer_form_loading = False

    async def toggle_customer_manual_block(self):
        redirect = self._require_customer_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        if self.customer_detail is None:
            self.customer_detail_error = "Cliente não carregado."
            return
        bloqueado = not self.customer_detail["bloqueio_manual_ativo"]
        errors, payload = validar_bloqueio_manual(
            bloqueado=bloqueado, motivo=self.customer_block_reason
        )
        if errors:
            self.customer_detail_error = next(iter(errors.values()))
            return
        self.customer_block_loading = True
        self.customer_detail_error = ""
        try:
            self.customer_detail = await set_customer_manual_block_xano(
                self._xano_auth_token,
                self.customer_detail["id"],
                bloqueado=bool(payload["bloqueado"]),
                motivo=payload["motivo"] if isinstance(payload["motivo"], str) else None,
            )
        except XanoCustomerError as err:
            self.customer_detail_error = err.user_message
        else:
            self.customer_block_reason = ""
            self.customers_success = (
                "Bloqueio manual aplicado com sucesso."
                if bloqueado
                else "Bloqueio manual removido com sucesso."
            )
        finally:
            self.customer_block_loading = False

    def _require_catalog_admin(self):
        if not self._xano_auth_token:
            self._clear_session()
            return rx.redirect("/login")
        if self._user_role != "admin":
            return rx.redirect("/filmes")
        return None

    async def load_films(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")

        self.films_loading = True
        self.films_error = ""
        try:
            films = await list_films_xano(
                self._xano_auth_token,
                titulo=self.title_search,
                genero=self.genre_filter,
            )
        except XanoCatalogError as err:
            self.films_error = err.user_message
            self.films = []
        else:
            self.films = [
                {
                    **film,
                    "valor_locacao_display": centavos_para_reais(
                        film["valor_locacao_centavos"]
                    ),
                }
                for film in films
            ]
        finally:
            self.films_loading = False

    async def load_new_film(self):
        redirect = self._require_catalog_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        self._clear_film_form()
        self.editing_film = False
        self.films_success = ""

    async def load_film_for_edit(self):
        redirect = self._require_catalog_admin()
        await self._sync_dashboard_session()
        if redirect:
            return redirect
        self._clear_film_form()
        self.editing_film = True
        self.films_success = ""

        film_id_value = self.router.page.params.get("film_id", "")
        if not film_id_value.isdecimal():
            self.form_error = "Identificador do filme inválido."
            return

        self.form_loading = True
        try:
            film = await get_film_xano(
                self._xano_auth_token,
                int(film_id_value),
            )
        except XanoCatalogError as err:
            self.form_error = err.user_message
        else:
            self.editing_film_id = film["id"]
            self.form_title = film["titulo"]
            self.form_genre = film["genero"]
            self.form_year = str(film["ano_lancamento"])
            self.form_classification = film["classificacao"]
            self.form_rent_price = centavos_para_reais(
                film["valor_locacao_centavos"]
            ).removeprefix("R$ ")
            self.form_status = film["status"]
            self.form_cover_url = film.get("capa_url", "")
            self.form_cover_link = film.get("capa_link", "")
        finally:
            self.form_loading = False

    async def _cover_redirect(self):
        """Capa só para administrador com sessão; o Xano confere o papel de novo."""
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")
        if self._user_role != "admin":
            return rx.redirect("/filmes")
        return None

    def _cover_ready(self) -> bool:
        if self.cover_loading:
            return False
        self.cover_error = ""
        self.cover_success = ""
        if not self.editing_film or not self.editing_film_id:
            self.cover_error = "Carregue o filme antes de alterar a capa."
            return False
        return True

    async def upload_film_cover(self, files: list[rx.UploadFile]):
        redirect = await self._cover_redirect()
        if redirect is not None:
            yield redirect
            return
        if not self._cover_ready():
            return
        if len(files) != 1:
            self.cover_error = "Selecione uma única imagem para a capa."
            return
        # Lê no máximo 1 byte além do limite: arquivo maior é recusado sem carregar tudo.
        content = await files[0].read(CAPA_MAX_BYTES + 1)
        try:
            mime, extension = validar_capa(content)
        except ValueError as err:
            self.cover_error = str(err)
            return

        self.cover_loading = True
        yield
        try:
            film = await upload_film_cover_xano(
                self._xano_auth_token, self.editing_film_id, content, mime, extension
            )
        except XanoCatalogError as err:
            self.cover_error = err.user_message
        else:
            self.form_cover_url = film["capa_url"]
            self.cover_success = "Capa atualizada."
        finally:
            self.cover_loading = False

    async def remove_film_cover(self):
        redirect = await self._cover_redirect()
        if redirect is not None:
            yield redirect
            return
        if not self._cover_ready():
            return
        self.cover_loading = True
        yield
        try:
            film = await remove_film_cover_xano(self._xano_auth_token, self.editing_film_id)
        except XanoCatalogError as err:
            self.cover_error = err.user_message
        else:
            self.form_cover_url = film["capa_url"]
            self.form_cover_link = film["capa_link"]
            self.cover_success = "Capa removida."
        finally:
            self.cover_loading = False

    def capture_cover_link(self, value: str):
        self.form_cover_link = value

    async def save_film_cover_link(self):
        redirect = await self._cover_redirect()
        if redirect is not None:
            yield redirect
            return
        if not self._cover_ready():
            return
        try:
            link = validar_link_capa(self.form_cover_link)
        except ValueError as err:
            self.cover_error = str(err)
            return
        self.cover_loading = True
        yield
        try:
            film = await set_film_cover_link_xano(self._xano_auth_token, self.editing_film_id, link)
        except XanoCatalogError as err:
            self.cover_error = err.user_message
        else:
            self.form_cover_url = film["capa_url"]
            self.form_cover_link = film["capa_link"]
            self.cover_success = "Link da capa salvo." if link else "Link da capa removido."
        finally:
            self.cover_loading = False

    def reject_film_cover(self, rejections: list[dict[str, Any]]):
        """Recusa do navegador (tipo ou tamanho); nada é enviado ao servidor."""
        self.cover_success = ""
        self.cover_error = "A capa deve ser uma imagem JPEG, PNG ou WebP com até 2 MB."

    async def submit_film(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")
        if self._user_role != "admin":
            return rx.redirect("/filmes")

        self.form_error = ""
        errors, payload = validar_filme(
            titulo=self.form_title,
            genero=self.form_genre,
            ano_lancamento=self.form_year,
            classificacao=self.form_classification,
            valor_locacao=self.form_rent_price,
            status=self.form_status,
        )
        if errors:
            self.form_error = next(iter(errors.values()))
            return

        self.form_loading = True
        try:
            if self.editing_film:
                await update_film_xano(
                    self._xano_auth_token,
                    self.editing_film_id,
                    payload,
                )
                self.films_success = "Filme atualizado com sucesso."
            else:
                payload.pop("status")
                await create_film_xano(self._xano_auth_token, payload)
                self.films_success = "Filme cadastrado com sucesso."
        except XanoCatalogError as err:
            self.form_error = err.user_message
        else:
            self._clear_film_form()
            return rx.redirect("/filmes")
        finally:
            self.form_loading = False

    async def restore_session(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return

        try:
            me = await get_me_xano(self._xano_auth_token)
        except XanoSessionUnavailable:
            # Oscilação de rede: manter o token e deixar a pessoa tentar de novo.
            return
        if not me or not is_authorized_employee(me):
            self._clear_session()
            await self._sync_dashboard_session()
            return

        self._set_user(me)
        await self._sync_dashboard_session()
        return rx.redirect("/backoffice")

    async def require_session(self):
        if not self._xano_auth_token:
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")

        if self._recently_verified():
            await self._sync_dashboard_session()
            return None

        try:
            me = await get_me_xano(self._xano_auth_token)
        except XanoSessionUnavailable as error:
            # Sessão não provada inválida: não desconectar por uma falha transitória.
            if error.retry_after:
                return rx.toast.error(
                    "O Xano atingiu o limite de requisições do plano. "
                    f"Aguarde {error.retry_after} s e atualize a página."
                )
            return rx.toast.error(
                "Não foi possível confirmar sua sessão agora. Atualize a página para tentar novamente."
            )
        if not me or not is_authorized_employee(me):
            self._clear_session()
            await self._sync_dashboard_session()
            return rx.redirect("/login")

        self._set_user(me)
        self._mark_session_verified()
        await self._sync_dashboard_session()

    async def load_dashboard(self):
        redirect = await self.require_session()
        if redirect is not None:
            return redirect
        # Locações e clientes valem para member e admin; o resumo do acervo segue restrito ao admin.
        return [DashboardState.load_summary(), DashboardState.load_rentals(), DashboardState.load_customers()]

    async def load_new_rental(self):
        redirect = await self.require_session()
        if redirect is not None:
            return redirect
        return LocacoesState.load_new()

    async def load_rental_detail(self):
        redirect = await self.require_session()
        if redirect is not None:
            return redirect
        return LocacoesState.load_detail()

    async def submit_login(self, form_data: dict[str, Any]):
        if self.is_loading:
            return
        self._login_email = str(form_data.get("login", ""))
        self._login_password = str(form_data.get("password", ""))
        if not self._login_email.strip() or not self._login_password:
            return await self.handle_login()
        # Atualiza a interface antes da chamada de rede: o estado só é enviado
        # ao navegador quando o handler termina, então a consulta ao Xano
        # roda em um evento encadeado.
        self.login_submitting = True
        self.error_message = ""
        return State.handle_login

    async def handle_login(self):
        if self.is_loading:
            return

        email = self._login_email.strip()
        password = self._login_password
        if not email or not password:
            self._login_password = ""
            self.error_message = LOGIN_REQUIRED_ERROR
            return

        self.is_loading = True
        self.error_message = ""
        try:
            auth_data = await login_xano(email, password)
            if not auth_data or not auth_data.get("authToken"):
                self._clear_session()
                await self._sync_dashboard_session()
                self.error_message = GENERIC_AUTH_ERROR
                return

            try:
                me_data = await get_me_xano(auth_data["authToken"])
            except XanoSessionUnavailable:
                me_data = None
            if not me_data or not is_authorized_employee(me_data):
                self._clear_session()
                await self._sync_dashboard_session()
                self.error_message = GENERIC_AUTH_ERROR
                return

            self._session_revision += 1
            self._xano_auth_token = auth_data["authToken"]
            self._set_user(me_data)
            self._mark_session_verified()
            await self._sync_dashboard_session()
            return rx.redirect("/backoffice")
        finally:
            password = ""
            self._login_password = ""
            self.is_loading = False
            self.login_submitting = False

    async def logout(self) -> None:
        self._clear_session()
        await self._sync_dashboard_session()
        return rx.redirect("/login")

    async def submit_reset_link(self, form_data: dict[str, Any]) -> None:
        if self.reset_loading:
            return
        self._reset_request_email = str(form_data.get("email", ""))
        await self.request_reset_link()

    async def request_reset_link(self) -> None:
        if self.reset_loading:
            return

        email = self._reset_request_email.strip()
        if not EMAIL_PATTERN.fullmatch(email):
            self.reset_message = RESET_EMAIL_ERROR
            self.reset_message_is_error = True
            return

        self.reset_loading = True
        self.reset_message = RESET_GENERIC_MESSAGE
        self.reset_message_is_error = False
        try:
            await request_password_reset(email)
        finally:
            self._reset_request_email = ""
            self.reset_loading = False

    async def consume_reset_link(self) -> None:
        params = self.router.url.query_parameters
        magic_token = params.get("magic_token", "")
        email = params.get("email", "")
        if not magic_token or not email:
            self.reset_message = "O link de redefinição é inválido ou está incompleto."
            self.reset_message_is_error = True
            return

        reset_data = await consume_password_reset_token(magic_token, email)
        if not reset_data or not reset_data.get("authToken"):
            self.reset_message = "O link de redefinição é inválido, expirou ou já foi usado."
            self.reset_message_is_error = True
            return

        self._reset_auth_token = str(reset_data["authToken"])
        self._reset_email = email
        self.reset_link_ready = True
        self.reset_message = "Escolha uma nova senha para sua conta."
        self.reset_message_is_error = False

    async def update_password(self) -> None:
        password = self._new_password
        confirm_password = self._confirm_new_password
        if len(password) < 8 or password != confirm_password:
            self.reset_message = "Informe duas senhas iguais com pelo menos 8 caracteres."
            self.reset_message_is_error = True
            self._reset_auth_token = ""
            self._new_password = ""
            self._confirm_new_password = ""
            self.reset_link_ready = False
            return

        updated = await update_password_xano(
            self._reset_auth_token,
            password,
            confirm_password,
        )
        self._reset_auth_token = ""
        self._new_password = ""
        self._confirm_new_password = ""
        self.reset_link_ready = False
        if not updated:
            self.reset_message = "Não foi possível atualizar a senha. Solicite um novo link."
            self.reset_message_is_error = True
            return

        return rx.redirect("/login")


LOGIN_POSTERS = (
    "01-caligari.JPG",
    "02-general.png",
    "03-charade.jpg",
    "04-hisgirlfriday.jpg",
    "05-detour.jpg",
    "06-plan9.jpg",
    "07-carnival.jpg",
    "08-kid.jpg",
    "10-phantom.jpg",
    "11-sherlockjr.jpg",
    "12-safetylast.jpg",
    "13-goldrush.jpg",
    "14-hauntedhill.jpg",
    "15-beatthedevil.jpg",
    "16-hitchhiker.jpeg",
)
LOGIN_WALL_TILES = 60
LOGIN_SUPPORT_ID = "login-support"


def login_poster_wall() -> rx.Component:
    """Parede decorativa de cartazes, inclinada, atrás do painel."""

    return rx.box(
        rx.box(
            *[
                rx.el.img(
                    src=f"/login-capas/{LOGIN_POSTERS[(index * 4) % len(LOGIN_POSTERS)]}",
                    alt="",
                    decoding="async",
                    class_name="vitrine-login__poster",
                )
                for index in range(LOGIN_WALL_TILES)
            ],
            class_name="vitrine-login__wall-grid",
        ),
        class_name="vitrine-login__wall",
        aria_hidden="true",
    )


def login_backdrop() -> rx.Component:
    """Fundo completo: cartazes, camada escura e vinheta."""

    return rx.box(
        login_poster_wall(),
        rx.box(class_name="vitrine-login__veil"),
        rx.box(class_name="vitrine-login__vignette"),
        class_name="vitrine-login__backdrop",
        aria_hidden="true",
    )


def cassette_badge() -> rx.Component:
    """Marca visual da locadora: botão de reprodução em moldura clara."""

    return rx.box(
        rx.icon("play", size=18, stroke_width=0, fill="currentColor"),
        class_name="vitrine-login__logo",
        role="img",
        aria_label="Logotipo CINEBYTE LOCADORA",
    )


def login_topbar() -> rx.Component:
    """Identificação da locadora à esquerda e link de ajuda à direita."""

    return rx.el.header(
        rx.box(
            cassette_badge(),
            rx.text(
                rx.text.span("CINEBYTE", class_name="vitrine-login__brand-name"),
                rx.text.span(" LOCADORA", class_name="vitrine-login__brand-tag"),
                class_name="vitrine-login__brand",
            ),
            class_name="vitrine-login__identity",
        ),
        rx.el.a(
            "Ajuda",
            href=f"#{LOGIN_SUPPORT_ID}",
            class_name="vitrine-login__help",
        ),
        class_name="vitrine-login__topbar",
    )


def login_header() -> rx.Component:
    """Título e subtítulo do painel de acesso."""

    return rx.el.header(
        rx.heading(
            "Acesso do funcionário",
            class_name="vitrine-login__title",
        ),
        rx.text(
            "Entre para gerenciar o acervo e os aluguéis.",
            class_name="vitrine-login__subtitle",
        ),
        class_name="vitrine-login__header",
    )


def login_field(
    *,
    label: str,
    field_id: str,
    name: str,
    placeholder: str,
    input_type,
    on_change,
    auto_complete: str,
    trailing: rx.Component | None = None,
) -> rx.Component:
    """Campo reutilizável com label e controle opcional à direita."""

    return rx.box(
        rx.el.label(
            label,
            html_for=field_id,
            class_name="vitrine-login__label",
        ),
        rx.box(
            rx.el.input(
                id=field_id,
                name=name,
                placeholder=placeholder,
                type=input_type,
                auto_complete=auto_complete,
                required=True,
                on_change=on_change,
                aria_describedby="login-error",
                aria_invalid=State.error_message != "",
                class_name=(
                    "vitrine-login__input vitrine-login__input--trailing"
                    if trailing is not None
                    else "vitrine-login__input"
                ),
            ),
            trailing if trailing is not None else rx.fragment(),
            class_name="vitrine-login__field-shell",
        ),
        class_name="vitrine-login__field",
    )


def password_visibility_button() -> rx.Component:
    """Controle acessível que alterna a apresentação da senha."""

    return rx.button(
        rx.cond(State.password_visible, "ocultar", "mostrar"),
        type="button",
        on_click=State.toggle_password_visibility,
        aria_label=State.password_toggle_label,
        title=State.password_toggle_label,
        class_name="vitrine-login__password-toggle",
    )


def login_error_region() -> rx.Component:
    """Reserva espaço estável para validação e falhas de autenticação."""

    return rx.box(
        rx.cond(
            State.error_message != "",
            rx.text(
                State.error_message,
                role="alert",
                aria_live="assertive",
                class_name="vitrine-login__error-text",
            ),
            rx.text(
                " ",
                aria_hidden="true",
                class_name="vitrine-login__error-text",
            ),
        ),
        id="login-error",
        class_name="vitrine-login__error-slot",
    )


def password_recovery_dialog() -> rx.Component:
    """Diálogo de recuperação ligado ao fluxo real de magic link."""

    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                "Esqueci minha senha",
                type="button",
                class_name="vitrine-login__forgot",
            )
        ),
        rx.dialog.content(
            rx.dialog.title(
                "Recuperar acesso",
                class_name="vitrine-reset__title",
            ),
            rx.dialog.description(
                "Informe seu e-mail para receber um link de redefinição.",
                class_name="vitrine-reset__description",
            ),
            rx.form(
                rx.box(
                    rx.el.label(
                        "E-mail",
                        html_for="reset-email",
                        class_name="vitrine-login__label",
                    ),
                    rx.el.input(
                        id="reset-email",
                        name="email",
                        type="email",
                        placeholder="Digite seu e-mail",
                        auto_complete="email",
                        required=True,
                        on_change=State.capture_reset_request_email,
                        aria_describedby="reset-message",
                        class_name="vitrine-login__input",
                    ),
                    class_name="vitrine-login__field",
                ),
                rx.box(
                    rx.cond(
                        State.reset_message != "",
                        rx.text(
                            State.reset_message,
                            role=rx.cond(
                                State.reset_message_is_error,
                                "alert",
                                "status",
                            ),
                            aria_live="polite",
                            class_name=rx.cond(
                                State.reset_message_is_error,
                                "vitrine-reset__message vitrine-reset__message--error",
                                "vitrine-reset__message",
                            ),
                        ),
                        rx.text(" ", aria_hidden="true"),
                    ),
                    id="reset-message",
                    class_name="vitrine-reset__message-slot",
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancelar",
                            type="button",
                            class_name="vitrine-reset__cancel",
                        )
                    ),
                    rx.button(
                        "Enviar link",
                        type="submit",
                        loading=State.reset_loading,
                        disabled=State.reset_loading,
                        class_name="vitrine-reset__submit",
                    ),
                    class_name="vitrine-reset__actions",
                ),
                on_submit=State.submit_reset_link,
                no_validate=True,
                reset_on_submit=False,
                class_name="vitrine-reset__form",
            ),
            class_name="vitrine-reset-dialog",
        ),
        open=State.reset_dialog_open,
        on_open_change=State.set_reset_dialog_open,
    )


def login_form() -> rx.Component:
    """Formulário único de login, acionável por clique ou Enter."""

    return rx.form(
        login_field(
            label="E-mail",
            field_id="login-identifier",
            name="login",
            placeholder="nome@exemplo.com",
            input_type="email",
            on_change=State.capture_login_email,
            auto_complete="username",
        ),
        login_field(
            label="Senha",
            field_id="login-password",
            name="password",
            placeholder="Sua senha",
            input_type=State.password_input_type,
            on_change=State.capture_login_password,
            auto_complete="current-password",
            trailing=password_visibility_button(),
        ),
        rx.box(
            password_recovery_dialog(),
            class_name="vitrine-login__options",
        ),
        login_error_region(),
        rx.button(
            rx.cond(
                State.is_loading | State.login_submitting,
                rx.fragment(
                    rx.el.span(class_name="vitrine-login__spinner", aria_hidden="true"),
                    "Entrando…",
                ),
                "Entrar",
            ),
            type="submit",
            disabled=State.is_loading | State.login_submitting,
            aria_busy=State.is_loading | State.login_submitting,
            aria_label="Entrar no sistema",
            class_name="vitrine-login__submit",
        ),
        on_submit=State.submit_login,
        no_validate=True,
        reset_on_submit=False,
        class_name="vitrine-login__form",
    )


def login_footer() -> rx.Component:
    """Orientação de suporte, alvo do link Ajuda."""

    return rx.el.footer(
        rx.text(
            "Sem acesso? Fale com o administrador da sua loja.",
            id=LOGIN_SUPPORT_ID,
            tab_index=-1,
            class_name="vitrine-login__support",
        ),
        class_name="vitrine-login__footer",
    )


def login_panel() -> rx.Component:
    """Painel central de vidro com o formulário completo."""

    return rx.el.section(
        login_header(),
        login_form(),
        login_footer(),
        class_name="vitrine-login__panel",
        aria_label="Acesso do funcionário",
    )


@rx.page(route="/login", on_load=State.restore_session)
def login_page() -> rx.Component:
    return rx.el.main(
        login_backdrop(),
        login_topbar(),
        login_panel(),
        rx.text(
            "Acesso restrito a funcionários da CINEBYTE LOCADORA",
            class_name="vitrine-login__legal",
        ),
        class_name="vitrine-login",
    )


DASHBOARD_NAV_ITEMS = (
    ("Visão geral", "/backoffice"),
    ("Acervo", "/filmes"),
    ("Exemplares", "/exemplares"),
    ("Clientes", "/clientes"),
    ("Locações", "/locacoes/nova"),
)
DASHBOARD_NAV_UPCOMING = ("Multas", "Relatórios")


def dashboard_nav(active: str = "/backoffice") -> rx.Component:
    """Navegação horizontal: páginas existentes são links; as demais ficam desabilitadas."""

    return rx.el.nav(
        *[
            rx.el.a(
                label,
                href=href,
                aria_current="page" if href == active else None,
                class_name=(
                    "vitrine-dash__nav-item vitrine-dash__nav-item--active"
                    if href == active
                    else "vitrine-dash__nav-item"
                ),
            )
            for label, href in DASHBOARD_NAV_ITEMS
        ],
        *[
            rx.el.span(
                label,
                rx.el.span("Em breve", class_name="vitrine-dash__soon"),
                aria_disabled="true",
                class_name="vitrine-dash__nav-item vitrine-dash__nav-item--disabled",
            )
            for label in DASHBOARD_NAV_UPCOMING
        ],
        aria_label="Navegação principal",
        class_name="vitrine-dash__nav",
    )


def dashboard_topbar(active: str = "/backoffice") -> rx.Component:
    """Barra superior: marca CINEBYTE, navegação e identificação do usuário."""

    return rx.el.header(
        rx.box(
            rx.box(
                rx.icon("play", size=18, stroke_width=0, fill="currentColor"),
                class_name="vitrine-dash__logo",
                role="img",
                aria_label="Logotipo CINEBYTE LOCADORA",
            ),
            rx.text(
                rx.text.span("CINEBYTE", class_name="vitrine-dash__brand-name"),
                rx.text.span(" LOCADORA", class_name="vitrine-dash__brand-tag"),
                class_name="vitrine-dash__brand",
            ),
            class_name="vitrine-dash__identity",
        ),
        dashboard_nav(active),
        rx.box(
            rx.box(
                rx.el.span(
                    rx.cond(State.user_name != "", State.user_name, "Funcionário"),
                    class_name="vitrine-dash__user-name",
                ),
                rx.el.span(
                    State.user_role_label,
                    class_name="vitrine-dash__user-role",
                ),
                class_name="vitrine-dash__user-text",
            ),
            rx.box(
                rx.cond(
                    State.user_initials != "",
                    State.user_initials,
                    rx.icon("user", size=16, aria_hidden="true"),
                ),
                class_name="vitrine-dash__avatar",
                aria_hidden="true",
            ),
            rx.button(
                "Sair",
                on_click=State.logout,
                class_name="vitrine-dash__logout",
            ),
            class_name="vitrine-dash__user",
        ),
        class_name="vitrine-dash__topbar",
    )


def dashboard_heading() -> rx.Component:
    """Título da página, contexto do perfil e ações do resumo."""

    return rx.el.section(
        rx.box(
            rx.el.h1("Visão geral", class_name="vitrine-dash__title"),
            rx.el.p(
                rx.cond(
                    State.user_role == "admin",
                    "Painel administrativo · Locadora",
                    "Painel do funcionário · Locadora",
                ),
                class_name="vitrine-dash__subtitle",
            ),
            class_name="vitrine-dash__heading-text",
        ),
        rx.box(
            rx.el.span(State.user_email, class_name="vitrine-dash__email"),
            render_summary_toolbar(State.user_role),
            class_name="vitrine-dash__heading-side",
        ),
        class_name="vitrine-dash__heading",
    )


def render_dashboard() -> rx.Component:
    return rx.el.main(
        dashboard_topbar(),
        dashboard_heading(),
        rx.box(
            render_acervo_summary(State.user_role),
            rental_metric_card(),
            customer_metric_card(),
            empty_metric_card("Multas pendentes", "wallet", "dashboard-multas-pendentes"),
            class_name="vitrine-dash__cards",
        ),
        rx.box(
            movement_panel(),
            genre_panel(State.user_role),
            class_name="vitrine-dash__charts",
        ),
        rx.box(
            customer_list_panel(),
            customer_situation_panel(),
            class_name="vitrine-dash__charts",
        ),
        rx.box(
            overdue_panel(),
            top_customers_panel(),
            class_name="vitrine-dash__charts",
        ),
        class_name="vitrine-dash",
    )


def customer_status_badge(status) -> rx.Component:
    """Situação cadastral (active/inactive), independente do bloqueio manual."""

    return rx.el.span(
        rx.el.span(class_name="vitrine-clientes__dot", aria_hidden="true"),
        rx.cond(status == "active", "Ativo", "Inativo"),
        class_name=rx.cond(
            status == "active",
            "vitrine-clientes__badge vitrine-clientes__badge--active",
            "vitrine-clientes__badge",
        ),
    )


def customer_block_badge(blocked, *, short: bool = False) -> rx.Component:
    """Bloqueio manual, condição separada da situação cadastral."""

    return rx.el.span(
        rx.el.span(class_name="vitrine-clientes__dot", aria_hidden="true"),
        rx.cond(
            blocked,
            "Bloqueado" if short else "Bloqueio manual ativo",
            "Sem bloqueio" if short else "Sem bloqueio manual",
        ),
        class_name=rx.cond(
            blocked,
            "vitrine-clientes__badge vitrine-clientes__badge--blocked",
            "vitrine-clientes__badge",
        ),
    )


def render_customer_card(customer: ClienteLinha) -> rx.Component:
    """Linha da tabela: somente os campos do resumo; sem contato na listagem."""

    return rx.el.tr(
        rx.el.td(
            rx.box(
                rx.el.span(
                    customer["iniciais"],
                    class_name="vitrine-clientes__avatar",
                    aria_hidden="true",
                ),
                rx.el.span(customer["nome"], class_name="vitrine-clientes__name"),
                class_name="vitrine-clientes__person",
            ),
            data_label="Cliente",
        ),
        rx.el.td(
            rx.el.span(customer["cpf_mascarado"], class_name="vitrine-clientes__mono"),
            data_label="CPF",
        ),
        rx.el.td(customer_status_badge(customer["status"]), data_label="Situação"),
        rx.el.td(
            customer_block_badge(customer["bloqueio_manual_ativo"], short=True),
            data_label="Bloqueio manual",
        ),
        rx.el.td(
            rx.el.a(
                "Consultar",
                rx.icon("arrow-right", size=16, stroke_width=1.8, aria_hidden="true"),
                href=f"/clientes/{customer['id']}",
                aria_label="Consultar " + customer["nome"],
                class_name="vitrine-clientes__consult",
            ),
            class_name="vitrine-clientes__action",
        ),
    )


def customers_filters() -> rx.Component:
    return rx.box(
        rx.box(
            rx.icon("search", size=18, stroke_width=1.8, aria_hidden="true"),
            rx.el.input(
                placeholder="Buscar por nome",
                value=State.customer_name_search,
                on_change=State.capture_customer_name_search,
                aria_label="Buscar cliente por nome",
                class_name="vitrine-clientes__input vitrine-clientes__input--icon",
            ),
            class_name="vitrine-clientes__search",
        ),
        rx.box(
            rx.icon("credit-card", size=18, stroke_width=1.8, aria_hidden="true"),
            rx.el.input(
                placeholder="CPF completo",
                value=State.customer_cpf_search,
                on_change=State.capture_customer_cpf_search,
                aria_label="Buscar cliente por CPF completo",
                class_name="vitrine-clientes__input vitrine-clientes__input--icon",
            ),
            class_name="vitrine-clientes__search",
        ),
        rx.el.button(
            "Buscar",
            type="button",
            on_click=State.apply_customer_filters,
            class_name="vitrine-clientes__search-button",
        ),
        rx.el.span(
            State.customers_total,
            rx.cond(State.customers_total == 1, " cliente", " clientes"),
            class_name="vitrine-clientes__count",
            aria_live="polite",
        ),
        class_name="vitrine-clientes__filters",
    )


def render_customers_page() -> rx.Component:
    return rx.el.main(
        dashboard_topbar("/clientes"),
        rx.el.section(
            rx.box(
                rx.el.span("CADASTRO", class_name="vitrine-clientes__eyebrow"),
                rx.el.h1("Clientes", class_name="vitrine-dash__title"),
                class_name="vitrine-dash__heading-text",
            ),
            rx.cond(
                State.user_role == "admin",
                rx.el.a(
                    rx.icon("plus", size=18, stroke_width=2, aria_hidden="true"),
                    "Cadastrar cliente",
                    href="/clientes/novo",
                    class_name="vitrine-clientes__primary",
                ),
            ),
            class_name="vitrine-dash__heading",
        ),
        rx.cond(
            State.customers_success != "",
            rx.box(
                State.customers_success,
                role="status",
                class_name="vitrine-dash__notice vitrine-dash__notice--success",
            ),
        ),
        customers_filters(),
        rx.cond(
            State.customers_error != "",
            rx.box(
                State.customers_error,
                role="alert",
                class_name="vitrine-dash__notice vitrine-dash__notice--error",
            ),
        ),
        rx.cond(
            State.customers_loading,
            rx.box(
                rx.spinner(),
                rx.text("Carregando clientes…"),
                role="status",
                aria_live="polite",
                class_name="vitrine-dash__notice vitrine-dash__notice--loading",
            ),
            rx.cond(
                State.customers_error != "",
                rx.fragment(),
                rx.cond(
                    State.has_customers,
                    rx.box(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Cliente"),
                                    rx.el.th("CPF"),
                                    rx.el.th("Situação"),
                                    rx.el.th("Bloqueio manual"),
                                    rx.el.th(
                                        rx.el.span("Ações", class_name="vitrine-clientes__sr"),
                                    ),
                                ),
                            ),
                            rx.el.tbody(rx.foreach(State.customers_view, render_customer_card)),
                            class_name="vitrine-clientes__table",
                        ),
                        class_name="vitrine-clientes__table-wrap",
                    ),
                    rx.el.p("Nenhum cliente encontrado.", class_name="vitrine-clientes__empty"),
                ),
            ),
        ),
        rx.box(
            rx.el.button(
                "Anterior",
                type="button",
                on_click=State.previous_customers_page,
                disabled=~State.customers_has_previous_page,
                class_name="vitrine-clientes__page-button",
            ),
            rx.el.span(
                "Página ",
                State.customers_page,
                " · ",
                State.customers_total,
                " cliente(s)",
                class_name="vitrine-clientes__page-info",
            ),
            rx.el.button(
                "Próxima",
                type="button",
                on_click=State.next_customers_page,
                disabled=~State.customers_has_next_page,
                class_name="vitrine-clientes__page-button",
            ),
            class_name="vitrine-clientes__pager",
        ),
        class_name="vitrine-dash vitrine-clientes",
    )


def customer_field(label: str, field_id: str, control: rx.Component) -> rx.Component:
    return rx.box(
        rx.el.label(label, html_for=field_id, class_name="vitrine-clientes__label"),
        control,
        class_name="vitrine-clientes__field",
    )


def customer_status_picker() -> rx.Component:
    """Situação cadastral na edição: active/inactive, sem exclusão."""

    return rx.cond(
        State.editing_customer,
        rx.box(
            rx.el.span("Situação cadastral", class_name="vitrine-clientes__label"),
            rx.box(
                *[
                    rx.el.button(
                        label,
                        type="button",
                        on_click=State.capture_customer_status(value),
                        aria_pressed=State.customer_form_status == value,
                        class_name=rx.cond(
                            State.customer_form_status == value,
                            "vitrine-clientes__seg vitrine-clientes__seg--on",
                            "vitrine-clientes__seg",
                        ),
                    )
                    for value, label in (("active", "Ativo"), ("inactive", "Inativo"))
                ],
                role="group",
                aria_label="Situação cadastral do cliente",
                class_name="vitrine-clientes__segmented",
            ),
            class_name="vitrine-clientes__field",
        ),
    )


def render_customer_form() -> rx.Component:
    return rx.el.main(
        dashboard_topbar("/clientes"),
        rx.el.section(
            rx.box(
                rx.box(
                    rx.el.h1(
                        rx.cond(State.editing_customer, "Editar cliente", "Cadastrar cliente"),
                        class_name="vitrine-clientes__form-title",
                    ),
                    rx.el.p(
                        rx.cond(
                            State.editing_customer,
                            "Altere os dados cadastrais do cliente.",
                            "Preencha os dados cadastrais do cliente.",
                        ),
                        class_name="vitrine-clientes__form-sub",
                    ),
                ),
                rx.el.a(
                    rx.icon("x", size=18, stroke_width=1.8, aria_hidden="true"),
                    href="/clientes",
                    aria_label="Voltar aos clientes",
                    title="Voltar aos clientes",
                    class_name="vitrine-clientes__close",
                ),
                class_name="vitrine-clientes__form-head",
            ),
            rx.cond(
                State.customer_form_error != "",
                rx.box(
                    State.customer_form_error,
                    role="alert",
                    class_name="vitrine-dash__notice vitrine-dash__notice--error",
                ),
            ),
            customer_field(
                "Nome completo",
                "customer-name",
                rx.el.input(
                    id="customer-name",
                    placeholder="Nome completo",
                    value=State.customer_form_name,
                    on_change=State.capture_customer_name,
                    max_length=200,
                    required=True,
                    aria_label="Nome completo do cliente",
                    class_name="vitrine-clientes__input",
                ),
            ),
            customer_field(
                "CPF",
                "customer-cpf",
                rx.el.input(
                    id="customer-cpf",
                    placeholder="CPF",
                    value=State.customer_form_cpf,
                    on_change=State.capture_customer_cpf,
                    required=True,
                    aria_label="CPF do cliente",
                    class_name="vitrine-clientes__input vitrine-clientes__mono",
                ),
            ),
            rx.box(
                customer_field(
                    "E-mail",
                    "customer-email",
                    rx.el.input(
                        id="customer-email",
                        placeholder="E-mail",
                        type="email",
                        value=State.customer_form_email,
                        on_change=State.capture_customer_email,
                        max_length=254,
                        aria_label="E-mail do cliente",
                        class_name="vitrine-clientes__input",
                    ),
                ),
                customer_field(
                    "Telefone",
                    "customer-phone",
                    rx.el.input(
                        id="customer-phone",
                        placeholder="Telefone",
                        value=State.customer_form_phone,
                        on_change=State.capture_customer_phone,
                        aria_label="Telefone do cliente",
                        class_name="vitrine-clientes__input",
                    ),
                ),
                class_name="vitrine-clientes__row",
            ),
            rx.box(
                rx.icon("info", size=16, stroke_width=1.8, aria_hidden="true"),
                rx.el.span("Informe ao menos um contato: e-mail ou telefone."),
                class_name="vitrine-clientes__hint",
            ),
            customer_status_picker(),
            rx.box(
                rx.el.a("Cancelar", href="/clientes", class_name="vitrine-clientes__cancel"),
                rx.button(
                    "Salvar cliente",
                    on_click=State.submit_customer,
                    loading=State.customer_form_loading,
                    disabled=State.editing_customer & (State.editing_customer_id == 0),
                    class_name="vitrine-clientes__primary",
                ),
                class_name="vitrine-clientes__form-actions",
            ),
            class_name="vitrine-clientes__form-card",
        ),
        class_name="vitrine-dash vitrine-clientes vitrine-clientes--form",
    )


def customer_data_item(label: str, icon_name: str, value) -> rx.Component:
    return rx.box(
        rx.box(
            rx.icon(icon_name, size=18, stroke_width=1.6, aria_hidden="true"),
            class_name="vitrine-clientes__data-icon",
        ),
        rx.box(
            rx.el.span(label, class_name="vitrine-clientes__data-label"),
            rx.el.span(value, class_name="vitrine-clientes__data-value"),
        ),
        class_name="vitrine-clientes__data-item",
    )


def customer_history_panel() -> rx.Component:
    """Histórico e pendências: aguardam locações, multas e pagamentos (sem dados)."""

    return rx.el.section(
        rx.box(
            rx.el.h2("Histórico e pendências", class_name="vitrine-clientes__panel-title"),
            rx.box(
                *[
                    rx.el.span(
                        label,
                        rx.el.span("Em breve", class_name="vitrine-dash__soon"),
                        aria_disabled="true",
                        class_name="vitrine-clientes__tab",
                    )
                    for label in ("Locações", "Multas", "Pagamentos")
                ],
                class_name="vitrine-clientes__tabs",
            ),
            class_name="vitrine-clientes__panel-head",
        ),
        rx.box(
            rx.icon("clock", size=22, stroke_width=1.6, aria_hidden="true"),
            rx.el.h3("Histórico em construção", class_name="vitrine-clientes__empty-title"),
            rx.el.p(
                "Aguardando implementação das capacidades de locações, multas e pagamentos. "
                "Nenhum saldo ou histórico financeiro é apresentado nesta versão.",
                class_name="vitrine-clientes__empty-text",
            ),
            class_name="vitrine-clientes__placeholder",
        ),
        class_name="vitrine-clientes__panel",
        aria_label="Histórico e pendências",
    )


def customer_block_panel() -> rx.Component:
    """Bloqueio manual (admin): mesmo handler, motivo obrigatório para aplicar."""

    blocked = State.customer_detail["bloqueio_manual_ativo"]
    return rx.el.section(
        rx.box(
            rx.icon("shield", size=20, stroke_width=1.6, aria_hidden="true"),
            class_name="vitrine-clientes__shield",
        ),
        rx.el.h2("Controle de bloqueio manual", class_name="vitrine-clientes__panel-title"),
        rx.el.p(
            "Marca o cliente como inelegível para futuras locações até o bloqueio ser removido. "
            "O motivo fica registrado no cadastro.",
            class_name="vitrine-clientes__panel-sub",
        ),
        rx.box(
            rx.el.span("Situação atual"),
            customer_block_badge(blocked, short=False),
            class_name="vitrine-clientes__block-state",
        ),
        rx.cond(
            blocked,
            rx.box(
                rx.el.span("Motivo", class_name="vitrine-clientes__label"),
                rx.el.p(
                    State.customer_detail["motivo_bloqueio_manual"],
                    class_name="vitrine-clientes__reason",
                ),
                class_name="vitrine-clientes__field",
            ),
            rx.box(
                rx.el.label(
                    "Motivo",
                    html_for="customer-block-reason",
                    class_name="vitrine-clientes__label",
                ),
                rx.el.textarea(
                    id="customer-block-reason",
                    placeholder="Obrigatório. Informe o motivo do bloqueio.",
                    value=State.customer_block_reason,
                    on_change=State.capture_customer_block_reason,
                    max_length=500,
                    aria_label="Motivo do bloqueio manual",
                    class_name="vitrine-clientes__input vitrine-clientes__textarea",
                ),
                class_name="vitrine-clientes__field",
            ),
        ),
        rx.button(
            rx.cond(blocked, "Remover bloqueio manual", "Aplicar bloqueio manual"),
            on_click=State.toggle_customer_manual_block,
            loading=State.customer_block_loading,
            class_name=rx.cond(
                blocked,
                "vitrine-clientes__primary vitrine-clientes__primary--neutral",
                "vitrine-clientes__primary",
            ),
        ),
        rx.cond(
            ~blocked,
            rx.el.p(
                "O bloqueio é registrado em nome de ",
                State.user_name,
                ".",
                class_name="vitrine-clientes__footnote",
            ),
        ),
        class_name="vitrine-clientes__panel vitrine-clientes__panel--block",
        aria_label="Controle de bloqueio manual",
    )


def render_customer_detail() -> rx.Component:
    detail = State.customer_detail
    return rx.el.main(
        dashboard_topbar("/clientes"),
        rx.el.a(
            rx.icon("arrow-left", size=16, stroke_width=1.8, aria_hidden="true"),
            "Voltar aos clientes",
            href="/clientes",
            class_name="vitrine-clientes__back",
        ),
        rx.cond(
            State.customer_detail_error != "",
            rx.box(
                State.customer_detail_error,
                role="alert",
                class_name="vitrine-dash__notice vitrine-dash__notice--error",
            ),
        ),
        rx.cond(
            State.customers_success != "",
            rx.box(
                State.customers_success,
                role="status",
                class_name="vitrine-dash__notice vitrine-dash__notice--success",
            ),
        ),
        rx.cond(
            State.customer_detail_loading,
            rx.box(
                rx.spinner(),
                rx.text("Carregando cliente…"),
                role="status",
                aria_live="polite",
                class_name="vitrine-dash__notice vitrine-dash__notice--loading",
            ),
            rx.cond(
                State.customer_detail_loaded,
                rx.fragment(
                    rx.el.section(
                        rx.box(
                            rx.el.span(
                                State.customer_detail_initials,
                                class_name="vitrine-clientes__avatar vitrine-clientes__avatar--lg",
                                aria_hidden="true",
                            ),
                            rx.box(
                                rx.el.h1(detail["nome"], class_name="vitrine-dash__title"),
                                rx.box(
                                    customer_status_badge(detail["status"]),
                                    customer_block_badge(detail["bloqueio_manual_ativo"]),
                                    class_name="vitrine-clientes__badges",
                                ),
                            ),
                            class_name="vitrine-clientes__person vitrine-clientes__person--lg",
                        ),
                        rx.cond(
                            State.user_role == "admin",
                            rx.el.a(
                                rx.icon("pencil", size=16, stroke_width=1.8, aria_hidden="true"),
                                "Editar cadastro",
                                href=f"/clientes/{detail['id']}/editar",
                                class_name="vitrine-clientes__secondary",
                            ),
                        ),
                        class_name="vitrine-dash__heading",
                    ),
                    rx.box(
                        rx.box(
                            rx.el.section(
                                rx.el.h2("Dados do cliente", class_name="vitrine-clientes__panel-title"),
                                rx.box(
                                    customer_data_item("CPF", "credit-card", detail["cpf"]),
                                    customer_data_item(
                                        "E-mail",
                                        "mail",
                                        rx.cond(detail["email"], detail["email"], "Não informado"),
                                    ),
                                    customer_data_item(
                                        "Telefone",
                                        "smartphone",
                                        rx.cond(detail["telefone"], detail["telefone"], "Não informado"),
                                    ),
                                    customer_data_item(
                                        "Situação",
                                        "user",
                                        rx.cond(detail["status"] == "active", "Ativo", "Inativo"),
                                    ),
                                    customer_data_item(
                                        "Bloqueio manual",
                                        "shield",
                                        rx.cond(
                                            detail["bloqueio_manual_ativo"],
                                            "Ativo",
                                            "Não aplicado",
                                        ),
                                    ),
                                    class_name="vitrine-clientes__data-grid",
                                ),
                                rx.cond(
                                    detail["bloqueio_manual_ativo"],
                                    rx.el.p(
                                        "Motivo: ",
                                        detail["motivo_bloqueio_manual"],
                                        class_name="vitrine-clientes__reason",
                                    ),
                                ),
                                class_name="vitrine-clientes__panel",
                                aria_label="Dados do cliente",
                            ),
                            customer_history_panel(),
                            class_name="vitrine-clientes__main-col",
                        ),
                        rx.cond(State.user_role == "admin", customer_block_panel()),
                        class_name="vitrine-clientes__detail-grid",
                    ),
                ),
                rx.fragment(),
            ),
        ),
        class_name="vitrine-dash vitrine-clientes",
    )


FILM_POSTER_TONES = 5
FILM_STATUS_FILTERS = (
    ("all", "Todos"),
    ("active", "Ativos"),
    ("inactive", "Inativos"),
)
CLASSIFICATION_BADGES = {
    "Livre": ("L", "livre"),
    "10 anos": ("10", "10"),
    "12 anos": ("12", "12"),
    "14 anos": ("14", "14"),
    "16 anos": ("16", "16"),
    "18 anos": ("18", "18"),
}


def classification_badge(classification) -> rx.Component:
    """Selo de classificação indicativa; aceita valor literal ou Var."""

    return rx.el.span(
        rx.match(
            classification,
            *[(name, label) for name, (label, _) in CLASSIFICATION_BADGES.items()],
            "?",
        ),
        role="img",
        aria_label=classification,
        class_name=rx.match(
            classification,
            *[
                (name, f"vitrine-acervo__rating vitrine-acervo__rating--{tone}")
                for name, (_, tone) in CLASSIFICATION_BADGES.items()
            ],
            "vitrine-acervo__rating",
        ),
    )


def render_film_card(film: FilmeCatalogo) -> rx.Component:
    return rx.el.article(
        rx.box(
            rx.el.span(film["genero"], class_name="vitrine-acervo__poster-genre"),
            rx.el.span(film["titulo"], class_name="vitrine-acervo__poster-title"),
            rx.el.span(film["ano_lancamento"], class_name="vitrine-acervo__poster-year"),
            # Com capa, a imagem cobre o pôster de cor; sem capa, ele continua visível.
            rx.cond(
                film["capa_url"],
                rx.el.img(
                    src=film["capa_url"],
                    alt="Capa de " + film["titulo"],
                    loading="lazy",
                    decoding="async",
                    class_name="vitrine-acervo__poster-img",
                ),
            ),
            class_name=(
                "vitrine-acervo__poster vitrine-acervo__poster--tone-"
                + (film["id"] % FILM_POSTER_TONES).to_string()
            ),
            aria_hidden="true",
        ),
        rx.cond(
            State.user_role == "admin",
            rx.el.a(
                rx.icon("pencil", size=16, stroke_width=1.8, aria_hidden="true"),
                href=f"/filmes/{film['id']}/editar",
                aria_label="Editar " + film["titulo"],
                title="Editar",
                class_name="vitrine-acervo__edit",
            ),
        ),
        rx.box(
            rx.box(
                rx.el.h3(film["titulo"], class_name="vitrine-acervo__film-title"),
                rx.el.p(
                    film["genero"],
                    " · ",
                    film["ano_lancamento"],
                    class_name="vitrine-acervo__film-meta",
                ),
                class_name="vitrine-acervo__film-main",
            ),
            rx.box(
                rx.box(
                    rx.el.span("Classificação", class_name="vitrine-acervo__stat-label"),
                    classification_badge(film["classificacao"]),
                    class_name="vitrine-acervo__stat",
                ),
                rx.box(
                    rx.el.span("Locação", class_name="vitrine-acervo__stat-label"),
                    rx.el.span(
                        film["valor_locacao_display"],
                        class_name="vitrine-acervo__price",
                    ),
                    class_name="vitrine-acervo__stat",
                ),
                rx.box(
                    rx.el.span("Status", class_name="vitrine-acervo__stat-label"),
                    rx.el.span(
                        rx.el.span(
                            class_name=rx.cond(
                                film["status"] == "active",
                                "vitrine-acervo__dot vitrine-acervo__dot--on",
                                "vitrine-acervo__dot",
                            ),
                            aria_hidden="true",
                        ),
                        rx.cond(film["status"] == "active", "Ativo", "Inativo"),
                        class_name="vitrine-acervo__status",
                    ),
                    class_name="vitrine-acervo__stat",
                ),
                class_name="vitrine-acervo__film-foot",
            ),
            class_name="vitrine-acervo__film-info",
        ),
        class_name="vitrine-acervo__card",
    )


def new_film_tile() -> rx.Component:
    """Atalho administrativo ao formulário real de cadastro."""

    return rx.cond(
        State.user_role == "admin",
        rx.el.a(
            rx.box(
                rx.icon("plus", size=20, stroke_width=2, aria_hidden="true"),
                class_name="vitrine-acervo__tile-icon",
            ),
            rx.el.span("Cadastrar filme", class_name="vitrine-acervo__tile-title"),
            rx.el.span(
                "Título, gênero, ano, classificação e valor",
                class_name="vitrine-acervo__tile-note",
            ),
            href="/filmes/novo",
            class_name="vitrine-acervo__tile",
        ),
    )


def film_status_filter_group() -> rx.Component:
    """Filtro de apresentação sobre a lista já carregada; não consulta o Xano."""

    return rx.box(
        *[
            rx.el.button(
                label,
                type="button",
                on_click=State.capture_film_status_filter(value),
                aria_pressed=State.film_status_filter == value,
                class_name=rx.cond(
                    State.film_status_filter == value,
                    "vitrine-acervo__seg vitrine-acervo__seg--on",
                    "vitrine-acervo__seg",
                ),
            )
            for value, label in FILM_STATUS_FILTERS
        ],
        role="group",
        aria_label="Filtrar por status",
        class_name="vitrine-acervo__segmented",
    )


def films_filters() -> rx.Component:
    return rx.box(
        rx.box(
            rx.icon("search", size=18, stroke_width=1.8, aria_hidden="true"),
            rx.el.input(
                placeholder="Buscar por título",
                value=State.title_search,
                on_change=State.capture_title_search,
                aria_label="Buscar por título",
                class_name="vitrine-acervo__input vitrine-acervo__input--icon",
            ),
            class_name="vitrine-acervo__search",
        ),
        rx.el.input(
            placeholder="Filtrar por gênero",
            value=State.genre_filter,
            on_change=State.capture_genre_filter,
            aria_label="Filtrar por gênero",
            class_name="vitrine-acervo__input vitrine-acervo__genre",
        ),
        film_status_filter_group(),
        rx.el.button(
            "Buscar",
            type="button",
            on_click=State.apply_film_filters,
            class_name="vitrine-acervo__search-button",
        ),
        rx.el.span(
            State.visible_films.length(),
            rx.cond(State.visible_films.length() == 1, " filme", " filmes"),
            class_name="vitrine-acervo__count",
            aria_live="polite",
        ),
        class_name="vitrine-acervo__filters",
    )


def render_films_page() -> rx.Component:
    return rx.el.main(
        dashboard_topbar("/filmes"),
        rx.el.section(
            rx.box(
                rx.el.span("ACERVO", class_name="vitrine-acervo__eyebrow"),
                rx.el.h1("Catálogo de filmes", class_name="vitrine-dash__title"),
                class_name="vitrine-dash__heading-text",
            ),
            rx.cond(
                State.user_role == "admin",
                rx.el.a(
                    rx.icon("plus", size=18, stroke_width=2, aria_hidden="true"),
                    "Cadastrar filme",
                    href="/filmes/novo",
                    class_name="vitrine-acervo__primary",
                ),
            ),
            class_name="vitrine-dash__heading",
        ),
        rx.cond(
            State.films_success != "",
            rx.box(
                State.films_success,
                role="status",
                class_name="vitrine-dash__notice vitrine-dash__notice--success",
            ),
        ),
        films_filters(),
        rx.cond(
            State.films_error != "",
            rx.box(
                State.films_error,
                role="alert",
                class_name="vitrine-dash__notice vitrine-dash__notice--error",
            ),
        ),
        rx.cond(
            State.films_loading,
            rx.box(
                rx.spinner(),
                rx.text("Carregando filmes…"),
                role="status",
                aria_live="polite",
                class_name="vitrine-dash__notice vitrine-dash__notice--loading",
            ),
            rx.cond(
                State.films_error != "",
                rx.fragment(),
                rx.fragment(
                    rx.cond(
                        State.has_films,
                        rx.cond(
                            State.visible_films.length() > 0,
                            rx.fragment(),
                            rx.el.p(
                                "Nenhum filme com este status.",
                                class_name="vitrine-acervo__empty",
                            ),
                        ),
                        rx.el.p(
                            "Nenhum filme encontrado.",
                            class_name="vitrine-acervo__empty",
                        ),
                    ),
                    rx.box(
                        rx.foreach(State.visible_films, render_film_card),
                        new_film_tile(),
                        class_name="vitrine-acervo__grid",
                    ),
                    rx.el.p(
                        "Mostrando ",
                        State.visible_films.length(),
                        " de ",
                        State.films.length(),
                        rx.cond(State.films.length() == 1, " filme", " filmes"),
                        class_name="vitrine-acervo__footer",
                    ),
                ),
            ),
        ),
        class_name="vitrine-dash vitrine-acervo",
    )


def render_exemplar_card(exemplar: Exemplar) -> rx.Component:
    """Identificador do exemplar exibido como dado, sem ações de edição."""

    return rx.el.li(
        rx.el.span("EXEMPLAR", class_name="vitrine-exemplares__chip-label"),
        rx.el.span(exemplar["identificador"], class_name="vitrine-exemplares__chip-code"),
        class_name="vitrine-exemplares__chip",
    )


def exemplar_copy_shortcut(group: ExemplarGrupo) -> rx.Component:
    """Abre o cadastro com o filme pré-selecionado; não gera identificador."""

    return rx.cond(
        (State.user_role == "admin") & group["pode_adicionar"],
        rx.el.button(
            rx.icon("plus", size=16, stroke_width=2, aria_hidden="true"),
            rx.cond(group["count"] > 0, "Outra cópia", "Adicionar cópia"),
            type="button",
            on_click=[
                State.capture_exemplar_film_selection(group["opcao"]),
                State.set_exemplar_dialog_open(True),
            ],
            aria_label="Adicionar cópia de " + group["titulo"],
            class_name="vitrine-exemplares__add",
        ),
    )


def render_exemplar_group(group: ExemplarGrupo) -> rx.Component:
    return rx.el.article(
        rx.box(
            rx.box(
                rx.el.span(group["titulo"], class_name="vitrine-exemplares__thumb-text"),
                # Com capa no catálogo, a imagem cobre o gradiente.
                rx.cond(
                    group["capa_url"],
                    rx.el.img(
                        src=group["capa_url"],
                        alt="",
                        loading="lazy",
                        decoding="async",
                        class_name="vitrine-exemplares__thumb-img",
                    ),
                ),
                class_name="vitrine-exemplares__thumb",
                aria_hidden="true",
            ),
            rx.box(
                rx.el.h3(group["titulo"], class_name="vitrine-exemplares__film-title"),
                rx.cond(
                    group["detalhe"] != "",
                    rx.el.p(group["detalhe"], class_name="vitrine-exemplares__film-meta"),
                ),
                rx.el.p(
                    "ID do filme: ",
                    group["filme_id"],
                    class_name="vitrine-exemplares__film-id",
                ),
                class_name="vitrine-exemplares__film-text",
            ),
            class_name="vitrine-exemplares__film",
        ),
        rx.box(
            rx.el.span(group["count"], class_name="vitrine-exemplares__count-number"),
            rx.el.span(group["unidade"], class_name="vitrine-exemplares__count-unit"),
            class_name=rx.cond(
                group["count"] > 0,
                "vitrine-exemplares__count",
                "vitrine-exemplares__count vitrine-exemplares__count--empty",
            ),
        ),
        rx.el.ul(
            rx.foreach(group["exemplares"], render_exemplar_card),
            exemplar_copy_shortcut(group),
            aria_label="Exemplares de " + group["titulo"],
            class_name="vitrine-exemplares__chips",
        ),
        class_name="vitrine-exemplares__row vitrine-exemplares__row--tone-"
        + group["tom"].to_string(),
    )


def exemplares_filters() -> rx.Component:
    return rx.box(
        rx.box(
            rx.icon("search", size=18, stroke_width=1.8, aria_hidden="true"),
            rx.el.input(
                placeholder="Buscar por identificador",
                value=State.exemplar_search,
                on_change=State.capture_exemplar_search,
                aria_label="Buscar por identificador",
                class_name="vitrine-exemplares__input vitrine-exemplares__input--icon",
            ),
            class_name="vitrine-exemplares__search",
        ),
        rx.el.select(
            rx.foreach(
                State.exemplar_filter_options,
                lambda option: rx.el.option(option, value=option),
            ),
            value=State.exemplar_film_filter,
            on_change=State.capture_exemplar_film_filter,
            aria_label="Filtrar por filme",
            class_name="vitrine-exemplares__input vitrine-exemplares__select",
        ),
        rx.el.span(
            State.exemplar_summary,
            class_name="vitrine-exemplares__summary",
            aria_live="polite",
        ),
        class_name="vitrine-exemplares__filters",
    )


def exemplar_dialog() -> rx.Component:
    """Cadastro de exemplar em diálogo controlado; mesmos handlers do formulário anterior."""

    return rx.dialog.root(
        rx.dialog.content(
            rx.box(
                rx.box(
                    rx.dialog.title(
                        "Cadastrar exemplar",
                        class_name="vitrine-exemplares__dialog-title",
                    ),
                    rx.dialog.description(
                        "Cada cópia física do filme é um exemplar.",
                        class_name="vitrine-exemplares__dialog-sub",
                    ),
                ),
                rx.dialog.close(
                    rx.el.button(
                        rx.icon("x", size=18, stroke_width=1.8, aria_hidden="true"),
                        type="button",
                        aria_label="Fechar",
                        class_name="vitrine-exemplares__close",
                    )
                ),
                class_name="vitrine-exemplares__dialog-head",
            ),
            rx.cond(
                State.exemplar_films_error != "",
                rx.box(
                    State.exemplar_films_error,
                    role="alert",
                    class_name="vitrine-exemplares__alert",
                ),
            ),
            rx.cond(
                State.exemplar_form_error != "",
                rx.box(
                    State.exemplar_form_error,
                    role="alert",
                    class_name="vitrine-exemplares__alert",
                ),
            ),
            rx.box(
                rx.el.label(
                    "Identificador do exemplar",
                    html_for="exemplar-identifier",
                    class_name="vitrine-exemplares__label",
                ),
                rx.el.input(
                    id="exemplar-identifier",
                    placeholder="Identificador do exemplar",
                    value=State.exemplar_identifier,
                    on_change=State.capture_exemplar_identifier,
                    required=True,
                    aria_label="Identificador do exemplar",
                    class_name="vitrine-exemplares__input vitrine-exemplares__mono",
                ),
                rx.el.span(
                    "Código único do exemplar.",
                    class_name="vitrine-exemplares__hint",
                ),
                class_name="vitrine-exemplares__field",
            ),
            rx.box(
                rx.el.label(
                    "Filme",
                    html_for="exemplar-film",
                    class_name="vitrine-exemplares__label",
                ),
                rx.el.select(
                    rx.el.option("Selecione o filme", value="", disabled=True),
                    rx.foreach(
                        State.exemplar_film_options,
                        lambda option: rx.el.option(option, value=option),
                    ),
                    id="exemplar-film",
                    value=State.exemplar_film_selection,
                    on_change=State.capture_exemplar_film_selection,
                    required=True,
                    aria_label="Filme associado ao exemplar",
                    class_name="vitrine-exemplares__input vitrine-exemplares__select",
                ),
                class_name="vitrine-exemplares__field",
            ),
            rx.box(
                rx.dialog.close(
                    rx.el.button(
                        "Cancelar",
                        type="button",
                        class_name="vitrine-exemplares__cancel",
                    )
                ),
                rx.button(
                    "Cadastrar exemplar",
                    on_click=State.submit_exemplar,
                    loading=State.exemplar_form_loading,
                    class_name="vitrine-exemplares__primary",
                ),
                class_name="vitrine-exemplares__dialog-actions",
            ),
            class_name="vitrine-exemplares-dialog",
        ),
        open=State.exemplar_dialog_open,
        on_open_change=State.set_exemplar_dialog_open,
    )


def render_exemplares_page() -> rx.Component:
    return rx.el.main(
        dashboard_topbar("/exemplares"),
        rx.el.section(
            rx.box(
                rx.el.span("ACERVO", class_name="vitrine-exemplares__eyebrow"),
                rx.el.h1("Exemplares", class_name="vitrine-dash__title"),
                class_name="vitrine-dash__heading-text",
            ),
            rx.cond(
                State.user_role == "admin",
                rx.el.button(
                    rx.icon("plus", size=18, stroke_width=2, aria_hidden="true"),
                    "Cadastrar exemplar",
                    type="button",
                    on_click=State.set_exemplar_dialog_open(True),
                    class_name="vitrine-exemplares__primary",
                ),
            ),
            class_name="vitrine-dash__heading",
        ),
        rx.cond(
            State.exemplares_success != "",
            rx.box(
                State.exemplares_success,
                role="status",
                class_name="vitrine-dash__notice vitrine-dash__notice--success",
            ),
        ),
        rx.cond(
            State.exemplares_error != "",
            rx.box(
                State.exemplares_error,
                role="alert",
                class_name="vitrine-dash__notice vitrine-dash__notice--error",
            ),
        ),
        rx.cond(
            (State.user_role == "admin") & (State.exemplar_films_error != ""),
            rx.box(
                State.exemplar_films_error,
                role="alert",
                class_name="vitrine-dash__notice vitrine-dash__notice--error",
            ),
        ),
        exemplares_filters(),
        rx.cond(
            State.exemplares_loading,
            rx.box(
                rx.spinner(),
                rx.text("Carregando exemplares…"),
                role="status",
                aria_live="polite",
                class_name="vitrine-dash__notice vitrine-dash__notice--loading",
            ),
            rx.cond(
                State.exemplares_error != "",
                rx.fragment(),
                rx.fragment(
                    rx.cond(
                        State.has_exemplares,
                        rx.cond(
                            State.exemplar_groups.length() > 0,
                            rx.fragment(),
                            rx.el.p(
                                "Nenhum exemplar corresponde aos filtros.",
                                class_name="vitrine-exemplares__empty",
                            ),
                        ),
                        rx.el.p(
                            "Nenhum exemplar encontrado.",
                            class_name="vitrine-exemplares__empty",
                        ),
                    ),
                    rx.cond(
                        State.exemplar_groups.length() > 0,
                        rx.box(
                            rx.foreach(State.exemplar_groups, render_exemplar_group),
                            class_name="vitrine-exemplares__list",
                        ),
                    ),
                ),
            ),
        ),
        rx.cond(State.user_role == "admin", exemplar_dialog()),
        class_name="vitrine-dash vitrine-exemplares",
    )


def film_form_field(label: str, field_id: str, control: rx.Component, class_name: str = "") -> rx.Component:
    return rx.box(
        rx.el.label(label, html_for=field_id, class_name="vitrine-acervo__label"),
        control,
        class_name=f"vitrine-acervo__field {class_name}".strip(),
    )


def classification_picker() -> rx.Component:
    """Seleção segmentada ligada ao mesmo handler do campo de classificação."""

    return rx.box(
        rx.el.span("Classificação indicativa", class_name="vitrine-acervo__label"),
        rx.box(
            *[
                rx.el.button(
                    classification_badge(name),
                    rx.el.span("Livre" if name == "Livre" else name.removesuffix(" anos")),
                    type="button",
                    on_click=State.capture_film_classification(name),
                    aria_pressed=State.form_classification == name,
                    aria_label=name,
                    class_name=rx.cond(
                        State.form_classification == name,
                        "vitrine-acervo__choice vitrine-acervo__choice--on",
                        "vitrine-acervo__choice",
                    ),
                )
                for name in CLASSIFICACOES
            ],
            role="group",
            aria_label="Classificação indicativa",
            class_name="vitrine-acervo__choices",
        ),
        class_name="vitrine-acervo__field",
    )


def film_status_picker() -> rx.Component:
    """Status do filme no catálogo; exibido somente na edição."""

    return rx.cond(
        State.editing_film,
        rx.box(
            rx.el.span("Status", class_name="vitrine-acervo__label"),
            rx.box(
                *[
                    rx.el.button(
                        label,
                        type="button",
                        on_click=State.capture_film_status(value),
                        aria_pressed=State.form_status == value,
                        class_name=rx.cond(
                            State.form_status == value,
                            "vitrine-acervo__seg vitrine-acervo__seg--on",
                            "vitrine-acervo__seg",
                        ),
                    )
                    for value, label in (("active", "Ativo"), ("inactive", "Inativo"))
                ],
                role="group",
                aria_label="Status do filme",
                class_name="vitrine-acervo__segmented",
            ),
            class_name="vitrine-acervo__field",
        ),
    )


FILM_COVER_UPLOAD_ID = "film-cover"


def film_cover_field() -> rx.Component:
    """Capa na edição: enviada e removida direto no Xano, sem depender de "Salvar"."""

    has_cover = State.form_cover_url != ""
    return rx.cond(
        State.editing_film,
        rx.box(
            rx.el.span("Capa", class_name="vitrine-acervo__label"),
            rx.box(
                rx.cond(
                    has_cover,
                    rx.el.img(
                        src=State.form_cover_url,
                        alt="Capa de " + State.form_title,
                        class_name="vitrine-acervo__cover-preview",
                    ),
                    rx.box(
                        rx.icon("image", size=22, stroke_width=1.6, aria_hidden="true"),
                        rx.el.span("Sem capa"),
                        class_name="vitrine-acervo__cover-preview vitrine-acervo__cover-preview--empty",
                    ),
                ),
                rx.box(
                    rx.upload(
                        rx.box(
                            rx.icon("upload", size=18, stroke_width=1.8, aria_hidden="true"),
                            rx.el.span(
                                rx.cond(has_cover, "Trocar capa", "Enviar capa"),
                                class_name="vitrine-acervo__cover-cta",
                            ),
                            rx.el.span(
                                "Arraste ou clique · JPEG, PNG ou WebP até 2 MB",
                                class_name="vitrine-acervo__cover-hint",
                            ),
                            class_name="vitrine-acervo__cover-drop-inner",
                        ),
                        id=FILM_COVER_UPLOAD_ID,
                        accept=CAPA_ACCEPT,
                        max_files=1,
                        multiple=False,
                        max_size=CAPA_MAX_BYTES,
                        disabled=State.cover_loading,
                        on_drop=State.upload_film_cover(rx.upload_files(upload_id=FILM_COVER_UPLOAD_ID)),
                        on_drop_rejected=State.reject_film_cover,
                        class_name="vitrine-acervo__cover-drop",
                    ),
                    # Sem storage de arquivos no plano do Xano, a capa pode vir de um link https.
                    rx.box(
                        rx.el.input(
                            id="film-cover-link",
                            type="url",
                            placeholder="ou cole o link https da imagem",
                            value=State.form_cover_link,
                            on_change=State.capture_cover_link,
                            max_length=500,
                            aria_label="Link https da imagem da capa",
                            class_name="vitrine-acervo__input vitrine-acervo__cover-link",
                        ),
                        rx.el.button(
                            "Usar link",
                            type="button",
                            on_click=State.save_film_cover_link,
                            disabled=State.cover_loading,
                            class_name="vitrine-acervo__cover-remove",
                        ),
                        class_name="vitrine-acervo__cover-link-row",
                    ),
                    rx.cond(
                        has_cover,
                        rx.el.button(
                            rx.icon("trash-2", size=15, stroke_width=1.8, aria_hidden="true"),
                            "Remover capa",
                            type="button",
                            on_click=State.remove_film_cover,
                            disabled=State.cover_loading,
                            class_name="vitrine-acervo__cover-remove",
                        ),
                    ),
                    rx.cond(
                        State.cover_loading,
                        rx.box(
                            rx.spinner(size="1"),
                            rx.text("Gravando a capa no Xano…"),
                            role="status",
                            aria_live="polite",
                            class_name="vitrine-acervo__cover-status",
                        ),
                    ),
                    rx.cond(
                        State.cover_error != "",
                        rx.box(State.cover_error, role="alert",
                               class_name="vitrine-acervo__cover-status vitrine-acervo__cover-status--error"),
                    ),
                    rx.cond(
                        State.cover_success != "",
                        rx.box(State.cover_success, role="status",
                               class_name="vitrine-acervo__cover-status vitrine-acervo__cover-status--ok"),
                    ),
                    class_name="vitrine-acervo__cover-actions",
                ),
                class_name="vitrine-acervo__cover",
            ),
            id="film-cover-field",
            class_name="vitrine-acervo__field",
        ),
    )


def render_film_form() -> rx.Component:
    return rx.el.main(
        dashboard_topbar("/filmes"),
        rx.el.section(
            rx.box(
                rx.box(
                    rx.el.h1(
                        rx.cond(State.editing_film, "Editar filme", "Cadastrar filme"),
                        class_name="vitrine-acervo__form-title",
                    ),
                    rx.el.p(
                        rx.cond(
                            State.editing_film,
                            "Altere os dados do filme no catálogo.",
                            "O filme entra no catálogo assim que for salvo.",
                        ),
                        class_name="vitrine-acervo__form-sub",
                    ),
                ),
                rx.el.a(
                    rx.icon("x", size=18, stroke_width=1.8, aria_hidden="true"),
                    href="/filmes",
                    aria_label="Voltar ao catálogo",
                    title="Voltar ao catálogo",
                    class_name="vitrine-acervo__close",
                ),
                class_name="vitrine-acervo__form-head",
            ),
            rx.cond(
                State.form_error != "",
                rx.box(
                    State.form_error,
                    role="alert",
                    class_name="vitrine-dash__notice vitrine-dash__notice--error",
                ),
            ),
            film_cover_field(),
            film_form_field(
                "Título",
                "film-title",
                rx.el.input(
                    id="film-title",
                    placeholder="Título",
                    value=State.form_title,
                    on_change=State.capture_film_title,
                    max_length=200,
                    required=True,
                    aria_label="Título",
                    class_name="vitrine-acervo__input",
                ),
            ),
            rx.box(
                film_form_field(
                    "Gênero",
                    "film-genre",
                    rx.el.input(
                        id="film-genre",
                        placeholder="Gênero",
                        value=State.form_genre,
                        on_change=State.capture_film_genre,
                        max_length=100,
                        required=True,
                        aria_label="Gênero",
                        class_name="vitrine-acervo__input",
                    ),
                ),
                film_form_field(
                    "Ano de lançamento",
                    "film-year",
                    rx.el.input(
                        id="film-year",
                        placeholder="Ano de lançamento",
                        type="text",
                        input_mode="numeric",
                        pattern="[0-9]*",
                        max_length=4,
                        value=State.form_year,
                        on_change=State.capture_film_year,
                        required=True,
                        aria_label="Ano de lançamento",
                        class_name="vitrine-acervo__input",
                    ),
                ),
                class_name="vitrine-acervo__row",
            ),
            classification_picker(),
            rx.box(
                film_form_field(
                    "Valor da locação",
                    "film-rent",
                    rx.el.input(
                        id="film-rent",
                        placeholder="Valor da locação (R$)",
                        value=State.form_rent_price,
                        on_change=State.capture_film_rent_price,
                        required=True,
                        aria_label="Valor da locação em reais",
                        class_name="vitrine-acervo__input",
                    ),
                ),
                film_status_picker(),
                class_name="vitrine-acervo__row",
            ),
            rx.box(
                rx.el.a(
                    "Cancelar",
                    href="/filmes",
                    class_name="vitrine-acervo__cancel",
                ),
                rx.button(
                    "Salvar alterações",
                    on_click=State.submit_film,
                    loading=State.form_loading,
                    disabled=State.editing_film & (State.editing_film_id == 0),
                    class_name="vitrine-acervo__primary vitrine-acervo__submit",
                ),
                class_name="vitrine-acervo__form-actions",
            ),
            class_name="vitrine-acervo__form-card",
        ),
        class_name="vitrine-dash vitrine-acervo vitrine-acervo--form",
    )


@rx.page(route="/clientes", on_load=State.load_customers)
def customers_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_customers_page(), rx.fragment())


@rx.page(route="/clientes/novo", on_load=State.load_new_customer)
def new_customer_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_customer_form(), rx.fragment())


@rx.page(route="/clientes/[customer_id]", on_load=State.load_customer_detail)
def customer_detail_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_customer_detail(), rx.fragment())


@rx.page(route="/clientes/[customer_id]/editar", on_load=State.load_customer_for_edit)
def edit_customer_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_customer_form(), rx.fragment())


@rx.page(route="/filmes", on_load=State.load_films)
def films_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_films_page(), rx.fragment())


@rx.page(route="/exemplares", on_load=State.load_exemplares)
def exemplares_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_exemplares_page(), rx.fragment())


@rx.page(route="/locacoes/nova", on_load=State.load_new_rental)
def rental_registration_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_rental_registration(State.user_role == "admin", dashboard_topbar("/locacoes/nova")), rx.fragment())


@rx.page(route="/locacoes/[rental_id]", on_load=State.load_rental_detail)
def rental_detail_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_rental_detail(dashboard_topbar("/locacoes/nova")), rx.fragment())


@rx.page(route="/filmes/novo", on_load=State.load_new_film)
def new_film_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_film_form(), rx.fragment())


@rx.page(route="/filmes/[film_id]/editar", on_load=State.load_film_for_edit)
def edit_film_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_film_form(), rx.fragment())


@rx.page(route="/", on_load=State.load_dashboard)
def index() -> rx.Component:
    return rx.cond(
        State.is_authenticated,
        render_dashboard(),
        rx.fragment(),
    )


@rx.page(route="/backoffice", on_load=State.load_dashboard)
def backoffice_page() -> rx.Component:
    return rx.cond(
        State.is_authenticated,
        render_dashboard(),
        rx.fragment(),
    )


@rx.page(route="/recuperar-senha")
def request_reset_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Recuperar senha", size="8"),
            rx.text("Informe seu e-mail para receber um link de redefinição."),
            rx.input(
                placeholder="E-mail",
                type="email",
                required=True,
                size="3",
                on_change=State.capture_reset_request_email,
            ),
            rx.button(
                "Enviar link",
                on_click=State.request_reset_link,
                size="3",
                width="100%",
            ),
            rx.cond(
                State.reset_message != "",
                rx.callout(
                    State.reset_message,
                    color_scheme="red",
                    role="status",
                ),
            ),
            rx.link("Voltar ao login", href="/login"),
            spacing="4",
            justify="center",
            min_height="85vh",
            max_width="28rem",
            margin="auto",
        )
    )


@rx.page(route="/redefinir-senha", on_load=State.consume_reset_link)
def reset_password_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Redefinição de senha", size="8"),
            rx.cond(
                State.reset_message != "",
                rx.callout(
                    State.reset_message,
                    color_scheme=rx.cond(State.reset_message_is_error, "red", "green"),
                    role="status",
                ),
            ),
            rx.cond(
                State.reset_link_ready,
                rx.vstack(
                    rx.input(
                        placeholder="Nova senha",
                        type="password",
                        required=True,
                        min_length=8,
                        size="3",
                        on_change=State.capture_new_password,
                    ),
                    rx.input(
                        placeholder="Confirme a nova senha",
                        type="password",
                        required=True,
                        min_length=8,
                        size="3",
                        on_change=State.capture_confirm_new_password,
                    ),
                    rx.button(
                        "Atualizar senha",
                        on_click=State.update_password,
                        size="3",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.text(
                    "Abra o link recebido por e-mail para habilitar a troca da senha."
                ),
            ),
            rx.link("Voltar ao login", href="/login"),
            spacing="4",
            justify="center",
            min_height="85vh",
            max_width="28rem",
            margin="auto",
        )
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap",
        "/login.css",
        "/dashboard.css",
        "/acervo.css",
        "/exemplares.css",
        "/clientes.css",
        "/locacoes.css",
    ]
)
