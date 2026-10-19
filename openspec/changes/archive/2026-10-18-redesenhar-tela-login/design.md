# Design

## Context

Ver [proposal.md](./proposal.md) para a motivação. A rota `/login` e o estado de autenticação estão hoje no módulo principal `ProjetoLocadora/ProjetoLocadora.py`; a autenticação real usa `login_xano`, revalida a conta com `get_me_xano` e mantém token, identidade e senha em variáveis privadas do servidor Reflex. A recuperação já usa o Xano e possui as rotas públicas `/recuperar-senha` e `/redefinir-senha`.

O projeto fixa Reflex 0.9.11 e já possui os plugins de Tailwind e Radix. A implementação deve continuar integralmente em Python/Reflex. A referência visual foi verificada em viewport móvel de 390 × 844 px e em viewport de baixa altura: o painel tem largura máxima próxima de 460 px, campos de 54 px, botão de 56 px e quebra do título sem overflow horizontal.

## Goals / Non-Goals

**Goals:**

- Encapsular a composição do login em componentes Python reutilizáveis, mantendo o estado e as integrações existentes.
- Usar primitives documentadas do Reflex 0.9.11 para formulário, diálogo, estado, eventos e responsividade.
- Preservar as garantias de segurança: senha e tokens fora do estado público, mensagens genéricas e backend Xano como autoridade.
- Permitir verificação automatizada de eventos e estrutura, compilação Reflex e inspeção visual em desktop e celular.

**Non-Goals:**

- Alterar endpoints, tabelas, funções ou a branch `v1` do Xano.
- Aceitar nome de usuário quando o backend atual autentica por e-mail; “LOGIN” é o rótulo visual do identificador existente.
- Redesenhar backoffice, tela de redefinição ou módulos operacionais.
- Remover as rotas públicas atuais de recuperação.
- Introduzir React manual, JavaScript customizado ou biblioteca visual adicional.

## Decisions

### 1. Manter o estado de autenticação no módulo principal e decompor somente a camada visual

A página permanecerá registrada no módulo principal para evitar uma refatoração transversal do `State` e das demais páginas. A composição será dividida em funções de componente para fundo, painel, cabeçalho, campo com ícone, formulário, diálogo de recuperação e rodapé. Estilos compartilhados e efeitos que dependem de pseudo-elementos ficarão em `assets/login.css`.

Alternativa considerada: mover toda a autenticação e a página para módulos novos. Foi rejeitada porque ampliaria o risco de ciclos de importação e mudaria uma arquitetura além do necessário para esta change.

### 2. Usar `rx.form` como único caminho de submissão

O formulário envolverá os dois campos e um botão `type="submit"`; `on_submit` chamará o mesmo handler usado para login. Isso entrega envio por Enter e por clique sem manter dois caminhos de evento. O handler adicionará uma guarda imediata para `is_loading`, validará os campos e só então iniciará o fluxo Xano. O botão refletirá `loading` e `disabled` durante a chamada.

A validação de obrigatoriedade será controlada pelo handler para garantir mensagem em português, com região de erro reservada, `role="alert"`, `aria-invalid` e `aria-describedby`. A validação nativa poderá complementar a semântica, mas não será a única fonte da mensagem.

Alternativa considerada: manter apenas `on_click`. Foi rejeitada porque não garante submissão consistente por Enter e favorece duplicação de lógica.

### 3. Separar estado público de apresentação e estado privado de credenciais

Serão públicas apenas variáveis de interface não sensíveis, como `password_visible`, estado de abertura do diálogo e indicadores/mensagens necessários à renderização. Login, senha, token e e-mail de recuperação continuarão em variáveis privadas/backend do `State`; a senha será limpa após qualquer tentativa. A alternância muda somente o tipo visual do campo e o nome acessível do botão, preservando o valor já digitado.

Alternativa considerada: controlar `value` da senha por uma base var pública. Foi rejeitada porque serializaria a credencial para o estado do cliente e contrariaria os testes e invariantes de segurança existentes.

### 4. Usar diálogo controlado para recuperação sem remover as rotas atuais

O link abrirá `rx.dialog.root` controlado por estado, com `rx.dialog.title`, `rx.dialog.description`, formulário de e-mail e controles de cancelar/enviar. O handler `request_reset_link` receberá guarda contra duplicidade, validará o e-mail, chamará o endpoint real e continuará apresentando resposta genérica. Fechar o diálogo limpará somente campos e mensagens da interação, sem afetar a sessão.

A rota `/recuperar-senha` continuará disponível e poderá reutilizar o mesmo formulário/handler. `/redefinir-senha` e o consumo do magic link não serão alterados.

Alternativa considerada: substituir a recuperação real por demonstração local. Foi rejeitada porque o backend já existe e a change não pode degradar o contrato `recuperacao-segura`.

### 5. Combinar propriedades Reflex com uma folha CSS local focada

Layout, conteúdo e eventos permanecerão declarados em componentes Reflex. `assets/login.css` concentrará textura de scanlines/VHS, cantoneiras, gradiente multicolorido, sombras deslocadas, pseudoestados e media queries de altura/largura. A folha será registrada em `rx.App(stylesheets=[...])`, junto aos imports de “Press Start 2P” e “Space Mono”, conforme a API documentada do Reflex 0.9.11.

As cores, dimensões e tipografia serão expressas por variáveis CSS para evitar divergência entre componentes. Breakpoints preservarão 24 px de padding interno em celular, 32–40 px em desktop e `overflow-y: auto` na página. Animações, se usadas, respeitarão `prefers-reduced-motion`.

Alternativa considerada: expressar todos os efeitos inline. Foi rejeitada porque pseudo-elementos, scanlines, cantoneiras e media queries ficariam duplicados e menos verificáveis.

### 6. Usar ícones nativos disponíveis e não copiar ativos da referência

Ícones de cassete, usuário, cadeado, olho e seta serão fornecidos pelo conjunto Lucide já instalado por meio de componentes Reflex. O visual será reproduzido por composição e CSS, sem incorporar código ou ativos proprietários da página de referência.

### 7. Verificar comportamento, compilação e geometria visual

Testes de estado cobrirão obrigatoriedade, guarda contra duplicidade, limpeza da senha, alternância de visibilidade e recuperação real. Testes estruturais cobrirão formulário, labels, nomes acessíveis e diálogo. A aplicação será compilada com o processo Reflex do projeto.

A inspeção em navegador usará pelo menos 1440 × 900 px, 390 × 844 px e uma viewport de baixa altura. Serão verificados largura do painel, ausência de overflow horizontal, rolagem vertical, ordem do conteúdo, foco visível, quebra do título/botão e estados de loading/erro. A referência externa servirá como comparação visual, não como dependência de execução.

## Risks / Trade-offs

- **[Fontes externas indisponíveis]** → Manter fallback `monospace`; se o ambiente exigir operação sem rede, os arquivos licenciados poderão ser hospedados em `assets/fonts` sem mudar os componentes.
- **[Mudança de tipo do input pode perder o valor em uma remontagem]** → Manter identidade estável do componente e adicionar teste funcional de alternância com valor preenchido.
- **[CSS global afeta outras páginas]** → Prefixar seletores com uma classe raiz exclusiva da tela de login e limitar variáveis ao escopo do painel.
- **[Duplo envio por clique e Enter]** → Centralizar submissão em `rx.form` e repetir a guarda no handler servidor, não somente no estado visual do botão.
- **[Layout fiel mas excessivamente rígido]** → Usar medidas da referência como tokens e máximos, não larguras absolutas, além de testar os três tamanhos definidos.
- **[Texto “LOGIN” sugere usuário livre]** → Manter placeholder solicitado, mas configurar autocomplete e validação para o identificador aceito hoje pelo backend, sem prometer autenticação por nome.

## Migration Plan

1. Adicionar a folha de estilos e registrar fontes/estilos na aplicação.
2. Introduzir os estados e handlers de apresentação sem alterar a integração Xano.
3. Substituir a composição de `/login` pelos componentes reutilizáveis e integrar o diálogo ao handler existente.
4. Manter `/recuperar-senha` e `/redefinir-senha` operacionais e executar os testes de regressão de autenticação/recuperação.
5. Compilar e verificar visualmente os breakpoints antes de concluir a change.

Rollback: reverter a composição da rota e a folha `login.css`; como não há migração de dados, API ou Xano, o fluxo anterior pode ser restaurado sem conversão de estado persistido.
