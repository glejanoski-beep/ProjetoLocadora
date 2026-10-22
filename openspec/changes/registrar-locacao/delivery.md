# Entrega local — registrar-locacao

## Estado

Implementação local na branch `codex/registrar-locacao`, baseada em `origin/main` `1a21fc8`, após autorização de APPLY. O fetch, a busca de PRs e o export de leitura de `v1` foram repetidos: mesmos PRs #1/#2 e 40 recursos publicados, sem locação de colega identificada. Nenhum registro, API, tabela, variável ou configuração foi alterado remotamente. Não houve push Git, PR ou merge.

Frontend e transporte locais estão implementados e compilam. Backend tem schemas/stacks declarados e sintaxe validada; não foi executado no workspace. O módulo permanece sem URL real configurada e com escritas desabilitadas por padrão. A change não está concluída nem pronta para arquivamento: a homologação remota é pendente.

## Comportamento implementado localmente

- `/locacoes/nova`: consulta de clientes reais com nome e CPF mascarado, seleção identificada de exemplar disponível, vencimento em Brasília, resumo para confirmação e seção administrativa de condição.
- `/locacoes/[rental_id]`: consulta protegida da confirmação persistida.
- Autorização atual `member/admin`, cliente ativo e sem bloqueio manual, exemplar conferido, filme ativo, vencimento posterior à retirada gerada pelo servidor e status `active`.
- Estado privado da tentativa e seleção por IDs de resultados consultados; uma falha de comunicação preserva a chave e impede troca silenciosa do conteúdo. Consulta ou repetição usa a mesma chave. Respostas tardias são descartadas após transição de sessão.
- Auditoria posterior ao commit, com sucesso parcial explícito se o log não for confirmado. Repetição não cria outro evento presumido: consulta o evento existente. O histórico da locação guarda rótulos de cliente/exemplar/filme no instante da retirada, além das referências, para evitar que edições cadastrais reescrevam a confirmação histórica.
- Sem devolução, cobrança, multa, cancelamento, exclusão, liberação de ocupação ou novos indicadores de dashboard. Nenhuma modernização visual dos módulos existentes.

## Evidência técnica de integridade

Fontes oficiais consultadas:

- [Get Record](https://docs.xano.com/the-function-stack/functions/database-requests/get-record): bloqueio dentro de transação impede alteração concorrente do registro por outros stacks até a liberação.
- [Database Transaction](https://docs.xano.com/the-function-stack/functions/database-requests/database-transaction): operações de banco formam uma unidade; somente erros de operações de banco são considerados na determinação do rollback. Por isso todas as preconditions e transformações de elegibilidade antecedem a primeira inserção, e a falha injetada na homologação será uma violação real de índice na segunda inserção.
- Xano Developer MCP, documentação 2.7.1, tópicos `database`, `tables`, `syntax` e filtros de datas/regex. O exemplo com `isolation="serializable"` fornecido por essa documentação foi recusado pelo validador; não está no código. A implementação usa `db.get ... lock=true`, aceito pelo validador e documentado na página oficial acima.

Na stack local, a ordem é conta → cliente → exemplar → filme, com bloqueios antes da validação/gravação. O bloqueio de conta também serializa chamadas da mesma conta/chave. `rental` tem índice único por `(registered_by, operation_key)`; `rental_occupancy` tem índices únicos por exemplar e por locação. As duas inserções estão na mesma transação. O catch fica fora da transação, descarta variáveis de resultado abortado e consulta a chave novamente antes de responder. Não há alteração de condição do exemplar nem evento de auditoria dentro da unidade de inserção.

Essas evidências fundamentam o desenho e a sintaxe. **Não comprovam** índices aplicados, funcionamento de locks/joins no plano contratado, rollback, coerções de schema, nomes de erros HTTP ou concorrência real no Xano. A criação não deve ser liberada para uso operacional antes da homologação.

## Arquivos e inventário remoto proposto

| Ação futura em `v1` | Recursos locais correspondentes |
| --- | --- |
| Criar tabela de histórico | `xano/xano/table/rental.xs` |
| Criar tabela de ocupação exclusiva | `xano/xano/table/rental_occupancy.xs` |
| Acrescentar quatro campos à tabela existente | `xano/xano/table/exemplar.xs`: condição, instante, responsável e motivo |
| Criar grupo `Locações`, sem identidade inventada | `xano/xano/api/locacoes/locacoes.xs` |
| Criar cinco endpoints | POST criação, GET detalhe, GET reconciliação, GET elegíveis, PATCH condição em `xano/xano/api/locacoes/` |
| Criar função de validação de vencimento | `xano/xano/function/locacoes/parse_due_at.xs` |
| Criar variável Xano com valor inicial textual `false` | `XANO_RENTAL_WRITES_ENABLED` |
| Recurso opcional e temporário para homologação de rollback | `tests/xano_validation/rollback_POST.xs`, fora do diretório normal de implantação, protegido por `admin` e variável `XANO_RENTAL_ROLLBACK_TEST_ENABLED` |

O GUID local de `exemplar` foi reconciliado com o GUID real repetidamente consultado no export: `8vzM3sxxeTHrTxaJGPUfK1JI8ZA`. Não foi criada outra tabela remota. Preservar esse recurso, seus IDs e os três campos originais. Os novos recursos não receberam `canonical` ou GUID fictícios. Não executar push integral, `sync --delete`, backfill de disponibilidade ou import de registros.

Integração Reflex: quatro módulos novos (`locacoes.py`, `locacoes_client.py`, `locacoes_state.py`, `locacoes_ui.py`), configuração própria e integração pontual no módulo principal. Cadastros, transporte existente, contratos públicos e change da dashboard foram preservados.

## Configuração futura

No `.env` local, somente após obter a base real do grupo criado:

```dotenv
# Preencher com a base HTTPS REAL do grupo Locações, sem /locacoes no final.
XANO_RENTAL_API_URL=
# Manter false durante preparação e até a homologação.
XANO_RENTAL_WRITES_ENABLED=false
```

Ausência ou URL inválida informa indisponibilidade, sem usar outro grupo como fallback. A variável de escrita existe independentemente no frontend e no Xano; ambas precisam de liberação deliberada. Leituras e reconciliação continuam possíveis quando as escritas forem desabilitadas. Criar a variável Xano explicitamente antes da publicação; ausência não deve ser usada como mecanismo implícito de configuração.

## Plano executável de homologação, ainda não executado

`python -m scripts.verify_rental_integrity` mostra o plano sem abrir conexão. `--help` descreve os argumentos. Somente `--execute` faz chamadas de escrita. Tokens são lidos de `LOCADORA_VALIDATION_TOKEN_A` e, para corrida entre contas, `LOCADORA_VALIDATION_TOKEN_B`; nunca passá-los na linha de comando ou registrar seus valores. A configuração real dos grupos existentes também é necessária para revalidar contas/clientes. O script só aceita IDs indicados pelo operador, verifica dados reais antes do envio e não cria clientes, filmes ou exemplares. As chaves de correlação são informadas antes do envio para permitir reconciliação se a conexão cair.

1. Com autorização específica, implantar somente os recursos listados, inicialmente com gates `false`. Confirmar schemas/índices no banco e ausência de backfill. Obter a URL real; manter interface operacional desabilitada.
2. Escolher contas internas ativas e cliente/exemplares reais destinados à operação ou a um ambiente de validação explicitamente autorizado. Não criar cadastros fictícios na base compartilhada. Os cenários de sucesso registram retiradas reais e não fazem limpeza destrutiva. Cada cenário exige exemplar disponível próprio.
3. Em janela controlada de validação, habilitar o gate Xano e apenas o ambiente do executor. Executar cenário `distinct-keys` com duas contas diferentes e mesmo exemplar: exigir uma confirmação e um conflito; conferir no banco exatamente uma locação e uma ocupação. Executar `same-key` com a mesma conta/chave: exigir o mesmo ID nas duas respostas, um único histórico e ocupação.
4. Publicar o harness temporário somente se autorizado, habilitar sua variável própria apenas na janela do teste e usar `--scenario rollback`. Ele exige administrador, um exemplar disponível e o ID de uma locação ativa de outro exemplar. Após criar a primeira linha, tenta criar ocupação sobre exemplar já ocupado e bloqueado: a violação real do índice deve abortar as duas inserções. Conferir no request history que a falha ocorreu no segundo insert por esse índice, consultar a chave e verificar no banco ausência de locação/ocupação nova e preservação da ocupação anterior. Erro HTTP genérico sozinho não prova rollback. Desabilitar a variável do harness e retirar somente a API temporária ao finalizar; nunca apagar registros para simular sucesso.
5. Executar a matriz abaixo e documentar requisições/resultados minimizados. Se houver inconsistência, desabilitar gates, preservar o histórico e planejar correção auditada; não liberar exemplares ou remover constraints para esconder falha.
6. Depois da homologação, registrar evidência e liberar a interface explicitamente. Sem aprovação, manter ambos os gates `false`. Arquivar somente após concluir tarefas remotas.

| Verificação real pendente | Resultado exigido |
| --- | --- |
| Sem token, token antigo de conta inativa, papel desconhecido | Sem consulta de dados protegidos ou efeito operacional |
| `member` tenta PATCH condição | Recusa antes da gravação |
| Cliente inexistente/inativo/bloqueado, filme inativo, exemplar ausente/não conferido/ocupado | Sem locação/ocupação nova |
| Vencimento sem offset, relativo, calendário impossível ou não posterior à retirada | Sem gravação |
| Mudança cadastral/condição concorrente | Ordem serializável pelas linhas bloqueadas, sem validar estado obsoleto |
| Resposta perdida após commit | Consulta/repetição retorna a locação original, sem duplicação |
| Auditoria falha após commit | Gravação preservada e auditoria não confirmada explícita |

## Validação local

- Python 3.11 e Reflex **0.9.11**, correspondente ao `requirements.txt`. Ambiente existente foi reutilizado por link `.venv`, sem reinstalar pacotes nem alterar o checkout original.
- **175 testes** na descoberta principal, incluindo **48 novos** de locação (domínio/configuração/transporte, estado real Reflex e contratos estáticos Xano).
- **52 testes** adicionais dos cadastros aprovados; cinco métodos específicos de Windows excluídos conforme limitação já registrada em `inspection.md`. Total confirmado: **227 testes**; não se declara aprovação desses cinco.
- `reflex compile --dry`: compilação concluída. Sem servidor iniciado ou teste visual de navegador. A formatação automática de `reflex.lock/package.json` produzida pelo compilador foi revertida para manter o diff focado.
- Validador XanoScript: os dez arquivos de produção novos/alterados e o harness temporário são sintaticamente válidos. Validação não executa o banco.
- Verificação do script de homologação executada somente no modo padrão sem conexão; não foram usados tokens de validação, dados reais ou escrita remota nesta entrega.
- `openspec validate registrar-locacao --strict` e revisão de whitespace/diff devem passar antes do commit local.

## Pendências e limite de autorização

As tarefas de backend com verificação comportamental permanecem abertas até a execução no Xano; o código local correspondente já foi entregue. A tarefa 4.2 requer autorização específica para publicação e testes de escrita. A autorização de APPLY concedida nesta conversa permite esta implementação local; não foi interpretada como autorização de migração ou de locações reais. O estado OpenSpec deve refletir essa distinção.
