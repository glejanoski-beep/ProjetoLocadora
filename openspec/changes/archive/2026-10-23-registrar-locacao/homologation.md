# Homologação real — 23/10/2026

## Escopo e privacidade

Executada no workspace já implantado, branch `v1`, fonte `live`, após autorização
de testes de escrita e indicação explícita de cliente, três exemplares, vencimento
(30/10/2026 às 18h de Brasília) e duas contas administradoras. O operador autorizou
a geração de tokens internos do executor Xano; credenciais foram mantidas privadas,
sem inclusão no Git ou neste relatório. Nenhum cliente, filme, exemplar ou usuário
fictício foi criado. Este relatório público contém somente resultados agregados.

## Execução e resultados

| Verificação | Evidência real |
| --- | --- |
| Gate de escrita fechado | PATCH autenticado recusado com HTTP 403 antes da janela |
| Exemplares sem conferência | POST recusado com HTTP 400; consulta inicial sem elegíveis |
| Confirmação administrativa | Três condições confirmadas pela API, com auditoria bem-sucedida; três elegíveis |
| Primeira corrida entre contas | Exatamente uma locação/ocupação; detectado defeito de resposta HTTP no perdedor |
| Correção e nova corrida | Quatro POSTs simultâneos, duas contas e uma chave repetida por conta: dois sucessos com o mesmo ID e dois conflitos HTTP 400 |
| Resposta perdida/repetição | Reenvio e reconciliação retornam o registro original, sem nova locação ou evento |
| Conteúdo diferente com mesma chave | HTTP 400 com conflito, sem mudança do vencimento |
| Escopo da chave | Outra conta recebe HTTP 404 na reconciliação da chave alheia |
| Falha na segunda inserção | Depurador mostrou primeira linha inserida e `Duplicate record detected` na ocupação; após rollback, chave ausente e exemplar livre |
| Banco após rollback HTTP e depurado | Duas locações, duas ocupações; nenhuma linha para o exemplar do rollback |
| Cliente/exemplar inexistente | HTTP 400 sem nova linha |
| Vencimento passado, sem offset ou impossível | HTTP 400 sem nova linha |
| Cliente e filme inativos | HTTP 400; estados restaurados após ensaio |
| Member na operação administrativa | HTTP 403; o mesmo papel consegue reconciliar sua própria locação |
| Token emitido antes de inativação | HTTP 403 após inativação; conta restaurada ao papel e estado originais |
| Bloqueio e inativação concorrentes | Cliente previamente bloqueado permanece inelegível durante inativação simultânea ao POST; HTTP 400 |
| Condição concorrente | Mudança entre condições inelegíveis simultânea ao POST; HTTP 400; condição conferida restaurada ao final |
| Sem token/token inválido | HTTP 401 |
| Paginação inválida | HTTP 400 |
| Consulta por ID | HTTP 200; exatamente os 11 campos da allowlist, aceitos pelo validador real do frontend |
| Campos protegidos em replay | Responsável, retirada, status e histórico originais preservados apesar de campos extras enviados |
| Auditoria e contagens finais | Um evento `create_rental` por locação, apesar de replays e concorrência |

## Defeito corrigido durante a homologação

O runtime Xano encerrou `throw` customizado com HTTP 200 e corpo `{payload,
statement}`, em vez do contrato esperado de conflito. O executor detectou o corpo fora do contrato e interrompeu o teste; nenhuma segunda
retirada foi criada. O adaptador trata esse corpo como resultado desconhecido. A janela foi fechada, o banco
foi conferido e o erro foi corrigido para `precondition` com `inputerror` nos conflitos
e `standard` nas falhas inesperadas. A classificação do adaptador já reconhece as
mensagens de conflito em HTTP de erro. Apenas POST de produção e harness temporário
foram atualizados. Um teste estrutural de regressão passou a rejeitar `throw` customizado.

O teste foi retomado com o segundo exemplar; o primeiro registro foi preservado.
A corrida combinada posterior comprovou respostas e persistência corretas, sem
necessidade de excluir, liberar ou recriar a locação original.

## Limpeza e limites

A API temporária de rollback foi excluída pelo ID exato; consulta posterior retornou
HTTP 404. Gates de escrita e rollback foram restaurados a `false` ao encerrar a janela.
Cliente, filme e conta utilizados em estados temporários foram restaurados. Os três
exemplares mantêm a condição conferida; dois permanecem ocupados por locações reais,
com vencimento indicado pelo operador. O terceiro permanece sem ocupação.

Os executores locais tiveram interrupções de descoberta/importação/variável e uma
recusa de restauração; a reexecução informou explicitamente o campo opcional; as verificações interrompidas
foram corrigidas e reexecutadas, e os estados finais foram conferidos diretamente.
Uma primeira validação de detalhe recebeu corpo não conforme após a sequência;
a nova leitura HTTP 200 das duas confirmações passou pela allowlist. Não se conta
nenhuma execução interrompida como aprovação.

Foram aprovados 176 testes principais e 52 adicionais (228 no total). Cinco testes
específicos de Windows permanecem pendentes de ambiente adequado. Falha da auditoria
após commit foi coberta localmente; não se provocou indisponibilidade do serviço
compartilhado na base real. As corridas de bloqueio/condição cobriram transições que
permanecem inelegíveis, sem gerar uma terceira retirada apenas para testar ordenação.

Não há devolução, cancelamento ou liberação automática de ocupação neste incremento.
A interface é Reflex local; este trabalho não cria hospedagem externa.
