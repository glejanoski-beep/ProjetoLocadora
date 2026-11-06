"""Página de relatórios consolidados (somente administradores)."""

import reflex as rx

from ProjetoLocadora.relatorios_state import RelatoriosState as Reports


def _notice(content, kind: str, role: str) -> rx.Component:
    return rx.box(content, role=role, class_name=f"vitrine-dash__notice vitrine-dash__notice--{kind}")


def _shortcut(item) -> rx.Component:
    selected = Reports.shortcut == item["key"]
    return rx.el.button(
        item["label"], type="button", role="tab", aria_selected=selected,
        on_click=Reports.set_shortcut(item["key"]), disabled=Reports.loading,
        class_name=rx.cond(selected, "vitrine-locacoes__tab vitrine-locacoes__tab--on", "vitrine-locacoes__tab"),
    )


def _filter() -> rx.Component:
    return rx.el.section(
        rx.box(rx.foreach(Reports.shortcuts, _shortcut), role="tablist", aria_label="Período", class_name="vitrine-locacoes__tabs"),
        rx.box(
            rx.box(
                rx.el.label("Início", html_for="relatorio-inicio", class_name="vitrine-clientes__data-label"),
                rx.el.input(id="relatorio-inicio", type="date", value=Reports.start_text, on_change=Reports.capture_start, class_name="vitrine-locacoes__datetime"),
                class_name="vitrine-relatorios__field",
            ),
            rx.box(
                rx.el.label("Fim", html_for="relatorio-fim", class_name="vitrine-clientes__data-label"),
                rx.el.input(id="relatorio-fim", type="date", value=Reports.end_text, on_change=Reports.capture_end, class_name="vitrine-locacoes__datetime"),
                class_name="vitrine-relatorios__field",
            ),
            rx.el.button(
                rx.cond(Reports.loading, rx.spinner(size="1"), rx.icon("chart-column", size=16, stroke_width=1.8, aria_hidden="true")),
                "Gerar relatório", type="button", on_click=Reports.generate, disabled=Reports.loading,
                class_name="vitrine-clientes__primary",
            ),
            class_name="vitrine-relatorios__dates",
        ),
        class_name="vitrine-clientes__panel vitrine-relatorios__filter",
        aria_label="Filtro de período",
    )


def _card(item) -> rx.Component:
    return rx.box(
        rx.el.span(item["label"], class_name="vitrine-dash__card-label"),
        rx.el.p(item["value"], class_name="vitrine-dash__value"),
        rx.el.p(item["note"], class_name="vitrine-dash__card-note"),
        class_name="vitrine-dash__card",
    )


def _group(title: str, subtitle, cards, extra=None) -> rx.Component:
    return rx.el.section(
        rx.el.h2(title, class_name="vitrine-clientes__panel-title"),
        rx.el.p(subtitle, class_name="vitrine-clientes__panel-sub"),
        rx.box(rx.foreach(cards, _card), class_name="vitrine-relatorios__cards"),
        extra if extra is not None else rx.fragment(),
        class_name="vitrine-clientes__panel",
        aria_label=title,
    )


def _method_row(row) -> rx.Component:
    return rx.el.li(rx.el.span(row["label"]), rx.el.span(row["value"], class_name="vitrine-multas__money"), class_name="vitrine-relatorios__method")


def _film_row(row) -> rx.Component:
    return rx.el.li(
        rx.el.span(row["position"], class_name="vitrine-clientes__mono vitrine-relatorios__position"),
        rx.box(
            rx.el.span(row["title"], class_name="vitrine-locacoes__row-title"),
            rx.box(rx.box(class_name="vitrine-relatorios__bar-fill", style={"width": row["width"]}), class_name="vitrine-relatorios__bar", aria_hidden="true"),
            rx.el.span(row["detail"], class_name="vitrine-locacoes__row-meta"),
            class_name="vitrine-relatorios__film-main",
        ),
        class_name="vitrine-relatorios__film",
    )


def _report() -> rx.Component:
    return rx.fragment(
        rx.box(
            _group(
                "Locações no período",
                "Atraso conta a devolução depois do vencimento; a multa só é gerada após a tolerância de 2 horas.",
                Reports.rental_cards,
            ),
            _group(
                "Situação atual",
                "Independente do período escolhido.",
                Reports.current_cards,
            ),
            class_name="vitrine-relatorios__columns",
        ),
        _group(
            "Financeiro no período",
            "Pagamentos recebidos excluem os que foram estornados depois; estornos contam na data do estorno.",
            Reports.finance_cards,
            rx.box(
                rx.el.h3("Recebido por meio de pagamento", class_name="vitrine-locacoes__review-title"),
                rx.el.ul(rx.foreach(Reports.method_rows, _method_row), class_name="vitrine-relatorios__methods"),
            ),
        ),
        rx.el.section(
            rx.el.h2("Filmes mais alugados", class_name="vitrine-clientes__panel-title"),
            rx.el.p("Retiradas no período por filme, somando todas as cópias.", class_name="vitrine-clientes__panel-sub"),
            rx.cond(
                Reports.film_rows.length() > 0,
                rx.el.ol(rx.foreach(Reports.film_rows, _film_row), class_name="vitrine-relatorios__films", aria_label="Filmes mais alugados"),
                rx.el.p("Nenhuma locação no período.", class_name="vitrine-clientes__empty-title"),
            ),
            class_name="vitrine-clientes__panel",
            aria_label="Filmes mais alugados",
        ),
    )


def reports_page(topbar: rx.Component) -> rx.Component:
    return rx.el.main(
        topbar,
        rx.el.section(
            rx.box(
                rx.el.h1("Relatórios", class_name="vitrine-dash__title"),
                rx.el.p(
                    rx.cond(Reports.period_label != "", Reports.period_label, "Locações, financeiro e filmes mais alugados por período."),
                    class_name="vitrine-dash__subtitle",
                ),
                class_name="vitrine-dash__heading-text",
            ),
            rx.el.span(Reports.generated_label, class_name="vitrine-dash__email"),
            class_name="vitrine-dash__heading",
        ),
        rx.cond(
            Reports.state == "forbidden",
            _notice("Relatórios disponíveis apenas para administradores.", "muted", "status"),
            rx.fragment(
                _filter(),
                rx.cond(Reports.message != "", _notice(Reports.message, "error", "alert")),
                rx.cond(
                    Reports.state == "loading",
                    rx.box(rx.spinner(), rx.text("Gerando relatório…"), role="status", aria_live="polite", class_name="vitrine-dash__notice vitrine-dash__notice--loading"),
                ),
                rx.cond(
                    Reports.state == "error",
                    rx.el.button("Tentar novamente", type="button", on_click=Reports.generate, disabled=Reports.loading, class_name="vitrine-clientes__secondary"),
                ),
                rx.cond(Reports.has_report & (Reports.state == "ready"), _report()),
            ),
        ),
        class_name="vitrine-dash vitrine-locacoes vitrine-relatorios",
    )
