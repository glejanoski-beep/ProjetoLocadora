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

## Continuação da homologação — 22/10/2026

O usuário autorizou prosseguir com as pendências. A consulta de fontes de dados
retornou somente `live`; não foi criado ambiente, branch Xano ou cadastro de teste.
A indicação de contas e registros reais para retiradas foi solicitada. Não foram
recebidas credenciais, criados tokens privilegiados ou efetuadas escritas de negócio.

O teste real da função pura de datas encontrou rejeição indevida de offset
`-03:00`. A validação de calendário foi corrigida para comparar o relógio local
em UTC, separadamente da conversão do instante com offset. Foi publicado somente
`Locacoes/parse_due_at`, preservando seu GUID, sem alterar gates ou outros recursos.
As chamadas reais abaixo foram executadas após a correção:

| Entrada | Resultado Xano |
| --- | --- |
| `2030-01-02T15:00:00Z` | `1893596400000` |
| `2030-01-02T12:00:00-03:00` | `1893596400000` |
| `2030-01-02T20:30:00+05:30` | `1893596400000` |
| `2030-02-30T15:00:00Z` | Recusa: vencimento inválido |

Sem offset e expressão relativa também foram recusados antes da correção;
a validação de formato foi preservada. São somente valores para uma função pura,
sem persistência de locação ou dados fictícios de negócio.

As seis bases reais dos grupos foram configuradas no `.env` privado deste checkout,
com escritas `false`. Compilação Reflex aprovada. Servidor local em modo produção
na porta `3010`; acesso a `/locacoes/nova` sem sessão redirecionou para `/login`.
Após login feito pelo operador, a navegação pelo link do backoffice carregou a tela autenticada: oito clientes reais, quatro exemplares para conferência administrativa e zero exemplares elegíveis. Aviso de homologação pendente e botões de confirmação desabilitados visíveis. Nenhuma seleção foi confirmada ou condição alterada. Os 175 testes principais
passaram novamente após a correção, assim como validação sintática e OpenSpec estrito.
O exemplo de configuração versionado contém somente campos vazios e gate `false`.

O código pode ser revisado em PR de rascunho, mas os critérios de concorrência,
rollback, permissões e elegibilidade continuam pendentes. Não mesclar como operação
liberada, habilitar escritas ou arquivar a change antes dessas evidências.
