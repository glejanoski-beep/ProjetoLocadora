# Design: Recuperação de senha segura

## Decisões

- Manter uma resposta pública genérica para qualquer e-mail.
- Continuar usando `$env.$api_baseurl` e o serviço de e-mail configurado, salvo decisão posterior.
- Ocultar o resultado de busca de usuário no endpoint público.
- Consumir o token com atualização condicional ao estado ainda não usado, ou mecanismo equivalente suportado pelo Xano.
- Retornar internamente apenas dados necessários ao fluxo, nunca token em resposta pública ou log.
- Substituir a rota de demonstração por contrato explícito do frontend Reflex quando a tela for definida.

## Validação

Testar e-mails existentes e inexistentes, tokens expirados, tokens usados e duas requisições concorrentes no ambiente Xano.
