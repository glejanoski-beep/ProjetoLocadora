# Instruções para Agentes — Sistema de Gestão para Locadora

Este arquivo define como agentes de IA devem atuar neste repositório. Ele complementa, mas não substitui, a documentação de visão e domínio do projeto.

## 1. Consultar o contexto antes de alterar

Antes de realizar uma mudança significativa:

- consultar `docs/project-overview.md` para entender objetivos, escopo e restrições;
- consultar `docs/domain-model.md` para entender os conceitos e relacionamentos do domínio;
- consultar as especificações relacionadas em `openspec/`, quando existirem;
- verificar a implementação próxima da área afetada antes de propor novas estruturas.

Não repetir nesses arquivos as listas completas de requisitos ou entidades. Atualizar a documentação de contexto somente quando a mudança alterar uma decisão global do projeto.

## 2. Respeitar a arquitetura definida

- Usar Xano e XanoScript como base do backend, dados, APIs e funções do projeto.
- Reutilizar padrões, funções, tabelas, APIs e mecanismos de autenticação já existentes quando forem adequados.
- Não introduzir tecnologia alternativa ou dependência externa sem justificativa registrada e avaliação de impacto.
- Manter a separação conceitual entre filme e exemplar físico.

## 3. Controlar o escopo das mudanças

- Implementar somente o que estiver definido na solicitação ou especificação atual.
- Evitar refatorar, renomear ou modificar funcionalidades não relacionadas sem justificativa.
- Preferir mudanças pequenas, reversíveis e compatíveis com os dados e contratos existentes.
- Não apagar histórico de locações, devoluções, multas, pagamentos ou eventos para corrigir uma operação; usar ajustes rastreáveis quando necessário.
- Preservar as interfaces públicas existentes, salvo quando a mudança exigir sua evolução documentada.

## 4. Usar OpenSpec para mudanças funcionais

- Mudanças funcionais devem ser descritas em uma especificação dentro de `openspec/` antes da implementação, quando ainda não houver uma especificação aplicável.
- A especificação deve explicar contexto, comportamento esperado, regras, critérios de aceite e impactos relevantes.
- Manter a implementação alinhada à especificação aprovada.
- Se a implementação revelar uma decisão de domínio nova, atualizar a especificação correspondente e, quando necessário, o `project-overview.md` ou o `domain-model.md`.

## 5. Aplicar segurança no backend

- Autenticação e autorização devem ser verificadas no backend; a interface não é uma barreira de segurança.
- Aplicar o princípio do menor privilégio aos usuários, funcionários e perfis de acesso.
- Validar no backend operações sensíveis, incluindo locações, devoluções, multas, pagamentos, bloqueios e alterações administrativas.
- Nunca expor dados pessoais, financeiros ou credenciais além do necessário para a operação autorizada.
- Registrar eventos relevantes para auditoria sem armazenar dados sensíveis desnecessários.

## 6. Preservar integridade do domínio

Ao alterar regras ou fluxos:

- impedir que um exemplar tenha duas locações ativas simultaneamente;
- impedir novas locações para clientes bloqueados ou para exemplares indisponíveis;
- manter consistentes locação, devolução, disponibilidade, multa e pagamento;
- conservar os vínculos entre cliente, exemplar e locação;
- garantir que correções financeiras e operacionais permaneçam rastreáveis.

## 7. Verificar cada mudança

- Toda mudança funcional deve possuir uma estratégia de verificação adequada ao risco.
- Executar os testes, validações ou verificações disponíveis para a área alterada.
- Verificar especialmente transições de estado, permissões, cálculos de multa, pagamentos e concorrência sobre disponibilidade.
- Não considerar uma mudança concluída apenas porque o código foi escrito; registrar falhas de validação e limitações conhecidas.
- Manter verificações focadas na mudança e evitar alterar testes ou comportamentos não relacionados.

## 8. Documentar decisões

- Registrar em `openspec/` decisões específicas de uma mudança.
- Atualizar `docs/project-overview.md` quando houver alteração de escopo, objetivo, tecnologia ou restrição global.
- Atualizar `docs/domain-model.md` quando surgirem ou mudarem conceitos, relacionamentos ou invariantes do domínio.
- Manter a documentação concisa e complementar, sem duplicar a implementação nem os demais documentos.
