# CINEBYTE LOCADORA

Aplicação interna da locadora, com frontend em Python/Reflex e integrações de backend no Xano.

## Requisitos

- Python 3.14 compatível com o ambiente do projeto
- PowerShell no Windows
- Variáveis `XANO_AUTH_API_URL`, `XANO_CATALOG_API_URL`, `XANO_CUSTOMER_API_URL` e `XANO_EXEMPLAR_API_URL` configuradas no arquivo local `.env`
- `FRONTEND_BASE_URL` opcional; o padrão é `http://localhost:3000`

O `.env` não deve ser versionado. Nunca registre senhas, tokens ou valores reais das variáveis em documentação ou logs.

## Instalação

No PowerShell, a partir da raiz do repositório:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Verificação

Compile o frontend sem iniciar os servidores:

```powershell
.\.venv\Scripts\reflex.exe compile --dry
```

Execute todos os testes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

## Execução

Para o smoke test local com frontend e backend Reflex na mesma porta:

```powershell
.\.venv\Scripts\reflex.exe run --env prod --single-port
```

Abra `http://localhost:3000/login`. As rotas de recuperação permanecem disponíveis em `/recuperar-senha` e `/redefinir-senha`.

O login e a recuperação usam as integrações reais já existentes. Não há credenciais demonstrativas e a senha nunca deve ser persistida ou incluída em logs.

## Registro de locação

A change `registrar-locacao` acrescenta `/locacoes/nova` e a confirmação em
`/locacoes/{id}`, com seleção de cliente e exemplar reais. O backend de locações
está implantado no Xano `v1`; a interface precisa da base do grupo em
`XANO_RENTAL_API_URL`. Use `.env.example` como referência e preencha os valores
reais apenas no `.env` privado de cada ambiente.

Mantenha `XANO_RENTAL_WRITES_ENABLED=false` na interface e no Xano até concluir
a homologação. A variável do Xano deve ser configurada em Keys & Variables;
o importador parcial de XanoScript não a provisiona. Ausência de disponibilidade
não autoriza marcar exemplares como aptos sem conferência administrativa.

Os testes de integridade preparados em `scripts/verify_rental_integrity.py`
mostram o plano por padrão. `--execute` exige autorização e registros reais
indicados pelo operador, pois registra locações que permanecem no histórico.
Não há devolução neste incremento; exemplares alugados continuam ocupados.
A implantação e as pendências estão em
`openspec/changes/archive/2026-10-23-registrar-locacao/deployment.md`.
