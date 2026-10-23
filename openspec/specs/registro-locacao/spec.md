# Registro de locação

## Purpose

Permitir registrar a retirada de um único exemplar físico por um cliente elegível, com autorização, datas confiáveis e preservação da integridade e do histórico.

## Requirements

### Requirement: Operação exige conta interna autorizada

O backend SHALL autenticar e verificar existência, estado e papel atuais da conta antes de acessar dados de locação. Contas ativas `member` e `admin` SHALL poder registrar e consultar locações; estado legado ausente SHALL manter a compatibilidade de acesso vigente. O responsável SHALL ser derivado da identidade autenticada, sem aceitar identidade ou papel enviados pelo formulário.

#### Scenario: Operação permitida
- **WHEN** uma conta ativa `member` ou `admin` registra uma locação válida
- **THEN** o registro identifica essa conta como responsável

#### Scenario: Token sem autorização atual
- **WHEN** uma conta inexistente, explicitamente inativa ou de papel desconhecido apresenta token, ou a requisição não possui autenticação válida
- **THEN** a operação é recusada antes dos dados protegidos e sem efeitos operacionais

### Requirement: Cliente e exemplar são elegíveis no momento do registro

O backend SHALL exigir cliente existente com situação `active` e sem bloqueio manual ativo, exemplar existente com condição operacional confirmada `available`, filme associado existente e `active`, e ausência de ocupação por locação. Bloqueio manual ausente SHALL ser tratado como não aplicado, conforme compatibilidade do cadastro. O backend SHALL revalidar essas condições durante a operação protegida contra concorrência. Não SHALL inferir quitação, saldo ou bloqueio financeiro de módulos ausentes.

#### Scenario: Seleção válida
- **WHEN** cliente, exemplar e filme atendem às condições no momento da gravação
- **THEN** a locação pode ser registrada após as demais validações

#### Scenario: Seleção inválida ou desatualizada
- **WHEN** cliente está inativo ou bloqueado, exemplar não é elegível, ou alguma referência não existe ou foi alterada desde a seleção
- **THEN** o backend recusa sem criar locação nem ocupação

### Requirement: Datas e status são controlados

O sistema SHALL gerar a retirada no servidor e aceitar vencimento como instante ISO 8601 com offset explícito, convertido para UTC e estritamente posterior à retirada. Interface SHALL apresentar horário de Brasília (`America/Sao_Paulo`) e não preencher prazo comercial inventado. O status inicial SHALL ser `active`; responsável, retirada, status, valor financeiro e devolução SHALL NOT ser campos alteráveis pela entrada desta operação. O status SHALL passar a `returned` somente pela operação de devolução, e retirada e vencimento SHALL permanecer inalterados após a devolução.

#### Scenario: Prazo válido
- **WHEN** o usuário informa vencimento posterior à retirada
- **THEN** o backend persiste os instantes e status `active`, e a confirmação apresenta as datas no horário de Brasília

#### Scenario: Prazo inválido
- **WHEN** o vencimento está ausente, é inválido, não possui offset, ou é igual ou anterior à retirada
- **THEN** a operação é recusada sem gravação

#### Scenario: Status alterado somente pela devolução
- **WHEN** uma locação é devolvida
- **THEN** o status passa a `returned` e retirada e vencimento continuam iguais

### Requirement: Uma ocupação ativa por exemplar é garantida na persistência

O sistema SHALL garantir no banco no máximo uma ocupação por exemplar e SHALL confirmar locação e ocupação atomicamente. Uma consulta prévia ou bloqueio do botão SHALL NOT ser a única proteção. Falhas anteriores ao commit SHALL desfazer todos os efeitos da criação.

#### Scenario: Concorrência sobre exemplar
- **WHEN** duas requisições distintas tentam alugar o mesmo exemplar simultaneamente
- **THEN** no máximo uma locação e sua ocupação são confirmadas
- **AND** a outra recebe conflito sem registro parcial

#### Scenario: Falha entre gravações
- **WHEN** ocorre falha após iniciar a ocupação ou a locação e antes de confirmar a unidade atômica
- **THEN** não permanece locação sem ocupação nem ocupação órfã

### Requirement: Repetição da operação permite reconciliar o resultado

O sistema SHALL identificar cada tentativa lógica por chave de operação vinculada à conta. Repetição autenticada da mesma chave e conteúdo SHALL retornar a locação já confirmada, sem nova gravação e sem exigir que o exemplar continue disponível. Mesma chave com conteúdo diferente SHALL ser recusada. Timeout SHALL ser apresentado como resultado desconhecido até consulta ou repetição segura com a mesma chave; não SHALL disparar repetição automática com chave nova.

#### Scenario: Resposta perdida após commit
- **WHEN** o servidor confirmou a locação, a resposta foi perdida e a conta repete a mesma operação
- **THEN** recebe o mesmo identificador de locação sem duplicação

#### Scenario: Chave reutilizada para outro conteúdo
- **WHEN** uma chave já confirmada é enviada com outro cliente, exemplar ou vencimento
- **THEN** o backend informa conflito sem alterar a locação existente

### Requirement: Confirmação e auditoria preservam histórico e privacidade

O sistema SHALL oferecer consulta protegida da locação e reconciliação por chave da própria conta. Respostas SHALL conter somente identificação da locação, referências e rótulos necessários de cliente e exemplar, datas, status, responsável e, quando houver, instante e responsável da devolução (`returned_at` e `returned_by`, nulos enquanto `active`), sem CPF completo ou contatos. A criação SHALL registrar auditoria mínima com ação, resultado, usuário e identificador da locação. Falha de auditoria após commit SHALL distinguir gravação confirmada de auditoria pendente. A repetição da criação com a mesma chave SHALL retornar a locação em seu estado atual, inclusive `returned`. Nenhuma exclusão, cancelamento ou alteração de prazo SHALL ser oferecida.

#### Scenario: Registro confirmado
- **WHEN** a criação é confirmada
- **THEN** a consulta retorna dados persistidos e permite identificar cliente, exemplar, datas e status
- **AND** não apresenta saldos ou cobranças simulados

#### Scenario: Auditoria falha após commit
- **WHEN** a locação foi gravada mas o evento não foi confirmado
- **THEN** o resultado informa gravação confirmada com falha de auditoria e não orienta criar outra locação

#### Scenario: Consulta de locação devolvida
- **WHEN** a locação consultada já foi devolvida
- **THEN** a resposta inclui status `returned`, `returned_at` e `returned_by`, mantendo os demais campos originais

### Requirement: Formulário usa dados reais e isola sessões

A aplicação SHALL oferecer formulário autenticado com seleção de cliente e exemplar a partir das APIs reais, vencimento e confirmação explícita. SHALL distinguir carregamento, lista vazia, falha, conflito e sucesso; impedir envio duplicado enquanto pendente; limpar dados e invalidar respostas tardias após logout, troca de conta ou perda de autorização. Mudança de sessão SHALL NOT repetir a gravação pendente.

#### Scenario: Consulta falha
- **WHEN** não é possível obter clientes ou exemplares
- **THEN** a interface informa a falha sem inventar opções nem permitir confirmação baseada em disponibilidade desconhecida

#### Scenario: Logout com resposta pendente
- **WHEN** a sessão muda enquanto uma requisição está pendente
- **THEN** a resposta não repovoa dados nem apresenta sucesso na nova sessão

### Requirement: Consulta paginada das locações registradas

O backend SHALL expor `GET /locacoes` somente para contas autenticadas com papel `member` ou `admin`, conferindo o papel antes de qualquer leitura. A resposta SHALL ser `{items, page, per_page, total}`, ordenada por número decrescente, com `per_page` entre 1 e 50 e erro de entrada para paginação inválida. Cada item SHALL usar a mesma projeção de 13 campos de `GET /locacoes/{id}` e SHALL NOT incluir CPF, contato, chave de operação ou motivo de condição. A consulta SHALL NOT gravar dados e SHALL NOT depender de `XANO_RENTAL_WRITES_ENABLED`.

#### Scenario: Funcionário consulta a primeira página
- **WHEN** um `member` ou `admin` autenticado solicita `GET /locacoes?page=1&per_page=10`
- **THEN** recebe até 10 locações, mais recentes primeiro, e o total registrado

#### Scenario: Sem autorização
- **WHEN** a requisição não tem token válido ou a conta não é `member`/`admin` ativa
- **THEN** a consulta é recusada antes de ler locações

#### Scenario: Paginação inválida
- **WHEN** `page` é menor que 1 ou `per_page` está fora de 1 a 50
- **THEN** a resposta é erro de entrada, sem dados

### Requirement: Lista de locações separada em ativas e devolvidas

A lista "Locações registradas" SHALL oferecer as abas "Ativas" e "Devolvidas", iniciando em "Ativas", com o filtro aplicado pelo endpoint `GET /locacoes` por meio do parâmetro opcional `status` (`active` ou `returned`), preservando a paginação de 10 e a ordem mais recente primeiro. Cada aba SHALL exibir a contagem real quando conhecida. O endpoint SHALL recusar outros valores de `status` como erro de entrada e, sem `status`, SHALL listar todas as locações como antes. Cada locação SHALL aparecer em uma linha compacta e clicável com número, filme, cliente, exemplar, data de retirada (ativas) ou de devolução (devolvidas) e o selo "Vencida" quando ativa com vencimento ultrapassado. O cliente SHALL rejeitar uma página cujo item não corresponda à aba pedida.

#### Scenario: Troca de aba

- **WHEN** o funcionário seleciona "Devolvidas"
- **THEN** a lista mostra somente locações devolvidas, da mais recente para a mais antiga, a partir da primeira página

#### Scenario: Depois da devolução

- **WHEN** uma devolução é confirmada com sucesso
- **THEN** o app abre a lista na aba "Devolvidas" com o aviso "Locação #N devolvida."
- **AND** uma devolução com resultado desconhecido ou recusada permanece no detalhe da locação
