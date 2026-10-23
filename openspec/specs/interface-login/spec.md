# Interface Login Specification

## Purpose

Definir a apresentação, a responsividade, a acessibilidade e as interações da tela de acesso de funcionários da CINEBYTE LOCADORA sem alterar os contratos seguros de autenticação e recuperação existentes.

## Requirements

### Requirement: Tela de login reproduz a vitrine de vidro da CINEBYTE LOCADORA

A rota `/login` SHALL ocupar pelo menos toda a altura visível com fundo composto por uma parede inclinada de cartazes de filmes, uma camada escura (`#07070A` a cerca de 70% de opacidade) e uma vinheta radial. Os cartazes SHALL ser elementos decorativos ocultos de tecnologia assistiva, nunca uma imagem única que substitua os controles. A composição SHALL exibir, no canto superior esquerdo, o logotipo e a identificação “CINEBYTE LOCADORA” e, no canto superior direito, o link “Ajuda”. O painel central SHALL ter largura máxima de 420 px, fundo translúcido escuro com desfoque (efeito de vidro), borda branca de baixa opacidade e cantos arredondados, e SHALL apresentar, nesta ordem, título “Acesso do funcionário”, subtítulo, formulário, ação de recuperação, botão principal vermelho (`#DC2638`) e a orientação “Sem acesso? Fale com o administrador da sua loja.”. Um texto discreto “Acesso restrito a funcionários da CINEBYTE LOCADORA” SHALL aparecer ao pé da página. A tela SHALL NOT exibir dados fictícios, nome de outra marca nem opções sem funcionalidade implementada, como “Manter conectado”.

#### Scenario: Composição completa em desktop

- **WHEN** uma pessoa abre `/login` em uma janela de desktop
- **THEN** cartazes, camada escura, vinheta, identificação, link “Ajuda” e painel central aparecem na composição definida
- **AND** nenhum menu, dashboard ou elemento alheio à referência é exibido

#### Scenario: Identidade visual carregada

- **WHEN** a tela conclui o carregamento visual
- **THEN** títulos, labels, campos, botões e textos principais usam “Inter” com fallback sem serifa
- **AND** somente o texto de rodapé da página usa “Space Mono” com fallback monoespaçado
- **AND** o texto claro permanece legível sobre o fundo escuro

#### Scenario: Link de ajuda

- **WHEN** a pessoa ativa “Ajuda”
- **THEN** a página navega para a orientação de suporte no painel, sem criar rota nem endereço de contato

### Requirement: Formulário acessível envia o login real por botão ou Enter

O formulário SHALL apresentar os campos rotulados “E-mail” e “Senha”, respectivamente com os placeholders “nome@exemplo.com” e “Sua senha” e associação acessível entre cada label e seu controle. O valor de login SHALL seguir o identificador aceito pelo backend existente, atualmente o e-mail da conta. O envio pelo botão “Entrar” ou pela tecla Enter SHALL executar uma única tentativa pelo fluxo real de autenticação e manter as regras de acesso vigentes.

#### Scenario: Envio pelo botão

- **WHEN** a pessoa informa credenciais e ativa “Entrar”
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

O campo de senha SHALL oferecer um botão textual à direita (“mostrar”/“ocultar”) que alterne entre senha oculta e visível, preserve o valor digitado e possua nome acessível coerente com a ação disponível. A senha SHALL permanecer fora do estado público serializado, SHALL NOT ser registrada em logs e SHALL ser descartada do estado privado após cada tentativa de autenticação.

#### Scenario: Mostrar e ocultar senha

- **WHEN** a pessoa aciona o controle de visibilidade
- **THEN** o tipo visual do campo alterna sem apagar nem modificar o valor digitado
- **AND** o nome acessível alterna entre “Mostrar senha” e “Ocultar senha”

#### Scenario: Tentativa concluída

- **WHEN** uma tentativa de login termina com sucesso ou falha
- **THEN** a senha não permanece no estado público nem é incluída em mensagens ou logs

### Requirement: Validação e carregamento preservam o layout

E-mail e senha SHALL ser obrigatórios. Uma submissão incompleta SHALL exibir mensagem de validação em português sem chamar o backend e sem desmontar, deslocar de forma abrupta ou sobrepor o painel. Durante uma tentativa válida, o botão SHALL indicar carregamento, permanecer desabilitado para novas submissões e conservar dimensões suficientes para evitar mudança perceptível da composição. Erros de autenticação SHALL continuar genéricos e acessíveis.

#### Scenario: Campos obrigatórios ausentes

- **WHEN** a pessoa envia o formulário sem preencher e-mail ou senha
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

A ação sublinhada “Esqueci minha senha”, alinhada à direita abaixo da senha, SHALL abrir um diálogo simples com título e descrição acessíveis, campo de e-mail associado ao respectivo label e ações de envio e cancelamento. O envio SHALL reutilizar o endpoint real de recuperação e a resposta pública genérica definida por `recuperacao-segura`; SHALL NOT ser apresentado como demonstração. A rota `/recuperar-senha` SHALL permanecer funcional para compatibilidade e a rota `/redefinir-senha` SHALL continuar consumindo magic links.

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

Inputs SHALL usar fundo escuro translúcido, altura aproximada de 48 px, cantos arredondados e borda discreta. O botão principal SHALL ter largura total, altura mínima de 50 px e fundo vermelho `#DC2638`. Hover, foco e pressionamento SHALL fornecer resposta perceptível sem reduzir contraste, ocultar texto ou alterar a largura da composição. O diálogo de recuperação SHALL seguir o mesmo tratamento de vidro.

#### Scenario: Interação por ponteiro

- **WHEN** o ponteiro passa sobre ou pressiona um campo, link, controle de senha ou botão
- **THEN** o elemento apresenta resposta visual coerente com o tema de vidro
- **AND** o conteúdo permanece legível e estável

#### Scenario: Foco visível em alto contraste

- **WHEN** um controle recebe foco pelo teclado
- **THEN** um contorno claramente perceptível identifica o foco
- **AND** a indicação não depende somente de uma mudança sutil de cor
