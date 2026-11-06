# Tasks

Implementação local concluída: 491 testes e `reflex compile --dry` aprovados; endpoint aprovado pelo validador XanoScript. Publicado e conferido em 06/11/2026.

## 1. Domínio e período (app)

- [x] 1.1 `relatorios.py`: conversão de datas de Brasília em `[from, to)` em milissegundos, atalhos (7 dias, 30 dias, este mês, mês anterior), validação (início ≤ fim, até 366 dias).
- [x] 1.2 Validador da resposta do relatório: inteiros não negativos, coerência (atrasadas ≤ devoluções, vencidas ≤ ativas, soma por meio = recebido), filmes sem duplicidade e sem dados pessoais.
- [x] 1.3 Ranking: ordenação por retiradas e título, limite de 10, percentual de atraso sem divisão por zero.

## 2. Backend Xano (local; publicação somente com autorização)

- [x] 2.1 `GET /relatorios/operacional` no grupo `Locações`: `enforce_role` `admin` antes das leituras, validação do período, agregações conforme o `design.md`, sem escrita e sem trava de gravação.
- [x] 2.2 Validador XanoScript e testes estáticos: papel `admin` antes dos dados, nenhuma escrita, nenhum campo pessoal.

## 3. Cliente, estado e interface

- [x] 3.1 `relatorios_client.py`: requisição sem retry automático, categorias 401/403/400/429/timeout, validação da resposta.
- [x] 3.2 `relatorios_state.py`: período, atalhos, carregamento, descarte após troca de sessão, `member` sem consulta.
- [x] 3.3 `relatorios_ui.py` e `assets/relatorios.css`: filtro, grupos de indicadores, ranking com barras, estados.
- [x] 3.4 Navegação: "Relatórios" como link; rota `/relatorios`; sem itens "Em breve".

## 4. Testes

- [x] 4.1 Período e atalhos (inclusive virada de mês e ano), ranking e validador.
- [x] 4.2 Cliente: contrato e categorias de erro.
- [x] 4.3 Estado: admin carrega, member não consulta, período inválido não consulta, logout descarta a resposta.
- [x] 4.4 Interface e navegação; suítes completas e `reflex compile --dry`.

## 5. Publicação e conferência

- [x] 5.1 (06/11/2026: `relatorios/operacional GET` criado; `pull` sem referências vazias; 401 sem token) Publicar o endpoint no `v1` e conferir por `pull`.
- [x] 5.2 (06/11/2026: usuário conferiu "Últimos 30 dias" contra os totais calculados das tabelas pela Metadata API: 24 retiradas, 11 devoluções, 6 com atraso, 15 ativas, 11 vencidas, multas R$ 3,00, recebido R$ 3,00 em dinheiro, ranking liderado por Velozes e Furiosos 7) Conferir com um `admin` real que os totais de um período conhecido batem com as tabelas.

## 6. Documentação

- [x] 6.1 `docs/domain-model.md`: relatórios restritos a `admin` na matriz de permissões.
- [x] 6.2 `docs/project-overview.md`: incremento de relatórios.
- [x] 6.3 `openspec validate gerar-relatorios --strict`.
