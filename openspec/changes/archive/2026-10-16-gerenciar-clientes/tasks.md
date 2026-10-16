# Tasks

## 1. Modelo e validações de cliente

- [x] 1.1 Criar a tabela Xano `customer` com campos, defaults, referências e índices definidos no design, e verificar por dry-run/import no branch `v1` que CPF possui índice único e nenhum campo financeiro ou histórico foi introduzido.
- [x] 1.2 Implementar funções Xano reutilizáveis para normalizar/validar CPF e mascarar o documento, e verificar casos válidos com e sem pontuação, zero à esquerda, sequência repetida, dígitos verificadores inválidos e CPF parcial.
- [x] 1.3 Criar o módulo Python de clientes com tipos, normalização/máscara de CPF e validações de formulário, e verificar por testes unitários nome, CPF, e-mail, telefone, status, bloqueio e exigência de ao menos um contato.

## 2. APIs Xano protegidas e auditadas

- [x] 2.1 Criar o grupo `Clientes` e o endpoint paginado `GET /clientes` com filtros de nome/CPF, autorização `member` e projeção mínima, e verificar que resultados omitem CPF completo e contatos, buscas vazias retornam `items=[]` e `per_page` não excede 50.
- [x] 2.2 Implementar `GET /clientes/{id}` com autorização `member`, resposta de detalhe explicitamente projetada e `404` para id ausente, e verificar que chamadas anônimas, contas desativadas e papéis inválidos não recebem PII.
- [x] 2.3 Implementar `POST /clientes` com autorização `admin`, validação backend, defaults e tratamento do índice único, e verificar criação válida, CPF duplicado sequencial/concorrente, ausência de contato e recusa de `member` sem gravação.
- [x] 2.4 Implementar `PATCH /clientes/{id}` para dados cadastrais e situação, sem aceitar id ou bloqueio manual no payload, e verificar atualizações válidas, CPF conflitante, cliente inexistente, campos inesperados e recusa de `member`.
- [x] 2.5 Implementar `PATCH /clientes/{id}/bloqueio-manual` com motivo obrigatório para bloquear e limpeza do estado atual ao desbloquear, e verificar independência de `status`, preservação do estado após entrada inválida e autorização exclusiva de `admin`.
- [x] 2.6 Integrar `Quick Start/log_event` às escritas com ações distintas e resposta `audit_succeeded`, e verificar que eventos contêm somente usuário, ação, resultado, `resource_type=customer` e `resource_id`, sem CPF, nome, contato, motivo ou objeto completo.

## 3. Configuração e integração Python com Xano

- [x] 3.1 Adicionar `XANO_CUSTOMER_API_URL` à configuração local e sua validação contra grupos incorretos, e verificar por testes que Authentication, Catálogo e Clientes resolvem URLs independentes e falham com mensagem clara quando ausentes ou reutilizadas indevidamente.
- [x] 3.2 Extrair/generalizar o transporte autenticado comum de HTTPX e cURL/Schannel sem alterar os contratos públicos existentes, e verificar os testes de regressão de login e catálogo para URL, query, corpo, timeout, request ID e ausência de token/PII em comando e logs.
- [x] 3.3 Implementar o adaptador de clientes para listagem, detalhe, criação, atualização e bloqueio, e verificar por testes de contrato paginação, formatos de resumo/detalhe, conflitos, `404`, autorização, payload inválido e sucesso parcial de auditoria.

## 4. Interface Reflex de clientes

- [x] 4.1 Adicionar estado e eventos isolados para busca paginada de clientes, e verificar por testes do State os estados de carregamento, vazio, erro, troca de página, filtros e preservação independente do estado do catálogo de filmes.
- [x] 4.2 Criar `/clientes` e `/clientes/novo` com listagem mínima e formulário administrativo, e verificar que `member` pesquisa sem ver ações de manutenção, `admin` cadastra e o frontend não envia campos financeiros ou de bloqueio no endpoint cadastral.
- [x] 4.3 Criar `/clientes/[customer_id]` e `/clientes/[customer_id]/editar` com detalhe protegido, edição, situação e controle separado de bloqueio manual, e verificar redirecionamento por papel, cliente inexistente, motivo obrigatório e feedback de auditoria parcial.
- [x] 4.4 Adicionar ao detalhe o painel explícito “Histórico e pendências” sem valores fictícios nem ações financeiras, atualizar a navegação e a documentação de domínio somente com a fronteira entregue/futura, e verificar visualmente os papéis `member/admin` e executar `reflex compile --dry`.

## 5. Publicação e verificação integrada

- [x] 5.1 Executar dry-run do conjunto Xano no branch `v1`, resolver referências de tabela, funções, grupo e endpoints e confirmar que o escopo do push não inclui recursos não relacionados.
- [x] 5.2 Executar testes ponta a ponta no branch `v1` com contas descartáveis `member/admin`, incluindo token anterior de conta desativada, concorrência de CPF, paginação, minimização de PII, ausência de exclusão e conteúdo permitido dos eventos de auditoria.
- [x] 5.3 Após aprovação das verificações, publicar os recursos no branch `v1`, sincronizar GUIDs e `canonical`, configurar a URL do grupo Clientes e verificar que o cliente Python e as quatro páginas Reflex operam contra o Xano publicado sem regressão de autenticação ou catálogo.
- [x] 5.4 Validar a change com `openspec validate gerenciar-clientes --strict`, executar todas as suítes Python relevantes e revisar o diff final para confirmar que locações, multas, pagamentos, bloqueio financeiro e dados não especificados permaneceram fora do escopo.
