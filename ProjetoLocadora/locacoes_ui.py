"""Páginas operacionais de locação com os componentes Reflex existentes."""

import reflex as rx

from ProjetoLocadora.locacoes_state import LocacoesState as RentalState


def messages() -> rx.Component:
    return rx.vstack(
        rx.cond(RentalState.message != "", rx.callout(RentalState.message, color_scheme="red", role="alert")),
        rx.cond(RentalState.notice != "", rx.callout(RentalState.notice, color_scheme="blue", role="status")),
        rx.cond(RentalState.loading, rx.text("Consultando o serviço…", role="status")),
        width="100%",
    )


def confirmation() -> rx.Component:
    return rx.cond(
        RentalState.confirmation != "",
        rx.card(
            rx.vstack(
                rx.heading("Registro da locação", size="5"),
                rx.text(RentalState.confirmation),
                rx.link("Abrir confirmação", href=RentalState.confirmation_link),
                rx.link("Registrar outra locação", href="/locacoes/nova"),
                align="start",
            ), width="100%",
        ),
    )


def registration(is_admin: rx.Var[bool]) -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Registrar locação", size="7"),
            rx.link("Voltar ao início", href="/backoffice"),
            rx.text("Selecione um cliente e um exemplar. A retirada será registrada no momento da confirmação."),
            rx.text("A devolução será implementada em uma próxima etapa; o exemplar ficará ocupado até lá.", color="gray"),
            messages(),
            confirmation(),
            rx.cond(
                RentalState.has_pending,
                rx.card(
                    rx.vstack(
                        rx.text("Existe uma tentativa pendente de confirmação."),
                        rx.button("Consultar tentativa", on_click=RentalState.reconcile, disabled=RentalState.loading),
                        rx.button("Repetir a mesma tentativa", on_click=RentalState.repeat_pending, disabled=RentalState.loading | ~RentalState.writes_available, variant="outline"),
                        align="start",
                    ), width="100%",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Cliente", size="5"),
                    rx.input(placeholder="Buscar por nome", value=RentalState.customer_search, on_change=RentalState.capture_customer_search, disabled=RentalState.editing_disabled, aria_label="Buscar cliente para locação"),
                    rx.button("Buscar e atualizar opções", on_click=RentalState.search_customers, disabled=RentalState.editing_disabled),
                    rx.select(RentalState.customer_options, value=RentalState.customer_choice, on_change=RentalState.capture_customer, placeholder="Selecione o cliente", disabled=RentalState.editing_disabled, aria_label="Cliente da locação", width="100%"),
                    rx.text(RentalState.customer_paging, size="2"),
                    rx.text("Clientes inativos ou bloqueados não podem iniciar uma locação.", size="2", color="gray"),
                    rx.hstack(
                        rx.button("Clientes anteriores", on_click=RentalState.customer_page(-1), disabled=~RentalState.customer_previous | RentalState.editing_disabled, variant="outline"),
                        rx.button("Próximos clientes", on_click=RentalState.customer_page(1), disabled=~RentalState.customer_next | RentalState.editing_disabled, variant="outline"),
                        wrap="wrap",
                    ),
                    rx.heading("Exemplar disponível", size="5"),
                    rx.select(RentalState.exemplar_options, value=RentalState.exemplar_choice, on_change=RentalState.capture_exemplar, placeholder="Selecione o exemplar", disabled=RentalState.editing_disabled, aria_label="Exemplar da locação", width="100%"),
                    rx.text(RentalState.exemplar_paging, size="2"),
                    rx.hstack(
                        rx.button("Exemplares anteriores", on_click=RentalState.exemplar_page(-1), disabled=~RentalState.exemplar_previous | RentalState.editing_disabled, variant="outline"),
                        rx.button("Próximos exemplares", on_click=RentalState.exemplar_page(1), disabled=~RentalState.exemplar_next | RentalState.editing_disabled, variant="outline"),
                        wrap="wrap",
                    ),
                    rx.text("Somente exemplares conferidos por um administrador e sem locação ativa podem ser escolhidos.", color="gray", size="2"),
                    rx.text("Vencimento — data e hora de Brasília", weight="medium"),
                    rx.input(type="datetime-local", value=RentalState.due_local, on_change=RentalState.capture_due, disabled=RentalState.editing_disabled, aria_label="Vencimento no horário de Brasília"),
                    rx.text("Confira antes de confirmar:"),
                    rx.text(RentalState.customer_choice),
                    rx.text(RentalState.exemplar_choice),
                    rx.text(RentalState.due_local, " (horário de Brasília)"),
                    rx.button("Confirmar locação", on_click=RentalState.submit, disabled=~RentalState.can_create, loading=RentalState.loading),
                    align="start", spacing="4", width="100%",
                ), width="100%",
            ),
            rx.cond(
                is_admin,
                rx.card(
                    rx.vstack(
                        rx.heading("Conferir condição do exemplar", size="5"),
                        rx.text("Registre a condição após conferir o exemplar. Isso não libera exemplares com locação ativa."),
                        rx.select(RentalState.admin_exemplar_options, value=RentalState.condition_exemplar, on_change=RentalState.capture_condition_exemplar, placeholder="Selecione o exemplar conferido", disabled=RentalState.editing_disabled, aria_label="Exemplar para conferência", width="100%"),
                        rx.select(["Não conferido", "Apto para locação", "Indisponível"], value=RentalState.condition_label, on_change=RentalState.capture_condition, disabled=RentalState.editing_disabled, aria_label="Condição operacional"),
                        rx.input(value=RentalState.condition_reason, on_change=RentalState.capture_reason, placeholder="Motivo da confirmação", max_length=500, disabled=RentalState.editing_disabled, aria_label="Motivo da condição operacional", width="100%"),
                        rx.button("Confirmar condição", on_click=RentalState.save_condition, disabled=~RentalState.writes_available | RentalState.editing_disabled),
                        align="start", spacing="3", width="100%",
                    ), width="100%",
                ),
            ),
            spacing="5", align="start", padding_y="2em", width="100%",
        ), size="3",
    )


def detail() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Confirmação de locação", size="7"),
            rx.link("Voltar ao início", href="/backoffice"),
            messages(),
            confirmation(),
            rx.button("Atualizar confirmação", on_click=RentalState.load_detail, disabled=RentalState.loading),
            spacing="5", align="start", padding_y="2em",
        ), size="3",
    )
