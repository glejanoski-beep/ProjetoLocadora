# devolucao-locacao Specification

## Purpose
Registrar a devolução de uma locação ativa, liberar o exemplar físico para novas locações e preservar o histórico, com proteção contra duplicidade e concorrência.

## Requirements

### Requirement: Devolução exige conta interna autorizada

O backend SHALL autenticar e verificar existência, estado e papel atuais da conta antes de registrar a devolução. Contas ativas `member` e `admin` SHALL poder registrar devoluções. O responsável SHALL ser derivado da identidade autenticada, sem aceitar identidade, instante ou status enviados pelo formulário. A operação SHALL ser recusada sem efeitos enquanto `XANO_RENTAL_WRITES_ENABLED` não for `true` no backend; a interface SHALL respeitar a variável de mesmo nome no app.

#### Scenario: Devolução permitida
- **WHEN** uma conta ativa `member` ou `admin` devolve uma locação ativa
- **THEN** a devolução registra essa conta como responsável

#### Scenario: Conta sem autorização ou gravação desabilitada
- **WHEN** a requisição não tem autenticação válida, a conta está inativa ou tem papel desconhecido, ou a trava de gravação está fechada
- **THEN** a operação é recusada sem devolução, sem alteração de status e sem liberar o exemplar

### Requirement: Somente locação ativa pode ser devolvida, uma única vez

O backend SHALL exigir que a locação exista e esteja `active` no momento da gravação, com a leitura protegida contra alterações concorrentes. Cada locação SHALL ter no máximo um registro de devolução, garantido na persistência. Locação já devolvida SHALL ser recusada como conflito, sem alterar o registro existente.

#### Scenario: Locação ativa
- **WHEN** a locação existe e está `active`
- **THEN** a devolução pode ser registrada

#### Scenario: Locação inexistente
- **WHEN** o número não corresponde a uma locação
- **THEN** a operação informa locação não encontrada, sem gravação

#### Scenario: Devolução duplicada
- **WHEN** a locação já foi devolvida e chega outra devolução com chave diferente
- **THEN** o backend informa que a locação já foi devolvida e mantém a devolução original

#### Scenario: Devoluções simultâneas
- **WHEN** duas requisições distintas tentam devolver a mesma locação ao mesmo tempo
- **THEN** exatamente uma devolução é confirmada e a outra recebe conflito, sem registro parcial

### Requirement: Devolução e liberação do exemplar são atômicas

O sistema SHALL, em uma única unidade atômica, criar o registro de devolução com instante gerado pelo servidor e responsável, alterar o status da locação para `returned` e remover a ocupação vinculada ao identificador dessa locação. A ocupação SHALL ser localizada pela locação, nunca apenas pelo exemplar. Ocupação ausente para uma locação `active` SHALL ser tratada como inconsistência e abortar sem efeitos. Falha antes do commit SHALL desfazer todas as alterações.

#### Scenario: Devolução confirmada
- **WHEN** a devolução é confirmada
- **THEN** a locação fica `returned`, existe um registro de devolução e o exemplar deixa de estar ocupado

#### Scenario: Falha entre gravações
- **WHEN** ocorre falha após iniciar a devolução e antes de confirmar a unidade atômica
- **THEN** a locação continua `active`, sem registro de devolução, e a ocupação permanece

#### Scenario: Ocupação inconsistente
- **WHEN** a locação está `active` mas não há ocupação com seu identificador
- **THEN** a operação é recusada sem alterar dados e sem liberar outro exemplar

### Requirement: Exemplar volta a ser elegível somente pelas regras de disponibilidade

A devolução SHALL NOT alterar a condição operacional do exemplar nem o status do filme. Após a devolução, o exemplar SHALL voltar às opções de nova locação somente se a condição confirmada continuar `available`, o filme estiver `active` e não houver outra ocupação. Constatação de avaria SHALL ser registrada pela operação administrativa de condição já existente.

#### Scenario: Exemplar em condições de uso
- **WHEN** um exemplar com condição `available` e filme ativo é devolvido
- **THEN** ele volta a aparecer entre os exemplares disponíveis

#### Scenario: Exemplar marcado indisponível durante a locação
- **WHEN** um admin alterou a condição para `unavailable` antes da devolução
- **THEN** a devolução libera a ocupação, mas o exemplar continua fora das opções de locação

#### Scenario: Corrida entre devolução e nova locação
- **WHEN** uma nova locação do mesmo exemplar é enviada enquanto a devolução está em andamento
- **THEN** a criação é recusada até o commit da devolução, e nunca existem duas ocupações do exemplar

### Requirement: Repetição da devolução permite reconciliar o resultado

Cada tentativa SHALL ter chave de operação vinculada à conta. A repetição autenticada com a mesma chave para a mesma locação SHALL retornar a devolução já confirmada, sem nova gravação nem novo evento de auditoria. A mesma chave para outra locação SHALL ser recusada. Timeout ou resposta inválida SHALL ser apresentado como resultado desconhecido, e a repetição SHALL usar a mesma chave, sem nova chave automática.

#### Scenario: Resposta perdida após commit
- **WHEN** a devolução foi confirmada, a resposta se perdeu e a conta repete com a mesma chave
- **THEN** recebe a mesma devolução, sem duplicação

#### Scenario: Chave reutilizada em outra locação
- **WHEN** uma chave já usada é enviada para outra locação
- **THEN** o backend informa conflito sem alterar nenhuma das locações

### Requirement: Histórico e prazo originais são preservados

A devolução SHALL NOT apagar ou alterar a retirada, o vencimento, o cliente, o exemplar, o filme ou o responsável pelo registro. As respostas de locação SHALL incluir `returned_at` e `returned_by`, nulos enquanto `active` e preenchidos quando `returned`. Atraso SHALL ser derivado de `returned_at` posterior a `due_at`, sem calcular multa, valor ou pendência financeira. A devolução SHALL registrar auditoria mínima com ação `return_rental`, resultado, usuário e identificador da locação; falha de auditoria após o commit SHALL distinguir devolução confirmada de auditoria pendente.

#### Scenario: Devolução no prazo
- **WHEN** a devolução ocorre até o vencimento
- **THEN** a locação mostra data de devolução e indica devolução no prazo

#### Scenario: Devolução com atraso
- **WHEN** a devolução ocorre depois do vencimento
- **THEN** a locação indica atraso e mantém o vencimento original, sem gerar multa

### Requirement: Interface de devolução no detalhe da locação

O detalhe `/locacoes/{id}` SHALL oferecer "Registrar devolução" somente para locação `active`, com resumo da locação, indicação de vencimento ultrapassado e confirmação explícita antes do envio. A interface SHALL impedir envio duplicado enquanto houver tentativa em andamento, distinguir sucesso, conflito, falha, 429 e resultado desconhecido, e permitir repetir a mesma tentativa. Com gravações desabilitadas, SHALL exibir aviso neutro e manter a ação indisponível. Locação devolvida SHALL mostrar situação "Devolvida", data da devolução, responsável e se houve atraso, sem ação de escrita. Após logout, troca de conta ou perda de autorização, respostas pendentes SHALL ser descartadas.

#### Scenario: Confirmação da devolução
- **WHEN** o usuário confirma a devolução de uma locação ativa
- **THEN** a tela apresenta o resultado persistido pelo backend e deixa de oferecer a ação

#### Scenario: Resultado desconhecido
- **WHEN** a requisição expira ou a resposta é inválida
- **THEN** a tela informa resultado desconhecido e oferece repetir com a mesma chave ou atualizar o detalhe

#### Scenario: Locação já devolvida por outra pessoa
- **WHEN** o backend responde que a locação já foi devolvida
- **THEN** a tela informa o conflito e recarrega o detalhe com a devolução existente
