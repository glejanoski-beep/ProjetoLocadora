# Design

## Context

Ver `proposal.md` para objetivo e `inspection.md` para evidências de 21/10/2026. A main `1a21fc8` já contém o PR #2 e cadastros dos colegas. Xano `v1` possui `customer`, `film`, `exemplar`, `user` e `event_log`, sem locação nem disponibilidade. O frontend concentra cadastros em `ProjetoLocadora.py`, com exemplo de estado/adaptador separado na dashboard.

## Goals / Non-Goals

**Goals:** implementar uma operação de retirada por exemplar com integridade no servidor e integração mínima na sessão Reflex existente. Proteger recursos existentes contra recriação por divergência de GUID.

**Non-Goals:** criar um motor financeiro, concluir o ciclo de devolução, redesenhar componentes, refatorar os cadastros dos colegas ou publicar recursos durante o planejamento. Os requisitos comportamentais estão nos dois deltas de spec.

## Decisions

### 1. Uma locação por exemplar, com retirada imediata

Proposta para revisão: retirada gerada pelo relógio do servidor; usuário escolhe data e hora de vencimento em Brasília, sem default comercial. O adaptador envia ISO 8601 com offset e o backend normaliza UTC. Não aceitar retirada retroativa/futura, duração implícita nem locação com vários exemplares. Isso reduz estados e evita precificar operações ainda sem política financeira. Valor do filme não gera cobrança nesta entrega.

### 2. Separar condição operacional de ocupação

Adicionar a `exemplar` condição `unverified|available|unavailable`, instante e responsável pela confirmação; para condição nula aplicar `unverified`. Não fazer backfill massivo para disponível. Nova operação administrativa no grupo de locações confirma a condição com motivo obrigatório; formulário administrativo simples na página de locações. Preservar `/exemplares` e seu contrato atual. Auditar sem incluir motivo livre no evento.

Disponível para seleção = condição `available` + filme `active` + nenhuma ocupação. Não materializar um segundo booleano de disponibilidade nem alterar `qtd_estoque`. Uma tabela própria de ocupação conserva unicidade por exemplar enquanto a tabela de locação conserva o histórico. Uma constraint única em toda a coluna exemplar da tabela de locação impediria novas locações históricas após futura devolução; por isso não é a estratégia escolhida.

### 3. Modelo aditivo e proteção concorrente

Recursos propostos, com nomes finais mantidos consistentes no APPLY:

| Recurso | Campos e garantias |
| --- | --- |
| `rental` | `id`, `customer_id`, `exemplar_id`, `registered_by`, `rented_at`, `due_at`, `status=active`, `operation_key`; índice único composto `(registered_by, operation_key)`; índices nas referências |
| `rental_occupancy` | `id`, `exemplar_id` único não nulo, `rental_id` único não nulo; referências validadas; só o fluxo de locação escreve |
| `exemplar` | condição operacional, confirmação por usuário e instante, motivo protegido; ausência de condição = não verificado |

Uma unidade transacional no banco deve abranger a criação de locação e ocupação. Proteger as leituras de cliente/filme/exemplar e sua elegibilidade com bloqueio de linha ou isolamento equivalente confirmado pelo Xano, em ordem determinística. A atualização administrativa da condição também deve respeitar a mesma proteção do exemplar. Tratar conflito de índice como conflito de operação, sem estado parcial. Consulta seguida de insert, transação sem proteção de leitura e bloqueio apenas no Reflex são insuficientes.

**Critério técnico de liberação:** documentar primitives oficiais de transação, bloqueio/isolamento, rollback e índices disponíveis no workspace; validar sintaxe e executar cenários de corrida e falha em ambiente autorizado. Se a garantia não puder ser comprovada, manter criação desabilitada e informar a limitação, sem substituir por uma proteção apenas aparente. Isso não autoriza criar sandbox ou branch Xano: o destino definido pelo projeto continua `v1`, e qualquer teste de escrita requer autorização específica.

### 4. API nova, sem alterar contratos dos colegas

Novo grupo `Locações`; obter `canonical` real somente quando criação remota for autorizada. Usar `auth="user"` e `Quick Start/enforce_role` no início das operações: mínimo `member` para locação/consulta e `admin` para condição operacional.

| Operação proposta | Contrato |
| --- | --- |
| `POST locacoes` | `customer_id`, `exemplar_id`, `due_at`, `operation_key`; retorna locação persistida e `audit_succeeded` |
| `GET locacoes/{id}` | confirmação protegida com referências, nomes/rótulos, datas, status e responsável, sem contatos/CPF |
| `GET locacoes/operacoes/{operation_key}` | consulta restrita ao par conta autenticada/chave, para reconciliação |
| `GET locacoes/exemplares-disponiveis` | paginação `page/per_page`, identificação do exemplar e filme, somente elegíveis |
| `PATCH locacoes/exemplares/{id}/condicao` | administrador informa condição e motivo; retorna condição confirmada e auditoria |

Chave UUID da tentativa lógica persistida apenas no estado privado de servidor. No POST, autenticar e procurar chave já confirmada antes de revalidar a disponibilidade: repetição idêntica retorna o registro original; conteúdo diferente conflita. A constraint composta resolve a corrida entre duas requisições da mesma operação. Depois de uma falha de unicidade, reconsultar a chave fora da transação abortada para reconciliar. Não repetir automaticamente um POST com chave nova após timeout.

Auditoria de criação usa `Quick Start/log_event`, `resource_type=rental` e identificador interno, sem payload ou dados pessoais. Auditoria posterior ao commit mantém o padrão de sucesso parcial existente, sem afirmar rollback. O registro conserva responsável e datas mesmo se o log falhar. Falha de auditoria de confirmação operacional segue a mesma distinção.

### 5. Reflex com integração pontual

Novos módulos `locacoes.py`, `locacoes_client.py` e `locacoes_state.py`, reutilizando o transporte e os padrões existentes sem mover cadastros. Rotas `/locacoes/nova` e `/locacoes/[rental_id]`, link no backoffice, formulário com cliente (nome e CPF mascarado), exemplar identificado e título, vencimento com indicação de Brasília, resumo e botão de confirmar. A seção administrativa de condição só aparece para `admin`; backend continua sendo a barreira efetiva.

Reutilizar a consulta paginada de clientes; disponibilidade vem da nova API, sem filtrar em memória como fonte de verdade. Não completar clientes ou exemplares com dados fictícios. Não acrescentar histórico financeiro ao detalhe do cliente ou indicadores à dashboard neste recorte.

Usar identidade/token privados e revisão de sessão nos moldes de `dashboard_state.py`; invalidar seleções, confirmação e requisições pendentes na troca de sessão. Uma resposta HTTP de sucesso com corpo inválido é resultado não confirmado pela interface e requer reconciliação. Preservar a chave da tentativa enquanto resultado for desconhecido. No logout limpar a chave da sessão; uma operação já recebida pelo backend pode concluir e será consultável pelo registro persistido após novo login.

Adicionar `XANO_RENTAL_API_URL` independente das URLs atuais, HTTPS validada e sem URL inventada. Falta de configuração informa módulo indisponível; não recorrer a outro grupo de API.

## Risks / Trade-offs

- [Disponibilidade física desconhecida] → confirmação explícita por administrador; nenhum exemplar legado liberado automaticamente.
- [Divergência do export] → mapear por nome e identidade remota antes de alterar recursos; não executar push global, sync destrutivo ou substituir export dos colegas.
- [Primitives de atomicidade não comprovadas] → critério técnico de liberação acima; testes estruturais locais não equivalem a teste de concorrência no Xano.
- [Mudança cadastral concorrente] → proteger cliente, filme e exemplar durante a validação/gravação; bloqueio posterior não deve apagar locação já confirmada.
- [Resposta perdida] → idempotência por conta/chave e consulta de reconciliação; sem novo POST cego.
- [Operação sem devolução] → exemplares alugados permanecem ocupados; comunicar essa limitação. A futura devolução encerrará locação e liberará ocupação na mesma transação, preservando `rental`.
- [Finanças ausentes] → não afirmar quitação nem bloqueio financeiro; futuras capacidades financeiras deverão integrar sua própria elegibilidade.
- [Cinco testes Windows sem encerramento local] → manter registro da limitação e validar transporte Windows no ambiente apropriado; não alterar esse transporte nesta change.

## Migration Plan

1. Após nova solicitação de APPLY, revalidar main e Xano `v1`, conferir implementação concorrente e manter branch nova isolada. Confirmar as três skills Reflex versionadas antes de editar código.
2. Implementar e validar localmente schemas, APIs, adaptador, estado e páginas, preservando GUIDs e contratos atuais; manter nenhuma gravação remota enquanto não autorizada.
3. Apresentar diff e inventário exato de recursos remotos a criar/alterar, estratégia de integridade e verificações. Solicitar autorização concreta para publicação e testes de escrita, sem incluir dados reais em testes destrutivos.
4. Quando autorizado, aplicar alterações aditivas e transacionais em `v1`, verificar índices, semântica de nulos e condição `unverified`; obter URL real; então habilitar interface. Não baixar nem criar registros durante o planejamento.
5. Se houver falha de implantação, desabilitar a operação e preservar tabelas, ocupações e histórico já gravados. Não apagar locações, remover constraints ou liberar exemplares para simular rollback.
