# Domain Model — Sistema de Gestão para Locadora de Filmes

## 1. Visão do domínio

O domínio representa uma locadora que mantém um catálogo de filmes, possui um ou mais exemplares físicos de cada filme e registra o ciclo de locação desses exemplares para seus clientes.

O conceito central é a **locação**: um cliente retira um exemplar, deve devolvê-lo até um prazo, pode gerar uma multa por atraso e pode ter pagamentos associados. O sistema também controla usuários internos, permissões e os registros necessários para garantir rastreabilidade.

## 2. Mapa conceitual

```text
Usuário interno
	│ possui
	▼
Funcionário ── exerce ── Perfil de acesso
	│ realiza ou registra
	▼
Cliente ── possui histórico de ── Locação ── utiliza ── Exemplar ── é cópia de ── Filme
					    │                    │
					    │                    └── possui estado de disponibilidade
					    │
					    ├── termina em ── Devolução
					    ├── pode gerar ── Multa ── é quitada por ── Pagamento
					    └── é registrada por ── Usuário interno

Locações, devoluções, multas e pagamentos
	└── alimentam ── Consultas e Relatórios
```

## 3. Conceitos do domínio

### Filme

Representa a obra cinematográfica disponível no catálogo da locadora, independentemente da quantidade de cópias físicas existentes.

#### Responsabilidade

- Identificar e descrever o título disponível para consulta.
- Servir como referência comum para todos os seus exemplares.
- Apoiar consultas do catálogo e relatórios de popularidade.

#### Principais informações

- título;
- descrição ou sinopse;
- gênero ou categoria;
- classificação indicativa;
- ano de lançamento;
- situação no catálogo.

#### Relacionamentos

- Um filme pode possuir vários exemplares.
- Um filme pode aparecer em várias locações por meio de seus exemplares.
- Um filme pode ser agrupado em relatórios de filmes mais alugados.

#### Regras estruturais importantes

- O filme não representa uma cópia física específica.
- A existência de um filme no catálogo não significa que haja um exemplar disponível para locação.
- Um filme inativo pode permanecer no histórico das locações já realizadas.

### Exemplar

Representa uma cópia física individual de um filme, aquela que efetivamente pode ser retirada e devolvida.

#### Responsabilidade

- Controlar a identidade e a situação de cada cópia.
- Ser o recurso reservado por uma locação.
- Refletir se a cópia pode ou não ser alugada no momento.

#### Principais informações

- identificação do exemplar;
- filme ao qual pertence;
- situação física ou operacional;
- localização, quando aplicável;
- datas relevantes de aquisição, baixa ou manutenção, quando aplicável.

#### Relacionamentos

- Um exemplar pertence a um único filme.
- Um exemplar pode participar de várias locações ao longo do tempo, mas não de mais de uma locação ativa simultaneamente.
- Seu estado é alterado pelo fluxo de locação e devolução.

#### Regras estruturais importantes

- O exemplar deve ser identificável individualmente.
- Um exemplar alugado, danificado, perdido ou baixado não deve aparecer como disponível.
- A disponibilidade deve ser determinada no nível do exemplar, e não somente no nível do filme.

### Cliente

Representa a pessoa que pode realizar locações na locadora.

#### Responsabilidade

- Identificar o responsável pelas locações.
- Concentrar o histórico de locações e a situação financeira relacionada.
- Determinar, conforme suas pendências e regras vigentes, se pode realizar uma nova locação.

#### Principais informações

- nome;
- dados de contato;
- documento ou identificador cadastral;
- situação cadastral;
- situação de bloqueio;
- pendências financeiras, derivadas de multas e pagamentos.

#### Relacionamentos

- Um cliente pode ter várias locações.
- Uma locação pertence a um único cliente.
- Um cliente pode ter várias multas e pagamentos associados às suas locações.
- O cliente pode estar bloqueado por inadimplência ou por outra regra operacional.

#### Regras estruturais importantes

- Um cliente bloqueado não pode iniciar novas locações enquanto a condição de bloqueio persistir.
- O bloqueio não deve apagar o histórico do cliente.
- A situação do cliente deve ser compatível com suas pendências registradas.

### Locação

Representa o compromisso operacional de disponibilizar um exemplar a um cliente durante um período determinado.

#### Responsabilidade

- Registrar a retirada do exemplar e as condições da operação.
- Controlar o prazo esperado de devolução e o estado da locação.
- Servir de referência para devolução, cálculo de multa, pagamentos e histórico.

#### Principais informações

- cliente;
- exemplar;
- data e hora da locação;
- prazo ou data prevista para devolução;
- data efetiva de devolução, quando concluída;
- situação da locação;
- usuário interno responsável pelo registro.

#### Relacionamentos

- Uma locação pertence a um cliente.
- Uma locação utiliza um exemplar.
- Uma locação pode ter uma devolução.
- Uma locação pode gerar uma ou mais multas, conforme as regras de negócio.
- Uma locação pode possuir pagamentos relacionados.
- Uma locação é criada ou atualizada por um usuário interno autorizado.

#### Regras estruturais importantes

- Não deve existir locação ativa para exemplar indisponível.
- Não deve existir locação nova para cliente bloqueado.
- Uma locação encerrada deve conservar seus dados e permanecer disponível no histórico.
- O atraso é determinado comparando o prazo da locação com a devolução efetiva ou, enquanto não houver devolução, com a data de consulta vigente.

### Devolução

Representa o evento de retorno do exemplar à locadora e o encerramento, total ou parcial, da obrigação de devolução.

#### Responsabilidade

- Registrar quando e como o exemplar foi devolvido.
- Atualizar a situação do exemplar.
- Informar os dados necessários para identificar atraso, dano ou outras ocorrências.

#### Principais informações

- data e hora da devolução;
- locação relacionada;
- usuário interno que registrou a operação;
- observações ou condição do exemplar;
- indicação de atraso, quando aplicável.

#### Relacionamentos

- Uma devolução pertence a uma locação.
- A devolução altera a disponibilidade do exemplar utilizado pela locação.
- Uma devolução pode resultar na criação ou atualização de uma multa.

#### Regras estruturais importantes

- Uma locação não deve ser marcada como devolvida sem um registro de devolução válido.
- O exemplar só deve voltar ao estado disponível se sua condição permitir uma nova locação.
- O registro da devolução não deve alterar ou apagar o prazo originalmente contratado.

### Multa

Representa um valor devido em razão de atraso ou de outra ocorrência prevista nas regras da locadora.

#### Responsabilidade

- Registrar a obrigação financeira gerada por uma locação.
- Preservar o valor e o motivo calculados.
- Indicar se a obrigação está pendente, parcialmente paga, quitada ou cancelada conforme regra autorizada.

#### Principais informações

- locação que originou a multa;
- motivo;
- período considerado em atraso;
- valor calculado;
- situação de quitação;
- datas de criação e atualização.

#### Relacionamentos

- Uma multa está associada a uma locação e, indiretamente, a um cliente.
- Uma multa pode ser quitada por um ou mais pagamentos, se essa possibilidade for adotada.
- Multas pendentes podem contribuir para o bloqueio do cliente.

#### Regras estruturais importantes

- O valor deve ser calculado segundo uma regra de negócio registrada e reproduzível.
- Uma multa quitada não deve ser alterada silenciosamente.
- O cálculo exato, a tolerância e os critérios de cancelamento ainda devem ser definidos em especificação própria.

### Pagamento

Representa a quitação total ou parcial de uma obrigação financeira relacionada a uma locação ou multa.

#### Responsabilidade

- Registrar os valores recebidos pela locadora.
- Associar o recebimento à obrigação correspondente.
- Permitir determinar o saldo pendente e a situação financeira do cliente.

#### Principais informações

- valor;
- data e hora;
- obrigação ou multa relacionada;
- meio de pagamento, quando aplicável;
- situação do pagamento;
- usuário interno que registrou o recebimento.

#### Relacionamentos

- Um pagamento está relacionado a uma locação, multa ou outra cobrança definida pelo domínio.
- Uma multa pode ter um ou mais pagamentos.
- Pagamentos afetam a situação da multa e as condições de bloqueio do cliente.

#### Regras estruturais importantes

- Um pagamento registrado deve manter seu histórico e não ser removido para corrigir uma operação; ajustes devem ser rastreáveis.
- A soma dos pagamentos não deve quitar uma multa além do valor permitido pela regra vigente.
- Os meios de pagamento e o tratamento de estornos ainda não estão definidos no escopo inicial.

### Usuário interno

Representa a identidade autenticada de uma pessoa que utiliza o sistema em nome da locadora.

#### Responsabilidade

- Autenticar o acesso ao sistema.
- Executar somente as operações permitidas pelo seu perfil.
- Ser identificado nos registros de operações relevantes.

#### Principais informações

- credenciais ou referência de autenticação;
- nome e contato profissional;
- situação de acesso;
- perfil ou papéis atribuídos;
- datas de criação e último acesso, quando aplicável.

#### Relacionamentos

- Um usuário interno pode estar associado a um funcionário.
- Um usuário interno possui um ou mais perfis de acesso.
- Um usuário interno pode registrar locações, devoluções, pagamentos e alterações administrativas, conforme permissão.

#### Regras estruturais importantes

- Usuários desativados não devem iniciar novas operações.
- A permissão deve ser verificada no momento da operação, não apenas na interface.
- A autenticação e o controle de papéis já estão representados na base Xano/XanoScript do projeto.

### Funcionário

Representa a pessoa que trabalha na locadora e pode receber acesso operacional ao sistema.

#### Responsabilidade

- Descrever o vínculo profissional do usuário com a locadora.
- Apoiar a atribuição de permissões e a identificação dos responsáveis pelas operações.

#### Principais informações

- nome;
- identificação funcional;
- cargo ou função;
- situação do vínculo;
- usuário interno associado.

#### Relacionamentos

- Um funcionário pode possuir um usuário interno.
- Um funcionário pode exercer um perfil de acesso.
- Um funcionário pode ser responsável por operações registradas no sistema.

#### Regras estruturais importantes

- O encerramento do vínculo deve impedir novos acessos sem apagar o histórico de operações realizadas.
- A associação entre funcionário e usuário deve ser suficientemente clara para auditoria.

### Perfil de acesso

Representa o conjunto de permissões que define quais operações um usuário interno pode executar.

#### Responsabilidade

- Organizar permissões por função, como atendimento, gerência ou administração.
- Impedir acesso indevido a dados e operações sensíveis.

#### Principais informações

- nome do perfil;
- permissões concedidas;
- situação do perfil.

#### Relacionamentos

- Um perfil pode ser atribuído a vários usuários internos.
- Um usuário interno pode possuir um ou mais papéis, conforme a política adotada.

#### Regras estruturais importantes

- Permissões administrativas e financeiras devem ser concedidas somente a perfis autorizados.
- Alterações de permissões devem ser rastreáveis.

### Registro de evento

Representa o registro de uma ação relevante realizada no sistema, especialmente sobre dados sensíveis ou mudanças de estado.

#### Responsabilidade

- Fornecer rastreabilidade para operações administrativas e operacionais.
- Apoiar auditoria, investigação de inconsistências e acompanhamento da segurança.

#### Principais informações

- usuário responsável;
- tipo de ação;
- recurso afetado;
- data e hora;
- resultado da operação;
- contexto necessário para auditoria.

#### Relacionamentos

- Um registro de evento pode estar associado a um usuário interno.
- Pode referenciar locações, devoluções, pagamentos, multas, clientes, exemplares ou configurações alteradas.

#### Regras estruturais importantes

- Eventos relevantes não devem ser apagados como forma de corrigir o histórico.
- O log deve evitar armazenar dados sensíveis desnecessários.

## 4. Conceitos derivados e visões do domínio

### Disponibilidade do exemplar

Disponibilidade é o estado operacional derivado da situação do exemplar e de suas locações ativas. Não é necessariamente uma entidade independente.

Um exemplar pode estar disponível, alugado, reservado, indisponível, em manutenção, perdido ou baixado, conforme os estados que forem definidos nas regras detalhadas. A consulta de filmes disponíveis deve considerar exemplares realmente locáveis, e não apenas filmes ativos no catálogo.

### Histórico de locações

É a visão formada pelas locações e devoluções já registradas para um cliente ou exemplar. O histórico não deve exigir uma entidade separada se puder ser obtido a partir dos registros preservados.

### Relatórios

São visões consolidadas dos dados operacionais. Relatórios de locações podem combinar locações, devoluções, multas e pagamentos; o relatório de filmes mais alugados deve contar as locações por filme sem confundir quantidade de filmes com quantidade de exemplares.

## 5. Regras e invariantes principais

- Cada exemplar pertence a um único filme.
- Cada locação pertence a um único cliente e utiliza um único exemplar.
- Um exemplar não pode estar em duas locações ativas ao mesmo tempo.
- Um cliente bloqueado não pode iniciar uma nova locação.
- Uma locação ativa deve manter seu exemplar como não disponível para outra locação.
- Uma devolução deve estar vinculada a uma locação existente.
- A devolução deve atualizar a situação do exemplar de acordo com sua condição.
- Uma multa deve preservar o motivo e o valor calculados no momento da geração ou da última alteração autorizada.
- Um pagamento deve estar vinculado a uma obrigação identificável e refletir o saldo correspondente.
- Nenhuma correção operacional deve apagar o histórico da operação original.
- Operações sensíveis devem ser executadas por usuário autorizado e, quando aplicável, registradas em eventos de auditoria.

## 6. Decisões ainda em aberto

O modelo conceitual não fixa decisões que dependem de regras futuras, incluindo:

- se uma locação poderá conter vários exemplares ou se cada exemplar terá uma locação independente;
- se haverá reservas e por quanto tempo elas bloquearão exemplares;
- a fórmula exata da multa, períodos de tolerância e regras de arredondamento;
- quais pendências causam bloqueio automático do cliente;
- se pagamentos parciais, estornos e outros ajustes serão suportados;
- os estados completos do exemplar e da locação;
- os dados obrigatórios do cadastro de filmes, exemplares, clientes e funcionários.

Essas decisões devem ser detalhadas nas especificações de cada mudança antes de serem tratadas como contratos definitivos de implementação.

## 7. Relação com a persistência

Este documento descreve conceitos e relacionamentos do domínio, não um esquema físico de banco de dados. A implementação em Xano/XanoScript pode decompor, combinar ou materializar esses conceitos em tabelas, APIs, funções e visões, desde que preserve as responsabilidades, relacionamentos e invariantes aqui definidos.

