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

Decisões confirmadas pelo solicitante nesta etapa de Review: `member` pode consultar clientes, filmes e exemplares; a manutenção desses cadastros exige `admin`; `member` pode incluir locações e registrar pagamentos e multas conforme as regras de negócio; estornos, cancelamentos e ajustes financeiros ficam restritos a `admin`; `admin` tem acesso geral sujeito às regras de negócio; a entidade Funcionário é opcional e não é requisito para autenticação; os papéis atuais são `admin` e `member`; e o cadastro público concede acesso automático como `member`.

Essa política não define fórmulas financeiras nem permite alterar histórico silenciosamente. A permissão administrativa para excluir cadastros continua sujeita às invariantes de negócio e de preservação do histórico. Registrar uma transação pode atualizar o estado relacionado pelo fluxo de negócio sem conceder manutenção livre de cadastro. Devolução, reservas e relatórios ainda exigem definição de permissão em suas próprias Changes; não conceder acesso por analogia.

### 4. Preservar identidade e compatibilidade

Não migrar contas, não exigir aprovação, não criar funcionário e não promover/desativar usuários por aplicação da Change. O administrador continua controlando papel e estado pelo mecanismo administrativo disponível no Xano; uma interface própria é futura. O Reflex continua aceitando contas ativas `member/admin` e limpando a sessão quando `auth/me` recusa a revalidação. Não introduzir cookies com bearer nem um segundo modelo de autorização no frontend.

### 5. Verificação acadêmica sem ambiente Xano de teste

Não será criado nem solicitado um branch ou workspace Xano separado. Não executar funções, chamadas, testes ou operações de escrita no Xano remoto; não preparar destinatário de e-mail, conta descartável ou baseline. A falta desses recursos limita as conclusões, mas não bloqueia a avaliação acadêmica baseada nas evidências locais.

Classificar as evidências sem extrapolar seu alcance:

- **Estrutural/estática:** os testes existentes inspecionam os contratos no XanoScript, a ordem da guarda, os campos de auditoria, os filtros por identidade e os fluxos de cadastro e senha. Isso demonstra propriedades do código-fonte, não execução do stack Xano.
- **Sintaxe:** registrar os resultados já obtidos pelo validador XanoScript; sintaxe válida não comprova comportamento ou persistência.
- **Mockada/local:** os testes Reflex simulam login e resposta de identidade, revalidação de conta inativa, logout e transporte HTTP local. Não comprovam autenticação, autorização ou navegação integradas.
- **Runtime/compilação:** identificar explicitamente como não executados os casos Xano. Registrar a compilação Reflex bloqueada pelo Controle de Aplicativo do Windows como não concluída; não contornar a política nem inferir incompatibilidade de versões.

Para cada cenário, indicar qual evidência realmente o cobre e marcar como não executados ou não comprovados os cenários sem evidência. Não alegar persistência de auditoria, recusa efetiva no runtime, envio ou ausência de envio, alteração ou preservação real de dados, nem ausência de efeitos operacionais. Os cenários das capacidades ainda inexistentes permanecem responsabilidade de Changes futuras.

## Risks / Trade-offs

- Cadastro público concede acesso operacional de `member` -> decisão explícita mantida; documentar que leitura de cadastros e transações futuras será acessível a essas contas e verificar cuidadosamente cada API.
- Acesso geral do `admin` pode ser confundido com dispensa de regras -> aplicar validações de negócio após autorização para todos os papéis.
- Tokens anteriores continuam criptograficamente válidos -> consultar estado atual em cada operação protegida; não depender de logout ou expiração.
- Função compartilhada altera todos os chamadores -> preservar assinatura, testar os endpoints e compatibilidade de contas legadas.
- Ausência de ambiente Xano separado -> não permite comprovar runtime, persistência de auditoria ou efeitos operacionais; registrar esses limites sem confundir evidência local com integração.
- Controle de Aplicativo bloqueia a compilação Reflex -> registrar tentativa e bloqueio como resultado inconclusivo para compilação; não contornar a política nem atribuir a falha a incompatibilidade sem evidência.
- Spec consolidada não inclui os requisitos arquivados do login Reflex -> manter regressões desse comportamento e registrar a reconciliação documental separadamente, sem substituir contratos silenciosamente.

## Migration Plan

1. Aplicar a verificação comum e integrações mantendo GUIDs, canonical, assinatura e schemas existentes.
2. Executar os testes locais disponíveis e registrar testes, inspeção estrutural e validações de sintaxe segundo o alcance de cada evidência.
3. Registrar a compilação Reflex como bloqueada e não concluída; não alterar versões nem contornar controles de segurança sem decisão específica.
4. Consolidar a matriz de evidências para Verify, marcando casos de runtime e efeitos não comprovados como não executados. Não publicar em produção nem acessar o Xano remoto como parte desta Change.
