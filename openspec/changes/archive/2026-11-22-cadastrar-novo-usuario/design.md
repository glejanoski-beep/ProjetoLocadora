# Design

## Context

A tela de usuários já possui listagem, filtros e alteração protegida. O projeto também já oferece recuperação de senha por magic link e alteração da senha em `auth/reset/update_password`. A criação não deve reutilizar o cadastro público `auth/signup`, pois esse endpoint cria obrigatoriamente uma senha e fixa o papel `member`.

## Goals / Non-Goals

**Goals:**

- Adicionar uma ação simples de criação na tela `/usuarios`.
- Criar uma conta ativa sem senha inicial e sem senha padrão compartilhada.
- Permitir escolher `admin` ou `member` somente para um administrador autenticado.
- Reutilizar o fluxo existente de recuperação de senha.
- Evitar mudanças em endpoints e scripts já funcionais.

**Non-Goals:**

- Alterar `auth/signup`, login, magic link ou redefinição de senha existentes.
- Alterar listagem, edição, desativação ou auditoria já implementadas.
- Cadastrar nome ou outros dados no formulário básico.
- Enviar convite por e-mail automaticamente nesta primeira etapa.
- Permitir que `member` crie ou promova contas.

## Decisions

- **Criar um novo endpoint administrativo específico.**
  - `POST /usuarios` receberá e-mail e papel.
  - O endpoint exigirá conta ativa `admin`.
  - A implementação criará a conta sem campo de senha e com situação ativa.
  - Alternativa considerada: adaptar `auth/signup`. Foi descartada porque o cadastro público fixa `member`, exige senha e não possui o contrato administrativo adequado.

- **Não definir senha padrão.**
  - A conta criada ficará sem senha até o usuário solicitar “Esqueci minha senha”.
  - O usuário receberá um link existente e escolherá sua própria senha.
  - Alternativa considerada: gerar senha provisória. Foi descartada para evitar distribuir credenciais por tela ou log.

- **Usar nome, e-mail e papel no modal.**
  - O nome será obrigatório e limitado a 200 caracteres.
  - O backend salvará o nome no campo `name` da tabela `user`.
  - O modal exibirá e-mail e papel já previstos, sem solicitar senha inicial.
  - Alternativa considerada: manter nome vazio. Foi descartada porque o campo é necessário para identificar corretamente o usuário na lista.

- **Criar estado local de modal na tela de usuários.**
  - Campos, erros, carregamento e confirmação serão controlados por `UsuariosState`.
  - O estado será fechado e descartado ao cancelar ou concluir.
  - A lista será atualizada ou recarregada após criação bem-sucedida.

- **Reutilizar os estilos globais claro/escuro.**
  - `usuarios.css` e `theme.css` definirão o modal e o botão sem alterar o layout existente.

## Risks / Trade-offs

- [Conta sem senha não consegue login direto] → O fluxo guiado deve orientar o usuário a usar “Esqueci minha senha”.
- [E-mail pode ser digitado com erro] → Validar formato no frontend e normalizar/minúsculas no backend.
- [E-mail já existe] → Buscar antes de inserir e retornar conflito sem criar duplicata.
- [Interface chama endpoint sem autorização] → A regra real permanece no backend por `enforce_role`.
- [Criar admin indevidamente] → Exigir `admin` ativo no endpoint e confirmar o papel permitido.
- [Nome vazio na lista] → Preservar a apresentação neutra já existente, por exemplo “(sem nome)”.

## Migration Plan

1. Acrescentar o endpoint administrativo isolado `POST /usuarios` no branch Xano `v1`.
2. Validar XanoScript e testar casos de administrador, membro, e-mail duplicado e papel inválido.
3. Acrescentar estado, modal e botão ao frontend sem alterar os handlers existentes.
4. Executar testes focados e compilação seca.
5. Validar desktop/celular nos dois temas.
6. Rollback remove o botão/modal e desativa a rota apenas em uma publicação posterior; os dados já criados não são removidos.
