"""Estado isolado do resumo integrado à revisão privada da sessão."""

from datetime import date, datetime, timedelta
import math
import time
from typing import TypedDict
from zoneinfo import ZoneInfo

import reflex as rx

from ProjetoLocadora.dashboard_client import (
    DashboardErrorCategory,
    XanoDashboardError,
    get_dashboard_summary_xano,
)
from ProjetoLocadora.locacoes_client import RentalError, list_rentals
from ProjetoLocadora.xano_client import (
    XanoCatalogError,
    XanoCustomerError,
    XanoSessionUnavailable,
    get_me_xano,
    is_authorized_employee,
    list_customers_xano,
    list_films_xano,
)

GENEROS_EXIBIDOS = 6
GENERO_OUTROS = "Outros"

# Movimentação: janela em dias de Brasília e limite de leitura da listagem
# (cota do plano Xano: 10 requisições a cada 20 s).
MOVIMENTO_DIAS = 14
# Períodos do seletor do gráfico (dias); 30 = "1 mês".
MOVIMENTO_PERIODOS = (7, 14, 30)
LOCACOES_POR_PAGINA = 50
LOCACOES_PAGINAS_MAX = 3
BRASILIA = ZoneInfo("America/Sao_Paulo")
DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

# Clientes: mesma cota do Xano; a listagem aceita no máximo 50 por página.
CLIENTES_POR_PAGINA = 50
CLIENTES_PAGINAS_MAX = 2
CLIENTES_LISTADOS = 6
RANKING_CLIENTES = 5
VENCIDAS_LISTADAS = 5
DIA_MS = 86_400_000


class GeneroContagem(TypedDict):
    genero: str
    total: int
    rotulo: str
    largura: int
    percentual: int


class DiaMovimento(TypedDict):
    data: str
    semana: str
    retiradas: int
    devolucoes: int
    altura_retiradas: int
    altura_devolucoes: int
    texto_retiradas: str
    # Rótulo do eixo; vazio quando o período é longo e o dia não é rotulado.
    eixo: str
    texto_devolucoes: str
    rotulo: str


class ClienteLinha(TypedDict):
    id: int
    nome: str
    cpf_mascarado: str
    ativo: bool
    bloqueado: bool
    href: str


class ResumoClientes(TypedDict):
    ativos: int
    inativos: int
    bloqueados: int
    percentual_ativos: int
    lista: list[ClienteLinha]


class ClienteRanking(TypedDict):
    nome: str
    total: int
    rotulo: str
    largura: int
    href: str


class LocacaoVencida(TypedDict):
    id: int
    cliente: str
    filme: str
    atraso: str
    href: str


class ResumoLocacoes(TypedDict):
    ativas: int
    vencidas: int
    retiradas: int
    devolucoes: int
    dias: list[DiaMovimento]


def _dia_brasilia(ms: int) -> date:
    return datetime.fromtimestamp(ms / 1000, BRASILIA).date()


def _plural(total: int, singular: str, plural: str) -> str:
    return f"{total} {singular if total == 1 else plural}"


def resumir_locacoes(rentals, agora_ms: int, dias: int = MOVIMENTO_DIAS) -> ResumoLocacoes:
    """Contagens reais: ativas, vencidas e retiradas/devoluções por dia de Brasília.

    Altura de cada barra é proporcional ao maior valor diário do período (mínimo
    visível de 4% quando há movimento; zero continua zero).
    """
    hoje = _dia_brasilia(agora_ms)
    janela = [hoje - timedelta(days=offset) for offset in range(dias - 1, -1, -1)]
    retiradas = {dia: 0 for dia in janela}
    devolucoes = {dia: 0 for dia in janela}
    ativas = vencidas = 0
    for rental in rentals:
        if rental["status"] == "active":
            ativas += 1
            if rental["due_at"] < agora_ms:
                vencidas += 1
        dia = _dia_brasilia(rental["rented_at"])
        if dia in retiradas:
            retiradas[dia] += 1
        if rental.get("returned_at"):
            dia = _dia_brasilia(rental["returned_at"])
            if dia in devolucoes:
                devolucoes[dia] += 1
    pico = max([*retiradas.values(), *devolucoes.values(), 0])

    def altura(total: int) -> int:
        return max(round(total * 100 / pico), 4) if total and pico else 0

    return {
        "ativas": ativas,
        "vencidas": vencidas,
        "retiradas": sum(retiradas.values()),
        "devolucoes": sum(devolucoes.values()),
        "dias": [
            {
                "data": dia.strftime("%d/%m"),
                # Até 14 dias todos os dias são rotulados; em 1 mês, um a cada 5 (inclui hoje).
                "eixo": dia.strftime("%d/%m") if dias <= 14 or (hoje - dia).days % 5 == 0 else "",
                "semana": DIAS_SEMANA[dia.weekday()],
                "retiradas": retiradas[dia],
                "devolucoes": devolucoes[dia],
                "altura_retiradas": altura(retiradas[dia]),
                "altura_devolucoes": altura(devolucoes[dia]),
                "texto_retiradas": _plural(retiradas[dia], "retirada", "retiradas"),
                "texto_devolucoes": _plural(devolucoes[dia], "devolução", "devoluções"),
                "rotulo": (
                    f"{dia.strftime('%d/%m')}: {_plural(retiradas[dia], 'retirada', 'retiradas')}, "
                    f"{_plural(devolucoes[dia], 'devolução', 'devoluções')}"
                ),
            }
            for dia in janela
        ],
    }


def distribuir_generos(films, limite: int = GENEROS_EXIBIDOS) -> list[GeneroContagem]:
    """Conta os filmes reais por gênero (sem diferenciar maiúsculas/minúsculas).

    Mantém a grafia do primeiro filme de cada gênero, ordena do maior para o menor
    (empate pela ordem de aparição) e agrupa o excedente em "Outros".
    """
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for film in films:
        name = " ".join(str(film["genero"]).split())
        key = name.casefold()
        if not key:
            continue
        names.setdefault(key, name)
        counts[key] = counts.get(key, 0) + 1

    ordered = sorted(counts.items(), key=lambda item: -item[1])
    rows = [(names[key], total) for key, total in ordered]
    if len(rows) > limite:
        rows = [*rows[:limite], (GENERO_OUTROS, sum(total for _, total in rows[limite:]))]
    peak = max((total for _, total in rows), default=0)
    overall = sum(total for _, total in rows)
    return [
        {
            "genero": name,
            "total": total,
            "rotulo": f"{total} {'filme' if total == 1 else 'filmes'}",
            "largura": max(round(total * 100 / peak), 4) if peak else 0,
            # Participação no acervo exibido, para o detalhe ao passar o cursor.
            "percentual": round(total * 100 / overall) if overall else 0,
        }
        for name, total in rows
    ]


def resumir_clientes(customers, listados: int = CLIENTES_LISTADOS) -> ResumoClientes:
    """Situação cadastral real dos clientes lidos e os primeiros por nome para a lista.

    Bloqueio manual é independente da situação: um cliente ativo pode estar bloqueado.
    """
    ativos = sum(1 for customer in customers if customer["status"] == "active")
    total = len(customers)
    return {
        "ativos": ativos,
        "inativos": total - ativos,
        "bloqueados": sum(1 for customer in customers if customer["bloqueio_manual_ativo"]),
        "percentual_ativos": round(ativos * 100 / total) if total else 0,
        "lista": [
            {
                "id": customer["id"],
                "nome": customer["nome"],
                "cpf_mascarado": customer["cpf_mascarado"],
                "ativo": customer["status"] == "active",
                "bloqueado": customer["bloqueio_manual_ativo"],
                "href": f"/clientes/{customer['id']}",
            }
            for customer in customers[:listados]
        ],
    }


def ranking_clientes(rentals, limite: int = RANKING_CLIENTES) -> list[ClienteRanking]:
    """Clientes com mais locações (ativas e devolvidas) entre as locações lidas.

    Empate mantém a ordem de aparição, isto é, quem alugou mais recentemente.
    """
    counts: dict[int, int] = {}
    names: dict[int, str] = {}
    for rental in rentals:
        customer_id = rental["customer_id"]
        names.setdefault(customer_id, rental["customer_name"])
        counts[customer_id] = counts.get(customer_id, 0) + 1
    rows = sorted(counts.items(), key=lambda item: -item[1])[:limite]
    peak = max((total for _, total in rows), default=0)
    return [
        {
            "nome": names[customer_id],
            "total": total,
            "rotulo": _plural(total, "locação", "locações"),
            "largura": max(round(total * 100 / peak), 4) if peak else 0,
            "href": f"/clientes/{customer_id}",
        }
        for customer_id, total in rows
    ]


def locacoes_vencidas(rentals, agora_ms: int, limite: int = VENCIDAS_LISTADAS) -> list[LocacaoVencida]:
    """Locações ativas com vencimento ultrapassado, da mais atrasada para a menos."""
    vencidas = sorted(
        (rental for rental in rentals if rental["status"] == "active" and rental["due_at"] < agora_ms),
        key=lambda rental: rental["due_at"],
    )
    resultado: list[LocacaoVencida] = []
    for rental in vencidas[:limite]:
        dias = (agora_ms - rental["due_at"]) // DIA_MS
        resultado.append({
            "id": rental["id"],
            "cliente": rental["customer_name"],
            "filme": rental["film_title"],
            "atraso": f"{_plural(dias, 'dia', 'dias')} de atraso" if dias else "Venceu há menos de 1 dia",
            "href": f"/locacoes/{rental['id']}",
        })
    return resultado


class DashboardState(rx.State):
    status: str = "initial"
    loading: bool = False
    total_filmes: int | None = None
    total_exemplares: int | None = None
    generated_at: str = ""
    message: str = ""
    genres: list[GeneroContagem] = []
    genres_status: str = "initial"
    # Locações (member e admin), independentes do resumo do acervo:
    # initial | loading | success | error
    rentals_status: str = "initial"
    rentals_message: str = ""
    active_rentals: int | None = None
    overdue_rentals: int = 0
    movement: list[DiaMovimento] = []
    movement_retiradas: int = 0
    movement_devolucoes: int = 0
    # Mais locações que o limite de leitura: contagens das mais recentes.
    rentals_partial: bool = False
    rentals_note: str = ""
    movement_note: str = ""
    movement_days: int = MOVIMENTO_DIAS
    # Locações lidas na última carga: trocar o período recalcula sem nova consulta.
    _rentals_loaded: list[dict] = []
    top_customers: list[ClienteRanking] = []
    overdue_list: list[LocacaoVencida] = []
    # Clientes (member e admin), com estado próprio: initial | loading | success | error
    customers_status: str = "initial"
    customers_message: str = ""
    customers_total: int | None = None
    customers_active: int = 0
    customers_inactive: int = 0
    customers_blocked: int = 0
    customers_active_pct: int = 0
    customers_list: list[ClienteLinha] = []
    customers_note: str = ""
    _revision: int = 0
    _request_id: int = 0
    _rentals_request_id: int = 0
    _customers_request_id: int = 0

    def _clear_values(self) -> None:
        self.total_filmes = None
        self.total_exemplares = None
        self.generated_at = ""
        self.message = ""
        self.genres = []
        self.genres_status = "initial"

    def _clear_rentals(self) -> None:
        self.active_rentals = None
        self.overdue_rentals = 0
        self.movement = []
        self.movement_retiradas = self.movement_devolucoes = 0
        self.rentals_partial = False
        self.rentals_message = ""
        self.rentals_note = self.movement_note = ""
        self._rentals_loaded = []
        self.top_customers = []
        self.overdue_list = []

    def _clear_customers(self) -> None:
        self.customers_message = ""
        self.customers_total = None
        self.customers_active = self.customers_inactive = self.customers_blocked = 0
        self.customers_active_pct = 0
        self.customers_list = []
        self.customers_note = ""

    def _invalidate(self) -> None:
        """Ponto de integração futuro para transições locais da sessão."""
        self._revision += 1
        self._request_id += 1
        self._rentals_request_id += 1
        self._customers_request_id += 1
        self._clear_values()
        self._clear_rentals()
        self._clear_customers()
        self.loading = False
        self.status = "initial"
        self.rentals_status = "initial"
        self.customers_status = "initial"

    def _show_error(self, category: DashboardErrorCategory) -> None:
        # Não usar str(error): somente mensagens públicas controladas aqui.
        self._clear_values()
        if category == DashboardErrorCategory.AUTHENTICATION:
            self.status = "unauthenticated"
            self.message = "Entre novamente para consultar o resumo do acervo."
        elif category == DashboardErrorCategory.AUTHORIZATION:
            self.status = "forbidden"
            self.message = "Resumo do acervo restrito a administradores."
        elif category == DashboardErrorCategory.INVALID_RESPONSE:
            self.status = "invalid_response"
            self.message = "O serviço retornou um resumo inválido. Tente atualizar."
        elif category in {
            DashboardErrorCategory.CONNECTION, DashboardErrorCategory.TIMEOUT,
            DashboardErrorCategory.SERVICE,
        }:
            self.status = "unavailable"
            self.message = "Não foi possível consultar o resumo. Tente atualizar."
        else:
            self.status = "error"
            self.message = "A consulta do resumo não está disponível."

    async def _load_summary(self, fresh: bool = True):
        # Antes do primeiro await: bloqueia eventos simultâneos na mesma instância.
        if self.loading:
            return
        self._request_id += 1
        request_id, revision = self._request_id, self._revision
        self._clear_values()
        self.loading = True
        self.status = "loading"
        yield

        # Importação localizada evita que o módulo principal importe a si próprio
        # quando os eventos da Dashboard forem integrados futuramente.
        from ProjetoLocadora.ProjetoLocadora import State

        session = None
        snapshot = None

        def current():
            return (
                request_id == self._request_id and revision == self._revision
                and session is not None and snapshot == (
                    session._user_id, session._user_role, session._xano_auth_token, session._session_revision,
                )
            )

        try:
            session = await self.get_state(State)
            # Token existe somente na sessão original e em variáveis locais
            # durante a requisição; não vira campo de DashboardState.
            snapshot = (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)
            identity, role, token, _ = snapshot
            if not token or not identity:
                self._show_error(DashboardErrorCategory.AUTHENTICATION)
                return
            if role != "admin":
                self._show_error(DashboardErrorCategory.AUTHORIZATION)
                return

            # A carga de entrada vem logo após require_session, que acabou de conferir
            # esta mesma sessão; o Xano continua autorizando o resumo. "Atualizar"
            # (fresh=True) sempre revalida, como exige a especificação.
            checked_now = fresh or not session._recently_verified()
            if not checked_now:
                me = {"id": identity, "role": role, "is_active": True}
            else:
                try:
                    me = await get_me_xano(token)
                except XanoSessionUnavailable:
                    if current():
                        self._show_error(DashboardErrorCategory.CONNECTION)
                    return
                if not current():
                    return
            if not me or not is_authorized_employee(me) or str(me.get("id", "")) != identity:
                session._clear_session()
                await session._sync_dashboard_session()
                self._show_error(DashboardErrorCategory.AUTHENTICATION)
                yield rx.redirect("/login")
                return
            if me.get("role") != "admin":
                session._set_user(me)
                await session._sync_dashboard_session()
                self._show_error(DashboardErrorCategory.AUTHORIZATION)
                return
            if checked_now:
                # Locações e clientes, logo em seguida, reaproveitam esta conferência.
                session._mark_session_verified()

            summary = await get_dashboard_summary_xano(token)
            if not current():
                return
            self.total_filmes = summary["total_filmes"]
            self.total_exemplares = summary["total_exemplares"]
            self.generated_at = summary["generated_at"]
            # A distribuição por gênero vem do catálogo existente; sua falha não
            # invalida os totais do resumo.
            try:
                films = await list_films_xano(token)
            except XanoCatalogError:
                genres, genres_status = [], "error"
            except Exception:
                genres, genres_status = [], "error"
            else:
                genres, genres_status = distribuir_generos(films), "success"
            if not current():
                return
            self.genres = genres
            self.genres_status = genres_status
            self.status = "success"
        except XanoDashboardError as error:
            if current():
                if error.category == DashboardErrorCategory.AUTHENTICATION:
                    session._clear_session()
                    await session._sync_dashboard_session()
                self._show_error(error.category)
                if error.category == DashboardErrorCategory.AUTHENTICATION:
                    yield rx.redirect("/login")
        except Exception:
            if request_id == self._request_id and revision == self._revision:
                if session is None or current():
                    self._show_error(DashboardErrorCategory.UNEXPECTED_STATUS)
        finally:
            if request_id == self._request_id and revision == self._revision:
                if snapshot is not None and not current():
                    self._clear_values()
                    self.status = "initial"
                self.loading = False

    @rx.event
    async def load_summary(self):
        async for update in self._load_summary(fresh=False):
            yield update

    @rx.event
    async def refresh_summary(self):
        # A mesma rotina sempre revalida a sessão; não usa resultado em cache.
        async for update in self._load_summary(fresh=True):
            yield update

    async def _load_rentals(self):
        """Locações reais para o card de ativas e a movimentação dos últimos dias."""
        if self.rentals_status == "loading":
            return
        self._rentals_request_id += 1
        request_id, revision = self._rentals_request_id, self._revision
        self._clear_rentals()
        self.rentals_status = "loading"
        yield

        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        snapshot = (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)

        def current():
            return (
                request_id == self._rentals_request_id and revision == self._revision
                and snapshot == (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)
            )

        def fail(message: str):
            if current():
                self._clear_rentals()
                self.rentals_status = "error"
                self.rentals_message = message

        identity, _, token, _ = snapshot
        if not token or not identity:
            fail("Entre novamente para consultar as locações.")
            return
        try:
            # Entrada da página: require_session acabou de conferir a sessão.
            if not session._recently_verified():
                try:
                    me = await get_me_xano(token)
                except XanoSessionUnavailable:
                    fail("Não foi possível confirmar a sessão agora. Tente atualizar.")
                    return
                if not current():
                    return
                if not me or not is_authorized_employee(me) or str(me.get("id", "")) != identity:
                    session._clear_session()
                    await session._sync_dashboard_session()
                    yield rx.redirect("/login")
                    return
                session._mark_session_verified()

            first = await list_rentals(token, 1, LOCACOES_POR_PAGINA)
            if not current():
                return
            rentals = list(first["items"])
            pages = min(math.ceil(first["total"] / LOCACOES_POR_PAGINA), LOCACOES_PAGINAS_MAX)
            for number in range(2, pages + 1):
                page = await list_rentals(token, number, LOCACOES_POR_PAGINA)
                if not current():
                    return
                rentals.extend(page["items"])
            agora_ms = int(time.time() * 1000)
            resumo = resumir_locacoes(rentals, agora_ms, self.movement_days)
            self.top_customers = ranking_clientes(rentals)
            self.overdue_list = locacoes_vencidas(rentals, agora_ms)
            self.active_rentals = resumo["ativas"]
            self.overdue_rentals = resumo["vencidas"]
            self.rentals_partial = first["total"] > len(rentals)
            self._rentals_loaded = rentals
            vencidas = resumo["vencidas"]
            self.rentals_note = f"{vencidas} com vencimento ultrapassado" if vencidas else "Nenhuma com vencimento ultrapassado"
            if self.rentals_partial:
                self.rentals_note += f" · entre as {len(rentals)} locações mais recentes"
            self._apply_movement(resumo)
            self.rentals_status = "success"
        except RentalError as error:
            if error.category == "authentication" and current():
                session._clear_session()
                await session._sync_dashboard_session()
                yield rx.redirect("/login")
                return
            if error.category == "ratelimited":
                fail(f"O Xano atingiu o limite de requisições do plano. Aguarde {error.retry_after or 20} s e atualize.")
            elif error.category == "authorization":
                fail("Sua conta não tem permissão para consultar locações.")
            elif error.category == "notfound":
                fail("A listagem de locações não está disponível no serviço.")
            else:
                fail("Não foi possível carregar as locações. Tente atualizar.")
        except Exception:
            fail("Não foi possível carregar as locações. Tente atualizar.")

    def _apply_movement(self, resumo: ResumoLocacoes) -> None:
        """Gráfico e total do período escolhido, a partir de um resumo já calculado."""
        self.movement = resumo["dias"]
        self.movement_retiradas = resumo["retiradas"]
        self.movement_devolucoes = resumo["devolucoes"]
        periodo = "1 mês" if self.movement_days == 30 else f"{self.movement_days} dias"
        self.movement_note = (
            f"{_plural(resumo['retiradas'], 'retirada', 'retiradas')} e "
            f"{_plural(resumo['devolucoes'], 'devolução', 'devoluções')} em {periodo}"
        )
        if self.rentals_partial:
            self.movement_note += f" · entre as {len(self._rentals_loaded)} locações mais recentes"

    @rx.event
    def set_movement_period(self, days: int):
        """Troca 7/14/30 dias recalculando sobre as locações já lidas, sem consultar o Xano."""
        if days not in MOVIMENTO_PERIODOS or days == self.movement_days:
            return
        self.movement_days = days
        if self.rentals_status == "success":
            self._apply_movement(resumir_locacoes(self._rentals_loaded, int(time.time() * 1000), days))

    @rx.event
    async def load_rentals(self):
        async for update in self._load_rentals():
            yield update

    async def _load_customers(self):
        """Situação cadastral e lista curta de clientes a partir da listagem real."""
        if self.customers_status == "loading":
            return
        self._customers_request_id += 1
        request_id, revision = self._customers_request_id, self._revision
        self._clear_customers()
        self.customers_status = "loading"
        yield

        from ProjetoLocadora.ProjetoLocadora import State

        session = await self.get_state(State)
        snapshot = (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)

        def current():
            return (
                request_id == self._customers_request_id and revision == self._revision
                and snapshot == (session._user_id, session._user_role, session._xano_auth_token, session._session_revision)
            )

        def fail(message: str):
            if current():
                self._clear_customers()
                self.customers_status = "error"
                self.customers_message = message

        identity, _, token, _ = snapshot
        if not token or not identity:
            fail("Entre novamente para consultar os clientes.")
            return
        try:
            # Normalmente reaproveita a conferência feita pela carga das locações.
            if not session._recently_verified():
                try:
                    me = await get_me_xano(token)
                except XanoSessionUnavailable:
                    fail("Não foi possível confirmar a sessão agora. Tente atualizar.")
                    return
                if not current():
                    return
                if not me or not is_authorized_employee(me) or str(me.get("id", "")) != identity:
                    session._clear_session()
                    await session._sync_dashboard_session()
                    yield rx.redirect("/login")
                    return
                session._mark_session_verified()

            first = await list_customers_xano(token, page=1, per_page=CLIENTES_POR_PAGINA)
            if not current():
                return
            customers = list(first["items"])
            pages = min(math.ceil(first["total"] / CLIENTES_POR_PAGINA), CLIENTES_PAGINAS_MAX)
            for number in range(2, pages + 1):
                page = await list_customers_xano(token, page=number, per_page=CLIENTES_POR_PAGINA)
                if not current():
                    return
                customers.extend(page["items"])
            resumo = resumir_clientes(customers)
            self.customers_total = first["total"]
            self.customers_active = resumo["ativos"]
            self.customers_inactive = resumo["inativos"]
            self.customers_blocked = resumo["bloqueados"]
            self.customers_active_pct = resumo["percentual_ativos"]
            self.customers_list = resumo["lista"]
            self.customers_note = f"{_plural(resumo['ativos'], 'ativo', 'ativos')} · {resumo['bloqueados']} com bloqueio manual"
            if first["total"] > len(customers):
                self.customers_note += f" · situação entre os {len(customers)} primeiros por nome"
            self.customers_status = "success"
        except XanoCustomerError as error:
            if error.status == 401 and current():
                session._clear_session()
                await session._sync_dashboard_session()
                yield rx.redirect("/login")
                return
            # Mensagens de XanoCustomerError são fixas no cliente, sem payload do Xano.
            fail(error.user_message)
        except Exception:
            fail("Não foi possível carregar os clientes. Tente atualizar.")

    @rx.event
    async def load_customers(self):
        async for update in self._load_customers():
            yield update
