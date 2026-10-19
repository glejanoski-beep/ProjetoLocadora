# Spec Delta

## Purpose

Definir a apresentação, a responsividade, a acessibilidade e as interações da tela de acesso de funcionários da CINEBYTE LOCADORA sem alterar os contratos seguros de autenticação e recuperação existentes.

## ADDED Requirements

### Requirement: Tela de login reproduz a identidade retrô da CINEBYTE LOCADORA

A rota `/login` SHALL ocupar pelo menos toda a altura visível com fundo `#09090F`, textura discreta de linhas horizontais e formas alusivas a estantes de VHS. A composição SHALL exibir um painel vertical central com largura máxima aproximada de 440–460 px, fundo próximo de `#111118`, borda branca de baixa opacidade, sombra escura ampla, cantos retos e quatro cantoneiras claras. O painel SHALL apresentar, nesta ordem, ícone de fita cassete em ciano com moldura roxa, marca “CINEBYTE LOCADORA”, título “ACESSO DO FUNCIONÁRIO”, subtítulo, formulário, ação de recuperação, botão principal, separador e rodapé “ÁREA RESTRITA • VERSÃO 2.4.8”.

#### Scenario: Composição completa em desktop

- **WHEN** uma pessoa abre `/login` em uma janela de desktop
- **THEN** todos os elementos obrigatórios aparecem na ordem definida dentro de um único painel central
- **AND** nenhum menu, dashboard ou elemento alheio à referência é exibido

#### Scenario: Identidade visual carregada

- **WHEN** a tela conclui o carregamento visual
- **THEN** marca, título e botão usam “Press Start 2P” com fallback monoespaçado
- **AND** descrição, labels, campos, link e rodapé usam “Space Mono” com fallback monoespaçado
- **AND** o texto principal, os detalhes em roxo, ciano e laranja e os brilhos discretos permanecem legíveis sobre o fundo escuro

### Requirement: Composição se adapta sem cortar o formulário

A tela SHALL manter o painel centralizado horizontalmente, usar espaçamento interno aproximado de 32–40 px no desktop e 24 px no celular e permitir rolagem vertical quando a altura disponível for menor que o painel. Em larguras móveis, o painel SHALL respeitar as margens da viewport, o título e o botão SHALL poder quebrar em linhas e a página SHALL NOT produzir rolagem horizontal, sobreposição ou corte de controles.

#### Scenario: Celular estreito

- **WHEN** `/login` é exibida em uma viewport de aproximadamente 390 px de largura
- **THEN** o painel ocupa a largura disponível com margens laterais
- **AND** título, campos e botão permanecem integralmente visíveis e utilizáveis
- **AND** a largura total da página não excede a viewport

#### Scenario: Tela de pouca altura

- **WHEN** a altura da viewport é menor que a altura do painel
- **THEN** a pessoa consegue rolar verticalmente até todos os campos, ações e o rodapé
- **AND** nenhum conteúdo essencial fica preso fora da área alcançável

### Requirement: Formulário acessível envia o login real por botão ou Enter

O formulário SHALL apresentar os campos rotulados “LOGIN” e “SENHA”, respectivamente com os placeholders “Digite seu usuário” e “Digite sua senha”, ícones de usuário e cadeado e associação acessível entre cada label e seu controle. O valor de login SHALL seguir o identificador aceito pelo backend existente, atualmente o e-mail da conta. O envio pelo botão “ENTRAR NO SISTEMA” ou pela tecla Enter SHALL executar uma única tentativa pelo fluxo real de autenticação e manter as regras de acesso vigentes.

#### Scenario: Envio pelo botão

- **WHEN** a pessoa informa credenciais e ativa “ENTRAR NO SISTEMA”
- **THEN** a interface envia uma única tentativa ao fluxo de autenticação existente
- **AND** uma autenticação válida continua redirecionando ao backoffice

#### Scenario: Envio pela tecla Enter

- **WHEN** a pessoa preenche o formulário e pressiona Enter em um dos campos
- **THEN** o mesmo fluxo de submissão do botão é executado uma única vez

#### Scenario: Navegação por teclado

- **WHEN** a pessoa percorre a tela somente pelo teclado
- **THEN** campos, controle de visibilidade, recuperação e botão principal recebem foco em ordem lógica
- **AND** cada elemento interativo apresenta indicação de foco visível

### Requirement: Visibilidade da senha é alternável sem expor a credencial

O campo de senha SHALL oferecer um botão à direita que alterne entre senha oculta e visível, preserve o valor digitado e possua nome acessível coerente com a ação disponível. A senha SHALL permanecer fora do estado público serializado, SHALL NOT ser registrada em logs e SHALL ser descartada do estado privado após cada tentativa de autenticação.

#### Scenario: Mostrar e ocultar senha

- **WHEN** a pessoa aciona o controle de visibilidade
- **THEN** o tipo visual do campo alterna sem apagar nem modificar o valor digitado
- **AND** o nome acessível alterna entre “Mostrar senha” e “Ocultar senha”

#### Scenario: Tentativa concluída

- **WHEN** uma tentativa de login termina com sucesso ou falha
- **THEN** a senha não permanece no estado público nem é incluída em mensagens ou logs

### Requirement: Validação e carregamento preservam o layout

LOGIN e SENHA SHALL ser obrigatórios. Uma submissão incompleta SHALL exibir mensagem de validação em português sem chamar o backend e sem desmontar, deslocar de forma abrupta ou sobrepor o painel. Durante uma tentativa válida, o botão SHALL indicar carregamento, permanecer desabilitado para novas submissões e conservar dimensões suficientes para evitar mudança perceptível da composição. Erros de autenticação SHALL continuar genéricos e acessíveis.

#### Scenario: Campos obrigatórios ausentes

- **WHEN** a pessoa envia o formulário sem preencher LOGIN ou SENHA
- **THEN** a interface informa em português que os campos são obrigatórios
- **AND** nenhuma requisição de autenticação é iniciada

#### Scenario: Duplo acionamento durante autenticação

- **WHEN** uma tentativa já está em andamento e a pessoa ativa novamente o botão ou pressiona Enter
- **THEN** nenhuma segunda tentativa concorrente é iniciada
- **AND** o estado de carregamento permanece perceptível até a conclusão

#### Scenario: Credenciais recusadas

- **WHEN** o backend recusa a autenticação
- **THEN** a interface apresenta a mensagem genérica vigente com papel de alerta
- **AND** não revela se login, senha, papel ou estado cadastral causou a recusa

### Requirement: Recuperação de senha ocorre em diálogo acessível

A ação sublinhada “Esqueci minha senha”, alinhada à direita, SHALL abrir um diálogo simples com título e descrição acessíveis, campo de e-mail associado ao respectivo label e ações de envio e cancelamento. O envio SHALL reutilizar o endpoint real de recuperação e a resposta pública genérica definida por `recuperacao-segura`; SHALL NOT ser apresentado como demonstração. A rota `/recuperar-senha` SHALL permanecer funcional para compatibilidade e a rota `/redefinir-senha` SHALL continuar consumindo magic links.

#### Scenario: Abrir e fechar o diálogo

- **WHEN** a pessoa ativa “Esqueci minha senha”
- **THEN** o diálogo recebe foco e identifica sua finalidade para tecnologia assistiva
- **AND** pode ser fechado por ação explícita ou pela tecla Escape sem enviar dados

#### Scenario: Enviar recuperação válida

- **WHEN** a pessoa informa um e-mail válido e envia o diálogo
- **THEN** a aplicação chama o fluxo real de solicitação de recuperação uma única vez
- **AND** apresenta a mesma confirmação genérica para e-mails cadastrados e não cadastrados

#### Scenario: E-mail ausente ou inválido

- **WHEN** a pessoa tenta enviar o diálogo sem um e-mail válido
- **THEN** a aplicação exibe validação em português e não chama o endpoint de recuperação

### Requirement: Estados interativos preservam a estética e a legibilidade

Inputs e botão SHALL ter cantos retos. Inputs SHALL usar fundo próximo de `#0B0B11`, altura aproximada de 54 px e borda discreta. O botão principal SHALL ter largura total, altura mínima de 56 px, degradê horizontal baseado em `#6D28D9`, `#8B2CF5`, `#0891B2` e `#FF7A45`, borda clara sutil, brilho roxo e sombra sólida deslocada. Hover, foco e pressionamento SHALL fornecer resposta perceptível sem reduzir contraste, ocultar texto ou alterar a largura da composição.

#### Scenario: Interação por ponteiro

- **WHEN** o ponteiro passa sobre ou pressiona um campo, link, controle de senha ou botão
- **THEN** o elemento apresenta resposta visual coerente com a estética retrô
- **AND** o conteúdo permanece legível e estável

#### Scenario: Foco visível em alto contraste

- **WHEN** um controle recebe foco pelo teclado
- **THEN** um contorno ou brilho claramente perceptível identifica o foco
- **AND** a indicação não depende somente de uma mudança sutil de cor
