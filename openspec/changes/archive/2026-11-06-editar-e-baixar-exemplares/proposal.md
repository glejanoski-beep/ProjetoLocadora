# Proposal

## Why

O administrador só consegue cadastrar e consultar exemplares. Um identificador digitado errado não pode ser corrigido, uma cópia associada ao filme errado não pode ser ajustada, e uma cópia perdida, danificada ou descartada continua contada no acervo. A única saída hoje é marcá-la como `unavailable` na conferência operacional, que é um estado transitório, ou mexer direto no Xano. A matriz de permissões já prevê que `admin` edite e inative exemplares, e o domínio exige que um exemplar "perdido ou baixado não apareça como disponível", preservando o histórico.

## What Changes

- **Editar exemplar** (`admin`):
  - o identificador pode ser corrigido a qualquer momento, mantida a unicidade exata;
  - o filme só pode ser trocado se a cópia nunca participou de uma locação (o histórico guarda filme e identificador do momento da locação e não pode ficar contraditório);
  - exemplar baixado não é editado.
- **Dar baixa** (`admin`), em vez de exclusão:
  - tipo obrigatório (perdido, danificado, descartado ou outro) e motivo de até 500 caracteres;
  - recusada enquanto a cópia estiver alugada;
  - a baixa marca a condição operacional como `unavailable`, então o exemplar sai das opções de locação pelas regras existentes;
  - o exemplar e o histórico de locações dele são preservados.
- **Reativar** (`admin`): desfaz a baixa, por exemplo quando uma cópia perdida é encontrada. O motivo é obrigatório, e a cópia volta como "não conferida" (`unverified`), exigindo nova conferência antes de ser alugada.
- A conferência operacional existente passa a recusar exemplar baixado.
- A listagem de exemplares passa a informar se a cópia está baixada, com o tipo e o motivo.
- **Interface** (`/exemplares`):
  - para `admin`, cada cópia abre um diálogo com "Editar", "Dar baixa" ou "Reativar";
  - cópias baixadas ficam ocultas por padrão, com a opção "Mostrar baixados", e são marcadas como "Baixado";
  - as contagens consideram só as cópias ativas.
- Todas as operações são auditadas (`update_exemplar`, `retire_exemplar`, `reactivate_exemplar`).

**Não objetivos:**
- exclusão física de exemplar;
- histórico completo de baixas e reativações em tabela própria (o registro fica no log de eventos);
- localização física, data de aquisição e custo;
- baixa em lote;
- mudança no resumo do acervo do dashboard (o total continua contando todos os exemplares cadastrados).

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `exemplares`: edição e baixa/reativação administrativas; a vedação "edição e exclusão não fazem parte" é substituída.
- `disponibilidade-locacao`: a conferência operacional recusa exemplar baixado.
- `interface-exemplares`: ações administrativas por cópia e exibição de baixados.

## Impact

- Xano (`v1`, publicação somente com autorização):
  - tabela `exemplar` ganha `retired_at`, `retired_by`, `retire_kind` e `retire_reason`, todos anuláveis e sem backfill;
  - endpoints novos `PATCH /exemplares/{id}`, `POST /exemplares/{id}/baixa` e `POST /exemplares/{id}/reativacao` (grupo `Exemplares`);
  - `GET /exemplares` ganha `baixado`, `baixa_tipo` e `baixa_motivo`;
  - `PATCH /locacoes/exemplares/{id}/condicao` recusa exemplar baixado.
- App:
  - `exemplares.py` (validações e rótulos) e `xano_client.py` (três operações e normalização da listagem);
  - estado e diálogo de exemplares em `ProjetoLocadora.py`, `assets/exemplares.css` e testes.
- Documentação: `docs/domain-model.md`.
