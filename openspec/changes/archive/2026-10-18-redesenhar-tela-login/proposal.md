# Proposal

## Why

A tela de login atual cumpre o fluxo de autenticação, mas não representa a identidade visual retrô da CINEBYTE LOCADORA nem oferece, na própria composição, os comportamentos de usabilidade e acessibilidade esperados para entrada e recuperação de acesso. Esta mudança cria uma experiência fiel à referência fornecida, responsiva e operável por teclado, sem enfraquecer a autenticação e a proteção de credenciais já existentes.

## What Changes

- Redesenhar exclusivamente a rota pública `/login` em Reflex com composição retrô inspirada em videogames, VHS e terminais dos anos 1980/1990.
- Introduzir painel central responsivo, textura sutil de fundo, cantoneiras, ícone de fita cassete, tipografia pixelada, cores e efeitos neon compatíveis com a referência visual.
- Estruturar cabeçalho, campos com ícones, formulário, ação principal, diálogo de recuperação e rodapé como componentes reutilizáveis.
- Permitir envio do login pelo botão ou pela tecla Enter, validar os campos obrigatórios em português e impedir submissões duplicadas enquanto a autenticação real estiver em andamento.
- Adicionar alternância acessível de visibilidade da senha sem registrar, persistir ou expor a credencial no estado público do cliente.
- Fazer o link “Esqueci minha senha” abrir um diálogo acessível na própria tela e reutilizar o fluxo real e a resposta genérica de recuperação do Xano; a rota pública `/recuperar-senha` permanece disponível para compatibilidade.
- Verificar a composição em desktop, celular e telas de pouca altura, sem corte, sobreposição ou rolagem horizontal.

## Capabilities

### New Capabilities

- `interface-login`: apresentação, responsividade, acessibilidade e interações da tela de acesso de funcionários da CINEBYTE LOCADORA.

### Modified Capabilities

Nenhuma. Os contratos existentes de `acesso-seguro` e `recuperacao-segura` serão preservados e reutilizados.

## Impact

- Frontend Reflex da rota `/login`, estado de interface associado e componentes visuais reutilizáveis.
- Folha de estilos e carregamento das fontes “Press Start 2P” e “Space Mono” a partir dos assets do frontend ou de folhas externas registradas no Reflex.
- Testes de estado, estrutura de componentes, acessibilidade, submissão, recuperação e responsividade visual.
- Nenhuma alteração nos endpoints, tabelas ou regras de autorização do Xano; a autenticação e a recuperação reais continuam usando os contratos existentes.
- Nenhuma mudança no domínio de locações, catálogo, exemplares ou clientes.
