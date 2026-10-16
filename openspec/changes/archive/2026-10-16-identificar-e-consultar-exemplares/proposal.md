## Why

O domínio prevê cópias físicas individualizadas, mas o projeto ainda não possui uma capacidade implementada para cadastrá-las e consultá-las. Sem essa capacidade, não é possível identificar cada exemplar, garantir sua associação a um filme persistido nem oferecer consulta autorizada desse vínculo.

## What Changes

- Introduzir a capability `exemplares` para identificar e consultar cópias físicas associadas a filmes.
- Permitir o cadastro de exemplares somente por `admin` e a consulta por `member`, sempre com autorização validada no backend.
- Exigir que a referência informada corresponda a um filme existente antes de persistir o exemplar.
- Garantir a unicidade do identificador no backend/banco de dados, inclusive diante de gravações concorrentes; uma validação somente na interface não atende ao requisito.
- Comparar identificadores pelo valor exato informado, sem normalizar espaços ou caixa.
- Fazer a consulta apresentar cada exemplar e o filme ao qual pertence, sem confundir filme com cópia física.
- Acrescentar à auditoria segura o registro mínimo do cadastro administrativo de exemplares, conforme os padrões existentes.
- Organizar as operações em grupo Xano próprio de Exemplares, com URL independente na integração Reflex–Xano.
- Restringir a mudança aos requisitos de identificação, associação, manutenção e consulta; não definir campos adicionais, formato de identificador, rotas ou payloads sem evidência ou decisão.

## Capabilities

### New Capabilities

- `exemplares`: cadastro administrativo e consulta autorizada de exemplares físicos associados a filmes.

### Modified Capabilities

- `auditoria-segura`: estabelecer eventos mínimos de auditoria para o cadastro administrativo de exemplares.

## Impact

- Xano/XanoScript: nova representação persistida de exemplares e grupo próprio de operações protegidas, com integridade de unicidade e validação da referência ao filme antes da gravação.
- Reflex: consulta e controles de manutenção integrados aos padrões existentes de estado, navegação e cliente autenticado do Xano; a interface não substitui a autorização do backend.
- Especificações: nova capability de exemplares e delta de auditoria; a política existente `acesso-seguro` já determina consulta por `member` e manutenção de cadastros por `admin`, sem necessidade de alterá-la.
- Verificação: cobrir duplicidade, referência inválida sem gravação, identificação do filme na consulta e autorização de ambos os papéis. A change não autoriza chamadas, alterações ou publicação no Xano remoto.
- Não fazem parte desta change edição ou exclusão de exemplares, locação, disponibilidade, reserva, movimentação ou controle de estoque, nem mudanças ao cadastro de filmes.

## Questões de modelagem a resolver antes da implementação

- O identificador será comparado exatamente como informado, sem normalização de espaços ou caixa; o projeto não define formato nem outros tratamentos do valor, que permanecem fora desta change.
- O domínio cita situação, localização e datas como informações possíveis do exemplar, mas os critérios desta change não definem seus campos nem comportamentos. Eles não devem ser acrescentados ao modelo desta change sem decisão adicional.

Essas questões não impedem especificar os comportamentos de identificação, vínculo, autorização e consulta exigidos; delimitam decisões técnicas/de domínio que não devem ser presumidas durante a implementação.
