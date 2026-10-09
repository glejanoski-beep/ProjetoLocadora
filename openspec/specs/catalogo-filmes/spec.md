# Catálogo de filmes

## Purpose

Definir a consulta e a manutenção administrativa do catálogo de filmes persistido no Xano. A capacidade mantém filmes separados de exemplares físicos e aplica autorização e validação no backend.

## Requirements

### Requirement: Usuários internos consultam o catálogo persistido no Xano

A aplicação SHALL oferecer uma página Reflex autenticada que lista os filmes persistidos no Xano e permite buscar por trecho do título sem distinção entre maiúsculas e minúsculas. A consulta SHALL ser executada pelo backend Xano, respeitando a autorização de `member` definida em `acesso-seguro`. Uma lista sem registros SHALL ser distinguível de uma falha de consulta.

#### Scenario: Listagem com filmes cadastrados

- **WHEN** um usuário interno ativo e autenticado abre o catálogo
- **THEN** a aplicação consulta os filmes persistidos no Xano
- **AND** apresenta os resultados retornados

#### Scenario: Catálogo sem registros

- **WHEN** a consulta Xano termina com sucesso e não há filmes cadastrados
- **THEN** a aplicação informa que o catálogo está vazio
- **AND** não apresenta o estado vazio como erro de comunicação

#### Scenario: Falha ao consultar o catálogo

- **WHEN** a consulta Xano falha por rede, autorização ou erro do serviço
- **THEN** a aplicação informa que não foi possível carregar o catálogo
- **AND** não representa a falha como uma consulta bem-sucedida sem filmes

#### Scenario: Busca por trecho do título

- **WHEN** o usuário informa um trecho de título
- **THEN** a consulta ao Xano retorna filmes cujo título contém o trecho sem distinguir maiúsculas de minúsculas
- **AND** o resultado não depende de um conjunto de filmes em memória como fonte de verdade

### Requirement: Filtro por gênero corresponde ao modelo existente

A aplicação SHALL oferecer filtro por gênero usando o campo textual obrigatório `genero` do schema aprovado e SHALL aplicar a seleção na consulta Xano. A interface pode usar os gêneros existentes nos resultados persistidos como opções; não SHALL criar uma taxonomia ou lista fechada.

#### Scenario: Filtragem por gênero

- **WHEN** o usuário seleciona um gênero existente
- **THEN** a interface envia o valor do campo textual `genero`
- **AND** a consulta Xano aplica o filtro selecionado

### Requirement: Contrato técnico aprovado do catálogo

A aplicação e os endpoints SHALL usar o contrato de catálogo aprovado nesta Change e versioná-lo localmente antes da implementação. `id_filme` é o conceito de origem mapeado para `id`, não uma coluna adicional. A compatibilidade de `qtd_estoque` permanece pendente; esta Change não define valor inicial nem altera o campo.

#### Scenario: Identificador gerado

- **WHEN** um filme é criado
- **THEN** o Xano gera o inteiro `id`
- **AND** a interface não envia `id` como campo editável

#### Scenario: Validação de texto

- **WHEN** um administrador cria ou edita um filme
- **THEN** `titulo` e `genero` são obrigatórios, não vazios após trim e respeitam os máximos de 200 e 100 caracteres
- **AND** `genero` não depende de lista fechada nesta versão

#### Scenario: Validação do ano e classificação

- **WHEN** um administrador cria ou edita um filme
- **THEN** `ano_lancamento` é inteiro de 1888 até o ano corrente, inclusive
- **AND** `classificacao` aceita somente os seis valores definidos neste requisito

#### Scenario: Valor monetário em reais e centavos

- **WHEN** um administrador informa ou edita o valor de locação na interface
- **THEN** a interface recebe e apresenta reais e persiste `valor_locacao_centavos` como inteiro não negativo em centavos

#### Scenario: Status inicial e alteração administrativa

- **WHEN** um filme é criado ou tem sua situação cadastral alterada
- **THEN** `status` inicia como `active` e aceita somente `active` ou `inactive`
- **AND** somente `admin` pode alterar `status`
- **AND** `status` não representa disponibilidade de exemplares

#### Scenario: Estoque permanece pendente e inalterado

- **WHEN** `qtd_estoque` é incompatível ou ainda não confirmado no modelo técnico
- **THEN** a implementação do catálogo pode prosseguir omitindo o campo, se o schema permitir
- **AND** esta Change não define seu valor inicial nem o envia ou altera
- **AND** a definição de sua compatibilidade com filme/exemplar permanece pendente

### Requirement: Administrador cria filmes por formulário com persistência Xano

A aplicação SHALL permitir que somente um usuário interno ativo com papel `admin` crie filmes por formulário Reflex. Os campos e as validações SHALL corresponder ao schema aprovado, e o backend SHALL autorizar e validar antes de persistir no Xano. `id` é gerado pelo Xano; `status` inicia em `active`. `qtd_estoque` SHALL NOT ser incluído nem receber default definido por esta Change.

#### Scenario: Criação válida

- **WHEN** um administrador envia um formulário válido conforme o schema aprovado
- **THEN** o backend Xano persiste o filme
- **AND** a interface apresenta confirmação de sucesso após a resposta bem-sucedida
- **AND** o Xano gera `id`, e `status` inicia em `active`
- **AND** `qtd_estoque` não é usado como entrada para operação de estoque nesta Change

#### Scenario: Criação com dados inválidos

- **WHEN** um administrador envia dados que não atendem ao schema aprovado
- **THEN** a interface apresenta mensagens de validação compreensíveis
- **AND** o backend não persiste um filme inválido

#### Scenario: Criação solicitada por member

- **WHEN** um usuário `member` tenta criar um filme, inclusive por chamada direta ao endpoint
- **THEN** o backend recusa a operação antes de gravar
- **AND** a interface não apresenta confirmação de sucesso

#### Scenario: Falha de persistência na criação

- **WHEN** a gravação Xano falha ou é recusada
- **THEN** a interface informa que não foi possível cadastrar o filme
- **AND** não comunica sucesso

### Requirement: Administrador edita filmes existentes por formulário com persistência Xano

A aplicação SHALL permitir que somente um usuário interno ativo com papel `admin` carregue e edite um filme existente por formulário Reflex. A edição SHALL alterar apenas campos admitidos pelo schema aprovado, validar os dados no backend e persistir no Xano. Somente `admin` pode alterar `status`; `qtd_estoque` não pode ser incluído ou alterado.

#### Scenario: Edição válida

- **WHEN** um administrador altera dados válidos de um filme existente e salva
- **THEN** o backend Xano persiste as alterações permitidas
- **AND** a interface apresenta confirmação somente após a resposta bem-sucedida

#### Scenario: Edição de filme inexistente

- **WHEN** um administrador solicita a edição de um identificador sem filme correspondente
- **THEN** o backend informa que o recurso não foi encontrado
- **AND** a interface não apresenta um formulário com dados inventados nem confirma alteração

#### Scenario: Edição solicitada por member

- **WHEN** um usuário `member` tenta editar um filme, inclusive por chamada direta ao endpoint
- **THEN** o backend recusa a operação antes de alterar o registro
- **AND** a interface não apresenta confirmação de sucesso

#### Scenario: Falha de persistência na edição

- **WHEN** a gravação Xano falha ou é recusada
- **THEN** a interface informa que não foi possível salvar as alterações
- **AND** não comunica sucesso

### Requirement: Manutenção do catálogo não altera exemplares nem locações

As operações desta capacidade SHALL manter o cadastro de filme separado dos exemplares físicos e SHALL NOT criar, alterar ou inferir exemplares, controlar ou ajustar estoque, calcular disponibilidade ou operar locações. A possível presença do atributo conceitual `qtd_estoque` no modelo não concede comportamento de controle de estoque à aplicação.

#### Scenario: Criação ou edição de filme

- **WHEN** um filme é criado ou editado
- **THEN** a operação afeta somente os campos do filme definidos no schema aprovado
- **AND** não cria nem modifica exemplares, não executa operações de estoque ou disponibilidade e não opera locações

#### Scenario: Edição com quantidade de estoque existente

- **WHEN** um filme com `qtd_estoque` definido é editado
- **THEN** a interface não expõe esse atributo como campo editável
- **AND** a edição preserva o valor existente sem movimentar, calcular ou controlar estoque
