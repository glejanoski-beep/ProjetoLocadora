# Proposal

## Why

A tela de usuários já possui lista, filtros e diálogo de alteração, mas os controles e rótulos ainda precisam ter apresentação visual consistente nos modos claro e escuro. Isso deve melhorar a leitura e o uso sem criar funcionalidades administrativas fora do fluxo existente.

## What Changes

- Ajustar os controles da rota `/usuarios` para os modos claro e escuro, incluindo busca, filtros, atualização, linhas de conta e ações secundárias.
- Ajustar o modal de alteração de conta e o modal de confirmação de desativação, com fundo, bordas, ícones, rótulos, campos e botões legíveis em ambos os temas.
- Aplicar contraste adequado aos títulos, nomes, e-mails, datas, status, papel da conta e mensagens da tela.
- Preservar o comportamento atual: somente `admin` acessa a gestão, a própria conta não oferece alteração, a desativação exige confirmação e o backend continua responsável pela autorização.
- Não alterar endpoints, dados persistidos, permissões, validações, criação de contas ou exclusão de contas.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `interface-usuarios`: A apresentação da tela de usuários, seus controles e seu modal passa a ser definida também para os temas claro e escuro.

## Impact

- Frontend Reflex: componentes da página de usuários e folhas de estilo compartilhadas.
- Interface: barra de busca, filtros, linhas de conta, botão Atualizar, modal de alteração e confirmação de desativação.
- Sem impacto em Xano, XanoScript, cadastro de contas, autenticação ou autorização.
