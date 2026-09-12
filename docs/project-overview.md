# Project Overview — Sistema de Gestão para Locadora de Filmes

## 1. Visão geral

Este projeto consiste em um sistema de gestão para uma locadora de filmes. A aplicação centralizará o cadastro do acervo, o atendimento aos clientes e o controle do ciclo completo de uma locação, desde a retirada de um exemplar até a devolução e o pagamento de eventuais multas.

O sistema deve servir como fonte operacional para a equipe da locadora, reduzindo controles manuais e tornando mais confiáveis as informações sobre clientes, filmes, exemplares, disponibilidade, locações e pagamentos. As especificações poderão ser ampliadas ou ajustadas conforme as necessidades do negócio forem melhor compreendidas.

## 2. Problema

Uma locadora precisa controlar simultaneamente seu catálogo, várias cópias do mesmo filme, a situação de cada exemplar, os prazos de devolução e as pendências financeiras dos clientes. Sem um sistema centralizado, é fácil perder informações, disponibilizar um exemplar já alugado, calcular multas de forma inconsistente ou permitir novas locações para clientes inadimplentes.

O projeto busca organizar essas informações em um fluxo único, com regras claras, histórico consultável e rastreabilidade das operações realizadas pelos usuários da equipe.

## 3. Objetivos

- Centralizar os dados da locadora em um sistema confiável e de fácil consulta.
- Controlar o acervo físico e a disponibilidade real de cada exemplar.
- Registrar locações, devoluções, multas e pagamentos de forma consistente.
- Apoiar o atendimento com consultas rápidas sobre clientes, filmes e pendências.
- Impedir operações incompatíveis com as regras do negócio, como locações para clientes bloqueados.
- Disponibilizar históricos e relatórios para acompanhamento da operação e tomada de decisão.

## 4. Público-alvo e usuários

Os principais usuários são:

- **Atendentes:** cadastram clientes, consultam o acervo, realizam locações, registram devoluções e pagamentos.
- **Gerentes ou administradores:** acompanham a operação, gerenciam usuários e funcionários, consultam relatórios e supervisionam regras e permissões.
- **Funcionários autorizados:** executam as tarefas operacionais permitidas pelo seu perfil de acesso.
- **Clientes da locadora:** são a origem dos contratos, históricos, pagamentos e bloqueios, ainda que o acesso direto ao sistema não esteja definido para o escopo inicial.

## 5. Escopo inicial

O escopo inicial contempla o backoffice da locadora e o controle das seguintes entidades e processos:

- clientes;
- filmes e seus exemplares físicos;
- disponibilidade do acervo;
- locações e devoluções;
- multas por atraso;
- pagamentos;
- histórico de locações;
- usuários, funcionários e permissões;
- relatórios operacionais.

O escopo inicial não define, neste momento, um aplicativo voltado diretamente aos clientes, integração com meios de pagamento, integração com fornecedores ou canais externos de comunicação. Essas possibilidades poderão ser avaliadas em futuras evoluções.

## 6. Principais funcionalidades

### Cadastros e acervo

1. **Cadastro de clientes:** manter dados cadastrais, situação e informações necessárias para o atendimento.
2. **Cadastro de filmes:** registrar os dados do filme que compõe o catálogo.
3. **Cadastro de exemplares:** controlar cada cópia física, seu identificador e sua situação individual.
4. **Controle de disponibilidade:** indicar se um exemplar está disponível, alugado, reservado, indisponível ou em outra situação definida pela operação.
5. **Consulta de filmes disponíveis:** permitir localizar filmes e exemplares que podem ser alugados.

### Operação de locações

6. **Registro de locações:** associar cliente, filme ou exemplar, data da locação, prazo e situação da operação.
7. **Registro de devoluções:** registrar a devolução, atualizar a disponibilidade do exemplar e identificar atrasos ou pendências.
8. **Cálculo de multas por atraso:** calcular valores conforme o prazo contratado e as regras de negócio vigentes.
9. **Controle de pagamentos:** registrar pagamentos relacionados a locações e multas, mantendo seus valores, datas e situação.
10. **Histórico de locações:** consultar locações anteriores, devoluções, atrasos e pagamentos de cada cliente.
11. **Consulta de locações em atraso:** localizar rapidamente contratos ainda não devolvidos no prazo.
12. **Bloqueio de clientes inadimplentes:** impedir novas operações quando houver pendências que, de acordo com as regras definidas, exijam bloqueio.

### Administração e acompanhamento

13. **Controle de usuários e funcionários:** cadastrar usuários internos, definir perfis e controlar o acesso às operações autorizadas.
14. **Relatórios de locações:** apresentar informações consolidadas sobre locações, devoluções, atrasos e pagamentos.
15. **Relatórios de filmes mais alugados:** identificar a procura pelo catálogo para apoiar decisões de aquisição e gestão do acervo.

Os detalhes de telas, endpoints, campos, fórmulas exatas e fluxos de exceção deverão ser definidos nas especificações das mudanças correspondentes, sem antecipar essas decisões neste documento.

## 7. Requisitos e restrições importantes

- A disponibilidade deve refletir o estado real de cada exemplar, e não apenas o cadastro geral do filme.
- Uma locação deve estar vinculada a um cliente e a um exemplar identificável.
- Devoluções, multas e pagamentos precisam preservar o histórico das operações e não apagar informações já registradas.
- As regras para prazo, valor de multa, tolerância e bloqueio devem ser explícitas e configuráveis quando isso for necessário.
- O sistema deve impedir locações para clientes bloqueados ou para exemplares indisponíveis.
- Operações que alteram o acervo, a situação financeira ou o status de uma locação devem ser rastreáveis.
- Dados pessoais e financeiros devem ser acessíveis somente a usuários autorizados.
- A solução deve permitir evolução futura sem tornar o histórico existente inconsistente.
- A interface para clientes, notificações automáticas e integrações externas não fazem parte do compromisso inicial até que sejam formalmente especificadas.

## 8. Arquitetura tecnológica

Até o momento, a base técnica definida no repositório é:

- **Xano** como plataforma de backend, dados e APIs.
- **XanoScript** para funções, APIs e automações mantidas no repositório.
- Autenticação de usuários, controle de papéis e registro de eventos como fundamentos de segurança e rastreabilidade já representados na estrutura do projeto.

A tecnologia do frontend, a estratégia de hospedagem e eventuais integrações externas ainda não estão definidas neste overview. Essas decisões devem ser documentadas quando forem confirmadas.

## 9. Princípios de desenvolvimento

- Priorizar regras de negócio explícitas e consistentes.
- Manter separadas as informações do filme e de cada exemplar físico.
- Preservar histórico e rastreabilidade em vez de sobrescrever fatos operacionais importantes.
- Aplicar o princípio do menor privilégio aos usuários internos.
- Preferir mudanças pequenas, testáveis e compatíveis com os dados já existentes.
- Documentar decisões que afetem contratos, cálculos, permissões ou integridade dos registros.
- Tratar este documento como uma visão do produto, deixando o detalhamento de cada evolução para suas respectivas especificações.

## 10. Segurança e integridade

O acesso ao sistema deve exigir autenticação e respeitar o perfil do usuário. Operações administrativas e alterações sensíveis devem ser limitadas a funcionários autorizados e, quando aplicável, registradas em logs de eventos.

A integridade dos dados é especialmente importante nas transições de uma locação: criação, devolução, cálculo de multa, pagamento e atualização da disponibilidade do exemplar. Essas operações devem evitar estados contraditórios, como um exemplar simultaneamente disponível e alugado ou uma multa marcada como paga sem um pagamento registrado.

## 11. Estratégia de desenvolvimento

O desenvolvimento deve evoluir por fatias funcionais, começando pela fundação de autenticação, usuários e dados essenciais. Em seguida, devem ser implementados o cadastro do acervo, a disponibilidade, o fluxo de locação e devolução, as multas e pagamentos, e por fim os relatórios e melhorias administrativas.

Cada evolução deve definir seus próprios comportamentos, validações, permissões e critérios de aceite. Mudanças que afetem locações, disponibilidade, multas ou pagamentos devem receber atenção especial, pois podem impactar diretamente a operação e os registros financeiros da locadora.

## 12. Fonte de verdade e documentação

Este documento apresenta a visão geral e o escopo atual do produto. Ele não substitui as especificações detalhadas de cada mudança.

- A visão e o escopo geral devem ser mantidos em `docs/project-overview.md`.
- As especificações detalhadas e decisões de mudanças devem ser mantidas em `openspec/`.
- A implementação de backend, APIs, funções, tabelas e configurações Xano deve ser mantida em `xano/`.
- Quando houver conflito, uma decisão mais recente e formalmente documentada deve atualizar este overview e indicar qual comportamento passa a ser o vigente.
