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
