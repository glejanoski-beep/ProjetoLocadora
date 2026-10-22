# Implantação Xano — 22/10/2026

## Escopo autorizado e executado

Autorização explícita do usuário: “Sim, autorizo implantar os recursos”, após proposta de publicar recursos inicialmente com escritas desabilitadas. Destino: workspace `149184`, branch `v1`, fonte `live`.

- Duas tabelas novas: `rental` (`909094`) e `rental_occupancy` (`909095`), com índices únicos de chave por conta e ocupação por exemplar/locação.
- Quatro campos aditivos na tabela existente `exemplar` (`907795`), preservando GUID e campos anteriores; sem backfill de disponibilidade.
- Grupo `Locações` (`437482`), canonical real `BovA1vb0`, cinco endpoints e função `Locacoes/parse_due_at`.
- Base real: `https://x8ki-letl-twmt.n7.xano.io/api:BovA1vb0`.
- `XANO_RENTAL_WRITES_ENABLED` criado via painel, valor textual `false`. Valor reaberto e conferido após salvar. O importador parcial da CLI omitiu a variável do workspace; o painel foi necessário para concluir a configuração.

## Evidências

O preview parcial continha somente esses recursos, sem exclusão ou importação de registros. A primeira importação foi rejeitada porque o parser remoto não aceita nome dinâmico em `throw`, apesar da validação sintática local. Um export posterior confirmou os 40 recursos anteriores sem alteração. O código foi corrigido para nomes literais e os testes foram repetidos.

A segunda importação concluiu dez documentos e atribuiu nove GUIDs reais. O export de conferência contém 49 recursos. Todos os recursos preexistentes permaneceram byte a byte iguais, exceto `table/exemplar.xs`, que recebeu os campos previstos. Identidades reais foram incorporadas aos arquivos locais.

As três consultas novas, chamadas sem token, responderam HTTP **401**: elegíveis, detalhe e reconciliação. Nenhum POST/PATCH operacional foi chamado. As novas tabelas foram observadas com zero registros no painel. O harness temporário de rollback não foi publicado.

Após a correção e incorporação das identidades, os **175 testes** da descoberta principal passaram novamente. Os **52 testes** adicionais e compilação Reflex anteriores continuam válidos, sem alteração posterior de código frontend. Cinco testes específicos de Windows permanecem pendentes. OpenSpec estrito e verificação de whitespace executados antes do commit.

## Limites e próximos critérios

Não foram criados clientes, exemplares ou locações fictícios, nem alterada condição operacional de exemplar. Nenhum módulo dos colegas foi publicado ou modificado além da extensão aditiva prevista em exemplar. Não houve publicação da interface, push Git, PR ou merge.

A escrita permanece bloqueada. Antes de liberar uso, executar a homologação autorizada de concorrência, idempotência, rollback, elegibilidade e permissões descrita em `delivery.md`, com contas e registros reais indicados pelo operador. Publicação de definições e testes de autenticação sem token não comprovam integridade transacional em execução. A change permanece aberta.

Em caso de falha na homologação, manter os gates `false`, preservar schemas e histórico e corrigir de forma auditada; não excluir registros nem remover constraints para contornar falhas.
