# Design

## Context

Veja [proposal.md](./proposal.md) para a motivação. O repositório possui autenticação e autorização por `member/admin`, auditoria mínima, um catálogo Xano completo e páginas Reflex protegidas, mas não possui tabela, API, tipos ou interface de clientes. O endpoint de catálogo indicado pelo usuário confirma o padrão atual: grupo de API com `auth = "user"`, `Quick Start/enforce_role` antes do acesso ao banco, seleção explícita de campos e filtros executados no Xano.

Clientes introduzem PII e serão referenciados por locações e obrigações financeiras futuras. A implementação precisa evitar duas antecipações perigosas: armazenar saldo financeiro derivado no cadastro do cliente e representar ausência dos módulos de locação/pagamento como histórico vazio ou saldo zero confirmado.

## Goals / Non-Goals

**Goals:**

- Definir um modelo persistente de cliente com CPF brasileiro único e identidade estável.
- Reutilizar a autorização e auditoria existentes, mantendo PII fora de respostas desnecessárias e logs.
- Oferecer busca paginada, detalhe, criação, atualização, situação cadastral e bloqueio manual por contratos Xano explícitos.
- Integrar a capacidade ao Reflex com estados distintos de carregamento, vazio, erro, sucesso e dependência futura.
- Criar uma fronteira segura para futuras locações, multas e pagamentos sem acoplar o cadastro a dados ainda inexistentes.

**Non-Goals:**

- Implementar locação, devolução, multa, pagamento, cobrança, saldo, histórico operacional ou bloqueio financeiro.
- Permitir que `member` altere cadastros ou bloqueios manuais.
- Criar autoatendimento ou API pública para clientes.
- Excluir registros de cliente ou armazenar endereço nesta primeira versão.
- Alterar a política vigente de autenticação, papéis ou cadastro público de usuários internos.

## Decisions

### 1. Modelo `customer` mínimo e preparado para referências futuras

A tabela Xano `customer` terá:

- `id` inteiro gerado;
- `created_at` e `updated_at`;
- `nome` obrigatório, trim, máximo de 200 caracteres;
- `cpf` obrigatório, persistido com onze dígitos;
- `email` opcional, trim e lowercase, máximo de 254 caracteres;
- `telefone` opcional, persistido somente com dígitos brasileiros, com 10 ou 11 dígitos;
- `status` enum `active|inactive`, default `active`;
- `bloqueio_manual_ativo` booleano, default `false`;
- `motivo_bloqueio_manual` opcional, máximo de 500 caracteres;
- `bloqueado_em` e `bloqueado_por` opcionais para o estado manual atual.

Haverá índice primário em `id`, índice único em `cpf`, índice de busca em `nome` e índice em `status`. O índice único, além da validação antecipada, é a garantia contra duplicidade concorrente.

`status` e `bloqueio_manual_ativo` permanecem campos independentes. Ao remover o bloqueio atual, os campos de motivo, data e responsável atuais são limpos; a transição permanece no `event_log`, sem o texto do motivo. Nenhum campo `saldo`, `pendencia`, `multa`, `bloqueio_financeiro` ou lista de locações será criado em `customer`: esses valores serão derivados dos domínios de origem quando existirem.

Alternativas consideradas:

- CPF opcional ou identificador interno como única deduplicação: rejeitado porque não satisfaz a identificação acordada e permite cadastros duplicados.
- Campo único de status contendo `active`, `inactive` e `blocked`: rejeitado porque mistura encerramento cadastral com impedimento operacional.
- Saldo e bloqueio financeiro no cliente: rejeitado por duplicar estado financeiro e criar inconsistência futura.

### 2. Normalização e validação de CPF centralizadas no backend

Uma função Xano reutilizável normalizará CPF removendo pontuação permitida e validará tamanho, sequências repetidas e dígitos verificadores. Criação, atualização e busca exata reutilizarão a mesma regra. A interface poderá validar para resposta rápida, mas o backend continuará sendo a autoridade.

CPF será tratado como texto, nunca como número, para preservar zeros à esquerda. A listagem produzirá `cpf_mascarado` no backend e não retornará `cpf`; apenas o endpoint protegido de detalhe retornará o valor completo.

Alternativa considerada: validar somente no Reflex. Rejeitada porque chamadas diretas à API poderiam contornar a regra e porque a restrição de unicidade pertence à persistência.

### 3. Grupo de API e contratos separados por finalidade

Será criado o grupo de API Xano `Clientes`, com URL própria configurada por `XANO_CUSTOMER_API_URL`, seguindo a separação já adotada entre Authentication e Catálogo de Filmes.

Contratos propostos:

- `GET /clientes`: exige `member`; aceita `nome`, `cpf`, `page` e `per_page`; retorna `{items, page, per_page, total}` com `per_page` default 20 e máximo 50. Cada item contém apenas `id`, `nome`, `cpf_mascarado`, `status` e `bloqueio_manual_ativo`.
- `GET /clientes/{id}`: exige `member`; retorna o cadastro completo permitido ou `404`.
- `POST /clientes`: exige `admin`; cria com `status=active` e sem bloqueio manual; retorna `{customer, audit_succeeded}`.
- `PATCH /clientes/{id}`: exige `admin`; atualiza nome, CPF, contatos e situação cadastral; não altera bloqueio manual; retorna `{customer, audit_succeeded}`.
- `PATCH /clientes/{id}/bloqueio-manual`: exige `admin`; recebe `bloqueado` e, quando `true`, motivo obrigatório; controla somente o bloqueio manual atual e retorna `{customer, audit_succeeded}`.

O filtro por nome usa trecho sem distinção de caixa. CPF informado para busca deve representar um CPF completo; buscas parciais por documento não serão aceitas, reduzindo enumeração e resultados ambíguos. Não haverá endpoint `DELETE`.

Alternativas consideradas:

- Um único `PATCH` para todos os campos: rejeitado para evitar alterações acidentais do bloqueio e permitir auditoria inequívoca de `block_customer` e `unblock_customer`.
- Retornar lista simples sem paginação: rejeitado porque a cardinalidade de clientes tende a crescer e PII não deve ser carregada sem limite.

### 4. Autorização antes do acesso a PII e auditoria pós-gravação

Todos os endpoints terão `auth = "user"` e executarão `Quick Start/enforce_role` antes de ler ou alterar `customer`. Consultas exigem `member`; gravações exigem `admin`. A UI ocultará ações administrativas de `member`, mas isso será apenas uma conveniência visual.

Criação, atualização, mudança de situação, bloqueio e desbloqueio usarão `Quick Start/log_event` com ações distintas, `resource_type=customer` e `resource_id`. CPF, nome, contatos, motivo e objetos completos não serão enviados ao log. Como o padrão Xano atual não confirma transação atômica entre tabela e helper de auditoria, respostas de escrita manterão `audit_succeeded`; o cliente Reflex distinguirá gravação confirmada de falha posterior de auditoria e não repetirá automaticamente a operação.

Alternativa considerada: registrar CPF mascarado no evento para facilitar busca. Rejeitada porque o `customer.id` é suficiente para rastreabilidade e evita ampliar PII no log.

### 5. Cliente Python reutiliza transporte autenticado sem acoplar domínios

O transporte Windows/cURL e HTTPX existente será extraído ou generalizado para receber a URL base, rota, método, token, parâmetros e corpo, preservando timeout, captura segura de request ID e ausência do token na linha de comando/log. Autenticação, catálogo e clientes conservarão seus adaptadores de domínio e mensagens específicas.

Um módulo `clientes.py` conterá `TypedDict`, normalização/mascara de CPF e validações de formulário. O adaptador Xano validará rigorosamente os formatos distintos de resumo, detalhe, paginação e escrita antes de atualizar o estado Reflex.

Alternativa considerada: copiar `_catalog_request` para clientes. Rejeitada porque duplicaria o caminho TLS sensível e aumentaria o risco de divergência entre integrações.

### 6. Fluxo Reflex com detalhe preparado, sem histórico fictício

Rotas planejadas:

- `/clientes`: listagem paginada e busca por nome ou CPF;
- `/clientes/novo`: criação para `admin`;
- `/clientes/[customer_id]`: detalhe protegido para `member/admin`;
- `/clientes/[customer_id]/editar`: edição para `admin`.

A listagem mostrará nome, CPF mascarado, situação e bloqueio. O detalhe mostrará os dados completos admitidos, controles administrativos condicionais ao papel e um painel “Histórico e pendências” com estado explícito “aguardando implementação de locações, multas e pagamentos”. Não serão exibidos contadores com zero, saldo `R$ 0,00` ou lista vazia como se fossem dados consultados.

O estado Reflex continuará mantendo o token apenas no servidor. Estados e mensagens de clientes serão separados dos de filmes para que falhas de um módulo não apaguem resultados ou feedback do outro.

### 7. Integração financeira futura será derivada e orientada a pagamento

A futura capacidade financeira associará locações, multas e pagamentos por `customer.id`. Ela calculará pendências e eventual bloqueio financeiro a partir das obrigações, sem reusar `bloqueio_manual_ativo`. Conforme a política atual, `member` poderá registrar multa e pagamento válidos, mas não ajustar ou remover manualmente um bloqueio financeiro; a elegibilidade será liberada somente quando a regra futura confirmar a quitação necessária.

Essa decisão é documentada agora para impedir que a primeira versão crie um atalho de “desbloquear pendência” no cadastro do cliente.

## Risks / Trade-offs

- **[CPF e contato são PII]** → Minimizar campos na listagem, autenticar todas as rotas, manter token no servidor e proibir PII em auditoria e logs técnicos.
- **[Busca por nome pode crescer e ser custosa]** → Paginação obrigatória, limite máximo por página e índice em nome; revisar estratégia de busca somente com volume real.
- **[Validação antecipada não impede corrida de duplicidade]** → Índice único em CPF como garantia final e mapeamento do conflito para mensagem compreensível.
- **[Falha de auditoria após persistência]** → Resposta parcial explícita e proibição de retry automático, seguindo o padrão já adotado no catálogo.
- **[Motivo de bloqueio pode conter PII livre]** → Limite de tamanho, acesso somente no detalhe protegido e exclusão do texto dos eventos de auditoria.
- **[Placeholder de histórico pode ser confundido com funcionalidade entregue]** → Texto explícito de dependência futura e ausência de valores ou ações financeiras.
- **[Refatorar o transporte pode afetar catálogo e autenticação]** → Preservar contratos públicos e adicionar testes de regressão para URLs, headers, timeouts, sigilo do token e tratamento de erros dos módulos existentes.

## Migration Plan

1. Criar e validar a tabela `customer`, os índices e as funções auxiliares diretamente no branch Xano `v1`, conforme a política operacional do projeto.
2. Publicar o grupo `Clientes` e seus endpoints somente após testes de autorização, minimização de respostas, CPF concorrente e auditoria.
3. Registrar o `canonical` do grupo no export e configurar `XANO_CUSTOMER_API_URL` sem reutilizar a URL de Authentication ou Catálogo.
4. Entregar o transporte/cliente Python e as páginas Reflex com testes antes de adicionar a navegação do backoffice.
5. Executar teste ponta a ponta no branch `v1` com `member` e `admin`, incluindo token de conta desativada e verificação de que PII não aparece no log.

Não há dados de clientes existentes para migrar. Em rollback, remover navegação e desabilitar os endpoints, preservando tabela e registros para investigação; não apagar dados pessoais automaticamente. A restauração posterior deverá reutilizar o mesmo contrato e identificadores.
