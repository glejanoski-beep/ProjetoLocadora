# Tasks

## 1. Fundação do tema

- [x] 1.1 Criar a camada CSS global das paletas escura e clara e verificar que o modo escuro preserva os valores visuais atuais.
- [x] 1.2 Adicionar ao estado Reflex o modo ativo e a leitura segura da preferência armazenada no navegador; validar que valor inválido volta ao modo escuro.
- [x] 1.3 Implementar a persistência da preferência no navegador e verificar que ela permanece após recarregar e navegar entre rotas.
- [x] 1.4 Adicionar testes focados no estado inicial, na alternância e no tratamento de preferência inválida.

## 2. Controle na barra superior

- [x] 2.1 Inserir o botão de tema na barra compartilhada entre "Sair" e o bloco de usuário, sem alterar dimensões ou posições existentes dos demais elementos.
- [x] 2.2 Definir ícone, rótulo acessível e título coerentes com o modo que será ativado; verificar o foco pelo teclado.
- [x] 2.3 Conectar o botão à alternância global e validar a mudança imediata em uma página autenticada.
- [x] 2.4 Adicionar testes do botão e da alternância na composição da barra superior.

## 3. Paleta clara das telas principais

- [x] 3.1 Definir os tokens claros de fundo, superfície, texto, borda, vermelho de destaque e estados nas folhas globais.
- [x] 3.2 Aplicar os tokens claros à tela de login e validar contraste, foco e legibilidade.
- [x] 3.3 Aplicar os tokens claros ao dashboard e às páginas de acervo e exemplares, sem alterar estruturas existentes.
- [x] 3.4 Aplicar os tokens claros às páginas de clientes, locações, multas, relatórios e usuários.
- [x] 3.5 Atualizar inputs, selects, textareas, tabs, tabelas, cards, estados vazios, alertas e controles no mesmo conjunto de folhas.
- [x] 3.6 Adicionar ou ajustar testes visuais/unitários para confirmar que as telas usam o tema ativo e preservam seus comportamentos.

## 4. Modais e superfícies temporárias

- [x] 4.1 Auditar todos os diálogos e janelas abertas pela aplicação e mapear cores fixas usadas em fundo, borda, texto e ações.
- [x] 4.2 Converter essas cores fixas relevantes para os tokens do tema, preservando dimensões e hierarquia.
- [ ] 4.3 Validar recuperação de senha, cadastro/edição, bloqueios, baixa de exemplar, pagamento, estorno, abono e alteração de usuário nos dois modos.

## 5. Integração e validação final

- [x] 5.1 Revisar todas as folhas CSS por cores de estado, superfície e texto que não respondem ao tema.
- [x] 5.2 Executar os testes existentes e o compilador seco do Reflex para detectar regressões.
- [ ] 5.3 Percorrer todas as rotas autenticadas e a tela de login nos modos claro e escuro em desktop e celular.
- [x] 5.4 Validar que nenhuma regra de acesso, consulta ao Xano, conteúdo, navegação ou dimensão foi alterada pela troca de tema.
