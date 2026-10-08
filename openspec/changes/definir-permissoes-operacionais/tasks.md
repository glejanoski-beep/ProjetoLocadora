# Tasks

## 1. Preparação da verificação

- [ ] 1.1 Preparar branch ou workspace Xano de teste separado de produção, com cópia dos recursos afetados e contas fictícias `admin/member`; verificar identidade do ambiente e registrar baseline sanitizado de login, consulta de identidade e autorização administrativa.
- [ ] 1.2 Preparar destinatário de e-mail de teste e conta descartável para atualização de senha; verificar que os efeitos ocorrerão somente nesses recursos e registrar explicitamente qualquer pré-requisito indisponível.

## 2. Verificação reutilizável de acesso

- [ ] 2.1 Evoluir `Quick Start/enforce_role` para validar existência, estado atual, papel reconhecido e papel mínimo, preservando assinatura e GUID; verificar no runner Xano os casos ativo `member/admin`, inativo, inexistente, papel ausente/desconhecido, estado legado e papel mínimo inválido.
- [ ] 2.2 Integrar auditoria mínima das recusas por estado e papel usando o contrato existente; verificar eventos gerados no teste sem senha, token, e-mail submetido ou objeto completo de usuário e confirmar que a recusa não executa o efeito operacional.
- [ ] 2.3 Registrar a matriz de papéis e a compatibilidade de contas em `docs/domain-model.md` e `docs/project-overview.md`, sem marcar módulos futuros como implementados; verificar correspondência com o delta e distinguir complementos aprovados em Review das decisões já confirmadas.

## 3. Aplicação nos endpoints existentes

- [ ] 3.1 Aplicar a verificação comum a `auth/me` e `logs/user/my_events` antes de devolver dados; verificar acesso dos dois papéis ativos, recusa sem autenticação, recusa após desativação com token válido e manutenção do filtro de eventos pelo usuário autenticado.
- [ ] 3.2 Manter papel mínimo `admin` no envio de boas-vindas com validação do estado atual; verificar `member` recusado e `admin` inativo recusado sem envio, e envio autorizado para destinatário fictício por `admin` ativo.
- [ ] 3.3 Aplicar validação de estado e papel à atualização de senha antes da alteração; verificar conta descartável ativa autorizada e conta desativada com token válido recusada sem mudança da senha.
- [ ] 3.4 Preservar cadastro público e login automático de `member`; verificar criação de conta fictícia, ausência de promoção para `admin` mesmo com entrada manipulada e manutenção dos papéis/estados das contas pré-existentes no ambiente de teste.

## 4. Integração Reflex e evidências

- [ ] 4.1 Validar login, navegação e logout dos dois papéis e desativação durante sessão pelo Reflex; verificar que revalidação recusada limpa a sessão e redireciona ao login, mantendo bearer fora do estado enviado ao navegador. Acrescentar teste de regressão de comportamento apenas se necessário para uma correção nesse fluxo.
- [ ] 4.2 Executar `python -m unittest discover -v` e `reflex compile --dry` no ambiente Python do projeto; confirmar quantidade de testes executados e compilação concluída sem tratar esses checks como substitutos da integração Xano.
- [ ] 4.3 Consolidar resultados atuais da matriz Xano/Reflex sem segredos, com casos aprovados, falhos e não executados; verificar ausência de alterações operacionais nas recusas e registrar os cenários dos módulos ainda ausentes como responsabilidade de Changes futuras.

## Workflow follow-up

- Realizar Review dos artefatos, especialmente os complementos sobre exemplares e ajustes financeiros, antes de Apply.
- Executar Verify com evidências da implementação; pré-requisitos ausentes impedem considerar concluídos os casos afetados.
- Arquivar somente após validação e sincronização do delta de `acesso-seguro`, mantendo as demais especificações intactas.
- Tratar separadamente a reconciliação dos requisitos do login Reflex ausentes da especificação consolidada.
