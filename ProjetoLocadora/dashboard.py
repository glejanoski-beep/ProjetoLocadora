"""Componentes Reflex do resumo cadastrado; sem consultas ou dados simulados."""

from datetime import datetime
from zoneinfo import ZoneInfo

import reflex as rx

from ProjetoLocadora.dashboard_state import DashboardState


def format_generated_at(generated_at: str) -> str:
    """Formata o UTC validado para apresentação, sem modificar o original."""
    if not generated_at:
        return ""
    if not generated_at.endswith("Z"):
        return "Horário indisponível"
    try:
        instant = datetime.fromisoformat(generated_at[:-1] + "+00:00")
        local = instant.astimezone(ZoneInfo("America/Sao_Paulo"))
    except ValueError:
        return "Horário indisponível"
    return local.strftime("%d/%m/%Y às %H:%M:%S") + " (horário de Brasília)"


class DashboardPresentationState(DashboardState):
    """Projeção visual do estado pai; não mantém cópia do resumo ou da sessão."""

    @rx.var
    def generated_at_display(self) -> str:
        return format_generated_at(self.generated_at)


def _total_card(label: str, value, description: str, identifier: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(label, color="gray", size="3"),
            rx.heading(value, size="7"),
            rx.text(description, color="gray", size="2"),
            spacing="2",
            align="start",
        ),
        id=identifier,
        padding="1.5rem",
        border="1px solid var(--gray-6)",
        border_radius="12px",
        width="100%",
    )


def _summary_content() -> rx.Component:
    return rx.cond(
        DashboardState.loading,
        rx.hstack(
            rx.spinner(), rx.text("Carregando resumo do acervo…"),
            role="status", aria_live="polite", align="center", spacing="2",
        ),
        rx.cond(
            DashboardState.status == "success",
            rx.vstack(
                rx.grid(
                    _total_card(
                        "Total de filmes cadastrados", DashboardState.total_filmes,
                        "Inclui filmes ativos e inativos.", "dashboard-total-filmes",
                    ),
                    _total_card(
                        "Total de exemplares cadastrados", DashboardState.total_exemplares,
                        "Quantidade cadastrada; não indica disponibilidade para locação.",
                        "dashboard-total-exemplares",
                    ),
                    columns=rx.breakpoints(initial="1", sm="2"),
                    spacing="4", width="100%",
                ),
                rx.text("Gerado em ", DashboardPresentationState.generated_at_display, size="2", color="gray"),
                role="status", aria_live="polite", width="100%", align="stretch",
            ),
            rx.cond(
                DashboardState.status == "forbidden",
                rx.callout("Resumo do acervo restrito a administradores.", color_scheme="gray", role="status"),
                rx.cond(
                    DashboardState.status == "unauthenticated",
                    rx.vstack(
                        rx.callout("Sessão inválida. Entre novamente para consultar o resumo.", color_scheme="red", role="alert"),
                        rx.link("Ir para o login", href="/login"),
                        align="start",
                    ),
                    rx.cond(
                        DashboardState.status == "invalid_response",
                        rx.callout("O serviço retornou uma resposta inválida. Tente atualizar.", color_scheme="red", role="alert"),
                        rx.cond(
                            DashboardState.status == "unavailable",
                            rx.callout("Não foi possível consultar o resumo. Tente atualizar.", color_scheme="orange", role="alert"),
                            rx.cond(
                                DashboardState.status == "error",
                                rx.callout("A consulta do resumo não está disponível.", color_scheme="red", role="alert"),
                                rx.text("Resumo ainda não consultado. Selecione Atualizar.", color="gray", role="status"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def render_acervo_summary(user_role) -> rx.Component:
    """A restrição visual complementa a autorização de estado e backend."""
    return rx.box(
        rx.cond(
            user_role == "admin",
            rx.vstack(
                rx.flex(
                    rx.heading("Resumo do acervo", size="6"),
                    rx.button(
                        "Atualizar",
                        on_click=DashboardState.refresh_summary,
                        loading=DashboardState.loading,
                        disabled=(DashboardState.loading
                                  | (DashboardState.status == "forbidden")
                                  | (DashboardState.status == "unauthenticated")),
                        aria_label="Atualizar resumo do acervo",
                    ),
                    direction=rx.breakpoints(initial="column", sm="row"),
                    justify="between", gap="3", width="100%",
                ),
                _summary_content(),
                spacing="4", width="100%", align="stretch",
            ),
            rx.callout("Resumo do acervo restrito a administradores.", color_scheme="gray", role="status"),
        ),
        id="dashboard-summary", width="100%",
    )
