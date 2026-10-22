# Proposal

## Why

O sistema já possui autenticação, clientes, catálogo e identificação de exemplares, mas ainda não registra a retirada de um exemplar por um cliente. Priorizar essa operação permite avançar no atendimento sem modernizar o layout e sem criar disponibilidade ou informações financeiras fictícias.

## What Changes

- Registrar uma locação por exemplar para conta interna ativa `member` ou `admin`, com cliente elegível, exemplar disponível, instante de retirada gerado no servidor, vencimento informado e status inicial `active`.
- Persistir o responsável a partir de `$auth.id`; impedir sobreposição de locações com garantia no banco e operação atômica, além das validações de negócio.
- Introduzir confirmação administrativa explícita de condição operacional do exemplar; exemplares legados ou novos sem confirmação permanecem `unverified`, sem serem anunciados como disponíveis.
- Oferecer formulário Reflex simples em `/locacoes/nova` e consulta protegida de confirmação em `/locacoes/{id}`, reutilizando consultas reais de clientes/exemplares e sessão existente.
- Reconciliar tentativas repetidas pela chave da operação, inclusive após timeout; distinguir confirmação, conflito, falha e resultado ainda desconhecido.
- Preservar histórico e auditoria mínima. Não oferecer devolução, cancelamento, exclusão, multa, pagamento, reserva, relatórios ou novos indicadores de dashboard neste incremento.
- Adiar modernização visual. Esta proposta não altera código funcional nem autoriza publicação, migração, criação de dados ou testes de escrita no Xano.

## Capabilities

### New Capabilities

- `registro-locacao`: registro protegido e idempotente por exemplar, validação de cliente e datas, integridade concorrente, confirmação e formulário Reflex.
- `disponibilidade-locacao`: condição operacional confirmada por administrador e consulta de exemplares elegíveis, sem inferir disponibilidade dos registros legados.

### Modified Capabilities

Nenhuma. As novas operações ficam em contratos próprios. `clientes`, `exemplares`, `catalogo-filmes`, `acesso-seguro` e `auditoria-segura` continuam com seus contratos existentes; não haverá manutenção livre de exemplar por `member`.

## Impact

- Xano `v1`: novos recursos de locação e ocupação exclusiva; extensão aditiva do schema de exemplar para condição operacional. Preservar identidades remotas, funções e APIs existentes.
- Reflex: novos adaptador, estado e página próprios; integração pontual de navegação e invalidação de sessão. Preservar módulos dos colegas.
- Configuração futura `XANO_RENTAL_API_URL`, obtida do grupo real quando a publicação for autorizada; nenhum `canonical` ou URL inventado.
- Verificação obrigatória de autenticação, elegibilidade, datas, atomicidade, concorrência, repetição de requisição e isolamento de sessão. Testes locais não comprovam execução Xano.
- Inspeção e riscos registrados em `inspection.md`; decisões técnicas e limites em `design.md`. Aplicação requer nova solicitação, conforme fluxo OpenSpec do projeto.
