# Tasks

Implementação local concluída: 525 testes (raiz) e 60 (`ProjetoLocadora/tests`) aprovados, `reflex compile --dry` sem erros e 2 arquivos XanoScript válidos. Publicado no Xano v1 em 06/11/2026; conferência real aprovada pelo usuário.

## 1. Backend Xano (local; publicação somente com autorização)

- [x] 1.1 `GET /usuarios` (grupo `Locações`): `admin`, `output` explícito sem senha, ordenado por nome, até 500, `is_active` ausente como `true`.
- [x] 1.2 `PATCH /usuarios/{id}`: `admin`, recusa a própria conta, motivo obrigatório, bloqueio das duas contas em ordem crescente de `id`, ator conferido dentro da transação, recusa sem mudança, edita só `role` e `is_active`, auditoria `update_user` depois do commit.
- [x] 1.3 Validador XanoScript e testes estáticos: papel antes de dados, sem senha no `output`, ordem de bloqueio, nenhuma exclusão.

## 2. App

- [x] 2.1 `usuarios.py`: rótulos, validação do item, busca sem acento, validação do motivo.
- [x] 2.2 `multas_client._request`: parâmetros `gated` e `business`; `usuarios_client.py` com `list_users` e `update_user`.
- [x] 2.3 `usuarios_state.py`: entrada da página, forbidden para member, filtro, diálogo, confirmação de desativação, envio único, "Você".
- [x] 2.4 `usuarios_ui.py`, `assets/usuarios.css`, rota `/usuarios` e item "Usuários" na navegação.

## 3. Testes

- [x] 3.1 Regras: rótulos, validação do item, busca, motivo.
- [x] 3.2 Transporte: contratos, recusas de negócio, escrita sem a flag de locação.
- [x] 3.3 Estado: member não consulta, própria conta sem ação, desativação pede confirmação, recusa mantém diálogo, sucesso atualiza a linha.
- [x] 3.4 Suítes completas e `reflex compile --dry`.

## 4. Publicação e conferência

- [x] 4.1 Publicar os dois endpoints e conferir por `pull` e 401 sem token (referências preservadas).
- [x] 4.2 Conferir com contas reais: promover, rebaixar, desativar (login recusado) e reativar; tentar alterar a própria conta.

## 5. Documentação

- [x] 5.1 `docs/domain-model.md`: gestão de contas e matriz de permissões.
- [x] 5.2 `openspec validate gerenciar-usuarios --strict`.
