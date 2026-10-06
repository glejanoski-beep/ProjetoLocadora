## Context

A capability `recuperacao-segura` já define respostas genéricas, uso único do magic link e rota `/redefinir-senha`, mas o frontend Reflex atual apenas exibe uma mensagem. Os endpoints Xano existentes são `GET /reset/request-reset-link`, `POST /reset/magic-link-login` e `POST /reset/update_password`.

## Goals / Non-Goals

**Goals:**
- Entregar as telas Reflex de solicitação e conclusão da recuperação.
- Usar `http://localhost:3000` como base do frontend neste ambiente de desenvolvimento.
- Consumir o magic link ao carregar `/redefinir-senha`.
- Manter tokens Xano de recuperação/autenticação somente em campos backend-only do State.
- Validar erros de rede, token inválido, expiração, reuso e validação de senha sem revelar dados sensíveis.

**Non-Goals:**
- Definir hostname de produção.
- Criar endpoint atômico novo no Xano.
- Alterar a política já implementada de enumeração e uso único.
- Integrar provedor externo de identidade ou armazenamento Redis.

## Decisions

### URL do frontend

Usar a variável de ambiente de frontend com valor `http://localhost:3000` no ambiente local. O endpoint Xano de solicitação deverá montar o link com uma variável de configuração de frontend, separada de `$env.$api_baseurl`, para não apontar para a API.

Nesta Change, a configuração alvo é local; valores de produção ficam para uma mudança de deployment.

### Consumo do magic link no carregamento

A tela lê `magic_token` e `email` dos parâmetros da rota e chama `reset/magic-link-login` no carregamento. O token de acesso retornado é armazenado somente em campo privado do State Reflex e nunca é exposto como Var, cookie ou storage do navegador.

A decisão aceita explicitamente que o magic link seja consumido antes de a pessoa salvar a nova senha. Se a pessoa fechar a página depois do consumo, deverá solicitar outro link.

### Atualização da senha

Depois do consumo bem-sucedido, o formulário envia `password` e `confirm_password` para `reset/update_password` usando o token privado da sessão. Após sucesso, o token e os dados da recuperação são limpos e a interface oferece retorno ao login.

### Tratamento de URL e mensagens

Parâmetros ausentes, erros de rede e falhas Xano serão apresentados como estado genérico de link inválido ou indisponível. O token não será incluído em mensagens, logs do frontend ou dados públicos do State.

## Risks / Trade-offs

- **O token é consumido antes da senha ser salva** -> documentar a consequência e permitir solicitar outro link; não tentar reutilizar token após falha.
- **A variável de frontend não existe no Xano atual** -> criar/configurar uma variável de ambiente específica para frontend no ambiente local e validar o link gerado antes de testar a tela.
- **A sessão backend-only do Reflex é perdida ao reiniciar o processo** -> pedir novo link/login; não persistir token em armazenamento acessível ao navegador.
- **Endpoint Xano usa senha protegida por token temporário** -> limpar o token após sucesso, falha ou logout e nunca exibir seu conteúdo.
