# Tasks

## 1. Modelo e configuração segura

- [x] 1.1 Criar tabela de vínculo entre cliente da locadora e cliente Asaas, com índice único e campos mínimos, e verificar que não há duplicação em repetição de criação.
- [x] 1.2 Criar tabela de tentativa de Checkout com multa, cliente, usuário, chave de operação, `checkout_id`, valor em centavos, estado e último evento, e verificar os índices de idempotência e reconciliação.
- [x] 1.3 Definir variáveis de ambiente para API key, segredo do webhook, URL/base do Asaas e habilitação da feature sem incluir valores reais em arquivos versionados; verificar que os segredos não aparecem em respostas, logs ou exemplos.

## 2. Integração Xano com Asaas

- [x] 2.1 Implementar função backend para localizar ou criar automaticamente o cliente Asaas de forma idempotente, usando dados mínimos do cliente, e cobrir timeout e repetição sem cliente duplicado.
- [x] 2.2 Implementar função backend para criar Checkout Asaas de saldo integral da multa aberta, com descrição e referência local, e verificar que a multa não é quitada na criação.
- [x] 2.3 Implementar endpoint autenticado para iniciar cobrança, validando sessão, papel, trava de escrita, estado da multa, saldo e chave idempotente antes da chamada externa; verificar recusas sem efeitos.
- [x] 2.4 Persistir a reserva `unknown` antes do POST, bloquear novo POST ao repetir a mesma chave e permitir associação administrativa auditada com base na `externalReference` e no valor conferidos no painel Asaas; confirmar pagamento somente pelo webhook.
- [x] 2.5 Implementar endpoint público Xano de webhook com validação do segredo Asaas, sanitização de erros e auditoria mínima; verificar que eventos inválidos não alteram dados.
- [x] 2.6 Implementar máquina de estados para `CREATED`, `PAID`, `CANCELED` e `EXPIRED`, processando `event.id` idempotentemente e ignorando regressões; verificar duplicidade e eventos fora de ordem.
- [x] 2.7 Ao confirmar `PAID`, criar ou localizar o único pagamento interno `credit_card`, atualizar saldo/status da multa dentro da transação e preservar histórico; verificar confirmação repetida e saldo insuficiente.
- [x] 2.8 Processar estorno externo válido sem apagar ou alterar o valor histórico do pagamento, usando o fluxo administrativo de reversão compatível; verificar saldo e auditoria após estorno.

## 3. Contratos e frontend Reflex

- [x] 3.1 Atualizar contratos Python para iniciar, consultar e representar a tentativa de Checkout sem expor credenciais ou payload bruto; verificar validação de estados e erros sanitizados.
- [x] 3.2 Adicionar no detalhe da multa a ação de cobrar o saldo integral via cartão, com confirmação explícita, bloqueio de envio duplicado e abertura do link hospedado pelo Asaas; verificar que a interface não captura dados do cartão.
- [x] 3.3 Exibir estados pendente, confirmado, recusado, cancelado e expirado, mantendo o saldo até confirmação; verificar logout, troca de sessão, timeout e resposta desconhecida.
- [x] 3.4 Atualizar histórico e relatórios para distinguir pagamento manual de cartão confirmado via Asaas sem alterar a semântica dos pagamentos existentes; verificar agregações e ausência de dados sensíveis.

## 4. Verificação e homologação

- [x] 4.1 Adicionar testes de contrato Xano para autorização, saldo integral, idempotência, concorrência, credencial ausente, webhook inválido, duplicado e fora de ordem; verificar execução com o comando de testes do projeto.
- [x] 4.2 Adicionar testes de cliente/estado/UI para confirmação, recusa, expiração, timeout e repetição da mesma operação; verificar que nenhum estado pendente aparece como quitado.
- [ ] 4.3 Configurar webhook e Checkout no Sandbox do Asaas, executar uma cobrança de teste e registrar evidência de criação, evento `PAID`, reconciliação administrativa de resultado ambíguo e eventual cancelamento, sem expor a chave.
- [x] 4.4 Validar a change com `openspec validate cobrar-cartao-asaas --strict` e revisar documentação de configuração, rollback e permissões antes da publicação.
