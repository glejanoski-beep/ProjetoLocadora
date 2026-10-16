## Context

Ver [proposal.md](./proposal.md) para motivação e [specs/exemplares/spec.md](./specs/exemplares/spec.md) e [specs/auditoria-segura/spec.md](./specs/auditoria-segura/spec.md) para os contratos. O Xano local já contém a tabela `film`, com `id` como chave primária, endpoints autenticados que chamam `Quick Start/enforce_role` antes da consulta/gravação, e eventos administrativos por `Quick Start/log_event`. O cliente Reflex organiza o transporte por grupos Xano configurados separadamente; a configuração atual possui URLs para Authentication, Catálogo de Filmes e Clientes.

O catálogo já documenta e implementa a separação entre filme e cópia física; não há tabela nem endpoints de exemplares. A implementação deve preservar essa fronteira, manter a autorização no Xano e usar Reflex para a interface, conforme as capacidades existentes.

## Goals / Non-Goals

**Goals:**

- Persistir exemplares como registros distintos dos filmes, associados à chave existente do filme.
- Combinar verificação da referência ao filme com proteção de unicidade no armazenamento, sem depender de validação exclusiva no cliente.
- Aplicar os papéis existentes no backend, apresentar o filme associado nas consultas e seguir o padrão existente de auditoria do cadastro administrativo.
- Isolar as operações em grupo Xano próprio de Exemplares e URL Reflex independente, conforme decisão confirmada para esta change.

**Non-Goals:**

- Definir formato, normalização ou regra de comparação do identificador além da unicidade exigida.
- Introduzir situação, localização, datas ou outros atributos de exemplar não definidos pelos critérios.
- Implementar edição ou exclusão de exemplares.
- Operar disponibilidade, estoque, locações, reservas ou devoluções, ou alterar o modelo/endpoints de filmes.
- Fixar rota, nomes de campos ou formato de payload Xano que não estejam definidos pelo projeto ou aprovados para esta change.

## Decisions

### Manter exemplar separado de filme e associá-lo pelo identificador persistido do filme

O registro de filme existente possui chave `id`; cada exemplar deve manter sua própria identidade e uma referência a um filme já persistido. Isso preserva a distinção de domínio e permite que mais de um exemplar pertença ao mesmo filme. A resposta de consulta precisa incluir informação suficiente para identificar o exemplar e o filme; o identificador e o título do filme já são conceitos/campos presentes no catálogo.

Alternativa considerada: representar cópias como quantidade no filme. Rejeitada por contrariar a separação explícita de filme e exemplar e por não permitir distinguir as cópias individualmente.

### Garantir unicidade exata na persistência, não por consulta prévia isolada

O identificador será comparado exatamente como informado, sem normalização de espaços ou caixa. O backend deve validar entradas e o armazenamento deve rejeitar valores de identificador repetidos por meio de uma garantia de unicidade suportada pelo banco. Uma busca anterior por duplicidade pode melhorar a mensagem de erro, mas não substitui a restrição de persistência: operações concorrentes ainda precisam resultar em no máximo uma gravação válida. O erro de conflito deve ser traduzido para uma falha explícita no contrato usado pelo Reflex.

Alternativa considerada: verificar apenas se já existe registro com o identificador antes de gravar. Rejeitada porque há uma janela de concorrência entre verificação e gravação.

### Validar o filme antes de criar o exemplar

Antes da gravação, o backend verifica a existência do filme referenciado e só então persiste a associação. Se a referência não existir, encerra a operação sem criar exemplar. Os critérios não distinguem filme ativo de inativo; não se adiciona filtro por `status` sem requisito aprovado.

Alternativa considerada: confiar na validação do formulário Reflex. Rejeitada porque chamadas diretas ao Xano devem respeitar as mesmas invariantes.

### Aplicar autorização e auditoria nos endpoints do Xano

As operações protegidas seguem a convenção local de autenticação e `Quick Start/enforce_role`, exigindo `member` para consulta e `admin` para cadastro antes de acessar dados ou produzir efeitos. O cadastro administrativo reutiliza `Quick Start/log_event` e segue o contrato mínimo já usado em criações de filmes. Edição e exclusão ficam fora desta change. A falha de auditoria após uma gravação confirmada deve ser apresentada como resultado parcial, sem sugerir rollback ou sucesso integral.

Alternativa considerada: proteger a manutenção apenas ocultando controles na interface. Rejeitada porque a interface não é mecanismo de segurança e APIs podem ser chamadas diretamente.

### Usar grupo e configuração de URL próprios para Exemplares

As APIs de exemplares ficarão em um grupo Xano próprio, identificado como Exemplares, e a aplicação Reflex terá configuração de URL independente para esse grupo. Isso segue o padrão usado para Clientes e evita acoplar chamadas de exemplares à configuração do catálogo de filmes. O nome da variável de ambiente e os caminhos concretos das rotas seguem a convenção de configuração e exportação existente, sem serem antecipados como requisitos.

As operações usarão o cliente Xano autenticado e o estado Reflex existentes, preservando o token somente no servidor e apresentando estados explícitos de carregamento, vazio, erro e sucesso. Acesso HTTP direto a partir dos componentes e uso de mocks como persistência foram rejeitados por desviar do cliente existente e não oferecer persistência real.

## Risks / Trade-offs

- O formato do identificador ainda não está definido; não presumir barcode, UUID ou outra representação. → Usar apenas o requisito de unicidade do valor recebido, sem normalização.
- A escrita e o evento de auditoria seguem operações separadas como no catálogo atual; falha do evento pode ocorrer após persistência. → Retornar estado parcial explícito e não presumir transação/rollback não comprovados.
- O export local não prova comportamento no runtime Xano, inclusive a recusa de gravações concorrentes pela restrição única. → Os testes locais verificam a declaração da constraint e a ordem das validações; não serão feitas chamadas de escrita, importações ou publicação no Xano remoto sem autorização explícita.

## Migration Plan

Não há migração de registros de exemplares existente no export local. A implementação deverá adicionar o recurso de persistência e seus contratos no export local e verificar que a restrição de unicidade é aplicável ao estado existente antes de qualquer implantação. Operações e publicação remotas ficam fora desta autorização.

## Open Questions

Nenhuma questão em aberto altera os requisitos ou a abordagem definidos. O formato do identificador e as rotas/payloads permanecem fora do escopo do contrato e devem seguir as decisões técnicas e convenções existentes durante a implementação.
