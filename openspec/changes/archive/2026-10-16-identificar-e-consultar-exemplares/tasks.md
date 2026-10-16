## 1. Persistência e operações Xano

- [x] 1.1 Definir e versionar no export local o modelo mínimo de exemplar, limitado ao identificador individual e à referência ao `id` de um filme, e verificar que não acrescenta campos de estoque, disponibilidade, situação ou localização.
- [x] 1.2 Garantir no banco a unicidade exata do identificador e implementar o cadastro validando no backend que o filme existe antes da gravação; verificar por testes/contratos que duplicidade e filme inexistente são recusados sem criar exemplar.
- [x] 1.3 Criar o grupo próprio de APIs Exemplares e as operações protegidas de consulta e cadastro, verificando `member` na consulta, `admin` no cadastro, resultado vazio válido e resposta que identifique o exemplar e seu filme.
- [x] 1.4 Integrar `Quick Start/log_event` ao cadastro confirmado com metadados mínimos e resposta explícita para falha parcial de auditoria; verificar que recusas prévias não são apresentadas como gravação bem-sucedida.
- [x] 1.5 Verificar o comportamento de unicidade sob gravações concorrentes por evidência de constraint e teste disponível; se o runtime Xano não estiver autorizado/disponível, registrar explicitamente essa limitação sem alegar validação integrada. A declaração da constraint foi verificada localmente; a concorrência real no runtime Xano permanece não verificada.

## 2. Integração Reflex–Xano

- [x] 2.1 Adicionar configuração independente para a URL do grupo Exemplares, seguindo o padrão de Authentication, Catálogo e Clientes; verificar erro claro quando ausente e que não reutiliza inadvertidamente outra URL de grupo.
- [x] 2.2 Implementar operações autenticadas de listagem e cadastro no cliente Xano existente; verificar contratos de URL/configuração, autenticação, associação filme-exemplar, duplicidade e erros de validação sem expor o token.
- [x] 2.3 Implementar em Reflex a consulta de exemplares com identificação do filme e formulário de cadastro visível somente a `admin`; verificar que `member` consulta sem controles de cadastro e recebe estados de vazio, erro e sucesso apropriados.

## 3. Documentação e validação

- [x] 3.1 Atualizar a documentação de domínio para registrar a fronteira implementada de identificação e associação dos exemplares, sem antecipar disponibilidade, estoque, locações ou atributos não definidos; verificar consistência com as especificações.
- [x] 3.2 Executar `openspec validate identificar-e-consultar-exemplares --strict` e as suítes/testes locais relevantes de XanoScript, cliente e Reflex; revisar o diff para confirmar que não foram alterados nem publicados recursos remotos do Xano.
