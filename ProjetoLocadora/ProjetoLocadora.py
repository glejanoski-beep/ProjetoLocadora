"""Aplicação principal da locadora com login de funcionários em Reflex."""

from __future__ import annotations

import reflex as rx

from ProjetoLocadora.xano_client import (
    GENERIC_AUTH_ERROR,
    get_me_xano,
    is_authorized_employee,
    login_xano,
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
            self.is_loading = False
            self.error_message = GENERIC_AUTH_ERROR
            self._clear_session()
            return

        me_data = await get_me_xano(auth_data["authToken"])
        if not me_data or not is_authorized_employee(me_data):
            self.is_loading = False
            self.error_message = GENERIC_AUTH_ERROR
            self._clear_session()
            return

        self._xano_auth_token = auth_data["authToken"]
        self._set_user(me_data)
        self.is_loading = False
        return rx.redirect("/backoffice")

    async def logout(self) -> None:
        self._clear_session()
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
                href="/redefinir-senha",
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
            spacing="5",
            min_height="85vh",
        ),
    )


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


@rx.page(route="/redefinir-senha")
def reset_password_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Redefinição de senha", size="8"),
            rx.text(
                "Use o link recebido por e-mail para continuar a redefinição da sua senha."
            ),
            rx.link("Voltar ao login", href="/login"),
            spacing="4",
            justify="center",
            min_height="85vh",
        )
    )


app = rx.App()
