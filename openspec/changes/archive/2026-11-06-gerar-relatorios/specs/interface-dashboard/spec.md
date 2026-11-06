# Spec Delta

## Purpose

Ativar "Relatórios" na navegação.

## MODIFIED Requirements

### Requirement: Barra superior identifica a marca, o usuário e a navegação

A barra SHALL exibir a marca "CINEBYTE LOCADORA" com o logotipo do login, a navegação horizontal e o usuário autenticado com nome real, perfil traduzido (`admin` → "Administrador", demais → "Funcionário") e iniciais calculadas a partir do primeiro e do último nome reais. Sem nome, SHALL ser exibido "Funcionário" e um ícone neutro. A ação "Sair" SHALL continuar encerrando a sessão e redirecionando para `/login`. A navegação SHALL conter links funcionais para:
- "Visão geral" (`/backoffice`);
- "Acervo" (`/filmes`);
- "Exemplares" (`/exemplares`);
- "Clientes" (`/clientes`);
- "Locações" (`/locacoes/nova`);
- "Multas" (`/multas`);
- "Relatórios" (`/relatorios`).

A página atual SHALL ser indicada por `aria-current`. Nenhum item SHALL aparecer como "Em breve".

#### Scenario: Item sem página implementada
- **WHEN** a navegação é exibida
- **THEN** todos os itens são links para páginas existentes, e nenhum aparece desabilitado ou com "Em breve"

#### Scenario: Acesso às multas
- **WHEN** a pessoa ativa "Multas"
- **THEN** a navegação abre `/multas`, e o item fica indicado como página atual

#### Scenario: Acesso aos relatórios
- **WHEN** a pessoa ativa "Relatórios"
- **THEN** a navegação abre `/relatorios`, e o item fica indicado como página atual
