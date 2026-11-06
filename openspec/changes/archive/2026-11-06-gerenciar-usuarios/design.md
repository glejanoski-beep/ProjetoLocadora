# Design

## Context

- A tabela `user` (Quick Start) guarda `name`, `email`, `password`, `role` (`admin|member`), `is_active` (padrão `true`; ausente é tratado como ativo) e `password_reset`.
- `Quick Start/enforce_role` já recusa contas inexistentes, desativadas ou com papel desconhecido em toda operação protegida, e o login recusa contas desativadas. Desativar uma conta, portanto, já corta o acesso na próxima requisição, sem precisar invalidar tokens.
- O app confere `auth/me` periodicamente (`_SessionBound._authorize`) e, se o papel mudou, atualiza a sessão e pede para reabrir a página.
- A locadora tem poucas contas (dezenas).
- A cota do plano é de 10 requisições a cada 20 s.

## Goals / Non-Goals

**Goals:**
- admin altera papel e situação de outras contas, com motivo e auditoria;
- é impossível ficar sem nenhum admin ativo;
- nenhum dado sensível sai do backend.

**Non-Goals:** criação de contas pelo admin, edição de nome, e-mail ou senha, exclusão e encerramento forçado de tokens.

## Decisions

### Grupo de API

Os endpoints ficam no grupo `Locações` (`XANO_RENTAL_API_URL`), como multas e relatórios. Assim não é preciso criar grupo novo nem nova variável no `.env`.

A flag `XANO_RENTAL_WRITES_ENABLED` protege o fluxo de locação. Ela não se aplica aqui: o transporte compartilhado ganha o parâmetro `gated`, e as escritas de usuário usam `gated=False`.

### Leitura: `GET /usuarios`

- Exige `admin`.
- Devolve `{items: [...]}`, ordenado por nome, com no máximo 500 contas.
- Cada item tem exatamente: `id`, `name`, `email`, `role`, `is_active` (ausente vira `true`) e `created_at`.
- `password` e `password_reset` nunca são lidos (`output` explícito).

Com poucas contas, busca e filtro ficam no app, sem nova requisição. Se vierem 500 itens, a tela avisa que a lista pode estar incompleta.

### Escrita: `PATCH /usuarios/{id}`

Entradas: `role` (`admin|member`), `is_active` (bool) e `reason` (obrigatório, até 500 caracteres). A requisição envia o estado desejado completo, não um delta.

1. `enforce_role` exige `admin` antes de qualquer leitura.
2. `id` precisa ser diferente de `$auth.id`: "Você não pode alterar a própria conta."
3. Dentro de `db.transaction`, as duas contas são bloqueadas em ordem crescente de `id`, e não "ator → alvo". Dois admins alterando um ao outro ao mesmo tempo pegam os bloqueios na mesma ordem, e não há impasse.
4. O ator, já bloqueado, precisa continuar ativo e `admin` ("Conta sem autorização atual."). O alvo precisa existir ("Usuário não encontrado.").
5. Se nada muda (mesmo papel e mesma situação): "Nenhuma alteração informada."
6. `db.edit user` grava só `role` e `is_active`.

A auditoria é gravada depois do commit: `log_event` com `action: "update_user"`, `resource_type: "user"`, `resource_id` e `result` = `"success: role A→B; active X→Y; reason: …"`, com no máximo 500 caracteres. Se a auditoria falhar, a alteração continua valendo e a resposta traz `audit_succeeded: false`, como nos demais endpoints.

Resposta: `{user: {id, name, email, role, is_active, created_at}, audit_succeeded}`.

### Por que sempre resta um admin

O ator não pode alterar a própria conta e precisa ser admin ativo no momento do commit, com a própria linha bloqueada. Logo, depois de qualquer alteração bem-sucedida, o ator continua admin ativo.

Se dois admins tentam rebaixar um ao outro, os bloqueios serializam as operações. A segunda encontra o próprio ator já rebaixado e é recusada.

### Idempotência

A operação define o estado final (não alterna). Repetir o mesmo envio depois de um sucesso cai em "Nenhuma alteração informada", sem gravar nada. Por isso não há `operation_key`. Quando o resultado de uma escrita fica incerto (erro de rede ou resposta inválida), o app não repete o envio: fecha o diálogo, relê a lista e pede para conferir a conta.

### App

- `usuarios.py`:
  - rótulos: `admin` → "Administrador", `member` → "Funcionário";
  - validação do item recebido (chaves exatas, tipos);
  - busca sem acento e sem diferença de maiúsculas;
  - validação do motivo.
- `usuarios_client.py`: `list_users(token)` e `update_user(token, id, role, is_active, reason)`. As recusas de negócio acima são exibidas como vieram.
- `usuarios_state.py`: `UsuariosState(_SessionBound, rx.State)`.
  - Lê na entrada da página.
  - O diálogo guarda papel, situação e motivo; envia uma vez; substitui o item pela resposta.
  - A própria conta aparece marcada "Você", sem ação.
  - Para `member`, o estado é "forbidden" sem consultar o backend.
- `usuarios_ui.py` + `assets/usuarios.css`: segue o padrão visual de relatórios e multas.

## Risks / Trade-offs

- **Token de conta desativada continua existindo.** Mitigação: `enforce_role` recusa toda operação protegida, e o app limpa a sessão quando `auth/me` falha. O login também é recusado.
- **Limite de 500 contas.** É muito acima do porte da locadora, e a tela avisa quando atinge o limite.
- **Quem foi rebaixado vê a tela antiga até a próxima conferência de sessão.** O backend recusa as escritas administrativas, e o app já trata a mudança de papel.
