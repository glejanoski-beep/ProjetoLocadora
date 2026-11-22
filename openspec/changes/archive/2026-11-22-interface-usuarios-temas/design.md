# Design

## Context

A tela `/usuarios` já usa `UsuariosState`, `usuarios_ui.py`, `usuarios.css` e componentes reutilizados de clientes e locações. A mudança será restrita à apresentação da lista e dos modais; a consulta ao Xano e os handlers existentes não serão substituídos.

## Goals / Non-Goals

**Goals:**

- Manter os estados, filtros, permissões e ações existentes da tela.
- Garantir contraste de todos os textos e controles nos modos claro e escuro.
- Estilizar o modal de alteração e a confirmação de desativação como superfícies claras no tema claro.
- Reutilizar os tokens globais de tema já existentes.

**Non-Goals:**

- Criar cadastro de usuários, exclusão de contas ou novos endpoints.
- Alterar papel, situação, motivo, auditoria ou regras de envio.
- Redesenhar a estrutura ou alterar dimensões da lista e do modal.

## Decisions

- **Usar os tokens CSS existentes para toda a tela.**
  - A paleta clara já definida em `assets/theme.css` será reaproveitada.
  - Nenhuma cor fixa clara será usada em texto sobre superfícies claras.

- **Aplicar estilos apenas às classes da tela de usuários e às classes compartilhadas usadas nela.**
  - `usuarios.css` receberá ajustes específicos para filtros e estado próprio.
  - `theme.css` receberá overrides limitados ao modo claro para classes usadas pela lista e pelo modal.

- **Preservar a implementação funcional atual.**
  - `UsuariosState.open_page`, `capture_search`, `set_status_filter`, `open_edit`, `submit_edit` e `set_edit_open` não serão alterados.
  - Os componentes continuarão consumindo os mesmos handlers e valores observáveis.

- **Tratar botão neutro e ação destrutiva como estados visuais distintos.**
  - Cancelar, fechar e voltar usam superfície neutra clara no modo claro.
  - Confirmar desativação e ações principais usam vermelho com texto branco.

## Risks / Trade-offs

- [Seletor amplo afetar outras telas] → Limitar os novos overrides às classes `vitrine-usuarios` e aos componentes compartilhados quando usados dentro da página.
- [Texto claro continuar fixo em classe específica] → Auditar as classes da página e substituir/overridear por variável temática.
- [Foco branco em fundo claro] → Usar vermelho ou contraste escuro como contorno de foco no modo claro.
- [Alteração visual aparentar mudança funcional] → Preservar todos os handlers, estados e permissões existentes.

## Migration Plan

1. Ajustar os estilos do tema claro da tela e dos modais.
2. Validar a listagem e os estados `admin`, `member`, loading, erro e vazio.
3. Validar alteração, cancelamento e confirmação de desativação nos dois temas.
4. Executar testes e compilação seca.
5. Caso necessário, remover apenas os overrides da tela; não há migração de dados ou API.
