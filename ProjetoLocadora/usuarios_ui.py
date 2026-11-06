"""Página de usuários (somente administradores): papel e situação das contas."""

import reflex as rx

from ProjetoLocadora.usuarios_state import UsuariosState as Users


def _notice(content, kind: str, role: str) -> rx.Component:
    return rx.box(content, role=role, class_name=f"vitrine-dash__notice vitrine-dash__notice--{kind}")


def _filter_tab(item) -> rx.Component:
    selected = Users.status_filter == item["key"]
    return rx.el.button(
        item["label"], type="button", role="tab", aria_selected=selected,
        on_click=Users.set_status_filter(item["key"]),
        class_name=rx.cond(selected, "vitrine-locacoes__tab vitrine-locacoes__tab--on", "vitrine-locacoes__tab"),
    )


def _row(row) -> rx.Component:
    main = (
        rx.box(
            rx.el.span(row["name"], class_name="vitrine-locacoes__row-title"),
            rx.el.span(row["email"], class_name="vitrine-locacoes__row-meta"),
            rx.el.span("Cadastro em " + row["created"], class_name="vitrine-locacoes__row-meta vitrine-locacoes__row-when"),
            class_name="vitrine-locacoes__row-main",
        ),
        rx.box(
            rx.el.span(row["role_label"], class_name="vitrine-multas__chip"),
            rx.cond(
                row["active"],
                rx.el.span("Ativa", class_name="vitrine-multas__chip vitrine-multas__chip--paid"),
                rx.el.span("Desativada", class_name="vitrine-multas__chip vitrine-multas__chip--open"),
            ),
            class_name="vitrine-multas__row-side",
        ),
    )
    return rx.el.li(
        rx.cond(
            row["is_self"],
            rx.box(
                *main,
                rx.el.span("Você", class_name="vitrine-usuarios__self"),
                class_name="vitrine-locacoes__row vitrine-usuarios__row--self",
            ),
            rx.el.button(
                *main,
                rx.icon("chevron-right", size=16, stroke_width=1.8, aria_hidden="true", class_name="vitrine-locacoes__row-arrow"),
                type="button",
                on_click=Users.open_edit(row["id"]),
                aria_label="Alterar conta de " + row["name"],
                class_name="vitrine-locacoes__row vitrine-usuarios__row-button",
            ),
        ),
        class_name="vitrine-locacoes__item",
    )


def _list() -> rx.Component:
    return rx.el.section(
        rx.box(
            rx.box(
                rx.el.h2("Contas", class_name="vitrine-clientes__panel-title"),
                rx.el.p(Users.summary, class_name="vitrine-clientes__panel-sub", aria_live="polite"),
            ),
            rx.el.button(
                rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                "Atualizar lista", type="button", on_click=Users.reload, disabled=Users.loading,
                class_name="vitrine-clientes__secondary",
            ),
            class_name="vitrine-locacoes__list-head",
        ),
        rx.box(
            rx.el.input(
                type="search", value=Users.search, on_change=Users.capture_search,
                placeholder="Buscar por nome ou e-mail", aria_label="Buscar por nome ou e-mail",
                class_name="vitrine-locacoes__select vitrine-usuarios__search",
            ),
            rx.box(rx.foreach(Users.status_filters, _filter_tab), role="tablist", aria_label="Situação das contas", class_name="vitrine-locacoes__tabs"),
            class_name="vitrine-usuarios__filters",
        ),
        rx.cond(
            Users.truncated,
            rx.el.p("Mostrando as primeiras 500 contas; a lista pode estar incompleta.", class_name="vitrine-locacoes__hint"),
        ),
        rx.cond(
            Users.rows.length() > 0,
            rx.el.ul(rx.foreach(Users.rows, _row), class_name="vitrine-locacoes__items", aria_label="Lista de contas"),
            rx.box(rx.el.p("Nenhuma conta encontrada.", class_name="vitrine-clientes__empty-title"), class_name="vitrine-clientes__placeholder"),
        ),
        class_name="vitrine-clientes__panel vitrine-locacoes__list",
        aria_label="Contas",
    )


def _edit_dialog() -> rx.Component:
    user = Users.edit_user
    return rx.dialog.root(
        rx.dialog.content(
            rx.box(
                rx.box(
                    rx.dialog.title("Alterar conta", class_name="vitrine-exemplares__dialog-title"),
                    rx.dialog.description(user["name"] + " · " + user["email"], class_name="vitrine-exemplares__dialog-sub"),
                ),
                rx.dialog.close(
                    rx.el.button(
                        rx.icon("x", size=18, stroke_width=1.8, aria_hidden="true"),
                        type="button", aria_label="Fechar", disabled=Users.saving,
                        class_name="vitrine-exemplares__close",
                    )
                ),
                class_name="vitrine-exemplares__dialog-head",
            ),
            rx.el.p("Hoje: " + user["role_label"] + " · " + user["active_label"], class_name="vitrine-exemplares__hint"),
            rx.cond(Users.edit_error != "", rx.box(Users.edit_error, role="alert", class_name="vitrine-exemplares__alert")),
            rx.cond(
                Users.confirming,
                rx.fragment(
                    rx.el.p(
                        "Confirmar a desativação? A pessoa não consegue mais entrar e as operações dela passam a ser recusadas. A conta e o histórico são preservados.",
                        class_name="vitrine-exemplares__dialog-sub",
                    ),
                    rx.box(
                        rx.el.button("Voltar", type="button", on_click=Users.cancel_confirm, disabled=Users.saving, class_name="vitrine-exemplares__cancel"),
                        rx.button(
                            "Confirmar desativação", on_click=Users.submit_edit, loading=Users.saving,
                            class_name="vitrine-exemplares__primary vitrine-exemplares__danger",
                        ),
                        class_name="vitrine-exemplares__dialog-actions",
                    ),
                ),
                rx.fragment(
                    rx.box(
                        rx.el.label("Papel", html_for="usuario-papel", class_name="vitrine-exemplares__label"),
                        rx.el.select(
                            rx.foreach(Users.role_options, lambda option: rx.el.option(option, value=option)),
                            id="usuario-papel", value=Users.edit_role_label, on_change=Users.capture_role,
                            disabled=Users.saving, class_name="vitrine-exemplares__input vitrine-exemplares__select",
                        ),
                        class_name="vitrine-exemplares__field",
                    ),
                    rx.el.label(
                        rx.el.input(
                            type="checkbox", checked=Users.edit_active, on_change=Users.capture_active,
                            disabled=Users.saving, class_name="vitrine-exemplares__checkbox",
                        ),
                        "Conta ativa",
                        class_name="vitrine-exemplares__toggle",
                    ),
                    rx.box(
                        rx.el.label("Motivo", html_for="usuario-motivo", class_name="vitrine-exemplares__label"),
                        rx.el.textarea(
                            id="usuario-motivo", value=Users.edit_reason, on_change=Users.capture_reason,
                            max_length=500, placeholder="Obrigatório. Até 500 caracteres.", disabled=Users.saving,
                            class_name="vitrine-exemplares__input vitrine-exemplares__textarea",
                        ),
                        class_name="vitrine-exemplares__field",
                    ),
                    rx.el.p("A alteração fica registrada em seu nome, com o motivo. Nenhuma conta é apagada.", class_name="vitrine-exemplares__hint"),
                    rx.box(
                        rx.dialog.close(rx.el.button("Cancelar", type="button", disabled=Users.saving, class_name="vitrine-exemplares__cancel")),
                        rx.button("Salvar", on_click=Users.submit_edit, loading=Users.saving, class_name="vitrine-exemplares__primary"),
                        class_name="vitrine-exemplares__dialog-actions",
                    ),
                ),
            ),
            class_name="vitrine-exemplares-dialog",
        ),
        open=Users.edit_open,
        on_open_change=Users.set_edit_open,
    )


def users_page(topbar: rx.Component) -> rx.Component:
    return rx.el.main(
        topbar,
        rx.el.section(
            rx.box(
                rx.el.h1("Usuários", class_name="vitrine-dash__title"),
                rx.el.p("Papel e situação das contas do backoffice. Novas contas entram pelo cadastro como Funcionário.", class_name="vitrine-dash__subtitle"),
                class_name="vitrine-dash__heading-text",
            ),
            class_name="vitrine-dash__heading",
        ),
        rx.cond(
            Users.state == "forbidden",
            _notice("Gestão de usuários disponível apenas para administradores.", "muted", "status"),
            rx.fragment(
                rx.cond(Users.message != "", _notice(Users.message, "error", "alert")),
                rx.cond(Users.notice != "", _notice(Users.notice, "success", "status")),
                rx.match(
                    Users.state,
                    ("loading", rx.box(rx.spinner(), rx.text("Carregando contas…"), role="status", aria_live="polite", class_name="vitrine-dash__notice vitrine-dash__notice--loading")),
                    ("error", rx.el.button("Tentar novamente", type="button", on_click=Users.reload, disabled=Users.loading, class_name="vitrine-clientes__secondary")),
                    ("ready", _list()),
                    rx.fragment(),
                ),
                _edit_dialog(),
            ),
        ),
        class_name="vitrine-dash vitrine-locacoes vitrine-usuarios",
    )
