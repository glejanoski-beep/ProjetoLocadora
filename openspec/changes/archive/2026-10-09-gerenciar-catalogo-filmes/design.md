# Design

## Contexto

O backoffice Reflex atual protege as páginas internas com `State.require_session` e mantém o token Xano em estado somente do servidor. O cliente HTTP existente atende autenticação e recuperação de senha; não há cliente de filmes. A exportação `xano/xano/table/` contém `user` e `event_log`, sem tabela de filmes ou endpoints de catálogo.

O modelo conceitual em `docs/domain-model.md` identifica filme separado de exemplar e cita título, gênero/categoria, classificação indicativa, ano de lançamento e situação no catálogo como informações principais. A definição inicial recebida para esta Change acrescenta/organiza os conceitos `id_filme`, `titulo`, `genero`, `ano_lancamento`, `classificacao`, `valor_locacao`, `qtd_estoque` e `status`. A busca no código, documentação, specs e Changes arquivadas não encontrou tabela ou contrato técnico de filmes: os nomes e conceitos fornecidos são base de planejamento, não confirmação de nomes de coluna, tipos, defaults, obrigatoriedade ou enumerações. A política ativa `acesso-seguro` autoriza `member` a consultar cadastros e exige `admin` para criar ou alterar cadastros. O registro de alterações administrativas deve preservar rastreabilidade com os metadados mínimos de `auditoria-segura`.

## Objetivos e não objetivos

**Objetivos:**

- Entregar uma fatia vertical de catálogo com interface Reflex e operações reais de leitura e gravação no Xano.
- Usar os atributos conceituais fornecidos como base para confirmar um contrato de filme compatível com o domínio.
- Centralizar busca e filtro compatíveis com o modelo no contrato de consulta Xano.
- Aplicar permissões e validações no backend, não somente na interface.
- Mostrar estados vazios, validação, sucesso e falha de forma explícita.

**Não objetivos:**

- Administrar exemplares, estoque, disponibilidade ou locações.
- Executar qualquer ação sobre `qtd_estoque`, inclusive movimentação, cálculo, ajuste, disponibilidade ou associação com exemplares; o atributo pode existir no schema sem ser operado por esta Change.
- Excluir filmes ou introduzir relacionamentos não existentes.
- Definir campos ou regras de domínio sem uma fonte aprovada.
- Usar dados em memória, fixtures ou mocks como persistência da funcionalidade.
- Acessar ou alterar o Xano remoto nesta Change sem autorização explícita.

## Decisões

### 1. Schema aprovado para a Change

Os documentos de domínio, código, specs e Changes arquivadas consultados não definem uma tabela de filmes. `docs/domain-model.md` confirma os conceitos de título, gênero/categoria, classificação indicativa, ano de lançamento e situação no catálogo; também determina que filme e exemplar físico são conceitos separados. A tabela abaixo registra decisões aprovadas para esta Change; isso não significa que o schema já exista no Xano/repositório.

| Conceito recebido | Campo técnico aprovado | Tipo Xano | Obrigatoriedade e validações aprovadas | Origem / edição | Situação no projeto |
|---|---|---|---|---|---|
| `id_filme` | `id` | `int`, chave primária | Obrigatório, único e gerado pelo Xano | Automático; não enviado nem editável | Tabelas locais `user` e `event_log` usam `int id` (fato observado); uso aprovado para filme. |
| `titulo` | `titulo` | `text` | Obrigatório; trim; não vazio; máximo de 200 caracteres | Informado e editável por `admin` | O domínio documenta o título; tipo, limite e validações foram aprovados para esta Change. |
| `genero` | `genero` | `text` | Obrigatório; trim; não vazio; máximo de 100 caracteres; sem lista fechada | Informado e editável por `admin` | O domínio documenta gênero/categoria; tipo e validações foram aprovados para esta Change. |
| `ano_lancamento` | `ano_lancamento` | `int` | Obrigatório; entre 1888 e o ano corrente, inclusive | Informado e editável por `admin` | O domínio documenta ano de lançamento; tipo e faixa foram aprovados para esta Change. |
| `classificacao` | `classificacao` | `enum` textual | Obrigatório; somente `Livre`, `10 anos`, `12 anos`, `14 anos`, `16 anos`, `18 anos` | Selecionado e editável por `admin` | O domínio documenta classificação indicativa; tipo e valores foram aprovados para esta Change. |
| `valor_locacao` | `valor_locacao_centavos` | `int` | Obrigatório; inteiro não negativo | Recebido/exibido em reais pela interface e convertido a centavos; editável por `admin` | Preço e precisão não eram definidos pelo domínio; inteiro em centavos e conversão na interface foram aprovados para esta Change. |
| `qtd_estoque` | **Pendente** | **Não definido nesta Change** | Sem default; não informado nem alterado | Não editável; preservar/omitir sem mutação | O domínio separa filme e exemplar (fato documentado). Compatibilidade e eventual representação do campo permanecem pendentes; não bloqueiam o restante se puder ser omitido sem violar o schema existente. |
| `status` | `status` | `enum` textual | Obrigatório; `active` ou `inactive`; default `active` | Default automático na criação; somente `admin` pode alterar | O domínio menciona situação cadastral e filmes inativos que permanecem no histórico; enumeração, default e autorização foram aprovados. Não representa disponibilidade. |

O campo de chave técnica é `id`; `id_filme` é o conceito de origem e não será duplicado como outra coluna. Os tipos/constraints devem ser representados usando a sintaxe XanoScript válida ao implementar.

`qtd_estoque` não recebe valor inicial nesta Change, não será campo de criação/edição e não será alterado. Antes de determinar sua existência ou representação, verificar a compatibilidade com o modelo de filmes e exemplares. A verificação não exige consultar o Xano remoto; se não houver definição local que resolva a questão, manter a pendência e prosseguir com as operações de catálogo que não dependam do campo.

Os valores monetários serão exibidos/recebidos na interface em reais e convertidos para um número inteiro não negativo de centavos para persistência. Não aplicar aritmética com ponto flutuante para representar o valor persistido.

O schema aprovado ainda não existe no export local. Implementar sua definição local versionada e alinhar forms, endpoints e validações Reflex/Xano ao contrato, sem consultar nem alterar o Xano remoto.

### 2. Permissões no backend

Aplicar a política ativa:

| Operação | Papel mínimo |
|---|---|
| Listar, buscar e filtrar filmes | `member` |
| Criar filme | `admin` |
| Editar filme e alterar `status` | `admin` |

Os endpoints exigem autenticação, revalidam o estado e o papel atuais da conta por meio dos padrões Xano existentes e verificam o papel mínimo antes de consultar dados protegidos ou gravar. Ocultar controles na interface para `member` não substitui essa autorização. Não oferecer exclusão nesta Change; a alteração cadastral de `status` para `inactive` continua sendo edição administrativa do filme e não indica disponibilidade física.

### 3. Operações Xano como fonte de verdade

Disponibilizar `GET /catalogo-filmes/filmes` para consulta/listagem, `POST /catalogo-filmes/filmes` para criação, e `GET`/`PATCH /catalogo-filmes/filmes/{id}` para carregar/editar um registro. Listagem aceita `titulo` (trecho sem distinção de caixa) e `genero` (valor textual exato) no contrato Xano. Todos os endpoints exigem autenticação e revalidam o papel atual com `Quick Start/enforce_role`; consulta exige `member` e gravação exige `admin`. Criação/edição retornam `{film, audit_succeeded}` para distinguir gravação confirmada de eventual falha no helper de auditoria. O cliente só informa sucesso integral quando ambos os resultados são confirmados. Nenhum contrato lê, envia ou atualiza `qtd_estoque`.

Esses contratos estão versionados localmente seguindo os padrões XanoScript disponíveis. Não há endpoints de filmes existentes no export para preservar; rotas, verbos e payloads são decisões técnicas desta implementação local, ainda sem verificação no runtime Xano.

### 4. Experiência Reflex

Adicionar uma entrada de navegação para o catálogo no backoffice. Propor as rotas `/filmes`, `/filmes/novo` e `/filmes/[id]/editar`, protegidas pela sessão existente. A listagem permite buscar por trecho do título sem distinção entre maiúsculas/minúsculas e filtrar pelo campo textual `genero`; a interface não deve criar lista fechada de gêneros nem aplicar filtro local que divirja do conjunto consultado pelo Xano.

Os formulários não expõem `id` nem `qtd_estoque`; o Xano gera `id`. Nenhum default de estoque será definido nesta Change. A edição não inclui `qtd_estoque` no payload e preserva o valor existente se o campo fizer parte do schema. A interface de `admin` pode alterar `status` entre `active` e `inactive`. A entrada monetária é apresentada em reais e convertida para centavos. A edição carrega o filme existente do Xano e preserva campos não editáveis. Exibir mensagens de sucesso somente após resposta bem-sucedida do backend. Diferenciar lista vazia de falha de consulta e informar falha de gravação sem expor detalhes internos ou segredos.

### 5. Auditoria mínima das alterações

Reutilizar `Quick Start/log_event` após criação ou edição confirmada, com usuário autenticado, ação, resultado, `resource_type` e o identificador confirmado pelo Xano. Não registrar o objeto completo, credenciais, token ou dados que não sejam necessários à rastreabilidade. A operação e sua auditoria devem ter resultado explícito; eventual falha de auditoria após uma gravação confirmada não pode ser apresentada como se a gravação tivesse sido revertida nem como sucesso integral. A estratégia de tratamento deve ser definida conforme as garantias de execução/transação disponíveis no Xano, sem alegar atomicidade não verificada.

### 6. Verificação sem ambiente Xano separado

Testes locais podem verificar validação, estado Reflex, tratamento de erros, contratos do cliente HTTP com transporte simulado e estrutura dos stacks XanoScript. Esses testes não demonstram persistência ou autorização no runtime Xano. Não executar requisições ao serviço remoto. Registrar a integração/runtime como não verificada até existir autorização explícita para executá-la.

## Decisões pendentes

- Verificar se `qtd_estoque` deve existir no modelo de filme ou pertencer exclusivamente ao futuro modelo de exemplares; não definir valor inicial nem alterar o campo nesta Change. Esta pendência não bloqueia o restante do catálogo se tecnicamente puder ser omitida dos contratos desta fatia.
- Compatibilidade futura de `qtd_estoque`, como descrita acima.
- Confirmação no runtime Xano das rotas locais, comportamento da consulta e do envelope de resposta de auditoria.
- Autorização futura para qualquer verificação integrada no Xano remoto; não é concedida por esta Change.

## Riscos e trade-offs

- **Schema técnico ausente localmente:** o schema aprovado deve ser versionado na aplicação local antes da integração; não alegar que já existe no Xano remoto.
- **`qtd_estoque` conflita ou duplica o futuro modelo de exemplares:** manter sem default e sem mutação; prosseguir sem esse campo se os contratos puderem omiti-lo.
- **`status` confundido com disponibilidade:** restringir seus valores à situação do filme no catálogo, sem inferir disponibilidade de exemplar.
- **Cliente pode indicar sucesso sem persistência:** Mitigação: só confirmar após resposta Xano bem-sucedida e cobrir falhas no tratamento Reflex.
- **Proteção somente no frontend:** permitiria chamadas diretas por `member`. Mitigação: exigir `admin` no backend em criação/edição.
- **Gravação e auditoria podem falhar em momentos diferentes:** o contrato local expõe o resultado parcial e o cliente recomenda não reenviar cegamente; runtime/transação ainda não verificados.
- **Testes locais não exercitam Xano:** não comprovam persistência, autorização no runtime nem auditoria efetiva. Mitigação: declarar esse limite e não acessar o remoto sem autorização.
