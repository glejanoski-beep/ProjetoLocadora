"""Páginas operacionais de locação, no padrão visual das telas do CineGestão."""

import reflex as rx

from ProjetoLocadora.locacoes_state import LocacoesState as RentalState

NEW_RENTAL_HREF = "/locacoes/nova"


def _notice(content, kind: str, role: str) -> rx.Component:
    return rx.box(content, role=role, class_name=f"vitrine-dash__notice vitrine-dash__notice--{kind}")


def messages() -> rx.Component:
    return rx.fragment(
        rx.cond(RentalState.message != "", _notice(RentalState.message, "error", "alert")),
        rx.cond(
            (RentalState.notice != "") & ~RentalState.writes_blocked,
            _notice(RentalState.notice, "success", "status"),
        ),
        rx.cond(
            RentalState.loading,
            rx.box(
                rx.spinner(),
                rx.text("Consultando o serviço…"),
                role="status",
                aria_live="polite",
                class_name="vitrine-dash__notice vitrine-dash__notice--loading",
            ),
        ),
    )


def _reload_button() -> rx.Component:
    return rx.cond(
        RentalState.message != "",
        rx.el.button(
            rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
            "Tentar novamente",
            type="button",
            on_click=RentalState.load_new,
            disabled=RentalState.loading,
            class_name="vitrine-clientes__secondary vitrine-locacoes__refresh",
        ),
    )


def _back_link(label: str, href: str) -> rx.Component:
    return rx.el.a(
        rx.icon("arrow-left", size=16, stroke_width=1.8, aria_hidden="true"),
        label,
        href=href,
        class_name="vitrine-clientes__back",
    )


def _heading(title: str, subtitle: str, aside: rx.Component | None = None) -> rx.Component:
    return rx.el.section(
        rx.box(
            rx.el.span("OPERAÇÃO", class_name="vitrine-clientes__eyebrow"),
            rx.el.h1(title, class_name="vitrine-dash__title"),
            rx.el.p(subtitle, class_name="vitrine-dash__subtitle"),
            class_name="vitrine-dash__heading-text",
        ),
        aside if aside is not None else rx.fragment(),
        class_name="vitrine-dash__heading",
    )


def rental_lookup() -> rx.Component:
    """Abre o detalhe de uma locação existente pelo número."""
    return rx.el.form(
        rx.el.label("Abrir locação pelo número", html_for="locacao-numero", class_name="vitrine-clientes__label"),
        rx.box(
            rx.el.input(
                id="locacao-numero",
                name="rental_number",
                type="text",
                input_mode="numeric",
                max_length=10,
                placeholder="Nº da locação",
                aria_label="Número da locação",
                class_name="vitrine-clientes__input vitrine-locacoes__lookup-input",
            ),
            rx.el.button("Abrir", type="submit", class_name="vitrine-clientes__search-button"),
            class_name="vitrine-locacoes__lookup-row",
        ),
        rx.cond(
            RentalState.lookup_error != "",
            rx.el.span(RentalState.lookup_error, role="alert", class_name="vitrine-locacoes__lookup-error"),
        ),
        on_submit=RentalState.open_rental,
        reset_on_submit=False,
        class_name="vitrine-locacoes__lookup",
        aria_label="Abrir locação pelo número",
    )


def _field(label: str, field_id: str, control: rx.Component, hint: str = "") -> rx.Component:
    return rx.box(
        rx.el.label(label, html_for=field_id, class_name="vitrine-clientes__label"),
        control,
        rx.el.span(hint, class_name="vitrine-locacoes__hint") if hint else rx.fragment(),
        class_name="vitrine-clientes__field",
    )


def _select(field_id: str, options, value, on_change, placeholder: str, label: str) -> rx.Component:
    return rx.el.select(
        rx.el.option(placeholder, value=""),
        rx.foreach(options, lambda option: rx.el.option(option, value=option)),
        id=field_id,
        value=value,
        on_change=on_change,
        disabled=RentalState.editing_disabled,
        aria_label=label,
        class_name="vitrine-clientes__input vitrine-locacoes__select",
    )


def confirmation() -> rx.Component:
    return rx.cond(
        RentalState.confirmation != "",
        rx.box(
            rx.el.h2("Locação registrada", class_name="vitrine-clientes__panel-title"),
            rx.el.p(RentalState.confirmation, class_name="vitrine-clientes__panel-sub"),
            rx.box(
                rx.el.a(
                    rx.icon("file-text", size=16, stroke_width=1.8, aria_hidden="true"),
                    "Abrir detalhes",
                    href=RentalState.confirmation_link,
                    class_name="vitrine-clientes__primary",
                ),
                rx.el.a("Registrar outra locação", href=NEW_RENTAL_HREF, class_name="vitrine-clientes__secondary"),
                class_name="vitrine-locacoes__actions",
            ),
            class_name="vitrine-clientes__panel",
            role="region",
            aria_label="Locação registrada",
        ),
    )


def _pending_panel() -> rx.Component:
    return rx.cond(
        RentalState.has_pending,
        rx.box(
            rx.el.h2("Tentativa pendente de confirmação", class_name="vitrine-clientes__panel-title"),
            rx.el.p(
                "Existe uma tentativa pendente de confirmação. Consulte-a antes de qualquer outra ação.",
                class_name="vitrine-clientes__panel-sub",
            ),
            rx.box(
                rx.el.button("Consultar tentativa", type="button", on_click=RentalState.reconcile, disabled=RentalState.loading, class_name="vitrine-clientes__primary"),
                rx.el.button("Repetir a mesma tentativa", type="button", on_click=RentalState.repeat_pending, disabled=RentalState.loading | ~RentalState.writes_available, class_name="vitrine-clientes__secondary"),
                class_name="vitrine-locacoes__actions",
            ),
            class_name="vitrine-clientes__panel",
            role="region",
            aria_label="Tentativa pendente",
        ),
    )


def _condition_panel() -> rx.Component:
    return rx.el.section(
        rx.el.h2("Conferir condição do exemplar", class_name="vitrine-clientes__panel-title"),
        rx.el.p("Registre a condição após conferir o exemplar. Isso não libera exemplares com locação ativa.", class_name="vitrine-clientes__panel-sub"),
        rx.cond(
            ~RentalState.admin_loaded,
            rx.el.button(
                "Carregar exemplares para conferência",
                type="button",
                on_click=RentalState.load_admin_exemplars,
                disabled=RentalState.loading,
                class_name="vitrine-clientes__secondary vitrine-locacoes__submit",
            ),
        ),
        _field(
            "Exemplar conferido", "locacao-condicao-exemplar",
            _select("locacao-condicao-exemplar", RentalState.admin_exemplar_options, RentalState.condition_exemplar, RentalState.capture_condition_exemplar, "Selecione o exemplar conferido", "Exemplar para conferência"),
        ),
        _field(
            "Condição operacional", "locacao-condicao",
            rx.el.select(
                rx.foreach(["Não conferido", "Apto para locação", "Indisponível"], lambda option: rx.el.option(option, value=option)),
                id="locacao-condicao", value=RentalState.condition_label, on_change=RentalState.capture_condition,
                disabled=RentalState.editing_disabled, aria_label="Condição operacional",
                class_name="vitrine-clientes__input vitrine-locacoes__select",
            ),
        ),
        _field(
            "Motivo da confirmação (obrigatório)", "locacao-motivo",
            rx.el.input(
                id="locacao-motivo", value=RentalState.condition_reason, on_change=RentalState.capture_reason,
                placeholder="Ex.: disco conferido, sem riscos", max_length=500, required=True,
                disabled=RentalState.editing_disabled,
                aria_label="Motivo da condição operacional", class_name="vitrine-clientes__input",
            ),
        ),
        rx.el.button(
            "Confirmar condição", type="button", on_click=RentalState.save_condition,
            disabled=~RentalState.writes_available | RentalState.editing_disabled,
            class_name="vitrine-clientes__secondary vitrine-locacoes__submit",
        ),
        class_name="vitrine-clientes__panel",
        aria_label="Conferir condição do exemplar",
    )


def _step_panel(number: str, title: str, hint: str, *body: rx.Component, label: str) -> rx.Component:
    return rx.el.section(
        rx.box(
            rx.el.span(number, class_name="vitrine-locacoes__step-number", aria_hidden="true"),
            rx.box(
                rx.el.h2(title, class_name="vitrine-clientes__panel-title"),
                rx.el.p(hint, class_name="vitrine-clientes__panel-sub"),
            ),
            class_name="vitrine-locacoes__step-head",
        ),
        *body,
        class_name="vitrine-clientes__panel vitrine-locacoes__step",
        aria_label=label,
    )


def _progress() -> rx.Component:
    return rx.el.ol(
        rx.foreach(
            RentalState.steps,
            lambda step: rx.el.li(
                rx.el.span(
                    rx.cond(step["state"] == "done", rx.icon("check", size=14, stroke_width=2.5, aria_hidden="true"), step["number"]),
                    class_name="vitrine-locacoes__progress-dot",
                ),
                rx.el.span(step["label"]),
                class_name="vitrine-locacoes__progress-item vitrine-locacoes__progress-item--" + step["state"],
                aria_current=rx.cond(step["state"] == "current", "step", None),
            ),
        ),
        class_name="vitrine-locacoes__progress",
        aria_label="Progresso do registro",
    )


def _pagination(visible, previous, next_, on_previous, on_next, summary, noun: str) -> rx.Component:
    return rx.cond(
        visible,
        rx.box(
            rx.el.span(summary, class_name="vitrine-locacoes__hint", aria_live="polite"),
            rx.box(
                rx.el.button("Anteriores", type="button", on_click=on_previous, disabled=~previous | RentalState.editing_disabled, aria_label=f"{noun} anteriores", class_name="vitrine-clientes__secondary"),
                rx.el.button("Próximos", type="button", on_click=on_next, disabled=~next_ | RentalState.editing_disabled, aria_label=f"Próximos {noun.lower()}", class_name="vitrine-clientes__secondary"),
                class_name="vitrine-locacoes__actions",
            ),
            class_name="vitrine-locacoes__pager",
        ),
    )


def _customer_card(card) -> rx.Component:
    return rx.el.button(
        rx.el.span(card["name"], class_name="vitrine-locacoes__card-title"),
        rx.el.span(card["cpf"], class_name="vitrine-locacoes__card-meta"),
        rx.cond(card["reason"] != "", rx.el.span(card["reason"], class_name="vitrine-locacoes__card-tag")),
        type="button",
        on_click=RentalState.capture_customer(card["label"]),
        disabled=card["disabled"] | RentalState.editing_disabled,
        aria_pressed=card["selected"],
        class_name=rx.cond(card["selected"], "vitrine-locacoes__card vitrine-locacoes__card--on", "vitrine-locacoes__card"),
    )


def _exemplar_card(card) -> rx.Component:
    return rx.el.button(
        rx.el.span(card["film"], class_name="vitrine-locacoes__card-title"),
        rx.el.span("Exemplar ", card["code"], class_name="vitrine-locacoes__card-meta"),
        type="button",
        on_click=RentalState.capture_exemplar(card["label"]),
        disabled=RentalState.editing_disabled,
        aria_pressed=card["selected"],
        class_name=rx.cond(card["selected"], "vitrine-locacoes__card vitrine-locacoes__card--on", "vitrine-locacoes__card"),
    )


def _customer_step() -> rx.Component:
    return _step_panel(
        "1", "Selecionar cliente", "Busque pelo nome e escolha quem vai retirar o filme.",
        rx.el.form(
            rx.box(
                rx.icon("search", size=18, stroke_width=1.8, aria_hidden="true"),
                rx.el.input(
                    placeholder="Buscar por nome",
                    value=RentalState.customer_search,
                    on_change=RentalState.capture_customer_search,
                    disabled=RentalState.editing_disabled,
                    aria_label="Buscar cliente para locação",
                    class_name="vitrine-clientes__input vitrine-clientes__input--icon",
                ),
                class_name="vitrine-clientes__search",
            ),
            rx.el.button("Buscar", type="submit", disabled=RentalState.editing_disabled, class_name="vitrine-clientes__search-button"),
            on_submit=lambda _: RentalState.search_customers(),
            class_name="vitrine-clientes__filters",
        ),
        rx.cond(
            RentalState.customer_cards.length() > 0,
            rx.box(rx.foreach(RentalState.customer_cards, _customer_card), class_name="vitrine-locacoes__cards", role="group", aria_label="Clientes"),
            rx.cond(
                RentalState.options_loaded,
                rx.el.p("Nenhum cliente encontrado.", class_name="vitrine-exemplares__empty"),
            ),
        ),
        rx.el.span("Clientes inativos ou bloqueados não podem iniciar uma locação.", class_name="vitrine-locacoes__hint"),
        _pagination(RentalState.customer_paginated, RentalState.customer_previous, RentalState.customer_next, RentalState.customer_page(-1), RentalState.customer_page(1), RentalState.customer_paging, "Clientes"),
        label="Etapa 1: cliente",
    )


def _exemplar_step() -> rx.Component:
    return _step_panel(
        "2", "Selecionar exemplar", "Escolha a cópia física do filme que será entregue. Só aparecem exemplares disponíveis.",
        rx.cond(
            RentalState.exemplar_cards.length() > 0,
            rx.box(rx.foreach(RentalState.exemplar_cards, _exemplar_card), class_name="vitrine-locacoes__cards", role="group", aria_label="Exemplares disponíveis"),
            rx.cond(
                RentalState.options_loaded,
                rx.el.p("Nenhum exemplar disponível para locação no momento.", class_name="vitrine-exemplares__empty"),
            ),
        ),
        _pagination(RentalState.exemplar_paginated, RentalState.exemplar_previous, RentalState.exemplar_next, RentalState.exemplar_page(-1), RentalState.exemplar_page(1), RentalState.exemplar_paging, "Exemplares"),
        label="Etapa 2: exemplar",
    )


def _summary_row(label: str, value) -> rx.Component:
    return rx.box(
        rx.el.dt(label, class_name="vitrine-clientes__data-label"),
        rx.el.dd(rx.cond(value != "", value, "—"), class_name="vitrine-clientes__data-value"),
        class_name="vitrine-locacoes__review-row",
    )


def _confirm_step() -> rx.Component:
    return _step_panel(
        "3", "Vencimento e confirmação", "Informe até quando o exemplar fica com o cliente e confira o resumo.",
        _field(
            "Vencimento (data e hora de Brasília)", "locacao-vencimento",
            rx.el.input(
                id="locacao-vencimento", type="datetime-local", value=RentalState.due_local,
                on_change=RentalState.capture_due, disabled=RentalState.editing_disabled,
                aria_label="Vencimento no horário de Brasília",
                class_name="vitrine-clientes__input vitrine-locacoes__datetime",
            ),
        ),
        rx.el.dl(
            _summary_row("Cliente", RentalState.customer_summary),
            _summary_row("Exemplar", RentalState.exemplar_summary),
            _summary_row("Vencimento (horário de Brasília)", RentalState.due_summary),
            class_name="vitrine-locacoes__review",
            aria_label="Resumo da locação",
        ),
        rx.cond(
            (RentalState.form_issues.length() > 0) & ~RentalState.has_rental,
            rx.box(
                rx.el.span("Para confirmar, falta:", class_name="vitrine-locacoes__issues-title"),
                rx.el.ul(rx.foreach(RentalState.form_issues, lambda issue: rx.el.li(issue)), class_name="vitrine-locacoes__issues-list"),
                class_name="vitrine-locacoes__issues",
                aria_live="polite",
            ),
        ),
        rx.cond(
            RentalState.writes_blocked,
            rx.box(
                rx.icon("lock", size=16, stroke_width=1.8, aria_hidden="true"),
                rx.el.span("O registro de locações está bloqueado neste ambiente: aguarda validação e habilitação do serviço. Você pode preencher e conferir, mas a confirmação fica indisponível."),
                class_name="vitrine-locacoes__blocked",
                role="status",
            ),
        ),
        rx.el.button(
            rx.cond(RentalState.loading, rx.spinner(size="1"), rx.icon("check", size=18, stroke_width=2, aria_hidden="true")),
            "Confirmar locação",
            type="button",
            on_click=RentalState.submit,
            disabled=~RentalState.can_create,
            class_name="vitrine-clientes__primary vitrine-locacoes__submit",
        ),
        rx.el.p("Confirmar registra a retirada (uma locação). A devolução não faz parte desta etapa; o exemplar fica ocupado até lá.", class_name="vitrine-clientes__panel-sub"),
        label="Etapa 3: vencimento e confirmação",
    )


def _admin_section(is_admin: rx.Var[bool]) -> rx.Component:
    return rx.cond(
        is_admin,
        rx.el.details(
            rx.el.summary("Ação administrativa: conferir condição do exemplar", class_name="vitrine-locacoes__admin-summary"),
            _condition_panel(),
            class_name="vitrine-locacoes__admin",
        ),
    )


def _rental_item(row) -> rx.Component:
    """Linha compacta e clicável; a aba já diz se a locação está ativa ou devolvida."""
    return rx.el.li(
        rx.el.a(
            rx.el.span(row["number"], class_name="vitrine-clientes__mono vitrine-locacoes__row-number"),
            rx.box(
                rx.el.span(row["film"], class_name="vitrine-locacoes__row-title"),
                rx.el.span(
                    row["customer"] + " · Exemplar " + row["exemplar"],
                    class_name="vitrine-locacoes__row-meta",
                ),
                rx.el.span(row["when"], class_name="vitrine-locacoes__row-meta vitrine-locacoes__row-when"),
                class_name="vitrine-locacoes__row-main",
            ),
            rx.cond(row["overdue"] != "", rx.el.span("Vencida", class_name="vitrine-locacoes__status vitrine-locacoes__status--late")),
            rx.icon("chevron-right", size=16, stroke_width=1.8, aria_hidden="true", class_name="vitrine-locacoes__row-arrow"),
            href=row["href"],
            aria_label="Abrir detalhes da locação " + row["number"] + ": " + row["film"] + ", " + row["status"],
            class_name="vitrine-locacoes__row",
        ),
        class_name="vitrine-locacoes__item",
    )


def _list_tab(tab: str, label) -> rx.Component:
    selected = RentalState.list_tab == tab
    return rx.el.button(
        label,
        type="button",
        role="tab",
        aria_selected=selected,
        on_click=RentalState.set_list_tab(tab),
        disabled=RentalState.list_state == "loading",
        class_name=rx.cond(selected, "vitrine-locacoes__tab vitrine-locacoes__tab--on", "vitrine-locacoes__tab"),
    )


def rentals_list() -> rx.Component:
    """Locações registradas, mais recentes primeiro; o detalhe continua em /locacoes/{id}."""
    return rx.el.section(
        rx.box(
            rx.box(
                rx.el.h2("Locações registradas", class_name="vitrine-clientes__panel-title"),
                rx.el.p("Mais recentes primeiro. Abra os detalhes para consultar uma locação.", class_name="vitrine-clientes__panel-sub"),
            ),
            rx.el.button(
                rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                "Atualizar lista",
                type="button",
                on_click=RentalState.load_rentals,
                disabled=RentalState.list_state == "loading",
                class_name="vitrine-clientes__secondary",
            ),
            class_name="vitrine-locacoes__list-head",
        ),
        rx.box(
            _list_tab("active", RentalState.tab_active_label),
            _list_tab("returned", RentalState.tab_returned_label),
            role="tablist",
            aria_label="Situação das locações",
            class_name="vitrine-locacoes__tabs",
        ),
        rx.cond(RentalState.list_notice != "", _notice(RentalState.list_notice, "success", "status")),
        rx.match(
            RentalState.list_state,
            (
                "loading",
                rx.box(
                    rx.spinner(),
                    rx.text("Carregando locações…"),
                    role="status",
                    aria_live="polite",
                    class_name="vitrine-dash__notice vitrine-dash__notice--loading",
                ),
            ),
            ("error", _notice(RentalState.list_message, "error", "alert")),
            (
                "empty",
                rx.box(
                    rx.el.p(
                        rx.cond(RentalState.list_tab == "active", "Nenhuma locação ativa", "Nenhuma locação devolvida"),
                        class_name="vitrine-clientes__empty-title",
                    ),
                    rx.el.p(
                        rx.cond(
                            RentalState.list_tab == "active",
                            "As locações confirmadas aparecem aqui até a devolução.",
                            "As locações aparecem aqui depois de devolvidas.",
                        ),
                        class_name="vitrine-clientes__empty-text",
                    ),
                    class_name="vitrine-clientes__placeholder",
                ),
            ),
            (
                "ready",
                rx.el.ul(
                    rx.foreach(RentalState.rental_rows, _rental_item),
                    class_name="vitrine-locacoes__items",
                    aria_label="Lista de locações",
                ),
            ),
            rx.fragment(),
        ),
        rx.cond(
            RentalState.list_paginated & (RentalState.list_state == "ready"),
            rx.box(
                rx.el.span(RentalState.list_paging, class_name="vitrine-locacoes__hint", aria_live="polite"),
                rx.box(
                    rx.el.button("Anteriores", type="button", on_click=RentalState.rentals_page(-1), disabled=~RentalState.list_previous, aria_label="Locações anteriores", class_name="vitrine-clientes__secondary"),
                    rx.el.button("Próximas", type="button", on_click=RentalState.rentals_page(1), disabled=~RentalState.list_next, aria_label="Próximas locações", class_name="vitrine-clientes__secondary"),
                    class_name="vitrine-locacoes__actions",
                ),
                class_name="vitrine-locacoes__pager",
            ),
        ),
        class_name="vitrine-clientes__panel vitrine-locacoes__list",
        aria_label="Locações registradas",
    )


def registration(is_admin: rx.Var[bool], topbar: rx.Component) -> rx.Component:
    return rx.el.main(
        topbar,
        _back_link("Voltar ao início", "/backoffice"),
        _heading("Registrar locação", "Siga as três etapas. A retirada só é registrada quando você confirmar na última.", rental_lookup()),
        _progress(),
        messages(),
        rx.cond(~RentalState.has_pending & ~RentalState.has_rental, _reload_button()),
        confirmation(),
        _pending_panel(),
        # Desktop: formulário e locações lado a lado; telas estreitas empilham.
        rx.el.div(
            rx.el.div(
                _customer_step(),
                _exemplar_step(),
                _confirm_step(),
                class_name="vitrine-locacoes__flow",
            ),
            rentals_list(),
            class_name="vitrine-locacoes__workspace",
        ),
        _admin_section(is_admin),
        class_name="vitrine-dash vitrine-locacoes",
    )


def _detail_item(label: str, icon_name: str, value) -> rx.Component:
    return rx.box(
        rx.box(rx.icon(icon_name, size=18, stroke_width=1.6, aria_hidden="true"), class_name="vitrine-clientes__data-icon"),
        rx.box(
            rx.el.span(label, class_name="vitrine-clientes__data-label"),
            rx.el.span(value, class_name="vitrine-clientes__data-value"),
        ),
        class_name="vitrine-clientes__data-item",
    )


def _return_section() -> rx.Component:
    """Devolução de locação ativa; locação devolvida mostra o registro, sem ação."""
    view = RentalState.rental_view
    return rx.cond(
        RentalState.is_active_rental,
        rx.box(
            rx.el.h3("Registrar devolução", class_name="vitrine-locacoes__review-title"),
            rx.cond(
                RentalState.writes_blocked,
                rx.box(
                    rx.icon("lock", size=16, stroke_width=1.8, aria_hidden="true"),
                    rx.el.span("O registro de devoluções está bloqueado neste ambiente: aguarda validação e habilitação do serviço."),
                    class_name="vitrine-locacoes__blocked",
                    role="status",
                ),
            ),
            rx.cond(
                RentalState.return_pending_here,
                rx.box(
                    rx.el.p("Resultado da devolução desconhecido. Confira o detalhe ou repita a mesma tentativa; uma nova devolução não será criada.", class_name="vitrine-clientes__panel-sub"),
                    rx.box(
                        rx.el.button("Repetir a mesma tentativa", type="button", on_click=RentalState.repeat_return, disabled=RentalState.loading, class_name="vitrine-clientes__primary"),
                        rx.el.button("Atualizar detalhes", type="button", on_click=RentalState.load_detail, disabled=RentalState.loading, class_name="vitrine-clientes__secondary"),
                        class_name="vitrine-locacoes__actions",
                    ),
                    class_name="vitrine-locacoes__return-box",
                    role="region",
                    aria_label="Devolução pendente de confirmação",
                ),
                rx.cond(
                    RentalState.return_confirming,
                    rx.box(
                        rx.el.p(
                            "Confirme a devolução da ", view["title"], ". O exemplar ", view["exemplar"],
                            " deixa de estar ocupado e volta a ser oferecido para locação somente se estiver apto.",
                            class_name="vitrine-clientes__panel-sub",
                        ),
                        rx.cond(
                            view["overdue"] != "",
                            rx.el.p("O vencimento já passou: a devolução ficará registrada com atraso. Nenhuma multa é calculada nesta versão.", class_name="vitrine-locacoes__late-note"),
                        ),
                        rx.box(
                            rx.el.button(
                                rx.cond(RentalState.loading, rx.spinner(size="1"), rx.icon("check", size=18, stroke_width=2, aria_hidden="true")),
                                "Confirmar devolução",
                                type="button",
                                on_click=RentalState.submit_return,
                                disabled=~RentalState.can_return,
                                class_name="vitrine-clientes__primary",
                            ),
                            rx.el.button("Cancelar", type="button", on_click=RentalState.cancel_return, disabled=RentalState.loading, class_name="vitrine-clientes__secondary"),
                            class_name="vitrine-locacoes__actions",
                        ),
                        class_name="vitrine-locacoes__return-box",
                        role="region",
                        aria_label="Confirmar devolução",
                    ),
                    rx.el.button(
                        rx.icon("undo-2", size=18, stroke_width=2, aria_hidden="true"),
                        "Registrar devolução",
                        type="button",
                        on_click=RentalState.ask_return,
                        disabled=~RentalState.can_return,
                        class_name="vitrine-clientes__primary vitrine-locacoes__submit",
                    ),
                ),
            ),
            class_name="vitrine-locacoes__return",
            aria_label="Registrar devolução",
        ),
        rx.box(
            _detail_item("Devolvida em", "calendar-check", view["returned_at"]),
            _detail_item("Recebida pelo funcionário nº", "badge-check", view["returned_by"]),
            _detail_item("Prazo", "clock", rx.cond(view["returned_late"] != "", "Devolvida com atraso", "Devolvida no prazo")),
            rx.el.p("Locação encerrada; nenhuma ação disponível.", class_name="vitrine-clientes__panel-sub"),
            class_name="vitrine-locacoes__return",
            aria_label="Devolução registrada",
        ),
    )


def detail(topbar: rx.Component) -> rx.Component:
    view = RentalState.rental_view
    return rx.el.main(
        topbar,
        _back_link("Voltar a locações", NEW_RENTAL_HREF),
        rx.cond(
            RentalState.has_rental,
            rx.el.section(
                rx.box(
                    rx.el.span("LOCAÇÃO", class_name="vitrine-clientes__eyebrow"),
                    rx.el.h1(view["title"], class_name="vitrine-dash__title"),
                    rx.box(
                        rx.el.span(
                            view["status"],
                            class_name=rx.cond(
                                RentalState.is_active_rental,
                                "vitrine-locacoes__status",
                                "vitrine-locacoes__status vitrine-locacoes__status--done",
                            ),
                        ),
                        rx.cond(
                            view["overdue"] != "",
                            rx.el.span("Vencimento ultrapassado", class_name="vitrine-locacoes__status vitrine-locacoes__status--late"),
                        ),
                        class_name="vitrine-locacoes__badges",
                    ),
                    class_name="vitrine-dash__heading-text",
                ),
                rental_lookup(),
                class_name="vitrine-dash__heading",
            ),
            _heading("Consultar locação", "Detalhes de uma locação registrada.", rental_lookup()),
        ),
        messages(),
        rx.cond(
            RentalState.detail_state == "error",
            rx.el.button(
                rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                "Tentar novamente",
                type="button",
                on_click=RentalState.load_detail,
                disabled=RentalState.loading,
                class_name="vitrine-clientes__secondary vitrine-locacoes__refresh",
            ),
        ),
        rx.cond(
            RentalState.has_rental,
            rx.fragment(
                rx.box(
                    rx.el.section(
                        rx.el.h2("Dados da locação", class_name="vitrine-clientes__panel-title"),
                        rx.box(
                            _detail_item("Cliente", "user", view["customer"]),
                            _detail_item("Exemplar", "disc", view["exemplar"]),
                            _detail_item("Filme", "film", view["film"]),
                            _detail_item("Retirada", "calendar", view["rented_at"]),
                            _detail_item("Vencimento (horário de Brasília)", "calendar-clock", view["due_at"]),
                            _detail_item("Registrada por (funcionário nº)", "badge-check", view["registered_by"]),
                            class_name="vitrine-clientes__data-grid",
                        ),
                        class_name="vitrine-clientes__panel",
                        aria_label="Dados da locação",
                    ),
                    rx.el.section(
                        rx.el.h2("Situação", class_name="vitrine-clientes__panel-title"),
                        _detail_item("Situação", "circle-check", view["status"]),
                        rx.cond(
                            view["overdue"] != "",
                            rx.el.p("O vencimento já passou e a devolução ainda não foi registrada.", class_name="vitrine-clientes__panel-sub"),
                        ),
                        _return_section(),
                        rx.el.a(
                            rx.icon("user", size=16, stroke_width=1.8, aria_hidden="true"),
                            "Ver cadastro do cliente",
                            href=view["customer_href"],
                            class_name="vitrine-clientes__secondary",
                        ),
                        class_name="vitrine-clientes__panel",
                        aria_label="Situação da locação",
                    ),
                    class_name="vitrine-clientes__detail-grid",
                ),
                rx.el.button(
                    rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                    "Atualizar detalhes",
                    type="button",
                    on_click=RentalState.load_detail,
                    disabled=RentalState.loading,
                    class_name="vitrine-clientes__secondary vitrine-locacoes__refresh",
                ),
            ),
        ),
        class_name="vitrine-dash vitrine-locacoes",
    )
