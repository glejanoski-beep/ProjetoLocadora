# Design

## Context

Ver `proposal.md` para motivação e o delta `specs/acesso-seguro/spec.md` para requisitos. A tabela `user` já possui `role` e `is_active`; o cadastro público atribui `member`. `Quick Start/enforce_role` aceita `user_id/required_role`, usa a hierarquia `admin:2, member:1` e não consulta `is_active`. Só o envio de boas-vindas usa essa função; `auth/me`, eventos pessoais e atualização de senha têm autenticação, mas não a verificação comum de estado e papel. O Reflex guarda o bearer no servidor e consulta `auth/me` ao entrar nas páginas internas.

Os módulos operacionais e suas APIs não existem. A matriz abaixo define o contrato de autorização que suas futuras Changes deverão incorporar; não é uma promessa de implementar esses módulos nesta Change.

## Goals / Non-Goals

**Goals:** manter autorização simples, reutilizável e obrigatória no backend; recusar tokens de contas desativadas antes de efeitos operacionais; preservar os contratos públicos e as contas existentes.

**Non-Goals:** criar tabelas de permissões, entidade Funcionário, painel de usuários, provedor de identidade, revogação remota de tokens ou novas operações financeiras. Não corrigir aqui todo o fluxo de recuperação nem criar APIs artificiais só para demonstrar permissões futuras.

## Decisions

### 1. Reutilizar os dois papéis e a função existente

Evoluir `Quick Start/enforce_role` preservando assinatura e identidade do recurso: consultar existência, estado e papel atual da conta, recusar estado explicitamente falso e papéis fora da hierarquia, validar `required_role` e só depois comparar níveis. Preservar a compatibilidade de estado legado sem valor explícito. Nunca confiar em papel ou identificação do operador enviados pelo navegador; endpoints usam `$auth.id`.

Alternativa: criar autorização por permissões armazenadas em tabelas. Não escolhida porque os dois papéis cobrem a política atual e evitam migração, painel e sincronização de permissões. Uma operação futura deverá declarar explicitamente o papel mínimo; ausência de definição não libera `member`.

### 2. Aplicar a verificação antes de dados protegidos e efeitos

| Endpoint existente | Papel mínimo | Verificação |
|---|---|---|
| `GET auth/me` | `member` | Conta ativa e papel antes de devolver identidade |
| `GET logs/user/my_events` | `member` | Conta ativa e papel; manter filtro por identidade autenticada |
| `POST message/send_welcome_email` | `admin` | Conta ativa e papel antes de consultar destinatário ou enviar |
| `POST reset/update_password` | `member` | Conta ativa e papel antes de consultar/alterar senha |

Login, cadastro público, solicitação de recuperação e troca de magic link continuam com seus contratos públicos e validações existentes. Não usar a função de operações autenticadas em endpoint público sem identidade autenticada.

O registro mínimo de recusa é a única escrita permitida quando a autorização falha. Reutilizar `Quick Start/log_event`, sem adicionar e-mail, token, senha, objeto de usuário ou dados pessoais aos metadados.

Alternativa: confiar apenas na revalidação Reflex. Não escolhida porque chamadas diretas ao Xano continuariam usando tokens válidos de contas desativadas.

### 3. Matriz de operações futuras

| Operação | Papel mínimo |
|---|---|
| Consultar clientes, filmes e exemplares | `member` |
| Criar, alterar ou inativar clientes, filmes e exemplares | `admin` |
| Incluir locação | `member` |
| Registrar recebimento e quitação conforme saldo | `member` |
| Registrar multa conforme política de cálculo | `member` |
| Estornar, cancelar ou ajustar transação financeira | `admin` |
| Gerenciar papéis e estado de acesso | `admin` |

Confirmado pelo usuário: leitura de cadastros para `member`, manutenção de clientes/filmes restrita, inclusão de locações e operação de pagamentos/multas permitidas, `admin` com acesso geral, conta interna suficiente e cadastro público com acesso automático.

Complementos propostos para Review: exemplares seguem a mesma separação entre consulta e manutenção; estornos, cancelamentos e ajustes ficam com `admin`. Essa política não define fórmulas financeiras nem permite alterar histórico silenciosamente. Registrar uma transação pode atualizar o estado relacionado pelo fluxo de negócio sem conceder manutenção livre de cadastro. Devolução, reservas e relatórios ainda exigem definição de permissão em suas próprias Changes; não conceder acesso por analogia.

### 4. Preservar identidade e compatibilidade

Não migrar contas, não exigir aprovação, não criar funcionário e não promover/desativar usuários por aplicação da Change. O administrador continua controlando papel e estado pelo mecanismo administrativo disponível no Xano; uma interface própria é futura. O Reflex continua aceitando contas ativas `member/admin` e limpando a sessão quando `auth/me` recusa a revalidação. Não introduzir cookies com bearer nem um segundo modelo de autorização no frontend.

### 5. Verificação proporcional em Xano de teste

Usar branch ou workspace Xano de teste separado de produção, conforme disponibilidade da plataforma, com as mesmas exportações e contas fictícias: `admin` ativo, `member` ativo e conta desativada após emissão de token. Usar infraestrutura Xano existente, sem emulador ou serviços novos. Obter credenciais pelo meio seguro disponível, nunca em artefatos ou logs.

Exercitar os endpoints existentes diretamente, sem depender da interface. Para o teste autorizado de e-mail, usar destinatário de teste e serviço configurado para testes; se indisponível, registrar o caso como não executado, sem alegar validação completa. Para senha, usar somente conta descartável. Exercitar também a função reutilizável no runner Xano com `required_role` igual a `member/admin`, papel ausente/desconhecido e papel requerido inválido, sem alterar schemas de produção.

Matriz mínima de evidência: não autenticado recusado; `member` recusado em operação administrativa; `admin` ativo autorizado; ambos os papéis ativos autorizados em operação comum; token emitido antes da desativação recusado; estado legado com papel válido compatível; auditoria mínima sem segredos. Contar eventos de envio, comparar dados antes/depois e verificar respostas para provar ausência de efeito em recusas.

Executar testes Python e compilação Reflex, além de login/revalidação/logout no ambiente de teste. Não descrever os testes estruturais atuais como cobertura de integração. Cenários de clientes, acervo e financeiro são obrigações das respectivas Changes, não testes executáveis nesta base.

## Risks / Trade-offs

- Cadastro público concede acesso operacional de `member` -> decisão explícita mantida; documentar que leitura de cadastros e transações futuras será acessível a essas contas e verificar cuidadosamente cada API.
- Acesso geral do `admin` pode ser confundido com dispensa de regras -> aplicar validações de negócio após autorização para todos os papéis.
- Tokens anteriores continuam criptograficamente válidos -> consultar estado atual em cada operação protegida; não depender de logout ou expiração.
- Função compartilhada altera todos os chamadores -> preservar assinatura, testar os endpoints e compatibilidade de contas legadas.
- Ausência de ambiente Xano ou de capacidade de runner -> impedir conclusão de Verify dos casos afetados; revisão estática não prova execução no backend.
- Spec consolidada não inclui os requisitos arquivados do login Reflex -> manter regressões desse comportamento e registrar a reconciliação documental separadamente, sem substituir contratos silenciosamente.

## Migration Plan

1. Após Review, preparar ambiente Xano de teste e registrar baseline sem segredos.
2. Aplicar a verificação comum e integrações mantendo GUIDs, canonical, assinatura e schemas existentes.
3. Executar a matriz de verificação, testes Python e compilação; comparar efeitos e auditoria.
4. Atualizar somente documentação de permissões afetada e apresentar evidências para Verify. Não publicar em produção como parte desta Change.
5. Em falha, restaurar os recursos modificados no ambiente de teste à versão anterior; conservar logs e registros necessários à investigação. Não excluir histórico ou restaurar produção para contornar falhas.
