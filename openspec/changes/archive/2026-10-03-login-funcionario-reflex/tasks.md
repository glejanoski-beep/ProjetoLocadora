## 1. Contrato de autenticação Xano

- [x] 1.1 Atualizar `auth/me` para devolver `is_active` junto com a identidade e validar o recurso com o validador XanoScript.
- [x] 1.2 Definir a URL base Xano por variável de ambiente do Reflex e verificar comportamento claro quando a configuração estiver ausente.

## 2. Login e sessão Reflex

- [x] 2.1 Criar a página pública `/login` com formulário de e-mail/senha, estados de carregamento e erro genérico; verificar a rota no app Reflex.
- [x] 2.2 Implementar evento de login que chama Xano, aceita somente contas ativas `member`/`admin` e consulta `auth/me`; testar credenciais válidas, inválidas e conta desativada.
- [x] 2.3 Guardar o bearer apenas em campo backend-only por sessão Reflex e expor ao cliente somente dados não secretos de identidade; verificar no delta/estado entregue ao cliente que o token não é serializado.
- [x] 2.4 Restaurar e revalidar a sessão usando `auth/me`; limpar a sessão e redirecionar ao login para token inválido, expirado, papel não permitido ou conta desativada.
- [x] 2.5 Implementar logout que limpa token e dados de sessão do backend Reflex e retorna à página pública de login.

## 3. Proteção e validação integrada

- [x] 3.1 Proteger páginas e eventos internos com as guardas Reflex, mantendo `/login` e `/redefinir-senha` públicas; testar acesso direto sem sessão e navegação autenticada.
- [x] 3.2 Executar compilação Reflex e testes dos fluxos de login, restauração, logout, mensagens genéricas e não exposição do bearer; registrar que autenticação/autorização continuam sendo impostas pelo Xano.
