# Proposal

## Why

A tela de usuários permite consultar, alterar o papel e desativar contas, mas não oferece uma ação simples para criar uma nova conta interna. A criação atual deve evitar senha inicial compartilhada: a conta será criada sem senha e o usuário definirá a própria senha pelo fluxo existente de “Esqueci minha senha”.

## What Changes

- Adicionar na tela `/usuarios` um botão simples “Novo usuário”, restrito a administradores.
- Abrir um modal com somente os dados básicos:
  - nome;
  - e-mail;
  - papel (`Administrador` ou `Funcionário`).
- Criar a conta sem senha inicial; o usuário deverá usar “Esqueci minha senha” na tela de login para receber o magic link e definir a senha.
- Criar a conta com situação ativa por padrão.
- Impedir e-mail duplicado e recusar dados inválidos no frontend e no backend.
- Incluir a nova conta imediatamente na lista após o sucesso.
- Manter fundos, textos, rótulos, campos, fechar/cancelar e confirmar legíveis nos modos claro e escuro.
- Preservar a autorização administrativa no backend; a interface não substitui esta proteção.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `gestao-usuarios`: acrescenta a criação administrativa de contas sem senha inicial.
- `interface-usuarios`: acrescenta o botão, o modal básico e os estados de criação.

## Impact

- Frontend Reflex: estado da página de usuários, modal de criação, validação básica e atualização da lista.
- Backend Xano/XanoScript: adicionar apenas o endpoint administrativo de criação `POST /usuarios`, evitando alterações nos endpoints existentes de login, recuperação e alteração.
- Autenticação: reutiliza o fluxo existente de magic link e redefinição de senha.
- Segurança: somente `admin` ativo cria contas; o backend valida e-mail duplicado e papel permitido; nenhuma senha padrão é compartilhada.
- Fora do escopo: exclusão de usuários, dados cadastrais adicionais, convites por e-mail automático e novas telas de autenticação.
