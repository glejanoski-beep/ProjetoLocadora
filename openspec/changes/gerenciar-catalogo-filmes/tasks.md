# Tasks

## 1. Registrar e verificar o contrato do domínio

- [x] 1.1 Versionar localmente o schema aprovado, mantendo `id` gerado pelo Xano e as validações aprovadas de título, gênero, ano, classificação, valor em centavos e status; não assumir que a tabela já existe no Xano remoto.
- [ ] 1.2 Verificar a compatibilidade de `qtd_estoque` com a separação filme/exemplar sem acessar o Xano remoto; não definir default, não enviar nem alterar o campo. Se puder ser omitido dos contratos desta fatia, prosseguir sem bloquear as demais operações.
- [x] 1.3 Definir nomes, rotas, verbos, payloads e respostas dos endpoints conforme o schema aprovado e os padrões Xano existentes; excluir `qtd_estoque` dos payloads se a definição/schema permitir.

## 2. Implementar persistência e autorização Xano

- [x] 2.1 Criar ou ajustar a definição local versionada do recurso de filmes conforme o schema aprovado; usar `id` gerado pelo Xano e não converter `id_filme` em coluna duplicada.
- [x] 2.2 Implementar consulta/listagem com busca por título e filtro pelo campo textual `genero`, aplicando autenticação e papel mínimo `member` antes de consultar.
- [x] 2.3 Implementar criação persistente e edição persistente somente dos campos aprovados para manutenção de catálogo, validar o payload, converter reais para centavos e exigir `admin` no backend antes de gravar.
- [x] 2.4 Registrar criações e edições confirmadas com `Quick Start/log_event`, identificador do usuário e do filme, sem registrar o objeto completo nem segredos.
- [x] 2.5 Excluir `qtd_estoque` dos payloads de criação/edição, sem default ou mutação; se fizer parte do schema, preservar o valor existente. Não conceder a `status` significado operacional de disponibilidade.
- [x] 2.6 Verificar estruturalmente os contratos dos endpoints, a autorização antes de leitura/gravação e os dados de auditoria; não afirmar execução ou persistência no runtime Xano sem evidência autorizada.

## 3. Integrar cliente e estado Reflex

- [x] 3.1 Adicionar operações HTTP de filmes ao cliente Xano existente, usando o token privado da sessão e tratando separadamente respostas inválidas, recusas e falhas de transporte.
- [x] 3.2 Implementar estado para listagem, busca, filtro compatível, carregamento do filme para edição e submissão dos formulários, sem usar mocks como fonte de dados.
- [x] 3.3 Garantir que falhas de consulta/gravação não sejam convertidas em lista vazia ou resposta de sucesso.

## 4. Entregar a interface visual

- [x] 4.1 Adicionar navegação do backoffice para o catálogo e a página autenticada de listagem com estados de carregamento, vazio e erro.
- [x] 4.2 Adicionar busca por título e filtro pelo valor textual de gênero refletidos na consulta ao Xano, sem catálogo de gêneros fechado.
- [x] 4.3 Implementar formulários Reflex de criação e edição com os campos aprovados, validação, conversão de valor em reais/centavos, feedback explícito e persistência Xano; não aceitar `qtd_estoque` como campo editável.
- [x] 4.4 Exibir ações de manutenção somente para `admin`, mantendo a autorização obrigatória nos endpoints para chamadas diretas.
- [x] 4.5 Manter exemplares, controle de estoque, disponibilidade e locações fora das páginas e operações desta Change; não apresentar `qtd_estoque` como controle funcional.

## 5. Validar a fatia vertical

- [x] 5.1 Adicionar testes locais para validações e integração HTTP simulada; mocks testam o cliente, mas não substituem nem são apresentados como persistência real.
- [x] 5.2 Executar verificações locais disponíveis para Reflex, Python e XanoScript, registrando bloqueios sem contorná-los. Suíte Python executada com sucesso e Reflex disponível localmente; não foi localizado validador XanoScript, portanto a validação de XanoScript permanece bloqueada.
- [x] 5.3 Confirmar que nenhuma chamada ou alteração foi feita no Xano remoto; registrar runtime, autorização e persistência remota como não verificados se continuarem sem execução autorizada.

### Resultado das verificações

- `python -m pytest`: 51 testes passaram (executado localmente com o Python da `.venv`).
- `openspec validate gerenciar-catalogo-filmes --strict`: válido.
- `git diff --check`: concluído sem erros; o Git reportou apenas avisos de conversão LF/CRLF nos arquivos existentes de `reflex.lock`.
- `reflex --version`: Reflex 0.9.11 disponível; os testes locais de estado Reflex fazem parte da suíte executada.
- Não foi localizado validador XanoScript local; a validação XanoScript e a integração, autorização e persistência no runtime Xano remoto continuam não verificadas.
- Nenhuma chamada ou alteração foi feita no Xano remoto.
