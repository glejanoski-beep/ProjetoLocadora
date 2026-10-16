# Spec Delta

## Purpose

Definir o cadastro, a localização e a manutenção protegida de clientes, preservando dados pessoais e preparando uma identidade estável para futuras locações, pendências e pagamentos.

## ADDED Requirements

### Requirement: Consultas de clientes são autenticadas e minimizam dados pessoais

O sistema SHALL permitir que contas internas ativas `member` e `admin` localizem clientes, mas SHALL exigir autenticação e revalidar o papel e o estado atual da conta no backend antes de devolver qualquer dado. A listagem SHALL retornar somente `id`, nome, CPF mascarado, situação cadastral e indicação de bloqueio manual; dados completos de contato e CPF completo SHALL permanecer restritos à consulta protegida do detalhe.

#### Scenario: Member ativo localiza cliente

- **WHEN** uma conta ativa `member` pesquisa clientes por uma operação implementada
- **THEN** o backend autoriza a consulta e retorna somente os campos definidos para a listagem

#### Scenario: Consulta sem autenticação

- **WHEN** uma requisição sem autenticação válida tenta listar ou consultar um cliente
- **THEN** o backend recusa a operação sem devolver dados cadastrais

#### Scenario: Conta desativada usa token anterior

- **WHEN** uma conta explicitamente desativada tenta consultar clientes com um token ainda válido
- **THEN** o backend recusa a consulta antes de acessar os dados pessoais

#### Scenario: Detalhe cadastral protegido

- **WHEN** uma conta interna ativa e autorizada consulta o detalhe de um cliente existente
- **THEN** o sistema retorna os dados cadastrais completos admitidos pelo contrato para uso no atendimento
- **AND** a resposta não inclui credenciais, dados financeiros inexistentes ou objetos de outros domínios

### Requirement: Cliente possui identificação estável e CPF único válido

O sistema SHALL gerar um `id` inteiro imutável para cada cliente e SHALL exigir CPF brasileiro válido e único. O CPF SHALL ser aceito com ou sem pontuação, normalizado para onze dígitos antes da validação e persistência, rejeitar sequências de dígitos repetidos e respeitar os dois dígitos verificadores. O `id` e o CPF normalizado SHALL formar a identidade estável usada por futuras integrações, sem permitir edição do `id`.

#### Scenario: CPF formatado válido

- **WHEN** um administrador cadastra um cliente com CPF válido contendo pontuação
- **THEN** o backend valida os dígitos verificadores e persiste somente os onze dígitos

#### Scenario: CPF inválido

- **WHEN** o cadastro ou atualização contém CPF com tamanho inválido, sequência repetida ou dígitos verificadores incorretos
- **THEN** o backend recusa a operação sem persistir a alteração

#### Scenario: CPF duplicado

- **WHEN** duas tentativas de cadastro usam o mesmo CPF após normalização, inclusive de forma concorrente
- **THEN** no máximo um cliente é criado
- **AND** a tentativa duplicada recebe uma resposta de conflito compreensível

### Requirement: Cadastro exige dados mínimos e contato válido

O sistema SHALL exigir nome completo não vazio com no máximo 200 caracteres e ao menos um meio de contato entre e-mail e telefone. E-mail e telefone SHALL ser opcionais individualmente, mas, quando informados, SHALL ser normalizados e validados no backend. Campos não definidos no contrato SHALL ser rejeitados ou ignorados sem alterar dados protegidos, conforme a política uniforme da API.

#### Scenario: Cadastro mínimo válido com e-mail

- **WHEN** um administrador informa nome, CPF válido e e-mail válido sem telefone
- **THEN** o backend cria o cliente com situação `active` e sem bloqueio manual

#### Scenario: Cadastro mínimo válido com telefone

- **WHEN** um administrador informa nome, CPF válido e telefone válido sem e-mail
- **THEN** o backend cria o cliente com situação `active` e sem bloqueio manual

#### Scenario: Cadastro sem contato

- **WHEN** e-mail e telefone estão ambos ausentes ou vazios após normalização
- **THEN** o backend recusa o cadastro e informa que ao menos um contato é obrigatório

#### Scenario: Contato inválido

- **WHEN** um e-mail ou telefone informado não atende ao formato aceito
- **THEN** o backend recusa a operação sem persistir dados inválidos

### Requirement: Busca localiza por nome ou CPF sem expor o CPF completo

O sistema SHALL permitir busca por trecho do nome sem distinção entre maiúsculas e minúsculas e por CPF exato após normalização. Uma busca sem filtros SHALL listar os clientes conforme paginação definida pelo contrato. O CPF completo SHALL NOT aparecer nos resultados da listagem, inclusive quando ele for o critério de busca.

#### Scenario: Busca por trecho do nome

- **WHEN** um usuário interno ativo informa parte do nome de um cliente
- **THEN** o backend retorna clientes cujos nomes contêm o trecho sem distinguir maiúsculas de minúsculas

#### Scenario: Busca por CPF formatado

- **WHEN** um usuário interno ativo informa um CPF completo válido com pontuação
- **THEN** o backend normaliza o valor e retorna, no máximo, o cliente correspondente
- **AND** apresenta o CPF mascarado no resultado

#### Scenario: Busca sem resultados

- **WHEN** uma consulta válida não encontra clientes
- **THEN** o sistema informa uma lista vazia como resultado bem-sucedido
- **AND** não representa ausência de resultados como falha de comunicação

### Requirement: Somente admin mantém o cadastro de clientes

O sistema SHALL permitir somente a contas ativas `admin` criar ou atualizar clientes, inclusive CPF, nome, contatos, situação cadastral e bloqueio manual. Contas `member` SHALL poder consultar clientes, mas SHALL NOT criar, alterar, inativar ou bloquear cadastros por chamada direta ou pela interface.

#### Scenario: Admin cria cliente válido

- **WHEN** uma conta ativa `admin` envia um cadastro válido e não duplicado
- **THEN** o backend persiste o cliente e retorna a confirmação da criação

#### Scenario: Admin atualiza cliente válido

- **WHEN** uma conta ativa `admin` altera campos permitidos de um cliente existente com valores válidos
- **THEN** o backend persiste somente os campos admitidos e retorna o estado atualizado

#### Scenario: Member tenta alterar cliente

- **WHEN** uma conta ativa `member` chama diretamente uma operação de criação ou atualização de cliente
- **THEN** o backend recusa a operação antes da gravação
- **AND** o cadastro permanece inalterado

### Requirement: Situação cadastral e bloqueio manual são independentes

O sistema SHALL representar a situação cadastral como `active` ou `inactive` e o bloqueio cadastral manual como condição independente. Aplicar um bloqueio manual SHALL exigir motivo não vazio e identificar a transição para auditoria; remover o bloqueio manual SHALL exigir `admin`. Cliente inativo ou manualmente bloqueado SHALL ser considerado inelegível para futura locação, sem que esta change crie ou execute uma locação.

#### Scenario: Admin aplica bloqueio manual

- **WHEN** uma conta ativa `admin` bloqueia manualmente um cliente ativo e informa um motivo válido
- **THEN** o cadastro permanece ativo, mas passa a indicar bloqueio manual
- **AND** o motivo fica disponível somente nas consultas protegidas que necessitam dele

#### Scenario: Bloqueio sem motivo

- **WHEN** um administrador tenta aplicar bloqueio manual sem motivo não vazio
- **THEN** o backend recusa a alteração e preserva o estado anterior

#### Scenario: Admin remove bloqueio manual

- **WHEN** uma conta ativa `admin` remove um bloqueio cadastral manual existente
- **THEN** o bloqueio manual deixa de impedir futuras operações
- **AND** a remoção não apaga a rastreabilidade da transição anterior

#### Scenario: Cliente inativo continua bloqueado manualmente

- **WHEN** um cliente com bloqueio manual é marcado como `inactive`
- **THEN** a situação cadastral muda sem apagar automaticamente o bloqueio ou seu histórico

### Requirement: Clientes não são apagados para encerrar ou corrigir cadastro

O sistema SHALL preservar o identificador e o histórico de alterações do cliente. O contrato desta change SHALL NOT oferecer exclusão de clientes; encerramento cadastral SHALL ocorrer por inativação e correções SHALL ocorrer por atualização auditada.

#### Scenario: Encerramento de cadastro

- **WHEN** um administrador precisa encerrar o uso de um cadastro de cliente
- **THEN** o cliente é marcado como `inactive`
- **AND** o registro e seu identificador permanecem disponíveis para referências históricas futuras

#### Scenario: Tentativa de exclusão

- **WHEN** um usuário tenta excluir um cliente por uma rota ou operação não prevista
- **THEN** o sistema não remove o registro nem seus dados de rastreabilidade

### Requirement: Histórico e pendências aguardam os domínios de origem

O sistema SHALL reservar o `id` do cliente como chave de associação futura e SHALL apresentar no detalhe uma seção identificada de histórico e pendências. Enquanto locações, multas e pagamentos não estiverem implementados, essa seção SHALL informar que os dados ainda não estão disponíveis e SHALL NOT criar registros financeiros, permitir cobrança, calcular saldo, remover bloqueio financeiro ou apresentar valores fictícios.

#### Scenario: Consulta antes da capacidade de locações

- **WHEN** um usuário consulta o detalhe de um cliente nesta versão
- **THEN** a seção de histórico e pendências informa que depende das futuras capacidades de locação, multa e pagamento
- **AND** não apresenta lista vazia ou saldo zero como se fossem dados financeiros confirmados

#### Scenario: Pagamento e desbloqueio financeiro fora do escopo

- **WHEN** um `member` tenta cobrar pendência, registrar pagamento ou remover bloqueio financeiro por esta capacidade
- **THEN** nenhuma dessas operações é oferecida ou executada
- **AND** a futura change financeira deverá aplicar a permissão operacional vigente e liberar bloqueio somente conforme a quitação confirmada

