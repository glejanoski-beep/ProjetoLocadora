# Proposal

## Why

A interface atual possui um tema escuro consistente, mas não oferece uma alternativa visual clara para ambientes com muita luminosidade ou preferências pessoais de contraste. Uma troca de tema deve ampliar a usabilidade sem alterar a composição, os dados, as regras de acesso ou os fluxos existentes.

## What Changes

- Adicionar um botão simples na barra superior autenticada, posicionado entre a ação "Sair" e o bloco do usuário.
- Permitir alternar entre os modos escuro e claro.
- Preservar o modo escuro atual como padrão e aplicar uma nova paleta clara, sem alterar dimensões, posições, tipografia, espaçamentos ou hierarquia visual.
- Aplicar o tema a todas as páginas autenticadas, à tela de login, aos formulários, confirmações e diálogos abertos durante o uso.
- Manter a preferência de tema da sessão ou do navegador e reutilizá-la ao navegar entre páginas.
- Atualizar os componentes visuais existentes para consumir tokens de cor centralizados; não alterar contratos Xano, regras de negócio, autenticação ou autorização.

## Capabilities

### New Capabilities

- `interface-temas`: Define o controle de alternância de tema e a aplicação verificável das paletas clara e escura em toda a interface Reflex.

### Modified Capabilities

- Nenhuma.

## Impact

- Frontend Reflex: estado global da interface, barra superior compartilhada, tela de login e folhas de estilo das páginas e diálogos.
- Persistência local do navegador para a preferência de tema; sem impacto em APIs ou banco de dados.
- Segurança: nenhuma mudança em autenticação ou autorização; o tema permanece uma preferência exclusivamente visual.
- Fora do escopo: redesign, novas telas, alterações de layout, navegação, comportamento funcional, backend Xano e XanoScript.
