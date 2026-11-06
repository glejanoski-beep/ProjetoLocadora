"""Páginas de multas e pagamentos e histórico financeiro do cliente."""

import reflex as rx

from ProjetoLocadora.multas_state import ClienteHistoricoState as History
from ProjetoLocadora.multas_state import MultasState as Fines

FINES_HREF = "/multas"


def _notice(content, kind: str, role: str) -> rx.Component:
    return rx.box(content, role=role, class_name=f"vitrine-dash__notice vitrine-dash__notice--{kind}")


def _loading(text: str) -> rx.Component:
    return rx.box(rx.spinner(), rx.text(text), role="status", aria_live="polite", class_name="vitrine-dash__notice vitrine-dash__notice--loading")


def _messages() -> rx.Component:
    return rx.fragment(
        rx.cond(Fines.message != "", _notice(Fines.message, "error", "alert")),
        rx.cond(Fines.notice != "", _notice(Fines.notice, "success", "status")),
    )


def _status_chip(label, key) -> rx.Component:
    return rx.el.span(label, class_name="vitrine-multas__chip vitrine-multas__chip--" + key)


def _heading(title, subtitle) -> rx.Component:
    return rx.el.section(
        rx.box(
            rx.el.h1(title, class_name="vitrine-dash__title"),
            rx.el.p(subtitle, class_name="vitrine-dash__subtitle"),
            class_name="vitrine-dash__heading-text",
        ),
        class_name="vitrine-dash__heading",
    )


def _fine_item(row) -> rx.Component:
    return rx.el.li(
        rx.el.a(
            rx.el.span(row["number"], class_name="vitrine-clientes__mono vitrine-locacoes__row-number"),
            rx.box(
                rx.el.span(row["customer"], class_name="vitrine-locacoes__row-title"),
                rx.el.span(row["film"] + " · Exemplar " + row["exemplar"], class_name="vitrine-locacoes__row-meta"),
                rx.el.span("Devolvida em " + row["returned_at"] + " · " + row["days"] + " de atraso", class_name="vitrine-locacoes__row-meta vitrine-locacoes__row-when"),
                class_name="vitrine-locacoes__row-main",
            ),
            rx.box(
                rx.el.span(row["balance"], class_name="vitrine-multas__money"),
                rx.el.span("de " + row["amount"], class_name="vitrine-locacoes__row-meta"),
                _status_chip(row["status"], row["status_key"]),
                class_name="vitrine-multas__row-side",
            ),
            rx.icon("chevron-right", size=16, stroke_width=1.8, aria_hidden="true", class_name="vitrine-locacoes__row-arrow"),
            href=row["href"],
            aria_label="Abrir multa " + row["number"] + " de " + row["customer"] + ": saldo " + row["balance"] + ", " + row["status"],
            class_name="vitrine-locacoes__row",
        ),
        class_name="vitrine-locacoes__item",
    )


def _tab(tab) -> rx.Component:
    selected = Fines.tab == tab["key"]
    return rx.el.button(
        tab["label"],
        type="button",
        role="tab",
        aria_selected=selected,
        on_click=Fines.set_tab(tab["key"]),
        disabled=Fines.list_state == "loading",
        class_name=rx.cond(selected, "vitrine-locacoes__tab vitrine-locacoes__tab--on", "vitrine-locacoes__tab"),
    )


def fines_page(topbar: rx.Component) -> rx.Component:
    return rx.el.main(
        topbar,
        _heading("Multas", "Multas por atraso geradas na devolução. Abra uma multa para registrar pagamentos."),
        _messages(),
        rx.el.section(
            rx.box(
                rx.box(
                    rx.el.h2("Multas registradas", class_name="vitrine-clientes__panel-title"),
                    rx.el.p("R$ 3,00 por dia de atraso após 2 h de tolerância, até 30 diárias. Mais recentes primeiro.", class_name="vitrine-clientes__panel-sub"),
                ),
                rx.el.button(
                    rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                    "Atualizar lista",
                    type="button",
                    on_click=Fines.load_list,
                    disabled=Fines.list_state == "loading",
                    class_name="vitrine-clientes__secondary",
                ),
                class_name="vitrine-locacoes__list-head",
            ),
            rx.box(rx.foreach(Fines.tabs, _tab), role="tablist", aria_label="Situação das multas", class_name="vitrine-locacoes__tabs"),
            rx.match(
                Fines.list_state,
                ("loading", _loading("Carregando multas…")),
                ("error", rx.el.button("Tentar novamente", type="button", on_click=Fines.load_list, class_name="vitrine-clientes__secondary")),
                ("empty", rx.box(rx.el.p(Fines.empty_text, class_name="vitrine-clientes__empty-title"), class_name="vitrine-clientes__placeholder")),
                ("ready", rx.el.ul(rx.foreach(Fines.rows, _fine_item), class_name="vitrine-locacoes__items", aria_label="Lista de multas")),
                rx.fragment(),
            ),
            rx.cond(
                (Fines.list_state == "ready") & (Fines.has_previous | Fines.has_next),
                rx.box(
                    rx.el.span(Fines.paging, class_name="vitrine-locacoes__hint", aria_live="polite"),
                    rx.box(
                        rx.el.button("Anteriores", type="button", on_click=Fines.change_page(-1), disabled=~Fines.has_previous, class_name="vitrine-clientes__secondary"),
                        rx.el.button("Próximas", type="button", on_click=Fines.change_page(1), disabled=~Fines.has_next, class_name="vitrine-clientes__secondary"),
                        class_name="vitrine-locacoes__actions",
                    ),
                    class_name="vitrine-locacoes__pager",
                ),
            ),
            class_name="vitrine-clientes__panel vitrine-locacoes__list",
            aria_label="Multas registradas",
        ),
        class_name="vitrine-dash vitrine-locacoes vitrine-multas",
    )


def _item(label: str, icon_name: str, value) -> rx.Component:
    return rx.box(
        rx.box(rx.icon(icon_name, size=18, stroke_width=1.6, aria_hidden="true"), class_name="vitrine-clientes__data-icon"),
        rx.box(
            rx.el.span(label, class_name="vitrine-clientes__data-label"),
            rx.el.span(value, class_name="vitrine-clientes__data-value"),
        ),
        class_name="vitrine-clientes__data-item",
    )


def _payment_item(row, is_admin) -> rx.Component:
    return rx.el.li(
        rx.box(
            rx.box(
                rx.el.span(row["amount"], class_name="vitrine-multas__money"),
                rx.el.span(row["method"] + " · " + row["paid_at"] + " · funcionário nº " + row["registered_by"], class_name="vitrine-locacoes__row-meta"),
                rx.cond(row["reversal"] != "", rx.el.span(row["reversal"], class_name="vitrine-locacoes__row-meta")),
                class_name="vitrine-locacoes__row-main",
            ),
            _status_chip(row["status"], rx.cond(row["reversed"] != "", "reversed", "paid")),
            rx.cond(
                is_admin & (row["reversed"] == "") & Fines.can_reverse & ~Fines.admin_pending,
                rx.el.button(
                    "Estornar", type="button", on_click=Fines.ask_reverse(row["id"]),
                    disabled=Fines.loading, aria_label="Estornar pagamento nº " + row["id"],
                    class_name="vitrine-clientes__secondary",
                ),
            ),
            class_name="vitrine-multas__payment",
        ),
        class_name="vitrine-locacoes__item",
    )


def _pay_section() -> rx.Component:
    return rx.cond(
        Fines.is_open,
        rx.box(
            rx.el.h3("Registrar pagamento", class_name="vitrine-locacoes__review-title"),
            rx.cond(
                Fines.writes_blocked,
                rx.box(
                    rx.icon("lock", size=16, stroke_width=1.8, aria_hidden="true"),
                    rx.el.span("O registro de pagamentos está bloqueado neste ambiente: aguarda habilitação do serviço."),
                    class_name="vitrine-locacoes__blocked", role="status",
                ),
            ),
            rx.cond(
                Fines.pay_pending,
                rx.box(
                    rx.el.p("Resultado do pagamento desconhecido. Confira os pagamentos ou repita a mesma tentativa; um segundo pagamento não será criado.", class_name="vitrine-clientes__panel-sub"),
                    rx.box(
                        rx.el.button("Repetir a mesma tentativa", type="button", on_click=Fines.repeat_pay, disabled=Fines.loading, class_name="vitrine-clientes__primary"),
                        rx.el.button("Atualizar detalhes", type="button", on_click=Fines.load_detail, disabled=Fines.loading, class_name="vitrine-clientes__secondary"),
                        class_name="vitrine-locacoes__actions",
                    ),
                    class_name="vitrine-locacoes__return-box", role="region", aria_label="Pagamento pendente de confirmação",
                ),
                rx.cond(
                    Fines.pay_confirming,
                    rx.box(
                        rx.el.p(Fines.pay_summary, class_name="vitrine-clientes__panel-sub"),
                        rx.box(
                            rx.el.button(
                                rx.cond(Fines.loading, rx.spinner(size="1"), rx.icon("check", size=18, stroke_width=2, aria_hidden="true")),
                                "Confirmar pagamento", type="button", on_click=Fines.submit_pay,
                                disabled=~Fines.can_pay, class_name="vitrine-clientes__primary",
                            ),
                            rx.el.button("Cancelar", type="button", on_click=Fines.cancel_pay, disabled=Fines.loading, class_name="vitrine-clientes__secondary"),
                            class_name="vitrine-locacoes__actions",
                        ),
                        class_name="vitrine-locacoes__return-box", role="region", aria_label="Confirmar pagamento",
                    ),
                    rx.box(
                        rx.box(
                            rx.el.label("Valor (R$)", html_for="multa-valor", class_name="vitrine-clientes__data-label"),
                            rx.el.input(
                                id="multa-valor", value=Fines.amount_text, on_change=Fines.capture_amount,
                                input_mode="decimal", placeholder="0,00", aria_describedby="multa-valor-erro",
                                class_name="vitrine-locacoes__select vitrine-multas__amount",
                            ),
                            rx.el.span(Fines.amount_issue, id="multa-valor-erro", role="alert", class_name="vitrine-locacoes__hint"),
                            class_name="vitrine-multas__field",
                        ),
                        rx.box(
                            rx.el.label("Meio de pagamento", html_for="multa-meio", class_name="vitrine-clientes__data-label"),
                            rx.el.select(
                                rx.foreach(Fines.method_options, lambda label: rx.el.option(label, value=label)),
                                id="multa-meio", value=Fines.method_label, on_change=Fines.capture_method,
                                class_name="vitrine-locacoes__select",
                            ),
                            class_name="vitrine-multas__field",
                        ),
                        rx.el.button(
                            rx.icon("wallet", size=18, stroke_width=2, aria_hidden="true"),
                            "Registrar pagamento", type="button", on_click=Fines.ask_pay,
                            disabled=~Fines.can_pay, class_name="vitrine-clientes__primary vitrine-locacoes__submit",
                        ),
                        class_name="vitrine-multas__form",
                    ),
                ),
            ),
            rx.el.p("Somente registro: o sistema não processa cobrança em cartão ou Pix.", class_name="vitrine-locacoes__hint"),
            class_name="vitrine-locacoes__return",
            aria_label="Registrar pagamento",
        ),
    )


def _admin_section(is_admin) -> rx.Component:
    return rx.cond(
        is_admin & (Fines.admin_action != ""),
        rx.box(
            rx.el.h3(Fines.admin_title, class_name="vitrine-locacoes__review-title"),
            rx.el.p("A operação fica registrada em seu nome, com o motivo informado. Nenhum registro é apagado.", class_name="vitrine-clientes__panel-sub"),
            rx.el.textarea(
                value=Fines.admin_reason, on_change=Fines.capture_admin_reason,
                placeholder="Obrigatório. Informe o motivo (até 500 caracteres).", max_length=500,
                disabled=Fines.admin_pending, aria_label="Motivo", class_name="vitrine-clientes__textarea",
            ),
            rx.cond(
                Fines.admin_pending,
                rx.box(
                    rx.el.button("Repetir a mesma tentativa", type="button", on_click=Fines.repeat_admin, disabled=Fines.loading, class_name="vitrine-clientes__primary"),
                    rx.el.button("Atualizar detalhes", type="button", on_click=Fines.load_detail, disabled=Fines.loading, class_name="vitrine-clientes__secondary"),
                    class_name="vitrine-locacoes__actions",
                ),
                rx.box(
                    rx.el.button("Confirmar", type="button", on_click=Fines.confirm_admin, disabled=~Fines.can_confirm_admin, class_name="vitrine-clientes__primary"),
                    rx.el.button("Cancelar", type="button", on_click=Fines.cancel_admin, disabled=Fines.loading, class_name="vitrine-clientes__secondary"),
                    class_name="vitrine-locacoes__actions",
                ),
            ),
            class_name="vitrine-locacoes__return-box", role="region", aria_label="Ajuste administrativo",
        ),
    )


def fine_detail(is_admin, topbar: rx.Component) -> rx.Component:
    view = Fines.fine_view
    return rx.el.main(
        topbar,
        rx.el.a(rx.icon("arrow-left", size=16, aria_hidden="true"), "Voltar a multas", href=FINES_HREF, class_name="vitrine-clientes__back"),
        rx.cond(
            Fines.has_fine,
            rx.el.section(
                rx.box(
                    rx.el.span("MULTA POR ATRASO", class_name="vitrine-clientes__eyebrow"),
                    rx.el.h1(view["title"], class_name="vitrine-dash__title"),
                    rx.box(_status_chip(view["status"], view["status_key"]), class_name="vitrine-locacoes__badges"),
                    class_name="vitrine-dash__heading-text",
                ),
                class_name="vitrine-dash__heading",
            ),
            _heading("Consultar multa", "Detalhes de uma multa registrada."),
        ),
        _messages(),
        rx.cond(Fines.loading & ~Fines.has_fine, _loading("Carregando multa…")),
        rx.cond(
            Fines.detail_state == "error",
            rx.el.button("Tentar novamente", type="button", on_click=Fines.load_detail, disabled=Fines.loading, class_name="vitrine-clientes__secondary vitrine-locacoes__refresh"),
        ),
        rx.cond(
            Fines.has_fine,
            rx.fragment(
                rx.box(
                    rx.el.section(
                        rx.el.h2("Origem", class_name="vitrine-clientes__panel-title"),
                        rx.box(
                            _item("Cliente", "user", rx.el.a(view["customer"], href=view["customer_href"], class_name="vitrine-multas__link")),
                            _item("Locação", "receipt", rx.el.a(view["rental"], href=view["rental_href"], class_name="vitrine-multas__link")),
                            _item("Filme · exemplar", "film", view["film"] + " · " + view["exemplar"]),
                            _item("Vencimento", "calendar-clock", view["due_at"]),
                            _item("Devolução", "calendar-check", view["returned_at"]),
                            _item("Cálculo", "calculator", view["policy"]),
                            class_name="vitrine-clientes__data-grid",
                        ),
                        class_name="vitrine-clientes__panel", aria_label="Origem da multa",
                    ),
                    rx.el.section(
                        rx.el.h2("Valores", class_name="vitrine-clientes__panel-title"),
                        rx.box(
                            _item("Valor da multa", "wallet", view["amount"]),
                            _item("Pago", "circle-check", view["paid"]),
                            _item("Abonado", "badge-check", view["waived"]),
                            _item("Saldo", "scale", rx.el.strong(view["balance"])),
                            class_name="vitrine-clientes__data-grid",
                        ),
                        rx.cond(view["waive_note"] != "", rx.el.p(view["waive_note"], class_name="vitrine-clientes__panel-sub")),
                        _pay_section(),
                        rx.cond(
                            is_admin & Fines.is_open & (Fines.admin_action == "") & ~Fines.admin_pending,
                            rx.el.button(
                                rx.icon("badge-percent", size=16, stroke_width=1.8, aria_hidden="true"),
                                "Abonar saldo", type="button", on_click=Fines.ask_waive, disabled=Fines.loading,
                                class_name="vitrine-clientes__secondary",
                            ),
                        ),
                        _admin_section(is_admin),
                        class_name="vitrine-clientes__panel", aria_label="Valores e pagamento",
                    ),
                    class_name="vitrine-clientes__detail-grid",
                ),
                rx.el.section(
                    rx.el.h2("Pagamentos", class_name="vitrine-clientes__panel-title"),
                    rx.cond(
                        Fines.payment_rows.length() > 0,
                        rx.el.ul(rx.foreach(Fines.payment_rows, lambda row: _payment_item(row, is_admin)), class_name="vitrine-locacoes__items", aria_label="Pagamentos da multa"),
                        rx.el.p("Nenhum pagamento registrado.", class_name="vitrine-clientes__panel-sub"),
                    ),
                    class_name="vitrine-clientes__panel", aria_label="Pagamentos",
                ),
                rx.el.button(
                    rx.icon("refresh-cw", size=16, stroke_width=1.8, aria_hidden="true"),
                    "Atualizar detalhes", type="button", on_click=Fines.load_detail, disabled=Fines.loading,
                    class_name="vitrine-clientes__secondary vitrine-locacoes__refresh",
                ),
            ),
        ),
        class_name="vitrine-dash vitrine-locacoes vitrine-multas",
    )


# ---------- Histórico do cliente ----------

def _history_tab(key: str, label: str) -> rx.Component:
    selected = History.tab == key
    return rx.el.button(
        label, type="button", role="tab", aria_selected=selected,
        on_click=History.set_tab(key), disabled=History.loading,
        class_name=rx.cond(selected, "vitrine-locacoes__tab vitrine-locacoes__tab--on", "vitrine-locacoes__tab"),
    )


def _history_row(row) -> rx.Component:
    return rx.match(
        History.tab,
        ("fines", _fine_item(row)),
        (
            "payments",
            rx.el.li(
                rx.el.a(
                    rx.box(
                        rx.el.span(row["amount"], class_name="vitrine-multas__money"),
                        rx.el.span(row["method"] + " · " + row["paid_at"] + " · multa " + row["fine_number"], class_name="vitrine-locacoes__row-meta"),
                        class_name="vitrine-locacoes__row-main",
                    ),
                    _status_chip(row["status"], rx.cond(row["reversed"] != "", "reversed", "paid")),
                    href=row["fine_href"],
                    class_name="vitrine-locacoes__row",
                ),
                class_name="vitrine-locacoes__item",
            ),
        ),
        rx.el.li(
            rx.el.a(
                rx.el.span(row["number"], class_name="vitrine-clientes__mono vitrine-locacoes__row-number"),
                rx.box(
                    rx.el.span(row["film"], class_name="vitrine-locacoes__row-title"),
                    rx.el.span("Exemplar " + row["exemplar"] + " · retirada " + row["rented_at"] + " · vence " + row["due_at"], class_name="vitrine-locacoes__row-meta"),
                    class_name="vitrine-locacoes__row-main",
                ),
                rx.el.span(row["status"], class_name="vitrine-locacoes__row-meta"),
                href=row["href"],
                class_name="vitrine-locacoes__row",
            ),
            class_name="vitrine-locacoes__item",
        ),
    )


def customer_history_panel() -> rx.Component:
    """Histórico real: locações, multas e pagamentos do cliente exibido."""
    return rx.el.section(
        rx.box(
            rx.el.h2("Histórico e pendências", class_name="vitrine-clientes__panel-title"),
            rx.box(
                rx.el.span("Saldo em aberto", class_name="vitrine-clientes__data-label"),
                rx.el.strong(
                    rx.match(History.balance_state, ("ready", History.balance_text), ("loading", "…"), "—"),
                    class_name="vitrine-multas__money",
                ),
                class_name="vitrine-multas__balance",
            ),
            class_name="vitrine-clientes__panel-head",
        ),
        rx.cond(
            History.has_open_fine,
            rx.box(
                rx.icon("lock", size=16, stroke_width=1.8, aria_hidden="true"),
                rx.el.span("Novas locações bloqueadas até a quitação ou o abono das multas em aberto."),
                class_name="vitrine-locacoes__blocked", role="status",
            ),
        ),
        rx.box(
            _history_tab("rentals", "Locações"),
            _history_tab("fines", "Multas"),
            _history_tab("payments", "Pagamentos"),
            role="tablist", aria_label="Histórico do cliente", class_name="vitrine-locacoes__tabs",
        ),
        rx.match(
            History.state,
            ("loading", _loading("Carregando histórico…")),
            (
                "error",
                rx.box(
                    _notice(History.message, "error", "alert"),
                    rx.el.button("Tentar novamente", type="button", on_click=History.retry, class_name="vitrine-clientes__secondary"),
                ),
            ),
            ("empty", rx.el.p(History.empty_text, class_name="vitrine-clientes__panel-sub")),
            ("ready", rx.el.ul(rx.foreach(History.rows, _history_row), class_name="vitrine-locacoes__items")),
            rx.fragment(),
        ),
        rx.cond(
            (History.state == "ready") & (History.has_previous | History.has_next),
            rx.box(
                rx.el.span(History.paging, class_name="vitrine-locacoes__hint", aria_live="polite"),
                rx.box(
                    rx.el.button("Anteriores", type="button", on_click=History.change_page(-1), disabled=~History.has_previous, class_name="vitrine-clientes__secondary"),
                    rx.el.button("Próximos", type="button", on_click=History.change_page(1), disabled=~History.has_next, class_name="vitrine-clientes__secondary"),
                    class_name="vitrine-locacoes__actions",
                ),
                class_name="vitrine-locacoes__pager",
            ),
        ),
        class_name="vitrine-clientes__panel",
        aria_label="Histórico e pendências",
    )
