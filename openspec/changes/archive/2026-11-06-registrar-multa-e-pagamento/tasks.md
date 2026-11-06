# Tasks

Implementação local concluída (grupos 1–8 e 10): 475 testes e `reflex compile --dry` aprovados, validador XanoScript sem erros nos 15 arquivos. Publicado no Xano `v1` em 06/11/2026 (9.1). Homologação com gravações reais (9.2–9.7) pendente.

## 1. Compatibilidade do app (antes de publicar o backend)

- [x] 1.1 A validação da resposta da devolução aceita `{rental, audit_succeeded}` (atual) e `{rental, fine, audit_succeeded}`, com `fine` nulo ou válido e coerente com `rental.id`.
- [x] 1.2 Validadores de `fine` e `payment` em `multas.py`: tipos inteiros em centavos, status permitidos, saldo ≥ 0, ausência de CPF e contatos, sem coerção de tipos.
- [x] 1.3 Testes de contrato para os dois formatos da devolução e para multas e pagamentos incoerentes.

## 2. Política de multa

- [x] 2.1 Função `locacoes/calculate_late_fine` em XanoScript: leitura das três variáveis (ausente = padrão) e validação, tolerância, `ceil` em blocos de 24 h, teto, retorno do retrato da política; falha com configuração inválida somente quando houver atraso.
- [x] 2.2 Cálculo equivalente em Python (`multas.py`), usado apenas para a estimativa, com testes dos exemplos do `design.md`: 1 h 30 → 0; 3 h → 300; 47 h → 600; 49 h → 900; 45 dias → 9000; exatamente na tolerância → 0.
- [x] 2.3 `GET /multas/politica` (`member`) retornando os parâmetros vigentes.

## 3. Backend Xano: multas (local; publicação somente com autorização)

- [x] 3.1 Tabela `fine` com índice único em `rental_id` e btree em (`customer_id`, `status`).
- [x] 3.2 `POST /locacoes/{id}/devolucao`: cálculo e inserção da multa dentro da transação; resposta com `fine`; repetição devolvendo a multa da locação; auditoria `create_fine` após o commit.
- [x] 3.3 `GET /multas` (filtros `status`, `customer_id`, `rental_id`, paginado), `GET /multas/{id}` (com pagamentos) e `GET /multas/resumo`.
- [x] 3.4 `POST /multas/{id}/abono` (`admin`, trava de escrita, motivo, chave, bloqueio conta → multa, auditoria `waive_fine`).

## 4. Backend Xano: pagamentos

- [x] 4.1 Tabela `payment` com índice único em (`registered_by`, `operation_key`) e btree em `fine_id` e `customer_id`.
- [x] 4.2 `POST /multas/{id}/pagamentos` conforme o `design.md`: trava, `enforce_role` `member`, transação conta → multa, idempotência, saldo, atualização de `paid_cents` e `status`, erros por `precondition`, auditoria `register_payment`.
- [x] 4.3 `POST /pagamentos/{id}/estorno` (`admin`, motivo, recusa para multa `waived`, devolve a multa a `open`, auditoria `reverse_payment`).
- [x] 4.4 `GET /pagamentos` (filtros `customer_id` e `fine_id`, paginado).

## 5. Backend Xano: locações

- [x] 5.1 `POST /locacoes`: recusa "Cliente com multa em aberto." depois de bloquear o cliente, sem mudar a ordem de bloqueios.
- [x] 5.2 `GET /locacoes`: filtro opcional `customer_id`.
- [x] 5.3 Validador XanoScript e testes estáticos de contrato: autorização antes dos dados, bloqueios, ausência de `throw` customizado, `db.add fine` dentro da transação da devolução, e nenhum `db.del` em `fine` e `payment`.

## 6. Cliente e estado (Reflex)

- [x] 6.1 `multas_client.py`: listar, detalhar, resumo, política, pagar, estornar, abonar e listar pagamentos; sem retry automático; 401/403/404/409/400/429/timeout mapeados.
- [x] 6.2 Endpoints no grupo `Locações` existente: o app reutiliza `XANO_RENTAL_API_URL` e `rental_writes_enabled()`, sem nova configuração.
- [x] 6.3 `multas_state.py`: abas, paginação, detalhe, pagamento com chave por tentativa, bloqueio de envio duplo, resultado desconhecido, ações de `admin` e descarte de respostas após troca de sessão.
- [x] 6.4 Estado da devolução: busca da política, estimativa e exibição da multa retornada.
- [x] 6.5 Estado da nova locação: consulta de multa em aberto ao selecionar o cliente e motivo "Multa em aberto".

## 7. Interface

- [x] 7.1 Página `/multas` (lista e detalhe) e `assets/multas.css` no padrão visual do backoffice.
- [x] 7.2 Navegação: "Multas" ativo, "Relatórios" continua "Em breve".
- [x] 7.3 Card "Multas pendentes" com o resumo real e estados de carregamento e erro.
- [x] 7.4 Detalhe da locação: estimativa na confirmação e multa gerada com link.
- [x] 7.5 Detalhe do cliente: saldo em aberto, aviso de bloqueio e abas "Locações", "Multas" e "Pagamentos" reais.

## 8. Testes automatizados

- [x] 8.1 Cliente: contratos, categorias de erro, sem retry.
- [x] 8.2 Estado: pagamento total e parcial, valor acima do saldo, duplo clique, timeout com a mesma chave, 409, 429, logout pendente, `member` sem ações de `admin`.
- [x] 8.3 Interface: abas, rótulo "Parcial", formatação monetária, card do dashboard, navegação e abas do cliente.
- [x] 8.4 Suítes completas (`unittest`/`pytest`) e `reflex compile --dry`.

## 9. Publicação e homologação no Xano `v1` (janela autorizada)

- [x] 9.1 (06/11/2026: tabelas `fine`/`payment` publicadas primeiro, depois 2 funções, 8 endpoints novos e 3 atualizados; `pull` sem referências vazias; rotas novas respondem 401 sem token) Publicar tabelas antes dos endpoints, com o app compatível já em uso; conferir no pull que não ficaram referências vazias (`db.get ""`, `table = ""`).
- [ ] 9.2 Devoluções reais: no prazo, dentro da tolerância, atrasada (1 e 3 dias) e, se houver dados, com teto; conferir `fine` e o retrato da política.
- [ ] 9.3 Pagamento parcial, quitação, repetição com a mesma chave e valor acima do saldo.
- [ ] 9.4 Dois pagamentos simultâneos na mesma multa.
- [ ] 9.5 Estorno e abono por `admin`; recusa para `member`; trava fechada recusando.
- [ ] 9.6 Bloqueio financeiro em `POST /locacoes` e liberação após a quitação ou o abono.
- [ ] 9.7 Auditoria de integridade: `paid_cents` igual à soma dos pagamentos `confirmed`; saldo ≥ 0; status coerente; uma multa por locação. Estender `scripts/verify_rental_integrity.py`.

## 10. Documentação

- [x] 10.1 `docs/domain-model.md`: política de multa, invariantes de saldo, matriz de permissões (pagamento: `member`/`admin`; estorno e abono: `admin`).
- [x] 10.2 `docs/project-overview.md`: incremento de multas e pagamentos.
- [x] 10.3 `openspec validate registrar-multa-e-pagamento --strict`.

## Evidências de homologação (06/11/2026, conta 3 `admin`)

Com `XANO_FINE_GRACE_MINUTES = 0` temporário no painel: locação 53 (cliente 12, CAR-001) vencida às 13:44 e devolvida às 13:46:45 gerou a multa 1 na mesma transação (1 dia, 300 centavos, retrato da política com tolerância 0); `rental_return` 18 criado e ocupação removida. Pagamentos 1 (100, dinheiro) e 2 (200, dinheiro): multa `open` → `paid`. Conferência pela Metadata API: `paid_cents` = soma dos `confirmed` (300), saldo 0, uma multa por locação; auditoria `return_rental`, `create_fine` e dois `register_payment` com sucesso, sem eventos de falha.

Ainda não homologado: atraso de vários dias e teto (9.2), repetição com a mesma chave e valor acima do saldo pelo backend (9.3), concorrência (9.4), estorno, abono e visão de `member` (9.5), bloqueio financeiro (9.6). A variável `XANO_FINE_GRACE_MINUTES` deve ser removida ao final.

## Encerramento (06/11/2026)

Arquivada por decisão do usuário. Itens 9.2–9.7 permanecem desmarcados: além do fluxo devolução → multa → pagamento parcial → quitação (evidência acima), estorno, abono, bloqueio financeiro e visão de `member` não aparecem no Xano (sem eventos `reverse_payment`, `waive_fine` nem recusa de locação até a conferência das 13:50); cobertura apenas pelos testes automatizados e contratos estáticos. Remoção de `XANO_FINE_GRACE_MINUTES` no painel não foi conferida (variáveis não são legíveis pela Metadata API).
