# Tasks

Implementação local concluída: 507 testes (raiz) e 60 (`ProjetoLocadora/tests`) aprovados, `reflex compile --dry` sem erros e 6 arquivos XanoScript válidos. Publicado no Xano v1 em 06/11/2026; conferência real aprovada pelo usuário.

## 1. Backend Xano (local; publicação somente com autorização)

- [x] 1.1 `exemplar`: campos anuláveis `retired_at`, `retired_by`, `retire_kind`, `retire_reason`, sem backfill.
- [x] 1.2 `PATCH /exemplares/{id}`: `admin`, transação conta → exemplar, não baixado, identificador único (exceto o próprio), troca de filme só sem locações, auditoria `update_exemplar`.
- [x] 1.3 `POST /exemplares/{id}/baixa`: `admin`, tipo e motivo, recusa com ocupação, grava baixa e condição `unavailable`, auditoria `retire_exemplar`.
- [x] 1.4 `POST /exemplares/{id}/reativacao`: `admin`, motivo, limpa baixa, condição `unverified`, auditoria `reactivate_exemplar`.
- [x] 1.5 `GET /exemplares` com `baixado`, `baixa_tipo`, `baixa_motivo`; `PATCH /locacoes/exemplares/{id}/condicao` recusa baixado.
- [x] 1.6 Validador XanoScript e testes estáticos: papel antes de dados, bloqueio do exemplar, recusa com ocupação e com histórico, nenhuma exclusão.

## 2. App

- [x] 2.1 `exemplares.py`: rótulos dos tipos, validação de edição, baixa e reativação.
- [x] 2.2 `xano_client.py`: normalização da listagem antiga, `update_exemplar_xano`, `retire_exemplar_xano`, `reactivate_exemplar_xano`, com as mensagens de negócio do backend.
- [x] 2.3 Estado: diálogo por cópia, rascunhos, envio único, atualização da lista, “Mostrar baixados”, contagens só de ativos.
- [x] 2.4 Interface: identificador clicável para `admin`, diálogo com edição, baixa e reativação, selo “Baixado”, estilos.

## 3. Testes

- [x] 3.1 Validações e normalização da listagem.
- [x] 3.2 Transporte: contratos e mensagens de negócio.
- [x] 3.3 Estado: member não abre diálogo, baixa remove da lista padrão, reativação, erro mantém o diálogo, contagens.
- [x] 3.4 Suítes completas e `reflex compile --dry`.

## 4. Publicação e conferência

- [x] 4.1 Publicar tabela antes dos endpoints e conferir por `pull` (referências preservadas; rotas novas respondem 401 sem token; grupo `Exemplares` e `POST /exemplares` não foram republicados).
- [x] 4.2 Conferir com exemplar real: edição, baixa (some das opções de locação), reativação (volta como não conferido).

## 5. Documentação

- [x] 5.1 `docs/domain-model.md`: baixa, reativação e regra de troca de filme.
- [x] 5.2 `openspec validate editar-e-baixar-exemplares --strict`.
