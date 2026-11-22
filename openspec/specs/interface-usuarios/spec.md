# interface-usuarios Specification

## Purpose
Página de usuários do backoffice.

## Requirements

### Requirement: Página de usuários para administradores

A rota `/usuarios` SHALL exigir sessão. Para `admin`, SHALL listar as contas com nome, e-mail, papel traduzido ("Administrador" ou "Funcionário"), situação ("Ativa" ou "Desativada") e data de cadastro, com busca por nome ou e-mail (sem diferença de acentos e maiúsculas) e filtro por situação, sem novas requisições ao buscar ou filtrar. Para `member`, a página SHALL informar que o conteúdo é restrita a administradores e SHALL NOT consultar o backend. A página SHALL apresentar fundo, superfícies, textos, bordas, ícones e botões legíveis nos modos claro e escuro, sem alterar as dimensões ou a composição existentes.

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

#### Scenario: Página no modo claro
- **WHEN** o tema claro está ativo na página de usuários
- **THEN** títulos, nomes, e-mails, datas, filtros, status, rótulos e ações secundárias usam contraste escuro legível sobre superfícies claras

#### Scenario: Página no modo escuro
- **WHEN** o tema escuro está ativo na página de usuários
- **THEN** a apresentação existente em modo escuro permanece visualmente coerente e legível

#### Scenario: Botão novo usuário
- **WHEN** um administrador visualiza a página de usuários
- **THEN** vê o botão “Novo usuário”
- **AND** o botão abre o modal de criação

### Requirement: Diálogo de alteração de conta

Para cada conta que não seja a própria, o admin SHALL poder abrir um diálogo com papel, situação e motivo obrigatório. O envio SHALL ocorrer uma única vez por clique, a lista SHALL ser atualizada com a resposta do backend e as recusas de negócio SHALL ser exibidas como vieram, mantendo o diálogo aberto. A própria conta SHALL aparecer marcada como "Você", sem ação de alteração. Desativar uma conta SHALL pedir confirmação explicando que a pessoa perde o acesso. Os controles, textos, bordas e ações do modal SHALL usar a paleta correspondente ao tema ativo.

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

#### Scenario: Modal no modo claro
- **WHEN** o tema claro está ativo e o admin abre o diálogo de alteração ou confirmação
- **THEN** o modal usa fundo claro, título e rótulos escuros, campo de motivo legível, botão cancelar neutro e ação principal com contraste adequado

#### Scenario: Modal no modo escuro
- **WHEN** o tema escuro está ativo e o admin abre o diálogo de alteração ou confirmação
- **THEN** o modal conserva a apresentação escura atual e todos os textos permanecem legíveis

### Requirement: Diálogo de criação de conta

Um administrador SHALL poder abrir um modal simples para cadastrar nova conta informando nome, e-mail e papel. O nome SHALL ser obrigatório e SHALL ter no máximo 200 caracteres. O papel SHALL aceitar somente `Administrador` ou `Funcionário`. O modal SHALL validar nome e e-mail antes do envio, não solicitar senha inicial e explicar que o novo usuário deverá usar “Esqueci minha senha” para definir a própria senha.

#### Scenario: Validação local
- **WHEN** o administrador tenta enviar o modal sem nome ou com e-mail inválido
- **THEN** a interface informa o problema
- **AND** nenhuma requisição é enviada

#### Scenario: Criação bem-sucedida
- **WHEN** o administrador informa nome e e-mail válidos, seleciona um papel e confirma
- **THEN** o backend cria uma conta ativa sem senha
- **AND** o modal fecha
- **AND** a nova conta aparece na lista
- **AND** o modal informa que o usuário deverá usar “Esqueci minha senha”

#### Scenario: E-mail duplicado
- **WHEN** o backend rejeita o e-mail por já existir
- **THEN** o modal permanece aberto
- **AND** exibe a mensagem recebida

#### Scenario: Cancelamento
- **WHEN** o administrador fecha ou cancela o modal
- **THEN** o rascunho é descartado
- **AND** nenhum usuário é criado

#### Scenario: Modal nos dois temas
- **WHEN** o modal é aberto no modo claro ou escuro
- **THEN** fundo, bordas, título, rótulos, campos, botão cancelar e botão criar permanecem legíveis
