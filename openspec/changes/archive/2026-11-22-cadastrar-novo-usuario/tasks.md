# Tasks

## 1. Endpoint administrativo de criação

- [x] 1.1 Criar o endpoint `POST /usuarios` no backend Xano, restrito a conta ativa `admin`, sem alterar os endpoints existentes.
- [x] 1.2 Validar nome obrigatório, e-mail normalizado, unicidade e papel `admin/member` antes da criação.
- [x] 1.3 Criar a conta ativa sem senha inicial e salvar o nome informado no campo `name`.
- [x] 1.4 Adicionar auditoria da criação sem armazenar senha ou dados de recuperação.
- [x] 1.5 Validar XanoScript e testar membro, e-mail duplicado, papel inválido e criação administrativa.

## 2. Estado e transporte frontend

- [x] 2.1 Adicionar ao estado da página os campos de nome, e-mail, papel, carregamento, erro e controle do modal.
- [x] 2.2 Implementar validação de nome obrigatório, e-mail válido e seleção somente entre administrador e funcionário.
- [x] 2.3 Implementar chamada protegida ao novo endpoint e atualizar a lista após sucesso.
- [x] 2.4 Garantir que erro, cancelamento e sessão expirada não criem registros.
- [x] 2.5 Adicionar testes focados do estado e do transporte da criação.

## 3. Interface da tela de usuários

- [x] 3.1 Adicionar o botão “Novo usuário” somente para administradores.
- [x] 3.2 Criar o modal com nome, e-mail, papel, cancelar e criar.
- [x] 3.3 Informar no modal que a primeira senha será definida pelo fluxo “Esqueci minha senha”.
- [x] 3.4 Aplicar estilos claro e escuro ao botão e ao modal sem alterar dimensões existentes.
- [x] 3.5 Validar foco pelo teclado, fechar pelo controle e cancelamento sem envio.

## 4. Verificação final

- [x] 4.1 Executar testes existentes e compilação seca do Reflex.
- [x] 4.2 Percorrer criação nos modos claro e escuro em desktop e celular.
- [x] 4.3 Confirmar que nenhum login, cadastro público, recuperação ou alteração existente foi alterado.
