# interface-usuarios Specification

## Purpose
Página de usuários do backoffice.

## Requirements

### Requirement: Página de usuários para administradores

A rota `/usuarios` SHALL exigir sessão. Para `admin`, SHALL listar as contas com nome, e-mail, papel traduzido ("Administrador" ou "Funcionário"), situação ("Ativa" ou "Desativada") e data de cadastro, com busca por nome ou e-mail (sem diferença de acentos e maiúsculas) e filtro por situação, sem novas requisições ao buscar ou filtrar. Para `member`, a página SHALL informar que o conteúdo é restrito a administradores e SHALL NOT consultar o backend.

#### Scenario: Admin abre a página
- **WHEN** um admin abre `/usuarios`
- **THEN** a lista de contas é carregada uma vez e exibida

#### Scenario: Busca
- **WHEN** o admin digita parte do nome ou do e-mail
- **THEN** a lista mostra só as contas correspondentes, sem nova requisição

#### Scenario: Member abre a página
- **WHEN** um member abre `/usuarios`
- **THEN** a página informa que é restrita a administradores, sem consultar o backend

#### Scenario: Erro ou limite de requisições
- **WHEN** a consulta falha ou o Xano atinge o limite do plano
- **THEN** a página mostra a mensagem correspondente e a ação "Tentar novamente"

### Requirement: Diálogo de alteração de conta

Para cada conta que não seja a própria, o admin SHALL poder abrir um diálogo com papel, situação e motivo obrigatório. O envio SHALL ocorrer uma única vez por clique, a lista SHALL ser atualizada com a resposta do backend e as recusas de negócio SHALL ser exibidas como vieram, mantendo o diálogo aberto. A própria conta SHALL aparecer marcada como "Você", sem ação de alteração. Desativar uma conta SHALL pedir confirmação explicando que a pessoa perde o acesso.

#### Scenario: Alteração bem-sucedida
- **WHEN** o admin muda o papel de uma conta, informa o motivo e salva
- **THEN** o diálogo fecha e a linha mostra o novo papel

#### Scenario: Recusa do backend
- **WHEN** o backend recusa a alteração
- **THEN** o diálogo continua aberto com a mensagem recebida

#### Scenario: Desativação pede confirmação
- **WHEN** o admin desmarca "Conta ativa" e salva
- **THEN** a interface pede confirmação antes de enviar

#### Scenario: Própria conta
- **WHEN** a lista mostra a conta do admin logado
- **THEN** a linha aparece marcada como "Você" e não oferece alteração
