<!-- reflex managed begin (do not edit inside this block; add custom content outside the markers) -->
# Agents

This project uses the **Reflex agent skills** � up-to-date knowledge for building full-stack Python web apps with [Reflex](https://reflex.dev). Install them first, then use them as described below.

## Installing the Skills

Before working on this project, make sure the Reflex skills are available to you.

### Claude Code

If the skills are not already available, install them yourself by running these shell commands:

```bash
claude plugin marketplace add reflex-dev/agent-skills
claude plugin install reflex@reflex-agent-skills
```

Newly installed plugins load on the next session. After installing, tell the user to restart the session so the skills auto-load; until then, read the skill files directly from `~/.claude/plugins/` when you need them.

### Other agents (Cursor, OpenCode, Codex, Pi)

```
npx skills add reflex-dev/agent-skills
```

Or clone https://github.com/reflex-dev/agent-skills and copy the `skills/` folders into your agent's skill directory (see the repo README for paths).

### Verifying

Before writing or editing any Reflex code, confirm these three skills are available: `reflex-docs`, `setup-python-env`, and `reflex-process-management`. If they are not, STOP and run the install step above � do not proceed without them.

## Using the Skills

### Reflex documentation

For anything about Reflex APIs � components, state management, events, styling, database, routing, authentication � use the **reflex-docs** skill rather than relying on memory. It carries current, version-accurate docs.

### Initializing a new Reflex project

When starting a new Reflex project or setting up a development environment, you **must** follow the **setup-python-env** skill before doing anything else.

Do not skip any steps. Do not assume a virtual environment or Reflex is already available � always verify first by following the skill's instructions in order.

After the environment is ready and Reflex is installed, run:

```bash
reflex init
```

Then proceed with the user's request.

### Managing a Reflex process

When you need to compile, run, reload, or debug a Reflex application, follow the **reflex-process-management** skill for the correct sequence and error investigation steps.
<!-- reflex managed end -->

## Regras gerais do projeto

Estas regras complementam as instruções gerenciadas do Reflex e devem ser consideradas em todo o projeto.

### Contexto e documentação

- Antes de mudanças significativas, consultar `docs/project-overview.md`, `docs/domain-model.md` e as especificações relacionadas em `openspec/`.
- Usar OpenSpec para mudanças funcionais e manter a implementação alinhada à especificação aprovada.
- Atualizar a documentação quando uma mudança alterar escopo, arquitetura, conceitos ou invariantes do domínio.
- Não duplicar nesses arquivos toda a documentação do projeto; registrar somente regras e decisões necessárias.

### Arquitetura

- Usar Xano e XanoScript como base do backend, dados, APIs e funções.
- Implementar o frontend exclusivamente com Reflex, utilizando seus mecanismos próprios para componentes, estado, eventos, páginas e interação.
- Não introduzir outra tecnologia de frontend para substituir ou complementar o Reflex sem alteração arquitetural explicitamente aprovada.
- Manter separados os conceitos de filme e exemplar físico, controlando a disponibilidade no nível do exemplar.
- Reutilizar padrões existentes e não introduzir tecnologias alternativas sem justificativa e avaliação de impacto.

### Segurança e integridade

- Aplicar autenticação e autorização no backend; a interface não é mecanismo de segurança.
- Aplicar o princípio do menor privilégio e proteger dados pessoais, financeiros, credenciais e tokens.
- Validar no backend operações de locação, devolução, multa, pagamento, bloqueio e administração.
- Preservar a rastreabilidade e o histórico; não apagar registros para corrigir operações.
- Impedir duas locações ativas para o mesmo exemplar e manter consistentes locação, devolução, disponibilidade, multa e pagamento.

### Escopo e validação

- Implementar somente o que estiver definido na solicitação ou especificação atual.
- Evitar alterações não relacionadas e preservar contratos existentes, salvo quando sua evolução estiver documentada.
- Toda mudança funcional deve ter estratégia de verificação proporcional ao risco.
- Verificar especialmente permissões, transições de estado, cálculos financeiros e concorrência sobre disponibilidade.

### Instruções especializadas

- Para alterações em Xano/XanoScript e no projeto Python auxiliar, consultar `.vscode/.github/copilot-instructions.md`.
- Essas instruções especializadas complementam este arquivo e não podem contrariar suas regras gerais.
