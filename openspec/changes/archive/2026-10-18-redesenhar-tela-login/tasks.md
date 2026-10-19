# Tasks

## 1. Estado e submissão segura

- [x] 1.1 Adicionar ao `State` somente as variáveis públicas não sensíveis de apresentação (visibilidade da senha, abertura do diálogo e carregamento da recuperação), mantendo login, senha, e-mail de recuperação e tokens em backend vars; verificar com testes que credenciais não aparecem em `State.base_vars`.
- [x] 1.2 Adaptar o login para uma única submissão de formulário com validação obrigatória em português, guarda imediata contra `is_loading` e limpeza da senha após sucesso ou falha; verificar com testes assíncronos que clique/Enter convergem para um único handler, campos vazios não chamam o Xano e reenvios concorrentes não duplicam a chamada.
- [x] 1.3 Implementar eventos de mostrar/ocultar senha com nome acessível reativo e verificar em teste funcional que o valor digitado é preservado nas duas transições.
- [x] 1.4 Reforçar `request_reset_link` com validação de e-mail, estado de carregamento e guarda contra duplicidade, preservando a resposta genérica e o endpoint real; verificar com testes que e-mail inválido não chama o cliente Xano e que uma solicitação válida o chama uma única vez sem expor cadastro.

## 2. Componentes e acessibilidade da tela

- [x] 2.1 Extrair funções de componente para fundo, painel, cabeçalho, cantoneiras, campo com ícone, formulário e rodapé e recompor `/login` na ordem definida pela spec; verificar por compilação e teste estrutural que textos, ícone de cassete, separador e versão 2.4.8 aparecem uma única vez e sem elementos extras.
- [x] 2.2 Implementar os campos LOGIN e SENHA dentro de `rx.form`, com labels associados, placeholders, autocomplete coerente, ícones, botão de visibilidade e região de erro reservada; verificar em teste de componente/navegador a ordem de foco, os nomes acessíveis, o envio por Enter e o `role="alert"` da mensagem.
- [x] 2.3 Integrar “Esqueci minha senha” a um `rx.dialog.root` controlado, com título, descrição, campo de e-mail, cancelamento por ação/Escape e submissão real; verificar por testes que abrir/fechar não autentica nem envia dados, que a resposta genérica é exibida e que `/recuperar-senha` e `/redefinir-senha` continuam compilando.
- [x] 2.4 Manter o botão principal com `type="submit"`, loading e disabled derivados do estado e verificar em teste que sua largura/altura e conteúdo não mudam entre repouso, carregamento e erro.

## 3. Identidade visual e responsividade

- [x] 3.1 Criar `assets/login.css` com tokens de cor, tipografia, dimensões, textura scanline/VHS, painel, cantoneiras, gradiente, brilhos e sombras, sempre sob uma classe raiz exclusiva; registrar a folha e as fontes “Press Start 2P” e “Space Mono” em `rx.App` e verificar com `reflex compile --dry` que os assets são resolvidos.
- [x] 3.2 Implementar hover, foco visível, pressionamento e `prefers-reduced-motion` para campos, links e botões, com cantos retos e contraste legível; verificar por navegação apenas com teclado e inspeção dos estilos computados que nenhum controle perde indicação de foco ou texto.
- [x] 3.3 Aplicar regras responsivas de largura, padding e overflow para desktop, 390 × 844 px e viewport de baixa altura; verificar no navegador que o painel respeita o máximo de 440–460 px, não há overflow horizontal e todo o conteúdo é alcançável por rolagem vertical.
- [x] 3.4 Comparar capturas desktop e celular com a referência fornecida e ajustar proporções, alinhamento, tipografia, cores e espaçamentos; verificar que título e botão quebram sem sobreposição e registrar as capturas finais usadas na revisão da change.

## 4. Instruções e integração

- [x] 4.1 Criar ou atualizar `README.md` com requisitos, instalação no ambiente Python escolhido, `reflex compile --dry` e execução em produção com `reflex run --env prod --single-port`; verificar cada comando documentado no ambiente do projeto sem incluir segredos do `.env`.
- [x] 4.2 Executar a suíte de testes de autenticação/recuperação e os novos testes da interface, corrigindo regressões; verificar que todos passam e que as asserções existentes sobre senha e tokens privados permanecem válidas.
- [x] 4.3 Executar `reflex compile --dry` e iniciar o app em produção para o smoke test local; verificar `/login`, `/recuperar-senha` e `/redefinir-senha`, os estados de validação/loading/erro com integrações mockadas e a ausência de exceções no log.
- [x] 4.4 Revisar o diff final para confirmar que nenhuma API, tabela ou função Xano foi alterada, que `.env` não foi modificado e que a implementação permanece restrita ao frontend Reflex e à documentação desta change.
