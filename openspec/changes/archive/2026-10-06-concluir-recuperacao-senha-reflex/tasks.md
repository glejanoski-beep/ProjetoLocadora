## 1. Configuração e cliente Xano

- [x] 1.1 Adicionar configuração local `FRONTEND_BASE_URL=http://localhost:3000` sem substituir `XANO_API_URL`, e verificar que cada variável mantém uma finalidade única.
- [x] 1.2 Implementar no cliente Xano chamadas para solicitar recuperação, consumir magic link e atualizar senha; verificar respostas genéricas e ausência de token em logs.
- [x] 1.3 Ajustar o endpoint Xano de solicitação para montar o link com a base frontend local e validar o XanoScript.

## 2. Tela de solicitação

- [x] 2.1 Criar a rota pública `/recuperar-senha` com campo de e-mail, validação, carregamento e mensagem genérica; verificar compilação e navegação local.
- [x] 2.2 Ligar o formulário ao endpoint de solicitação e tratar respostas de e-mail existente, inexistente, inválido e erro de rede sem enumerar contas.

## 3. Tela de redefinição

- [x] 3.1 Ler `magic_token` e `email` da URL `/redefinir-senha` e consumir o magic link no carregamento; verificar token válido, ausente, expirado e usado.
- [x] 3.2 Guardar o token de autenticação somente em estado backend-only e manter fora de Vars públicas, cookies e storage do navegador; verificar a estrutura do State Reflex.
- [x] 3.3 Criar formulário de nova senha e confirmação com validação local; impedir submissão de senhas divergentes ou inválidas.
- [x] 3.4 Enviar a nova senha ao endpoint protegido, limpar o token após sucesso/falha e exibir confirmação ou mensagem genérica; verificar retorno para `/login`.

## 4. Validação integrada

- [x] 4.1 Compilar o Reflex, executar testes automatizados e validar que `/login`, `/recuperar-senha` e `/redefinir-senha` renderizam no ambiente local.
- [x] 4.2 Executar o fluxo real em Xano com e-mail existente: solicitar link, abrir a rota local, consumir o token, alterar a senha e confirmar que o reuso é rejeitado.
