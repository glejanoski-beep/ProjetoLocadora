# Proposal

## Why

O projeto possui autenticação e papéis `admin/member`, mas ainda não define as permissões das operações da locadora e a função de autorização existente não verifica se a conta foi desativada. Antes de entregar cadastros e transações, é necessário estabelecer uma política simples e verificável no backend.

## What Changes

- Definir `admin` com acesso geral às operações, sempre sujeito às regras de negócio e à preservação do histórico.
- Definir `member` com leitura dos cadastros de clientes e filmes e permissão para incluir locações, registrar pagamentos e registrar multas. Criar ou alterar clientes e filmes exige `admin`.
- Preservar o cadastro público com papel `member` e acesso automático, sem aprovação prévia; preservar os papéis das contas existentes. A conta interna basta, sem entidade Funcionário obrigatória.
- Exigir conta ativa e papel reconhecido em cada operação protegida, inclusive quando o token foi emitido antes da desativação. **BREAKING**: contas explicitamente desativadas deixam de executar operações protegidas com tokens ainda válidos.
- Aplicar essa verificação aos endpoints protegidos existentes e estabelecer o contrato para as APIs operacionais futuras, sem criar esses módulos nesta Change.
- Propor, para revisão, administração de exemplares, gestão de acessos, estornos, cancelamentos e ajustes financeiros restritos a `admin`. Não tratar registro de multa como permissão para escolher valores arbitrários ou alterar multas quitadas.
- Definir verificação em ambiente Xano de teste, com contas e dados fictícios, chamadas diretas às APIs, regressão Reflex e evidência de ausência de efeitos colaterais em recusas.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `acesso-seguro`: acrescentar política por operação, acesso automático de novas contas `member` e verificação de estado ativo nas operações protegidas.

## Impact

- XanoScript: `Quick Start/enforce_role`, `auth/me`, `logs/user/my_events`, `message/send_welcome_email` e `reset/update_password`; os endpoints públicos de login, cadastro e recuperação continuam públicos.
- Reflex: preservar login, estado backend-only, revalidação e logout; verificar que desativação encerra o acesso local quando revalidado.
- Documentação: registrar a matriz e a distinção entre leitura de cadastro, manutenção de cadastro e transação operacional. A auditoria mantém seu contrato existente.
- Validação: Xano de teste e testes Python/compilação Reflex existentes; nenhum novo provedor de identidade, serviço de sessão ou tabela de permissões.
- Fora do escopo: implementar clientes, filmes, exemplares, locações, multas ou pagamentos; criar painel de gestão de usuários; mudar regras financeiras; publicar em produção; consolidar todo o histórico arquivado do OpenSpec. A ausência dos requisitos de login Reflex na spec principal fica registrada como pendência documental separada.
