# Tasks

## 1. Preparação após autorização de APPLY

- [x] 1.1 Revalidar main, branches, PRs e export de leitura Xano `v1`; verificar ausência de nova implementação de locação e registrar diferenças de recursos/GUIDs sem sobrescrever módulos dos colegas.
- [x] 1.2 Ler `reflex-docs`, `setup-python-env` e `reflex-process-management` versionadas; verificar ambiente e versão Reflex conforme skills, sem reinicializar o app existente.
- [x] 1.3 Confirmar primitives oficiais Xano para unidade transacional, proteção das leituras e índices únicos; entregar evidência técnica e plano executável de corrida/rollback antes de habilitar criação. Não aprovar proteção baseada somente em consulta seguida de insert.

## 2. Backend e schemas locais

- [x] 2.1 Preparar schemas aditivos de `rental`, `rental_occupancy` e condição operacional de exemplar; validar XanoScript e constraints, preservando identidades reais e sem backfill de disponibilidade.
- [ ] 2.2 Implementar consulta paginada de elegíveis e confirmação administrativa de condição; verificar autorização direta, registros não verificados, filme inativo e exemplar ocupado.
- [ ] 2.3 Implementar criação transacional com autenticação e papel atuais, elegibilidade e vencimento; verificar cliente inexistente/inativo/bloqueado, referência inválida, datas inválidas, campos protegidos e rollback.
- [ ] 2.4 Implementar chave por conta, conflito de conteúdo e consulta de reconciliação; verificar que repetição após commit retorna mesmo `id`, inclusive quando exemplar já está ocupado.
- [ ] 2.5 Implementar consulta por identificador e auditoria mínima; verificar allowlist da resposta, ausência de dados pessoais/segredos e distinção entre falha antes do commit e auditoria posterior.

## 3. Frontend Reflex e transporte

- [x] 3.1 Criar adaptador e configuração independente `XANO_RENTAL_API_URL`; testar URL ausente/inválida, token privado, HTTP 401/403/409/422/500, timeout e resposta inválida sem logs sensíveis.
- [x] 3.2 Criar estado próprio de locação com revisão de sessão e chave da tentativa; testar logout, troca de conta, resposta tardia, duplo envio e reconciliação sem chave nova após timeout.
- [x] 3.3 Criar formulário e confirmação protegidos, seletor real de cliente/exemplar, vencimento em Brasília e seção administrativa de condição; verificar vazio/erro/carregamento/sucesso, permissões e navegação preservada dos cadastros.
- [x] 3.4 Integrar rotas e link no backoffice com mudanças mínimas na sessão; rodar regressão de auth/dashboard/clientes/catálogo/exemplares e `reflex compile --dry` conforme skill, registrando ambiente e resultado.

## 4. Verificação de integridade e entrega

- [x] 4.1 Validar OpenSpec estrito e revisar diff limitado ao escopo; atualizar overview/domain-model somente para comportamentos efetivamente implementados, sem declarar entrega remota antes da hora.
- [x] 4.2 Entregar inventário de alterações Xano, plano de implantação em `v1`, recursos de teste e rollback que preserve histórico; obter autorização específica antes de qualquer publicação ou teste remoto de escrita.
- [ ] 4.3 Em ambiente autorizado, provar que duas requisições concorrentes diferentes no mesmo exemplar produzem um único registro/ocupação; provar idempotência concorrente da mesma chave e rollback com falha injetada entre gravações; registrar evidência real, sem substituir por mocks.
- [ ] 4.4 No mesmo ambiente autorizado, testar bloqueio/inativação e alteração de condição concorrentes, autorização com token antigo, confirmação auditada e resposta perdida; preservar registros operacionais e não criar dados fictícios na base compartilhada.
- [x] 4.5 Relatar arquivos, testes, limitações, estado de publicação e cinco testes Windows pendentes quando aplicável; habilitar criação somente após garantias de integridade e configuração real confirmadas.

## Evidência e pendências

Ver `delivery.md`: 227 testes locais, compilação Reflex e validação sintática Xano concluídos. As tarefas 2.2–2.5 têm código local entregue, mas permanecem abertas para não declarar verificação comportamental no Xano sem execução real. A implantação autorizada da tarefa 4.2 foi concluída com escritas desabilitadas; o usuário autorizou prosseguir com as pendências, mas os testes de escrita das tarefas 4.3–4.4 aguardam indicação de contas e registros reais e homologação remota. Os scripts de homologação foram preparados; somente o modo sem conexão foi executado. A condição de habilitação da tarefa 4.5 é respeitada mantendo as escritas desabilitadas.
