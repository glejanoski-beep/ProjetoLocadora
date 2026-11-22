# Design

## Context

A interface já utiliza variáveis CSS compartilhadas em parte das telas, mas mantém valores claros e escuros explícitos em várias folhas de estilo. A tela de login possui seu próprio conjunto de variáveis, enquanto as páginas autenticadas compartilham sobretudo as variáveis `--vd-*` de `dashboard.css`. O projeto não possui um seletor global de tema definido.

## Goals / Non-Goals

**Goals:**

- Centralizar a definição das duas paletas em uma camada visual transversal.
- Reutilizar os componentes Reflex existentes e adicionar somente o controle de tema necessário.
- Garantir que páginas e diálogos existentes respondam ao tema sem redefinir seu layout.
- Preservar o modo escuro atual como primeira opção.

**Non-Goals:**

- Redesenhar componentes, mudar espaçamentos, tipografia, hierarquia ou estrutura das páginas.
- Alterar lógica de autenticação, autorização, clientes, acervo, locações, multas, relatórios ou usuários.
- Criar integração com o Xano para salvar preferência.
- Adicionar temas além de claro e escuro.

## Decisions

- **Usar um atributo de tema no elemento raiz da aplicação e variáveis CSS por paleta.**
  - O atributo poderá ser aplicado a `data-theme="light"` ou `data-theme="dark"` no elemento raiz.
  - As variáveis existentes serão mantidas como contratos, com novos conjuntos para claro e escuro.
  - Alternativa considerada: aplicar classes a cada componente. Foi descartada porque exige edição espalhada e cria risco de superfícies esquecidas.

- **Representar o estado em `State` e persistir no navegador.**
  - A barra superior consumirá o estado global já existente no `State` principal.
  - A preferência será lida na inicialização e armazenada localmente no navegador.
  - Alternativa considerada: persistir no backend. Foi descartada por não haver necessidade funcional e por manter o tema como preferência local visual.

- **Adicionar o controle a `dashboard_topbar` junto às ações de usuário.**
  - O botão ficará entre "Sair" e o bloco de identificação do usuário, sem alterar a composição dos demais itens.
  - O modo atual será refletido por rótulo acessível e ícone compatível.
  - Alternativa considerada: adicionar o controle ao menu do avatar. Foi descartada por não atender à posição solicitada.

- **Converter cores fixas relevantes em tokens temáticos.**
  - As folhas `login.css`, `dashboard.css`, `acervo.css`, `exemplares.css`, `clientes.css`, `locacoes.css`, `multas.css`, `relatorios.css` e `usuarios.css` serão revisadas.
  - Cores de fundo, borda, texto, superfície e estado deverão usar variáveis.
  - Cores técnicas usadas apenas por gradientes decorativos estáveis poderão permanecer fora da paleta sem representar estado funcional.

- **Aplicar o mesmo tema aos diálogos nativos da interface.**
  - Como diálogos e confirmações estão dentro da árvore da aplicação, o atributo raiz deverá afetar seus componentes estilizados.
  - Qualquer folha específica de modal deverá referenciar os mesmos tokens, evitando cor fixa para conteúdo ou borda.

## Risks / Trade-offs

- [Existência de cores hexadecimal ou rgba fora das variáveis] → Auditar todas as folhas CSS e substituir somente as cores que representam superfície, texto, borda ou estado.
- [Paleta clara sem contraste suficiente] → Definir tokens claros com contraste verificável em texto principal, secundário, botão vermelho e estados de foco.
- [Preferência inválida armazenada no navegador] → Aceitar somente `light` ou `dark`; qualquer outro valor volta ao modo escuro.
- [Mudança visual em componentes externos de Reflex] → Ajustar o tema global disponível no aplicativo e os tokens CSS locais sem alterar a hierarquia dos componentes.
- [Ocultar elementos por dependência de cor] → Preservar texto, rótulo, borda ou ícone para estados como erro, sucesso e desabilitado.

## Migration Plan

1. Introduzir os tokens das paletas clara e escura sem remover os nomes já usados pelas telas.
2. Conectar o atributo raiz e o estado de tema.
3. Atualizar as folhas existentes para consumir os novos tokens e remover valores específicos conflitantes.
4. Validar todas as rotas, estados e diálogos nos dois modos.
5. Não há migração de dados ou API; rollback consiste em remover o estado visual e restaurar os valores escuros atuais.
