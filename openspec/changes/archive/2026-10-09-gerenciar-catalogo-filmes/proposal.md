# Proposal: Gerenciar catálogo de filmes

## Why

O backoffice Reflex ainda não oferece consulta nem manutenção do catálogo, e a exportação Xano versionada no repositório não contém tabela ou endpoints de filmes. A equipe não consegue administrar o catálogo pela aplicação com persistência no backend.

## What Changes

- Disponibilizar no Reflex uma tela autenticada para listar e buscar filmes por título.
- Adotar o schema técnico aprovado para esta Change: `id` gerado pelo Xano; título e gênero textuais obrigatórios com limites de 200 e 100 caracteres; ano inteiro de 1888 ao ano corrente; classificação pelos valores aprovados; valor de locação inteiro não negativo em centavos, com conversão de/para reais na interface; e status `active`/`inactive` com padrão `active`.
- Manter `qtd_estoque` fora das entradas e alterações desta Change, sem definir valor inicial. Confirmar sua compatibilidade com o modelo filme/exemplar sem bloquear as demais operações do catálogo se puder ser omitido dos payloads desta fatia.
- Oferecer filtro pelo campo textual `genero`, sem lista fechada nem taxonomia adicional.
- Permitir formulários visuais de criação e edição para administradores, usando somente os campos e regras do schema aprovado.
- Criar ou ajustar operações Xano para consulta, criação e edição, persistindo no banco Xano e aplicando autorização no backend.
- Exibir validações, confirmações de sucesso e erros de consulta ou gravação sem apresentar falhas como sucesso.
- Registrar com metadados mínimos as criações e edições administrativas de filmes.

## Capabilities

### New Capabilities

- `catalogo-filmes`: consulta, busca e manutenção administrativa de filmes no catálogo.

### Modified Capabilities

- `auditoria-segura`: registrar com segurança criações e edições administrativas de filmes.

## Impact

- Reflex: estado, cliente Xano, rotas e navegação do backoffice.
- XanoScript: schema local versionado conforme contrato aprovado e endpoints protegidos de consulta, criação e edição; a representação de `qtd_estoque` permanece pendente de compatibilidade.
- Auditoria: reutilização do mecanismo `Quick Start/log_event` para registrar ação e identificação do recurso, sem armazenar o objeto completo.
- Segurança: leitura por `admin` e `member`; criação e edição somente por `admin`, verificadas no backend.
- Verificação: testes locais e estáticos podem cobrir contratos e fluxos sem substituir persistência real. Não há workspace Xano de testes separado; nenhuma chamada ou alteração no Xano remoto será feita sem autorização explícita. A integração em runtime permanecerá não verificada sob essa restrição.

## Fora do escopo

- Exemplares físicos, controle operacional de estoque, disponibilidade, reservas e locações.
- Exclusão de filmes.
- Operações de controle de estoque: movimentação, cálculo, disponibilidade, reserva ou associação a exemplar. `qtd_estoque` não recebe default definido nem é informado ou alterado nesta Change.
- Criação de relacionamentos com exemplares ou locações.
- Acesso ou implantação no Xano remoto.

## Estado da implementação local

O schema e os endpoints foram versionados na exportação Xano local e o cliente/interface Reflex foram implementados para consumi-los. Eles ainda não foram importados ou executados em um workspace Xano, que não está disponível para esta Change; portanto, persistência, autorização e auditoria no runtime permanecem sem verificação. Nenhuma requisição ao Xano remoto foi feita.

Permanece pendente verificar se e como `qtd_estoque` deve existir no modelo de filme sem conflitar com a separação conceitual entre filme e exemplar. A definição e todos os payloads desta fatia omitem o campo; nenhum default é definido nem há mutação de estoque.
