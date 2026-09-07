# Instruções do agente do ProjetoLocadora

- Responda e escreva a documentação em português do Brasil.
- Preserve nomes de arquivos, identificadores, comandos, nomes de APIs e sintaxe técnica no formato original quando necessário.

## Estrutura do repositório

- `xano/xano/` é a aplicação principal: uma exportação declarativa do Xano.
- `xano/xano/table/` define schemas e índices do banco de dados.
- `xano/xano/api/` contém grupos de API e stacks de endpoints; os nomes dos arquivos normalmente terminam com o verbo HTTP, como `login_POST.xs`.
- `xano/xano/function/` contém funções reutilizáveis do Xano.
- `xano/xano/addon/`, `xano/xano/ai/` e `xano/xano/workspace/` contêm add-ons, definições de IA e metadados do workspace.
- `.vscode/` é um projeto separado de agente em Python. A configuração e os testes estão documentados em [.vscode/README.md](../README.md).

## Regras para editar Xano

- Trate os arquivos `.xs` como recursos exportados do Xano, não como código comum da aplicação. Preserve os nomes dos recursos, nomes dos grupos de API, caminhos de funções, valores de `guid` e identificadores `canonical` das APIs, exceto quando a alteração criar ou renomear um recurso intencionalmente.
- Antes de renomear uma tabela, função, grupo de API ou rota, pesquise referências em todos os arquivos `.xs` e atualize toda a cadeia de dependências.
- Siga a sintaxe existente do Xano e os padrões dos arquivos próximos para `db.get`, `db.add`, `db.query`, `function.run`, autenticação, preconditions e objetos de resposta.
- Preserve tags e metadados dos recursos, exceto quando houver um motivo específico para alterá-los.
- Mantenha o comportamento de autenticação explícito: endpoints protegidos usam a convenção existente de `auth`, a identidade do usuário vem de `$auth.id`, e operações de senha ou token usam os primitives de segurança do Xano.
- Não exponha hashes de senha, tokens de redefinição ou outros segredos nas respostas ou nos metadados de logs de eventos. Revise os dados registrados ao alterar fluxos de autenticação.
- Os fluxos de e-mail e redefinição de senha dependem dos serviços Xano configurados, de `$env.$api_baseurl` e da rota existente do frontend. Não altere esses contratos sem uma razão clara.

## Validação

- Não há compilador, formatter, parser ou suíte de testes local para as exportações `.xs`. Valide a sintaxe e o comportamento comparando com recursos próximos e, quando possível, importando ou exercitando a alteração no Xano.
- Quando os exemplos próximos não forem suficientes, consulte a documentação oficial do XanoScript ou o Xano Developer MCP antes de inventar sintaxe, especialmente para queries de banco e function stacks.
- Para o projeto Python separado, use os comandos em [.vscode/README.md](../README.md): instale as dependências com `python -m pip install -r requirements.txt`, execute com `python -m agent_app` e rode os testes com `pytest` a partir de `.vscode/`.
- Mantenha as alterações focadas e evite reformatar arquivos de exportação gerados ou arquivos não relacionados do projeto Python inicial.
