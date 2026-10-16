"""Aplicação principal da locadora com login de funcionários em Reflex."""

from __future__ import annotations

import reflex as rx

from ProjetoLocadora.catalogo_filmes import (
    CLASSIFICACOES,
    Filme,
    FilmeCatalogo,
    centavos_para_reais,
    validar_filme,
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
    get_me_xano,
    is_authorized_employee,
    list_films_xano,
    list_customers_xano,
    list_exemplares_xano,
    login_xano,
    request_password_reset,
    update_film_xano,
    update_customer_xano,
    update_password_xano,
    set_customer_manual_block_xano,
)


class State(rx.State):
    """Estado de autenticação do backoffice e sessão do funcionário."""

    is_loading: bool = False
    error_message: str = ""
    _login_email: str = ""
    _login_password: str = ""
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
    exemplar_films_error: str = ""
    exemplar_form_error: str = ""
    exemplar_form_loading: bool = False

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

    def capture_login_email(self, value: str) -> None:
        self._login_email = value

    def capture_login_password(self, value: str) -> None:
        self._login_password = value

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

    def _clear_session(self) -> None:
        self._login_email = ""
        self._login_password = ""
        self._xano_auth_token = ""
        self._user_id = ""
        self._user_name = ""
        self._user_email = ""
        self._user_role = ""
        self.error_message = ""

    def _set_user(self, me: dict[str, object]) -> None:
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

        if self._user_role == "admin":
            self.exemplar_films_error = ""
            self.exemplar_films = []
            try:
                self.exemplar_films = await list_films_xano(self._xano_auth_token)
            except XanoCatalogError as err:
                self.exemplar_films_error = err.user_message

    async def submit_exemplar(self):
        redirect = self._require_exemplar_admin()
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
        finally:
            self.exemplar_form_loading = False

    async def load_customers(self):
        if not self._xano_auth_token:
            self._clear_session()
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
        if redirect:
            return redirect
        self._clear_film_form()
        self.editing_film = False
        self.films_success = ""

    async def load_film_for_edit(self):
        redirect = self._require_catalog_admin()
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
        finally:
            self.form_loading = False

    async def submit_film(self):
        if not self._xano_auth_token:
            self._clear_session()
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
            return

        me = await get_me_xano(self._xano_auth_token)
        if not me or not is_authorized_employee(me):
            self._clear_session()
            return

        self._set_user(me)
        return rx.redirect("/backoffice")

    async def require_session(self):
        if not self._xano_auth_token:
            self._clear_session()
            return rx.redirect("/login")

        me = await get_me_xano(self._xano_auth_token)
        if not me or not is_authorized_employee(me):
            self._clear_session()
            return rx.redirect("/login")

        self._set_user(me)

    async def handle_login(self):
        email = self._login_email.strip()
        password = self._login_password
        self._login_password = ""
        if not email or not password:
            self.error_message = GENERIC_AUTH_ERROR
            return

        self.is_loading = True
        self.error_message = ""

        auth_data = await login_xano(email, password)
        password = ""
        if not auth_data or not auth_data.get("authToken"):
            self._clear_session()
            self.is_loading = False
            self.error_message = GENERIC_AUTH_ERROR
            return

        me_data = await get_me_xano(auth_data["authToken"])
        if not me_data or not is_authorized_employee(me_data):
            self._clear_session()
            self.is_loading = False
            self.error_message = GENERIC_AUTH_ERROR
            return

        self._xano_auth_token = auth_data["authToken"]
        self._set_user(me_data)
        self.is_loading = False
        return rx.redirect("/backoffice")

    async def logout(self) -> None:
        self._clear_session()
        return rx.redirect("/login")

    async def request_reset_link(self) -> None:
        email = self._reset_request_email.strip()
        self.reset_message = "Se o e-mail estiver cadastrado, enviaremos um link para redefinição."
        self.reset_message_is_error = False
        if email:
            await request_password_reset(email)

    async def consume_reset_link(self) -> None:
        params = self.router.page.params
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


@rx.page(route="/login", on_load=State.restore_session)
def login_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Acesso do funcionário", size="8"),
            rx.text("Use sua conta de membro ou administrador para entrar.", color="gray"),
            rx.vstack(
                rx.input(
                    placeholder="E-mail",
                    type="email",
                    required=True,
                    size="3",
                    on_change=State.capture_login_email,
                ),
                rx.input(
                    placeholder="Senha",
                    type="password",
                    required=True,
                    size="3",
                    on_change=State.capture_login_password,
                ),
                rx.cond(
                    State.error_message != "",
                    rx.callout(
                        State.error_message,
                        color_scheme="red",
                        role="alert",
                    ),
                ),
                rx.button(
                    "Entrar",
                    on_click=State.handle_login,
                    loading=State.is_loading,
                    size="3",
                    width="100%",
                ),
                spacing="4",
            ),
            rx.link(
                "Recuperar senha",
                href="/recuperar-senha",
                color="blue",
            ),
            spacing="4",
            justify="center",
            min_height="85vh",
        )
    )


def render_dashboard() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Backoffice da locadora", size="8"),
                    rx.cond(
                        State.user_name != "",
                        rx.text("Olá, ", State.user_name, " · ", State.user_role, color="gray"),
                        rx.text("Olá, funcionário · ", State.user_role, color="gray"),
                    ),
                    spacing="1",
                ),
                rx.button("Sair", on_click=State.logout, size="3"),
                width="100%",
                justify="between",
                align="center",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.text("Locações ativas", color="gray", size="3"),
                        rx.heading("—", size="7"),
                        rx.text("Dados indisponíveis", color="gray", size="2"),
                        spacing="0",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Exemplares disponíveis", color="gray", size="3"),
                        rx.heading("—", size="7"),
                        rx.text("Dados indisponíveis", color="gray", size="2"),
                        spacing="0",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Multas pendentes", color="gray", size="3"),
                        rx.heading("—", size="7"),
                        rx.text("Dados indisponíveis", color="gray", size="2"),
                        spacing="0",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            rx.hstack(
                rx.box(
                    rx.vstack(
                        rx.heading("Resumo da sessão", size="6"),
                        rx.text("Usuário: ", State.user_name),
                        rx.text("E-mail: ", State.user_email),
                        rx.text("Perfil: ", State.user_role),
                        spacing="2",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.heading("Ações rápidas", size="6"),
                        rx.text("Os módulos da locadora serão adicionados por etapas.", color="gray"),
                        spacing="2",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            rx.link("Gerenciar catálogo de filmes", href="/filmes"),
            rx.link("Gerenciar clientes", href="/clientes"),
            rx.link("Consultar exemplares", href="/exemplares"),
            spacing="5",
            min_height="85vh",
        ),
    )


def render_customer_card(customer: ClienteResumo) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading(customer["nome"], size="5"),
                rx.text(customer["cpf_mascarado"], color="gray"),
                rx.text(
                    rx.cond(customer["status"] == "active", "Ativo", "Inativo"),
                    " · ",
                    rx.cond(
                        customer["bloqueio_manual_ativo"],
                        "Bloqueio manual ativo",
                        "Sem bloqueio manual",
                    ),
                ),
                spacing="1",
                align="start",
            ),
            rx.link("Consultar", href=f"/clientes/{customer['id']}"),
            width="100%",
            justify="between",
            align="center",
        ),
        padding="1rem",
        border="1px solid #e5e7eb",
        border_radius="12px",
        width="100%",
    )


def render_customers_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.heading("Clientes", size="8"),
                rx.cond(
                    State.user_role == "admin",
                    rx.link("Cadastrar cliente", href="/clientes/novo"),
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            rx.link("Voltar ao backoffice", href="/backoffice"),
            rx.cond(
                State.customers_success != "",
                rx.callout(State.customers_success, color_scheme="green", role="status"),
            ),
            rx.hstack(
                rx.input(
                    placeholder="Buscar por nome",
                    value=State.customer_name_search,
                    on_change=State.capture_customer_name_search,
                    aria_label="Buscar cliente por nome",
                ),
                rx.input(
                    placeholder="CPF completo",
                    value=State.customer_cpf_search,
                    on_change=State.capture_customer_cpf_search,
                    aria_label="Buscar cliente por CPF completo",
                ),
                rx.button("Buscar", on_click=State.apply_customer_filters),
                width="100%",
            ),
            rx.cond(
                State.customers_error != "",
                rx.callout(State.customers_error, color_scheme="red", role="alert"),
            ),
            rx.cond(
                State.customers_loading,
                rx.spinner(),
                rx.cond(
                    State.customers_error != "",
                    rx.fragment(),
                    rx.cond(
                        State.has_customers,
                        rx.vstack(
                            rx.foreach(State.customers, render_customer_card),
                            width="100%",
                            align="stretch",
                        ),
                        rx.text("Nenhum cliente encontrado.", color="gray"),
                    ),
                ),
            ),
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=State.previous_customers_page,
                    disabled=~State.customers_has_previous_page,
                    variant="outline",
                ),
                rx.text("Página ", State.customers_page, " · ", State.customers_total, " cliente(s)"),
                rx.button(
                    "Próxima",
                    on_click=State.next_customers_page,
                    disabled=~State.customers_has_next_page,
                    variant="outline",
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        max_width="60rem",
        padding_y="2rem",
    )


def render_customer_form() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading(
                rx.cond(State.editing_customer, "Editar cliente", "Cadastrar cliente"),
                size="8",
            ),
            rx.link("Voltar aos clientes", href="/clientes"),
            rx.cond(
                State.customer_form_error != "",
                rx.callout(State.customer_form_error, color_scheme="red", role="alert"),
            ),
            rx.input(
                placeholder="Nome completo",
                value=State.customer_form_name,
                on_change=State.capture_customer_name,
                max_length=200,
                required=True,
                aria_label="Nome completo do cliente",
            ),
            rx.input(
                placeholder="CPF",
                value=State.customer_form_cpf,
                on_change=State.capture_customer_cpf,
                required=True,
                aria_label="CPF do cliente",
            ),
            rx.input(
                placeholder="E-mail",
                type="email",
                value=State.customer_form_email,
                on_change=State.capture_customer_email,
                max_length=254,
                aria_label="E-mail do cliente",
            ),
            rx.input(
                placeholder="Telefone",
                value=State.customer_form_phone,
                on_change=State.capture_customer_phone,
                aria_label="Telefone do cliente",
            ),
            rx.text("Informe ao menos um contato: e-mail ou telefone.", color="gray", size="2"),
            rx.cond(
                State.editing_customer,
                rx.select(
                    ["active", "inactive"],
                    value=State.customer_form_status,
                    on_change=State.capture_customer_status,
                    required=True,
                    aria_label="Situação cadastral do cliente",
                ),
            ),
            rx.button(
                "Salvar cliente",
                on_click=State.submit_customer,
                loading=State.customer_form_loading,
                disabled=State.editing_customer & (State.editing_customer_id == 0),
                width="100%",
            ),
            spacing="4",
            align="stretch",
            width="100%",
        ),
        max_width="36rem",
        padding_y="2rem",
    )


def render_customer_detail() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.link("Voltar aos clientes", href="/clientes"),
            rx.cond(
                State.customer_detail_error != "",
                rx.callout(State.customer_detail_error, color_scheme="red", role="alert"),
            ),
            rx.cond(
                State.customers_success != "",
                rx.callout(State.customers_success, color_scheme="green", role="status"),
            ),
            rx.cond(
                State.customer_detail_loading,
                rx.spinner(),
                rx.cond(
                    State.customer_detail_loaded,
                    rx.vstack(
                        rx.hstack(
                            rx.heading(State.customer_detail["nome"], size="8"),
                            rx.cond(
                                State.user_role == "admin",
                                rx.link(
                                    "Editar cadastro",
                                    href=f"/clientes/{State.customer_detail['id']}/editar",
                                ),
                            ),
                            width="100%",
                            justify="between",
                            align="center",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("CPF: ", State.customer_detail["cpf"]),
                                rx.text("E-mail: ", State.customer_detail["email"]),
                                rx.text("Telefone: ", State.customer_detail["telefone"]),
                                rx.text(
                                    "Situação: ",
                                    rx.cond(State.customer_detail["status"] == "active", "Ativo", "Inativo"),
                                ),
                                rx.text(
                                    "Bloqueio manual: ",
                                    rx.cond(
                                        State.customer_detail["bloqueio_manual_ativo"],
                                        "Ativo",
                                        "Não aplicado",
                                    ),
                                ),
                                rx.cond(
                                    State.customer_detail["bloqueio_manual_ativo"],
                                    rx.text("Motivo: ", State.customer_detail["motivo_bloqueio_manual"]),
                                ),
                                align="start",
                                spacing="2",
                            ),
                            padding="1.5rem",
                            border="1px solid #e5e7eb",
                            border_radius="12px",
                            width="100%",
                        ),
                        rx.cond(
                            State.user_role == "admin",
                            rx.box(
                                rx.vstack(
                                    rx.heading("Controle de bloqueio manual", size="5"),
                                    rx.cond(
                                        ~State.customer_detail["bloqueio_manual_ativo"],
                                        rx.input(
                                            placeholder="Motivo obrigatório",
                                            value=State.customer_block_reason,
                                            on_change=State.capture_customer_block_reason,
                                            max_length=500,
                                            aria_label="Motivo do bloqueio manual",
                                        ),
                                    ),
                                    rx.button(
                                        rx.cond(
                                            State.customer_detail["bloqueio_manual_ativo"],
                                            "Remover bloqueio manual",
                                            "Aplicar bloqueio manual",
                                        ),
                                        on_click=State.toggle_customer_manual_block,
                                        loading=State.customer_block_loading,
                                        color_scheme=rx.cond(
                                            State.customer_detail["bloqueio_manual_ativo"],
                                            "green",
                                            "red",
                                        ),
                                    ),
                                    align="stretch",
                                    spacing="3",
                                ),
                                padding="1.5rem",
                                border="1px solid #e5e7eb",
                                border_radius="12px",
                                width="100%",
                            ),
                        ),
                        rx.box(
                            rx.vstack(
                                rx.heading("Histórico e pendências", size="5"),
                                rx.text(
                                    "Aguardando implementação das capacidades de locações, multas e pagamentos. Nenhum saldo ou histórico financeiro é apresentado nesta versão.",
                                    color="gray",
                                ),
                                align="start",
                                spacing="2",
                            ),
                            padding="1.5rem",
                            border="1px solid #e5e7eb",
                            border_radius="12px",
                            width="100%",
                        ),
                        spacing="4",
                        width="100%",
                        align="stretch",
                    ),
                    rx.fragment(),
                ),
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        max_width="60rem",
        padding_y="2rem",
    )


def render_film_card(film: FilmeCatalogo) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading(film["titulo"], size="5"),
                rx.text(film["genero"], " · ", film["ano_lancamento"], color="gray"),
                rx.text(
                    film["classificacao"],
                    " · ",
                    film["valor_locacao_display"],
                    " · ",
                    rx.cond(film["status"] == "active", "Ativo", "Inativo"),
                ),
                spacing="1",
                align="start",
            ),
            rx.cond(
                State.user_role == "admin",
                rx.link(
                    "Editar",
                    href=f"/filmes/{film['id']}/editar",
                ),
            ),
            width="100%",
            justify="between",
            align="center",
        ),
        padding="1rem",
        border="1px solid #e5e7eb",
        border_radius="12px",
        width="100%",
    )


def render_films_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.heading("Catálogo de filmes", size="8"),
                rx.cond(
                    State.user_role == "admin",
                    rx.link("Cadastrar filme", href="/filmes/novo"),
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            rx.link("Voltar ao backoffice", href="/backoffice"),
            rx.cond(
                State.films_success != "",
                rx.callout(
                    State.films_success,
                    color_scheme="green",
                    role="status",
                ),
            ),
            rx.hstack(
                rx.input(
                    placeholder="Buscar por título",
                    value=State.title_search,
                    on_change=State.capture_title_search,
                    aria_label="Buscar por título",
                ),
                rx.input(
                    placeholder="Filtrar por gênero",
                    value=State.genre_filter,
                    on_change=State.capture_genre_filter,
                    aria_label="Filtrar por gênero",
                ),
                rx.button("Buscar", on_click=State.apply_film_filters),
                width="100%",
            ),
            rx.cond(
                State.films_error != "",
                rx.callout(State.films_error, color_scheme="red", role="alert"),
            ),
            rx.cond(
                State.films_loading,
                rx.spinner(),
                rx.cond(
                    State.films_error != "",
                    rx.fragment(),
                    rx.cond(
                        State.has_films,
                        rx.vstack(
                            rx.foreach(State.films, render_film_card),
                            width="100%",
                            align="stretch",
                        ),
                        rx.text("Nenhum filme encontrado.", color="gray"),
                    ),
                ),
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        max_width="60rem",
        padding_y="2rem",
    )


def render_exemplar_card(exemplar: Exemplar) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Exemplar ", exemplar["identificador"], size="5"),
            rx.text("Filme: ", exemplar["filme_titulo"]),
            rx.text("ID do filme: ", exemplar["filme_id"], color="gray"),
            spacing="1",
            align="start",
        ),
        padding="1rem",
        border="1px solid #e5e7eb",
        border_radius="12px",
        width="100%",
    )


def render_exemplares_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.heading("Exemplares", size="8"),
                width="100%",
                justify="between",
                align="center",
            ),
            rx.link("Voltar ao backoffice", href="/backoffice"),
            rx.cond(
                State.exemplares_success != "",
                rx.callout(
                    State.exemplares_success,
                    color_scheme="green",
                    role="status",
                ),
            ),
            rx.cond(
                State.exemplares_error != "",
                rx.callout(
                    State.exemplares_error,
                    color_scheme="red",
                    role="alert",
                ),
            ),
            rx.cond(
                State.user_role == "admin",
                rx.box(
                    rx.vstack(
                        rx.heading("Cadastrar exemplar", size="5"),
                        rx.cond(
                            State.exemplar_films_error != "",
                            rx.callout(
                                State.exemplar_films_error,
                                color_scheme="red",
                                role="alert",
                            ),
                        ),
                        rx.cond(
                            State.exemplar_form_error != "",
                            rx.callout(
                                State.exemplar_form_error,
                                color_scheme="red",
                                role="alert",
                            ),
                        ),
                        rx.input(
                            placeholder="Identificador do exemplar",
                            value=State.exemplar_identifier,
                            on_change=State.capture_exemplar_identifier,
                            required=True,
                            aria_label="Identificador do exemplar",
                        ),
                        rx.select(
                            State.exemplar_film_options,
                            value=State.exemplar_film_selection,
                            on_change=State.capture_exemplar_film_selection,
                            required=True,
                            aria_label="Filme associado ao exemplar",
                        ),
                        rx.button(
                            "Cadastrar exemplar",
                            on_click=State.submit_exemplar,
                            loading=State.exemplar_form_loading,
                            width="100%",
                        ),
                        spacing="3",
                        align="stretch",
                        width="100%",
                    ),
                    padding="1.5rem",
                    border="1px solid #e5e7eb",
                    border_radius="12px",
                    width="100%",
                ),
            ),
            rx.cond(
                State.exemplares_loading,
                rx.spinner(),
                rx.cond(
                    State.exemplares_error != "",
                    rx.fragment(),
                    rx.cond(
                        State.has_exemplares,
                        rx.vstack(
                            rx.foreach(State.exemplares, render_exemplar_card),
                            width="100%",
                            align="stretch",
                        ),
                        rx.text("Nenhum exemplar encontrado.", color="gray"),
                    ),
                ),
            ),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        max_width="60rem",
        padding_y="2rem",
    )


def render_film_form() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading(
                rx.cond(State.editing_film, "Editar filme", "Cadastrar filme"),
                size="8",
            ),
            rx.link("Voltar ao catálogo", href="/filmes"),
            rx.cond(
                State.form_error != "",
                rx.callout(State.form_error, color_scheme="red", role="alert"),
            ),
            rx.input(
                placeholder="Título",
                value=State.form_title,
                on_change=State.capture_film_title,
                max_length=200,
                required=True,
                aria_label="Título",
            ),
            rx.input(
                placeholder="Gênero",
                value=State.form_genre,
                on_change=State.capture_film_genre,
                max_length=100,
                required=True,
                aria_label="Gênero",
            ),
            rx.input(
                placeholder="Ano de lançamento",
                type="number",
                min=1888,
                value=State.form_year,
                on_change=State.capture_film_year,
                required=True,
                aria_label="Ano de lançamento",
            ),
            rx.select(
                list(CLASSIFICACOES),
                value=State.form_classification,
                on_change=State.capture_film_classification,
                required=True,
                aria_label="Classificação indicativa",
            ),
            rx.input(
                placeholder="Valor da locação (R$)",
                value=State.form_rent_price,
                on_change=State.capture_film_rent_price,
                required=True,
                aria_label="Valor da locação em reais",
            ),
            rx.cond(
                State.editing_film,
                rx.select(
                    ["active", "inactive"],
                    value=State.form_status,
                    on_change=State.capture_film_status,
                    required=True,
                    aria_label="Status do filme",
                ),
            ),
            rx.button(
                "Salvar alterações",
                on_click=State.submit_film,
                loading=State.form_loading,
                disabled=State.editing_film & (State.editing_film_id == 0),
                width="100%",
            ),
            spacing="4",
            align="stretch",
            width="100%",
        ),
        max_width="36rem",
        padding_y="2rem",
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


@rx.page(route="/filmes/novo", on_load=State.load_new_film)
def new_film_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_film_form(), rx.fragment())


@rx.page(route="/filmes/[film_id]/editar", on_load=State.load_film_for_edit)
def edit_film_page() -> rx.Component:
    return rx.cond(State.is_authenticated, render_film_form(), rx.fragment())


@rx.page(route="/", on_load=State.require_session)
def index() -> rx.Component:
    return rx.cond(
        State.is_authenticated,
        render_dashboard(),
        rx.fragment(),
    )


@rx.page(route="/backoffice", on_load=State.require_session)
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


app = rx.App()
