"""Componentes Reflex do dashboard; sem consultas ou dados simulados."""

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


def user_initials(name: str) -> str:
    """Iniciais do primeiro e do último nome reais; vazio quando não há nome."""
    words = [word for word in (name or "").split() if word[:1].isalnum()]
    if not words:
        return ""
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


class DashboardPresentationState(DashboardState):
    """Projeção visual do estado pai; não mantém cópia do resumo ou da sessão."""

    @rx.var
    def generated_at_display(self) -> str:
        return format_generated_at(self.generated_at)


def _notice(message, kind: str = "info", role: str = "status") -> rx.Component:
    return rx.box(
        message,
        role=role,
        class_name=f"vitrine-dash__notice vitrine-dash__notice--{kind}",
    )


def _card_shell(label: str, icon_name: str, *children, identifier: str | None = None) -> rx.Component:
    props = {"id": identifier} if identifier else {}
    return rx.box(
        rx.box(
            rx.el.span(label, class_name="vitrine-dash__card-label"),
            rx.icon(icon_name, size=18, stroke_width=1.6, aria_hidden="true"),
            class_name="vitrine-dash__card-head",
        ),
        *children,
        class_name="vitrine-dash__card",
        **props,
    )


def _total_card(label: str, value, description: str, identifier: str, icon_name: str) -> rx.Component:
    return _card_shell(
        label,
        icon_name,
        rx.el.p(value, class_name="vitrine-dash__value"),
        rx.el.p(description, class_name="vitrine-dash__card-note"),
        identifier=identifier,
    )


def empty_metric_card(label: str, icon_name: str, identifier: str) -> rx.Component:
    """Indicador sem fonte de dados: nunca exibe valor inventado."""
    return _card_shell(
        label,
        icon_name,
        rx.el.p("—", class_name="vitrine-dash__value vitrine-dash__value--empty"),
        rx.el.p("Sem dados ainda", class_name="vitrine-dash__card-note"),
        identifier=identifier,
    )


def rental_metric_card() -> rx.Component:
    """Locações ativas a partir da listagem real; sem valor enquanto não houver resposta."""
    succeeded = DashboardState.rentals_status == "success"
    return _card_shell(
        "Locações ativas",
        "arrow-left-right",
        rx.el.p(
            rx.cond(succeeded, DashboardState.active_rentals, rx.cond(DashboardState.rentals_status == "loading", "…", "—")),
            class_name=rx.cond(succeeded, "vitrine-dash__value", "vitrine-dash__value vitrine-dash__value--empty"),
            aria_live="polite",
        ),
        rx.el.p(
            rx.match(
                DashboardState.rentals_status,
                ("success", DashboardState.rentals_note),
                ("loading", "Carregando locações…"),
                ("error", "Indisponível no momento"),
                "Sem dados ainda",
            ),
            class_name="vitrine-dash__card-note",
        ),
        identifier="dashboard-locacoes-ativas",
    )


def _summary_content() -> rx.Component:
    return rx.cond(
        DashboardState.loading,
        rx.box(
            rx.spinner(), rx.text("Carregando resumo do acervo…"),
            role="status", aria_live="polite",
            class_name="vitrine-dash__notice vitrine-dash__notice--loading",
        ),
        rx.cond(
            DashboardState.status == "success",
            rx.fragment(
                _total_card(
                    "Filmes cadastrados", DashboardState.total_filmes,
                    "Inclui filmes ativos e inativos.", "dashboard-total-filmes", "film",
                ),
                _total_card(
                    "Exemplares cadastrados", DashboardState.total_exemplares,
                    "Quantidade cadastrada; não indica disponibilidade para locação.",
                    "dashboard-total-exemplares", "disc-3",
                ),
            ),
            rx.cond(
                DashboardState.status == "forbidden",
                _notice("Resumo do acervo restrito a administradores.", "muted"),
                rx.cond(
                    DashboardState.status == "unauthenticated",
                    rx.box(
                        rx.text("Sessão inválida. Entre novamente para consultar o resumo."),
                        rx.link("Ir para o login", href="/login"),
                        role="alert",
                        class_name="vitrine-dash__notice vitrine-dash__notice--error",
                    ),
                    rx.cond(
                        DashboardState.status == "invalid_response",
                        _notice("O serviço retornou uma resposta inválida. Tente atualizar.", "error", "alert"),
                        rx.cond(
                            DashboardState.status == "unavailable",
                            _notice("Não foi possível consultar o resumo. Tente atualizar.", "warning", "alert"),
                            rx.cond(
                                DashboardState.status == "error",
                                _notice("A consulta do resumo não está disponível.", "error", "alert"),
                                _notice("Resumo ainda não consultado. Selecione Atualizar.", "muted"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def render_acervo_summary(user_role) -> rx.Component:
    """Cards reais de filmes e exemplares; a restrição visual complementa o backend."""
    return rx.box(
        rx.cond(
            user_role == "admin",
            _summary_content(),
            _notice("Resumo do acervo restrito a administradores.", "muted"),
        ),
        id="dashboard-summary",
        class_name="vitrine-dash__summary",
    )


def render_summary_toolbar(user_role) -> rx.Component:
    """Atualização do resumo e horário da consulta, somente para administradores."""
    return rx.cond(
        user_role == "admin",
        rx.box(
            rx.cond(
                DashboardState.status == "success",
                rx.el.span(
                    "Gerado em ", DashboardPresentationState.generated_at_display,
                    class_name="vitrine-dash__stamp",
                ),
                rx.fragment(),
            ),
            rx.button(
                "Atualizar",
                # Resumo (revalida a sessão), locações e clientes, como eventos separados.
                on_click=[DashboardState.refresh_summary, DashboardState.load_rentals, DashboardState.load_customers],
                loading=DashboardState.loading,
                disabled=(DashboardState.loading
                          | (DashboardState.status == "forbidden")
                          | (DashboardState.status == "unauthenticated")),
                aria_label="Atualizar resumo do acervo",
                class_name="vitrine-dash__refresh",
            ),
            class_name="vitrine-dash__toolbar",
        ),
        rx.fragment(),
    )


EMPTY_CHART_SUBTITLE = "Sem dados ainda · será alimentado pelo histórico real"


MOVEMENT_SUBTITLE = "Retiradas e devoluções por dia nos últimos 14 dias (horário de Brasília)"
# Seletor do período: (dias, rótulo do botão, trecho do subtítulo).
MOVEMENT_PERIODS = ((7, "7 dias", "nos últimos 7 dias"), (14, "14 dias", "nos últimos 14 dias"), (30, "1 mês", "no último mês"))


def _period_text(template: str):
    """Texto conforme o período escolhido; 14 dias continua o padrão."""
    return rx.match(
        DashboardState.movement_days,
        *[(days, template.format(trecho)) for days, _, trecho in MOVEMENT_PERIODS],
        template.format("nos últimos 14 dias"),
    )


def _period_selector() -> rx.Component:
    """7 dias / 14 dias / 1 mês; troca sem nova consulta ao Xano."""
    return rx.box(
        *[
            rx.el.button(
                label,
                type="button",
                on_click=DashboardState.set_movement_period(days),
                aria_pressed=DashboardState.movement_days == days,
                class_name=rx.cond(
                    DashboardState.movement_days == days,
                    "vitrine-dash__period vitrine-dash__period--on",
                    "vitrine-dash__period",
                ),
            )
            for days, label, _ in MOVEMENT_PERIODS
        ],
        role="group",
        aria_label="Período da movimentação",
        class_name="vitrine-dash__periods",
    )


def _legend_item(label: str, modifier: str) -> rx.Component:
    return rx.el.span(
        rx.el.span(class_name=f"vitrine-dash__legend-dot vitrine-dash__legend-dot--{modifier}", aria_hidden="true"),
        label,
        class_name="vitrine-dash__legend-item",
    )


def _movement_day(day) -> rx.Component:
    """Coluna do dia; o detalhe aparece ao passar o cursor ou focar pelo teclado."""
    return rx.el.li(
        rx.box(
            rx.el.strong(day["data"]),
            rx.el.span(day["semana"], class_name="vitrine-dash__tip-muted"),
            rx.el.span(rx.el.span(class_name="vitrine-dash__legend-dot vitrine-dash__legend-dot--out"), day["texto_retiradas"]),
            rx.el.span(rx.el.span(class_name="vitrine-dash__legend-dot vitrine-dash__legend-dot--in"), day["texto_devolucoes"]),
            class_name="vitrine-dash__tip",
            aria_hidden="true",
        ),
        rx.box(
            rx.box(class_name="vitrine-dash__bar vitrine-dash__bar--out", style={"height": day["altura_retiradas"].to_string() + "%"}),
            rx.box(class_name="vitrine-dash__bar vitrine-dash__bar--in", style={"height": day["altura_devolucoes"].to_string() + "%"}),
            class_name="vitrine-dash__bars",
            aria_hidden="true",
        ),
        rx.el.span(day["eixo"], class_name="vitrine-dash__axis-label", aria_hidden="true"),
        tab_index=0,
        aria_label=day["rotulo"],
        class_name="vitrine-dash__day",
    )


def _movement_body() -> rx.Component:
    return rx.match(
        DashboardState.rentals_status,
        (
            "loading",
            rx.box(
                rx.spinner(), rx.text("Carregando movimentação…"),
                role="status", aria_live="polite",
                class_name="vitrine-dash__chart-empty vitrine-dash__chart-empty--row",
            ),
        ),
        (
            "error",
            rx.box(
                rx.el.p(DashboardState.rentals_message, class_name="vitrine-dash__empty-text", role="alert"),
                rx.el.button(
                    "Tentar novamente",
                    type="button",
                    on_click=DashboardState.load_rentals,
                    class_name="vitrine-dash__retry",
                ),
                class_name="vitrine-dash__chart-empty vitrine-dash__chart-empty--stack",
            ),
        ),
        (
            "success",
            rx.box(
                rx.box(class_name="vitrine-dash__gridlines", aria_hidden="true"),
                rx.el.ol(
                    rx.foreach(DashboardState.movement, _movement_day),
                    # Uma coluna por dia do período escolhido.
                    style={"gridTemplateColumns": "repeat(" + DashboardState.movement_days.to_string() + ", minmax(0, 1fr))"},
                    class_name=rx.cond(
                        DashboardState.movement_days > 14,
                        "vitrine-dash__days vitrine-dash__days--dense",
                        "vitrine-dash__days",
                    ),
                    aria_label="Retiradas e devoluções por dia",
                ),
                rx.cond(
                    (DashboardState.movement_retiradas + DashboardState.movement_devolucoes) == 0,
                    rx.el.p(_period_text("Nenhuma retirada ou devolução {}."), class_name="vitrine-dash__empty-text vitrine-dash__chart-overlay"),
                ),
                class_name="vitrine-dash__chart",
            ),
        ),
        rx.box(
            rx.box(class_name="vitrine-dash__gridlines", aria_hidden="true"),
            rx.el.p("Nenhuma locação para exibir.", class_name="vitrine-dash__empty-text"),
            class_name="vitrine-dash__chart-empty",
        ),
    )


def movement_panel() -> rx.Component:
    """Movimentação de locações a partir da listagem real (member e admin)."""
    return rx.el.section(
        rx.box(
            rx.el.h2("Movimentação de locações", class_name="vitrine-dash__panel-title"),
            rx.box(
                rx.box(_legend_item("Retiradas", "out"), _legend_item("Devoluções", "in"), class_name="vitrine-dash__legend"),
                _period_selector(),
                class_name="vitrine-dash__panel-tools",
            ),
            class_name="vitrine-dash__panel-head",
        ),
        rx.el.p(
            rx.cond(
                DashboardState.rentals_status == "success",
                _period_text("Retiradas e devoluções por dia {} (horário de Brasília)"),
                EMPTY_CHART_SUBTITLE,
            ),
            class_name="vitrine-dash__panel-sub",
        ),
        _movement_body(),
        rx.box(
            rx.cond(
                DashboardState.rentals_status == "success",
                rx.el.span(DashboardState.movement_note, class_name="vitrine-dash__panel-total"),
            ),
            rx.el.a("Ver locações", href="/locacoes/nova", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-movimentacao",
        class_name="vitrine-dash__panel",
        aria_label="Movimentação de locações",
    )


def _genre_row(item) -> rx.Component:
    """Linha do gênero; o destaque com a participação aparece ao passar o cursor ou focar."""
    return rx.el.li(
        rx.box(
            rx.el.span(item["genero"], class_name="vitrine-dash__genre-name"),
            rx.el.span(item["rotulo"], class_name="vitrine-dash__genre-count"),
            class_name="vitrine-dash__genre-head",
        ),
        rx.box(
            rx.box(
                class_name="vitrine-dash__genre-fill",
                style={"width": item["largura"].to_string() + "%"},
            ),
            class_name="vitrine-dash__genre-bar",
            aria_hidden="true",
        ),
        rx.el.span(
            item["percentual"].to_string() + "% do acervo",
            class_name="vitrine-dash__genre-share",
            aria_hidden="true",
        ),
        tab_index=0,
        aria_label=item["genero"] + ": " + item["rotulo"] + ", " + item["percentual"].to_string() + "% do acervo",
        class_name="vitrine-dash__genre-item",
    )


def _genre_body() -> rx.Component:
    return rx.cond(
        DashboardState.loading,
        rx.box(
            rx.spinner(), rx.text("Carregando distribuição…"),
            role="status", aria_live="polite",
            class_name="vitrine-dash__chart-empty vitrine-dash__chart-empty--row",
        ),
        rx.cond(
            DashboardState.genres_status == "success",
            rx.cond(
                DashboardState.genres.length() > 0,
                rx.el.ul(
                    rx.foreach(DashboardState.genres, _genre_row),
                    aria_label="Filmes por gênero",
                    class_name="vitrine-dash__genre-list",
                ),
                rx.box(
                    rx.el.p("Nenhum filme cadastrado.", class_name="vitrine-dash__empty-text"),
                    class_name="vitrine-dash__chart-empty",
                ),
            ),
            rx.cond(
                DashboardState.genres_status == "error",
                rx.box(
                    rx.el.p(
                        "Não foi possível carregar a distribuição por gênero. Tente atualizar.",
                        class_name="vitrine-dash__empty-text",
                        role="alert",
                    ),
                    class_name="vitrine-dash__chart-empty",
                ),
                rx.box(
                    rx.el.p("Nenhuma distribuição para exibir.", class_name="vitrine-dash__empty-text"),
                    class_name="vitrine-dash__chart-empty",
                ),
            ),
        ),
    )


def genre_panel(user_role) -> rx.Component:
    """Acervo por gênero: dados reais do catálogo, restritos a administradores."""
    return rx.el.section(
        rx.el.h2("Acervo por gênero", class_name="vitrine-dash__panel-title"),
        rx.cond(
            user_role == "admin",
            rx.fragment(
                rx.el.p(
                    rx.cond(
                        DashboardState.genres_status == "success",
                        "Filmes cadastrados por gênero, ativos e inativos",
                        EMPTY_CHART_SUBTITLE,
                    ),
                    class_name="vitrine-dash__panel-sub",
                ),
                _genre_body(),
            ),
            rx.fragment(
                rx.el.p(
                    "Distribuição disponível apenas para administradores.",
                    class_name="vitrine-dash__panel-sub",
                ),
                rx.box(
                    rx.el.p("Sem permissão para visualizar.", class_name="vitrine-dash__empty-text"),
                    class_name="vitrine-dash__chart-empty",
                ),
            ),
        ),
        rx.box(
            rx.el.a("Ver acervo", href="/filmes", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-generos",
        class_name="vitrine-dash__panel",
        aria_label="Acervo por gênero",
    )


def customer_metric_card() -> rx.Component:
    """Total real de clientes cadastrados; sem valor enquanto não houver resposta."""
    succeeded = DashboardState.customers_status == "success"
    return _card_shell(
        "Clientes cadastrados",
        "users",
        rx.el.p(
            rx.cond(succeeded, DashboardState.customers_total, rx.cond(DashboardState.customers_status == "loading", "…", "—")),
            class_name=rx.cond(succeeded, "vitrine-dash__value", "vitrine-dash__value vitrine-dash__value--empty"),
            aria_live="polite",
        ),
        rx.el.p(
            rx.match(
                DashboardState.customers_status,
                ("success", DashboardState.customers_note),
                ("loading", "Carregando clientes…"),
                ("error", "Indisponível no momento"),
                "Sem dados ainda",
            ),
            class_name="vitrine-dash__card-note",
        ),
        identifier="dashboard-clientes-total",
    )


def _panel_status_body(status, message, retry_event, loading_text: str, success: rx.Component) -> rx.Component:
    """Carregamento, falha com "Tentar novamente" e área vazia padrão dos painéis."""
    return rx.match(
        status,
        (
            "loading",
            rx.box(
                rx.spinner(), rx.text(loading_text),
                role="status", aria_live="polite",
                class_name="vitrine-dash__chart-empty vitrine-dash__chart-empty--row",
            ),
        ),
        (
            "error",
            rx.box(
                rx.el.p(message, class_name="vitrine-dash__empty-text", role="alert"),
                rx.el.button("Tentar novamente", type="button", on_click=retry_event, class_name="vitrine-dash__retry"),
                class_name="vitrine-dash__chart-empty vitrine-dash__chart-empty--stack",
            ),
        ),
        ("success", success),
        rx.box(
            rx.el.p("Nenhum dado para exibir.", class_name="vitrine-dash__empty-text"),
            class_name="vitrine-dash__chart-empty",
        ),
    )


def _panel_empty(text: str) -> rx.Component:
    return rx.box(rx.el.p(text, class_name="vitrine-dash__empty-text"), class_name="vitrine-dash__chart-empty")


def _situation_row(label: str, value, modifier: str) -> rx.Component:
    return rx.el.li(
        rx.el.span(class_name=f"vitrine-dash__legend-dot vitrine-dash__legend-dot--{modifier}", aria_hidden="true"),
        rx.el.span(label, class_name="vitrine-dash__situation-label"),
        rx.el.strong(value, class_name="vitrine-dash__situation-value"),
        class_name="vitrine-dash__situation-row",
    )


def customer_situation_panel() -> rx.Component:
    """Ativos x inativos em rosca, com bloqueios manuais à parte (são independentes)."""
    pct = DashboardState.customers_active_pct.to_string()
    lidos = DashboardState.customers_active + DashboardState.customers_inactive
    donut = rx.box(
        rx.box(
            rx.box(
                rx.el.strong(pct + "%", class_name="vitrine-dash__donut-value"),
                rx.el.span("ativos", class_name="vitrine-dash__donut-caption"),
                class_name="vitrine-dash__donut-hole",
            ),
            class_name="vitrine-dash__donut",
            style={"background": "conic-gradient(var(--vd-red) 0 " + pct + "%, #52525b 0)"},
            role="img",
            aria_label=(
                DashboardState.customers_active.to_string() + " clientes ativos e "
                + DashboardState.customers_inactive.to_string() + " inativos"
            ),
        ),
        rx.el.ul(
            _situation_row("Ativos", DashboardState.customers_active, "out"),
            _situation_row("Inativos", DashboardState.customers_inactive, "muted"),
            rx.el.li(
                rx.icon("lock", size=12, stroke_width=2, aria_hidden="true", class_name="vitrine-dash__situation-icon"),
                rx.el.span("Com bloqueio manual", class_name="vitrine-dash__situation-label"),
                rx.el.strong(DashboardState.customers_blocked, class_name="vitrine-dash__situation-value"),
                class_name="vitrine-dash__situation-row vitrine-dash__situation-row--sep",
            ),
            class_name="vitrine-dash__situation-list",
        ),
        class_name="vitrine-dash__situation",
    )
    return rx.el.section(
        rx.el.h2("Situação dos clientes", class_name="vitrine-dash__panel-title"),
        rx.el.p(
            rx.cond(
                DashboardState.customers_status == "success",
                "Situação cadastral; o bloqueio manual é independente dela",
                EMPTY_CHART_SUBTITLE,
            ),
            class_name="vitrine-dash__panel-sub",
        ),
        _panel_status_body(
            DashboardState.customers_status, DashboardState.customers_message, DashboardState.load_customers,
            "Carregando clientes…",
            rx.cond(lidos > 0, donut, _panel_empty("Nenhum cliente cadastrado.")),
        ),
        rx.box(
            rx.el.a("Ver clientes", href="/clientes", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-clientes-situacao",
        class_name="vitrine-dash__panel",
        aria_label="Situação dos clientes",
    )


def _customer_row(customer) -> rx.Component:
    return rx.el.li(
        rx.el.a(
            rx.box(
                rx.el.span(customer["nome"], class_name="vitrine-dash__row-title"),
                rx.el.span(customer["cpf_mascarado"], class_name="vitrine-dash__row-meta vitrine-dash__mono"),
                class_name="vitrine-dash__row-text",
            ),
            rx.box(
                rx.cond(
                    customer["bloqueado"],
                    rx.el.span(rx.icon("lock", size=11, stroke_width=2, aria_hidden="true"), "Bloqueado",
                               class_name="vitrine-dash__badge vitrine-dash__badge--alert"),
                ),
                rx.el.span(
                    rx.cond(customer["ativo"], "Ativo", "Inativo"),
                    class_name=rx.cond(customer["ativo"], "vitrine-dash__badge vitrine-dash__badge--on", "vitrine-dash__badge"),
                ),
                class_name="vitrine-dash__row-badges",
            ),
            href=customer["href"],
            class_name="vitrine-dash__row",
        ),
    )


def customer_list_panel() -> rx.Component:
    """Primeiros clientes por nome, com situação e bloqueio; CPF sempre mascarado."""
    return rx.el.section(
        rx.el.h2("Clientes", class_name="vitrine-dash__panel-title"),
        rx.el.p(
            rx.cond(
                DashboardState.customers_status == "success",
                "Em ordem alfabética · selecione um cliente para abrir o cadastro",
                EMPTY_CHART_SUBTITLE,
            ),
            class_name="vitrine-dash__panel-sub",
        ),
        _panel_status_body(
            DashboardState.customers_status, DashboardState.customers_message, DashboardState.load_customers,
            "Carregando clientes…",
            rx.cond(
                DashboardState.customers_list.length() > 0,
                rx.el.ul(rx.foreach(DashboardState.customers_list, _customer_row), class_name="vitrine-dash__rows",
                         aria_label="Clientes"),
                _panel_empty("Nenhum cliente cadastrado."),
            ),
        ),
        rx.box(
            rx.cond(
                DashboardState.customers_status == "success",
                rx.el.span(
                    "Exibindo ", DashboardState.customers_list.length(), " de ", DashboardState.customers_total,
                    class_name="vitrine-dash__panel-total",
                ),
            ),
            rx.el.a("Novo cliente", href="/clientes/novo", class_name="vitrine-dash__link"),
            rx.el.a("Ver todos os clientes", href="/clientes", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-clientes-lista",
        class_name="vitrine-dash__panel",
        aria_label="Clientes",
    )


def _overdue_row(item) -> rx.Component:
    return rx.el.li(
        rx.el.a(
            rx.box(
                rx.el.span(item["cliente"], class_name="vitrine-dash__row-title"),
                rx.el.span(item["filme"], class_name="vitrine-dash__row-meta"),
                class_name="vitrine-dash__row-text",
            ),
            rx.el.span(
                rx.icon("triangle-alert", size=12, stroke_width=2, aria_hidden="true"),
                item["atraso"],
                class_name="vitrine-dash__badge vitrine-dash__badge--alert",
            ),
            href=item["href"],
            class_name="vitrine-dash__row",
        ),
    )


def overdue_panel() -> rx.Component:
    """Locações ativas com vencimento ultrapassado, das mais atrasadas primeiro."""
    return rx.el.section(
        rx.el.h2("Locações vencidas", class_name="vitrine-dash__panel-title"),
        rx.el.p(
            rx.cond(
                DashboardState.rentals_status == "success",
                "Ativas com vencimento ultrapassado, das mais atrasadas primeiro",
                EMPTY_CHART_SUBTITLE,
            ),
            class_name="vitrine-dash__panel-sub",
        ),
        _panel_status_body(
            DashboardState.rentals_status, DashboardState.rentals_message, DashboardState.load_rentals,
            "Carregando locações…",
            rx.cond(
                DashboardState.overdue_list.length() > 0,
                rx.el.ul(rx.foreach(DashboardState.overdue_list, _overdue_row), class_name="vitrine-dash__rows",
                         aria_label="Locações vencidas"),
                _panel_empty("Nenhuma locação vencida. Tudo em dia."),
            ),
        ),
        rx.box(
            rx.cond(
                DashboardState.rentals_status == "success",
                rx.el.span(DashboardState.rentals_note, class_name="vitrine-dash__panel-total"),
            ),
            rx.el.a("Ver locações", href="/locacoes/nova", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-locacoes-vencidas",
        class_name="vitrine-dash__panel",
        aria_label="Locações vencidas",
    )


def _top_customer_row(item) -> rx.Component:
    return rx.el.li(
        rx.el.a(
            rx.box(
                rx.el.span(item["nome"], class_name="vitrine-dash__genre-name"),
                rx.el.span(item["rotulo"], class_name="vitrine-dash__genre-count"),
                class_name="vitrine-dash__genre-head",
            ),
            rx.box(
                rx.box(class_name="vitrine-dash__genre-fill", style={"width": item["largura"].to_string() + "%"}),
                class_name="vitrine-dash__genre-bar",
                aria_hidden="true",
            ),
            href=item["href"],
            aria_label=item["nome"] + ": " + item["rotulo"],
            class_name="vitrine-dash__genre-link",
        ),
        class_name="vitrine-dash__genre-item",
    )


def top_customers_panel() -> rx.Component:
    """Clientes com mais locações entre as locações lidas (ativas e devolvidas)."""
    return rx.el.section(
        rx.el.h2("Clientes que mais alugam", class_name="vitrine-dash__panel-title"),
        rx.el.p(
            rx.cond(
                DashboardState.rentals_status == "success",
                rx.cond(
                    DashboardState.rentals_partial,
                    "Entre as locações mais recentes, ativas e devolvidas",
                    "Todas as locações registradas, ativas e devolvidas",
                ),
                EMPTY_CHART_SUBTITLE,
            ),
            class_name="vitrine-dash__panel-sub",
        ),
        _panel_status_body(
            DashboardState.rentals_status, DashboardState.rentals_message, DashboardState.load_rentals,
            "Carregando locações…",
            rx.cond(
                DashboardState.top_customers.length() > 0,
                rx.el.ol(rx.foreach(DashboardState.top_customers, _top_customer_row), class_name="vitrine-dash__genre-list",
                         aria_label="Clientes que mais alugam"),
                _panel_empty("Nenhuma locação registrada."),
            ),
        ),
        rx.box(
            rx.el.a("Ver clientes", href="/clientes", class_name="vitrine-dash__link"),
            class_name="vitrine-dash__panel-footer",
        ),
        id="dashboard-clientes-ranking",
        class_name="vitrine-dash__panel",
        aria_label="Clientes que mais alugam",
    )
