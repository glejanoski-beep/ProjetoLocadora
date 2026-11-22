# CINEBYTE LOCADORA

O CINEBYTE LOCADORA é um aplicativo web interno para gestão de uma locadora de filmes. Ele centraliza o atendimento operacional, o cadastro do acervo e dos clientes, o controle de exemplares físicos, locações, devoluções, multas, pagamentos e relatórios.

O sistema ajuda a equipe a consultar informações rapidamente, evitar locações incompatíveis e manter o histórico das operações. O público-alvo são administradores e funcionários internos da locadora.

## Funcionalidades principais

- Alternância entre tema claro e tema escuro.
- Login e recuperação de acesso por e-mail.
- Dashboard administrativo e operacional.
- Cadastro, consulta e edição de clientes.
- Cadastro e consulta de filmes.
- Cadastro, edição e baixa de exemplares físicos.
- Registro e consulta de locações.
- Registro de devoluções.
- Consulta e pagamento de multas.
- Estorno e abono de valores por administradores.
- Gerenciamento de contas internas, papéis e situação de acesso.
- Relatórios por período e ranking de filmes mais alugados.
- Temas claro e escuro aplicados às páginas e janelas da aplicação.

## Perfis de usuários

### Administrador

O perfil `admin` pode consultar e administrar o sistema, incluindo:

- cadastrar, editar e inativar clientes;
- cadastrar e editar filmes;
- cadastrar, editar, baixar e reativar exemplares;
- registrar locações e devoluções;
- registrar pagamentos;
- abonar ou estornar multas;
- gerenciar usuários;
- alterar o papel de outra conta;
- desativar ou reativar outra conta;
- visualizar relatórios.

### Funcionário

O perfil `member` pode executar funções operacionais autorizadas, incluindo:

- consultar clientes, filmes e exemplares;
- registrar locações;
- registrar devoluções;
- registrar pagamentos e multas conforme as regras disponíveis;
- consultar o dashboard e o histórico.

O perfil `member` não pode alterar papéis, desativar contas, cadastrar ou excluir registros administrativos e executar ajustes financeiros exclusivos de administrador.

## Acesso ao aplicativo

Neste momento, não há uma URL pública de deploy configurada no repositório. O aplicativo é executado localmente.

Com o ambiente configurado, acesse:

```text
http://localhost:3000/login
```

O acesso exige uma conta interna criada no Xano ou cadastrada pelo fluxo existente da aplicação.

### Recuperação de senha

Se ainda não tiver uma senha ou tiver esquecido a atual:

1. Abra a tela de login.
2. Selecione **Esqueci minha senha**.
3. Informe o e-mail da conta.
4. Solicite o link de redefinição.
5. Abra o link recebido e escolha uma nova senha.

O link leva à rota `/redefinir-senha`. Tokens expirados ou já utilizados não podem ser reutilizados.

## Execução local

### Pré-requisitos

- Python 3.14 compatível com o ambiente do projeto.
- PowerShell no Windows.
- Ambiente virtual Python.
- Variáveis Xano configuradas no arquivo `.env`.
- Conexão com a instância Xano configurada.

### Instalação

Na raiz do repositório:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Iniciar

```powershell
.\.venv\Scripts\reflex.exe run --env prod --single-port
```

Em seguida, abra `http://localhost:3000/login`.

### Verificar antes de entregar

```powershell
.\.venv\Scripts\reflex.exe compile --dry
.\.venv\Scripts\python.exe -m unittest discover -v
```

As credenciais e os valores reais das variáveis devem permanecer no `.env` local e não devem ser enviados ao GitHub.

## Manual de utilização

### 1. Entrar no sistema

1. Acesse `/login`.
2. Informe o e-mail da conta.
3. Informe a senha.
4. Selecione **Entrar**.

Após autenticação válida, o sistema abre o dashboard conforme o perfil da conta.

Se a conta estiver desativada ou o papel não estiver autorizado, o acesso não será concluído.

### 2. Alternar tema claro ou escuro

1. Na barra superior, localize o botão de tema entre **Sair** e o nome do usuário.
2. Selecione o botão para alternar.

O modo escuro preserva a apresentação escura existente. O modo claro usa superfícies claras e textos escuros. A preferência é mantida no navegador.

### 3. Consultar o dashboard

1. Selecione **Visão geral** na barra superior.
2. Consulte os indicadores do acervo, clientes, locações, multas e movimentação.
3. Administradores podem atualizar dados e visualizar o resumo completo.
4. Funcionários podem consultar os indicadores permitidos para seu perfil.

Não são exibidos dados fictícios. Quando uma consulta falhar ou não houver registros, a tela apresenta seu estado correspondente.

### 4. Cadastrar ou consultar clientes

1. Selecione **Clientes**.
2. Use a busca por nome ou CPF completo.
3. Selecione **Buscar** para consultar no servidor.
4. Selecione **Consultar** para abrir o cadastro.
5. Na tela de detalhe, consulte dados, locações, multas e pagamentos.

Somente administradores podem cadastrar ou editar clientes.

Para cadastrar:

1. Selecione a ação de cadastro.
2. Informe nome, CPF e pelo menos um contato: e-mail ou telefone.
3. Confirme o cadastro.

### 5. Cadastrar ou consultar filmes

1. Selecione **Acervo**.
2. Pesquise pelo título ou gênero.
3. Use **Buscar** para aplicar os filtros.
4. O status **Todos, Ativos ou Inativos** pode filtrar os filmes já carregados.

Somente administradores podem cadastrar ou editar filmes.

No cadastro ou na edição, informe título, gênero, ano, classificação indicativa e valor da locação. Um administrador também pode enviar ou remover a capa do filme na edição.

### 6. Gerenciar exemplares

1. Selecione **Exemplares**.
2. Consulte os filmes e seus identificadores físicos.
3. Use busca ou filtro para localizar uma cópia.
4. Para administrador, selecione um identificador para editar, dar baixa ou reativar o exemplar.

Somente administradores podem cadastrar exemplares.

Ao cadastrar:

1. Informe o identificador da cópia.
2. Selecione o filme.
3. Confirme.

Exemplares baixados ficam ocultos por padrão. Ative **Mostrar baixados** para consultá-los.

### 7. Criar uma locação

1. Selecione **Locações**.
2. A tela utiliza três etapas:
   - selecionar cliente;
   - selecionar exemplar;
   - informar vencimento e confirmar.
3. Selecione um cliente disponível.
4. Selecione um exemplar disponível.
5. Informe uma data de vencimento válida e futura.
6. Confirme a locação.

O sistema não permite continuar enquanto houver pendências na seleção. Clientes bloqueados ou inativos não podem ser escolhidos.

Após a confirmação, o registro aparece na seção de locações recentes e pode ser aberto pelo número.

A conferência administrativa de condição dos exemplares, quando disponível, deve ser utilizada antes da locação.

### 8. Consultar uma locação

1. Em **Locações**, utilize **Abrir locação pelo número**.
2. Informe um número inteiro positivo.
3. Confirme.

A tela de detalhe mostra cliente, exemplar, filme, retirada, vencimento, situação e responsável.

Locações vencidas são identificadas como “Vencimento ultrapassado”.

### 9. Registrar devolução

1. Abra o detalhe da locação.
2. Confirme a devolução conforme o fluxo disponível.
3. Informe a condição exigida pelo processo administrativo.
4. Aguarde a resposta do servidor.

O sistema registra a devolução e atualiza a disponibilidade do exemplar. Uma devolução atrasada pode gerar multa conforme a política vigente.

### 10. Consultar multas

1. Selecione **Multas**.
2. Utilize as abas:
   - Em aberto;
   - Quitadas;
   - Abonadas;
   - Todas.
3. Selecione uma multa para consultar o detalhe.

O detalhe mostra valor, pago, saldo, política aplicada, locação e histórico de pagamentos.

### 11. Registrar pagamento manual

1. Abra uma multa em aberto.
2. Selecione **Registrar pagamento**.
3. Confirme o valor, sem ultrapassar o saldo.
4. Escolha o meio:
   - dinheiro;
   - Pix;
   - cartão de débito;
   - cartão de crédito.
5. Confirme a operação.

O resultado esperado é a atualização do valor pago e do saldo sem criar histórico paralelo.

### 12. Estornar ou abonar

Somente administradores podem realizar estas ações.

Para estornar um pagamento:

1. Abra o detalhe da multa.
2. Selecione **Estornar** no pagamento confirmado.
3. Informe o motivo.
4. Confirme.

Para abonar saldo:

1. Abra uma multa em aberto.
2. Selecione **Abonar saldo**.
3. Informe o motivo.
4. Confirme.

Estornos e abonos são registrados em histórico. O sistema não apaga os registros originais.

### 13. Cadastrar novo usuário

Somente administradores podem criar contas internas.

1. Selecione **Usuários**.
2. Selecione **Novo usuário**.
3. Informe:
   - nome;
   - e-mail;
   - papel `Administrador` ou `Funcionário`.
4. Confirme.

A conta é criada ativa, sem senha inicial definida pelo administrador. O novo usuário deve selecionar **Esqueci minha senha** na tela de login e definir sua própria senha pelo link disponível.

### 14. Alterar papel ou situação de usuário

Somente administradores podem alterar outra conta.

1. Selecione **Usuários**.
2. Selecione uma conta diferente da própria.
3. Escolha o novo papel.
4. Escolha ativa ou desativada.
5. Informe o motivo.
6. Confirme.

Ao desativar, o sistema pede uma confirmação adicional.

A própria conta não pode ser alterada pela própria pessoa. Contas desativadas não podem entrar ou executar operações protegidas.

### 15. Consultar relatórios

Somente administradores podem abrir a página completa de relatórios.

1. Selecione **Relatórios**.
2. Escolha um período rápido ou datas manuais.
3. Selecione **Gerar relatório**.

O relatório apresenta locações no período, financeiro, situação atual e filmes mais alugados.

## Exemplos práticos

### Exemplo de cadastro de cliente

- Nome: Ana Maria Souza
- CPF: documento válido do cliente
- E-mail: `ana@example.com`
- Situação: Ativo
- Resultado: o cliente aparece na lista e fica disponível para nova locação.

### Exemplo de cadastro de filme

- Título: filme do catálogo
- Gênero: Ação
- Ano: ano válido
- Valor da locação: informado em reais
- Resultado: o filme aparece no Acervo e pode receber exemplares físicos.

### Exemplo de locação

1. Selecione Ana Maria Souza.
2. Selecione o exemplar disponível.
3. Informe o vencimento.
4. Confirme.

Resultado: o exemplar deixa de estar disponível, a locação fica ativa e aparece no histórico do cliente e na lista de locações.

### Exemplo de devolução atrasada

1. Abra uma locação vencida.
2. Confirme a devolução.
3. Consulte a multa gerada.

Resultado: a locação é encerrada, o exemplar volta à disponibilidade correspondente e uma multa pode ser criada conforme a regra vigente.

## Limitações conhecidas

### Deploy público

- Não existe URL pública de deploy configurada neste repositório.
- Atualmente o uso documentado é local em `http://localhost:3000`.
- A aplicação utiliza uma instância Reflex única em memória; reiniciar o processo pode exigir novo login.

### Pagamento por cartão com Asaas

A change `pagamento cartão asaas` foi implementada parcialmente no código e no backend, mas a homologação externa completa ainda não foi concluída.

Para concluir essa integração com segurança foi identificado que a aplicação precisa estar publicada em uma URL externa acessível pelo Asaas. Em `localhost`, o callback e o retorno do fluxo hospedado não podem representar o ambiente real utilizado pelo Asaas.

Ainda não foi realizada:

- confirmação externa de uma cobrança de teste;
- registro final da evidência de evento `PAID`;
- homologação de reconciliação ambígua e cancelamento;
- operação com a chave de produção.

Até essa publicação externa, o pagamento por cartão deve ser considerado não homologado.

### Outros limites

- Não há cadastro direto de usuário público na tela de funcionários: novas contas administrativas são criadas pela área `/usuarios`.
- A tela não oferece exclusão permanente de usuários.
- A conta criada não recebe uma senha padrão.
- E-mails de recuperação dependem da configuração de entrega do Xano.
- Locação e devolução podem depender da variável de escrita `XANO_RENTAL_WRITES_ENABLED`.
- Relatórios exigem perfil `admin`.
- O sistema não substitui autorização backend: a interface apenas organiza o acesso.
- O uso em escala horizontal pode exigir configuração adicional de gerenciamento de estado Reflex.

## Estrutura da aplicação

- Frontend: Reflex em Python.
- Backend: Xano.
- Scripts: XanoScript.
- Especificações: OpenSpec em `openspec/`.
- Tema claro e escuro: `assets/theme.css` e folhas específicas da interface.

## Suporte

Em caso de falha de autenticação, limite de requisições ou indisponibilidade do Xano:

1. Confirme que a conta está ativa.
2. Atualize a página.
3. Saia e entre novamente.
4. Aguarde o prazo informado pela tela antes de tentar novamente.
5. Verifique a configuração das URLs e credenciais do ambiente local.
