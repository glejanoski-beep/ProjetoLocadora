# Proposal

## Why

O backoffice ainda não possui cadastro persistente de clientes, busca protegida nem uma fonte confiável para situação cadastral e bloqueios, impedindo que a equipe identifique a pessoa atendida antes das futuras operações de locação. A capacidade deve nascer com proteção de dados pessoais, prevenção de duplicidade e limites claros para não simular histórico ou pendências financeiras que ainda não existem.

## What Changes

- Criar o cadastro de clientes no Xano com identificador interno gerado, nome completo, CPF obrigatório normalizado, e-mail e telefone, exigindo ao menos uma forma de contato.
- Impedir CPF duplicado por validação no backend e restrição única persistente, considerando o valor normalizado somente com dígitos.
- Disponibilizar consultas autenticadas para localizar clientes por trecho do nome ou CPF exato, retornando na listagem somente os dados necessários ao atendimento, com CPF mascarado.
- Disponibilizar consulta protegida do detalhe cadastral, incluindo dados pessoais completos somente para usuários internos ativos autorizados.
- Permitir somente a `admin` criar, atualizar, ativar ou inativar clientes e aplicar ou remover bloqueio cadastral manual com motivo obrigatório; `member` pode localizar e consultar, mas não alterar o cadastro.
- Manter situação cadastral e bloqueio manual como conceitos separados e não excluir clientes para corrigir ou encerrar cadastros.
- Auditar criações, atualizações, mudanças de situação e mudanças de bloqueio com metadados mínimos, sem copiar CPF, contato ou o objeto completo do cliente para o log.
- Preparar a página de detalhe para uma futura seção de histórico e pendências, exibindo indisponibilidade explícita enquanto locações, multas e pagamentos não existirem, sem inventar saldos, cobranças ou históricos vazios como resultado real.
- Reservar o identificador estável do cliente como chave de integração para futuras changes de locação, multa e pagamento. O bloqueio financeiro e sua liberação decorrente de pagamento ficam fora desta change; quando implementados, `member` poderá registrar as operações permitidas pela política vigente, mas não remover bloqueios financeiros por ajuste manual.

## Capabilities

### New Capabilities

- `clientes`: Cadastro, localização, consulta, atualização, situação cadastral, bloqueio manual e preparação segura para histórico e pendências futuras.

### Modified Capabilities

- `auditoria-segura`: Acrescentar rastreabilidade mínima para criação, atualização, mudança de situação e bloqueio de clientes sem registrar dados pessoais nos eventos.

## Impact

- Nova tabela e grupo de API Xano para clientes, com endpoints protegidos de listagem, detalhe, criação e atualização.
- Reutilização de `Quick Start/enforce_role` e `Quick Start/log_event`, preservando a política atual de `member/admin`.
- Novo cliente HTTP, validações e tipos Python para o contrato de clientes.
- Novas páginas Reflex para listagem/busca, cadastro e detalhe/edição, integradas ao backoffice existente.
- Testes de normalização e duplicidade de CPF, validação cadastral, autorização, minimização de dados, auditoria e estados da interface.
- Nenhuma tabela ou operação de locação, multa, pagamento ou pendência financeira será criada nesta change; a documentação registrará a fronteira de integração futura.
