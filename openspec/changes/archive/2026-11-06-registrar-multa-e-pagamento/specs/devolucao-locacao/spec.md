# Spec Delta

## Purpose

Incluir a geração da multa por atraso na unidade atômica da devolução e apresentar a multa estimada e a gerada na interface.

## MODIFIED Requirements

### Requirement: Devolução e liberação do exemplar são atômicas

O sistema SHALL executar em uma única unidade atômica:
- criar o registro de devolução, com instante gerado pelo servidor e responsável;
- alterar o status da locação para `returned`;
- remover a ocupação vinculada ao identificador dessa locação;
- quando o atraso ultrapassar a tolerância da política de multas, criar a multa da locação.

A ocupação SHALL ser localizada pela locação, nunca apenas pelo exemplar. Ocupação ausente para uma locação `active` SHALL ser tratada como inconsistência e abortar sem efeitos. Falha antes do commit, inclusive no cálculo ou na gravação da multa, SHALL desfazer todas as alterações. A resposta SHALL conter `rental`, `fine` (a multa gerada, ou nulo quando não houver) e `audit_succeeded`. A repetição com a mesma chave SHALL devolver a mesma multa.

#### Scenario: Devolução confirmada
- **WHEN** a devolução é confirmada
- **THEN** a locação fica `returned`, existe um registro de devolução e o exemplar deixa de estar ocupado

#### Scenario: Devolução atrasada
- **WHEN** a devolução é confirmada após o vencimento acrescido da tolerância
- **THEN** a resposta inclui a multa `open` criada na mesma unidade atômica

#### Scenario: Falha entre gravações
- **WHEN** ocorre falha após iniciar a devolução e antes de confirmar a unidade atômica
- **THEN** a locação continua `active`, sem registro de devolução nem multa, e a ocupação permanece

#### Scenario: Ocupação inconsistente
- **WHEN** a locação está `active` mas não há ocupação com seu identificador
- **THEN** a operação é recusada sem alterar dados e sem liberar outro exemplar

### Requirement: Interface de devolução no detalhe da locação

O detalhe `/locacoes/{id}` SHALL oferecer "Registrar devolução" somente para locação `active`, com:
- resumo da locação;
- indicação de vencimento ultrapassado;
- quando estiver fora da tolerância, a multa estimada, calculada com a política vigente obtida do backend e rotulada como estimativa;
- confirmação explícita antes do envio.

A interface SHALL impedir envio duplicado enquanto houver tentativa em andamento, distinguir sucesso, conflito, falha, 429 e resultado desconhecido, e permitir repetir a mesma tentativa. Com gravações desabilitadas, SHALL exibir aviso neutro e manter a ação indisponível. Locação devolvida SHALL mostrar situação "Devolvida", data da devolução, responsável e se houve atraso, sem ação de escrita. Quando existir multa, SHALL mostrar o valor, a situação e um link para `/multas/{id}`. Após logout, troca de conta ou perda de autorização, respostas pendentes SHALL ser descartadas.

#### Scenario: Confirmação da devolução
- **WHEN** o usuário confirma a devolução de uma locação ativa
- **THEN** a tela apresenta o resultado persistido pelo backend, inclusive a multa gerada, e deixa de oferecer a ação

#### Scenario: Estimativa de multa
- **WHEN** a locação ativa está 49 horas após o vencimento, com a política padrão
- **THEN** a confirmação mostra a estimativa "R$ 9,00 (3 dias)", e o valor definitivo é o retornado pelo backend

#### Scenario: Resultado desconhecido
- **WHEN** a requisição expira ou a resposta é inválida
- **THEN** a tela informa resultado desconhecido e oferece repetir com a mesma chave ou atualizar o detalhe

#### Scenario: Locação já devolvida por outra pessoa
- **WHEN** o backend responde que a locação já foi devolvida
- **THEN** a tela informa o conflito e recarrega o detalhe com a devolução existente
