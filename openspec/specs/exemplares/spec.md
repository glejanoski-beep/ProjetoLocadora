# Exemplares Specification

## Purpose

Permitir identificar individualmente cada cópia física, associá-la a um filme existente e consultar essa relação por meio de operações protegidas.

## Requirements

### Requirement: Cada exemplar possui identificador único

O sistema SHALL persistir cada exemplar com um identificador que não possa identificar mais de um exemplar. A unicidade SHALL comparar exatamente o valor informado, sem normalização de espaços ou caixa, e SHALL ser garantida no backend/banco de dados, não somente pela interface.

#### Scenario: Identificador já utilizado

- **WHEN** uma operação tenta persistir um exemplar com o mesmo valor de identificador já associado a outro exemplar
- **THEN** o backend recusa a operação
- **AND** nenhum segundo exemplar com esse identificador é persistido

#### Scenario: Tentativas concorrentes com o mesmo identificador

- **WHEN** duas operações concorrentes tentam persistir exemplares com o mesmo valor de identificador
- **THEN** no máximo uma operação persiste um exemplar com esse identificador
- **AND** a outra operação recebe uma falha explícita

### Requirement: Exemplar pertence a filme existente

O sistema SHALL associar cada exemplar persistido a um filme existente. O backend SHALL validar a existência do filme antes de persistir o exemplar.

#### Scenario: Associação a filme existente

- **WHEN** um administrador autorizado solicita a criação de um exemplar associado a um filme existente
- **THEN** o exemplar é persistido com a associação a esse filme

#### Scenario: Associação a filme inexistente

- **WHEN** uma operação tenta criar um exemplar associado a um filme inexistente
- **THEN** o backend recusa a operação
- **AND** nenhum exemplar é persistido

### Requirement: Usuários autorizados consultam exemplares e seu filme

O sistema SHALL permitir que usuários ativos com papel `member` ou `admin` consultem exemplares. Cada resultado SHALL identificar individualmente o exemplar e informar a qual filme existente pertence.

#### Scenario: Consulta de exemplares associados a filmes

- **WHEN** um usuário autorizado consulta os exemplares
- **THEN** a resposta identifica cada exemplar individualmente
- **AND** informa o filme associado a cada exemplar

#### Scenario: Consulta sem exemplares cadastrados

- **WHEN** um usuário autorizado consulta e não há exemplares cadastrados
- **THEN** a consulta retorna um resultado vazio válido

### Requirement: Cadastro de exemplares exige administrador

O sistema SHALL permitir somente a usuários ativos com papel `admin` cadastrar, editar, dar baixa e reativar exemplares. A autorização SHALL ser verificada no backend; ocultar ou desabilitar controles na interface SHALL NOT substituir essa autorização. Exclusão física de exemplares SHALL NOT ser oferecida; a baixa a substitui.

#### Scenario: Administrador cadastra exemplar
- **WHEN** um usuário ativo `admin` solicita o cadastro de um exemplar com dados válidos
- **THEN** o backend autoriza a operação, sujeita aos requisitos de unicidade e associação a filme existente

#### Scenario: Member tenta cadastrar exemplar
- **WHEN** um usuário ativo `member` solicita diretamente o cadastro, a edição, a baixa ou a reativação de um exemplar
- **THEN** o backend recusa a operação
- **AND** nenhum exemplar é persistido ou alterado

#### Scenario: Conta sem autorização válida
- **WHEN** uma conta não autenticada, inativa ou com papel não reconhecido solicita uma operação protegida de exemplar
- **THEN** o backend recusa a operação antes de consultar ou alterar dados protegidos

### Requirement: Edição preserva unicidade e histórico

O administrador SHALL poder alterar o identificador e o filme de um exemplar não baixado. O identificador SHALL continuar não vazio e único, com comparação exata contra os demais exemplares e garantia final do banco. A troca de filme SHALL ser recusada quando existir qualquer locação registrada para o exemplar, ativa ou devolvida. A troca de identificador SHALL ser permitida mesmo com histórico, preservando nas locações o identificador do momento em que foram registradas. A edição SHALL ser protegida contra alterações concorrentes do exemplar e auditada como `update_exemplar`.

#### Scenario: Correção de identificador
- **WHEN** o administrador altera o identificador de um exemplar com locações anteriores para um valor ainda não usado
- **THEN** o exemplar passa a ter o novo identificador, e as locações anteriores mantêm o identificador registrado nelas

#### Scenario: Identificador já usado
- **WHEN** o novo identificador pertence a outro exemplar
- **THEN** o backend recusa a edição sem alterar o exemplar

#### Scenario: Troca de filme com histórico
- **WHEN** o administrador tenta trocar o filme de um exemplar que já participou de uma locação
- **THEN** o backend recusa com "Exemplar com locações registradas não pode trocar de filme."

#### Scenario: Troca de filme sem histórico
- **WHEN** o exemplar nunca foi alugado e o novo filme existe
- **THEN** o exemplar passa a pertencer ao novo filme

### Requirement: Baixa retira o exemplar do acervo sem apagar registros

O administrador SHALL poder dar baixa em um exemplar não baixado, informando o tipo (`lost`, `damaged`, `discarded` ou `other`) e um motivo obrigatório de até 500 caracteres. A baixa SHALL ser recusada enquanto existir ocupação por locação ativa. Na mesma operação, protegida contra concorrência, o sistema SHALL registrar instante, responsável, tipo e motivo da baixa e marcar a condição operacional como `unavailable`, com responsável, instante e motivo. O exemplar e suas locações SHALL ser preservados. A operação SHALL ser auditada como `retire_exemplar`.

#### Scenario: Baixa de cópia perdida
- **WHEN** o administrador dá baixa em uma cópia não alugada, com tipo `lost` e motivo
- **THEN** o exemplar fica baixado e deixa de aparecer nas opções de nova locação

#### Scenario: Cópia alugada
- **WHEN** o administrador tenta dar baixa em uma cópia com locação ativa
- **THEN** o backend recusa com "Exemplar alugado: registre a devolução antes da baixa." sem alterar o exemplar

#### Scenario: Baixa e nova locação simultâneas
- **WHEN** a baixa e uma nova locação da mesma cópia são enviadas ao mesmo tempo
- **THEN** no máximo uma das operações é confirmada, sem cópia baixada com locação ativa

### Requirement: Reativação exige nova conferência

O administrador SHALL poder reativar um exemplar baixado, informando um motivo obrigatório de até 500 caracteres. A reativação SHALL limpar os dados da baixa e definir a condição operacional como `unverified`, de modo que a cópia só volte a ser elegível após nova conferência `available`. A operação SHALL ser auditada como `reactivate_exemplar`.

#### Scenario: Cópia encontrada
- **WHEN** o administrador reativa uma cópia baixada como perdida
- **THEN** a cópia deixa de estar baixada, fica "não conferida" e não aparece nas opções de locação até ser conferida

### Requirement: Listagem informa a baixa

A consulta de exemplares SHALL informar, para cada exemplar, se está baixado, com o tipo e o motivo da baixa (vazios quando ativo), sem dados de clientes.

#### Scenario: Exemplar baixado na listagem
- **WHEN** um usuário autorizado consulta os exemplares
- **THEN** cada exemplar baixado aparece com `baixado = true`, o tipo e o motivo da baixa
