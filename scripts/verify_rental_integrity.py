"""Plano por padrão. Execução remota somente com --execute e dados reais indicados.

Não cria clientes/filmes/exemplares nem apaga locações. Corridas bem-sucedidas
registram uma locação REAL, que deve corresponder a uma retirada autorizada.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import os
from uuid import uuid4


async def execute(args):
    from ProjetoLocadora.locacoes_client import (
        RentalError, _request, available_exemplars, create_rental, get_rental, reconcile_rental,
    )
    from ProjetoLocadora.xano_client import get_me_xano, list_customers_xano

    token_a = os.getenv("LOCADORA_VALIDATION_TOKEN_A", "")
    token_b = os.getenv("LOCADORA_VALIDATION_TOKEN_B", "")
    if not token_a or (args.scenario == "distinct-keys" and not token_b):
        raise ValueError("Configure os tokens privados de validação no ambiente.")
    a = await get_me_xano(token_a)
    if not a or a.get("is_active") is False or a.get("role") not in {"admin", "member"}:
        raise ValueError("Conta de validação sem acesso atual.")
    if args.scenario == "distinct-keys":
        b = await get_me_xano(token_b)
        if not b or b.get("is_active") is False or b.get("role") not in {"admin", "member"} or b.get("id") == a.get("id"):
            raise ValueError("A corrida de exemplares exige duas contas ativas diferentes.")
    # Checagens reais e somente de leitura antes de tentar registrar uma retirada.
    customer = None
    for page in range(1, 101):
        result = await list_customers_xano(token_a, page=page, per_page=20)
        customer = next((row for row in result["items"] if row["id"] == args.customer_id), None)
        if customer or page * 20 >= result["total"]:
            break
    if not customer or customer["status"] != "active" or customer["bloqueio_manual_ativo"]:
        raise ValueError("Cliente real não localizado ou não elegível.")
    exemplar = None
    for page in range(1, 101):
        result = await available_exemplars(token_a, page)
        exemplar = next((row for row in result["items"] if row["id"] == args.exemplar_id), None)
        if exemplar or page * 20 >= result["total"]:
            break
    if not exemplar:
        raise ValueError("Exemplar real não localizado entre os disponíveis.")

    payload = {"customer_id": args.customer_id, "exemplar_id": args.exemplar_id, "due_at": args.due_at, "operation_key": str(uuid4())}
    # Chave de correlação não é credencial; registrar antes do envio permite
    # reconciliar a operação mesmo se o processo ou a conexão falhar.
    print(f"Chave da conta {a['id']}: {payload['operation_key']}", flush=True)
    if args.scenario == "rollback":
        if a.get("role") != "admin" or not args.occupied_rental_id:
            raise ValueError("Rollback exige administrador e locação ativa já existente.")
        occupied = await get_rental(token_a, args.occupied_rental_id)
        if occupied["exemplar_id"] == args.exemplar_id:
            raise ValueError("Escolha outro exemplar já ocupado para provocar a falha real de índice.")
        # Endpoint temporário revisado em tests/xano_validation/rollback_POST.xs.
        # A primeira inserção usa os dados reais; a segunda colide com ocupação
        # existente. Um HTTP de erro sozinho NÃO prova que houve rollback.
        failure = False
        try:
            await _request(token_a, "POST", "locacoes-validacao/rollback", payload={**payload, "occupied_exemplar_id": occupied["exemplar_id"]})
        except RentalError as error:
            failure = error.category == "unknown"
        if not failure:
            raise ValueError("A falha de banco esperada não foi observada; resultado inconclusivo.")
        try:
            await reconcile_rental(token_a, payload["operation_key"])
        except RentalError as error:
            if error.category != "notfound":
                raise ValueError("Não foi possível confirmar a ausência da primeira inserção.") from None
        else:
            raise ValueError("Falha de rollback: locação persistiu. Desabilite as escritas e preserve o registro para correção auditada.")
        print("Primeira inserção ausente após a falha. Conferir request history: a causa deve ser o índice único da ocupação, não outra falha anterior.")
        print("Conferir também no Xano que não existe ocupação para o exemplar de teste e que a ocupação anterior foi preservada.")
        return

    second = dict(payload)
    if args.scenario == "distinct-keys":
        second["operation_key"] = str(uuid4())
    else:
        token_b = token_a
    print(f"Chave da segunda requisição: {second['operation_key']}", flush=True)
    results = await asyncio.gather(create_rental(token_a, payload), create_rental(token_b, second), return_exceptions=True)
    confirmed = [item[0] for item in results if isinstance(item, tuple)]
    if args.scenario == "same-key":
        passed = len(confirmed) == 2 and confirmed[0]["id"] == confirmed[1]["id"]
    else:
        passed = len(confirmed) == 1 and sum(isinstance(item, RentalError) and item.category == "conflict" for item in results) == 1
    # Resultado desconhecido não é considerado rollback nem aprovação.
    if not passed:
        raise ValueError("Corrida inconclusiva ou inválida. Consulte ambas as chaves na mesma conta antes de repetir.")
    for token, sent in ((token_a, payload), (token_b, second)):
        try:
            actual = await reconcile_rental(token, sent["operation_key"])
        except RentalError as error:
            if args.scenario != "distinct-keys" or error.category != "notfound":
                raise ValueError("Reconciliação não confirmou o resultado da corrida.") from None
        else:
            if actual["id"] != confirmed[0]["id"]:
                raise ValueError("Mais de uma locação identificada para o mesmo exemplar.")
    print(f"Resultado HTTP confirmado: locação real #{confirmed[0]['id']}. Verificar no Xano uma única ocupação vinculada e preservar o histórico.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("distinct-keys", "same-key", "rollback"), default="distinct-keys")
    parser.add_argument("--execute", action="store_true", help="Executa escritas reais somente depois de autorização explícita.")
    parser.add_argument("--customer-id", type=int)
    parser.add_argument("--exemplar-id", type=int)
    parser.add_argument("--due-at", help="Vencimento real ISO 8601 com offset explícito.")
    parser.add_argument("--occupied-rental-id", type=int)
    args = parser.parse_args()
    if not args.execute:
        print("Somente plano; nenhuma conexão realizada.")
        print("distinct-keys: duas contas diferentes, duas chaves e um exemplar; deve confirmar uma única locação real.")
        print("same-key: duas requisições da mesma conta/chave; ambas devem retornar o mesmo registro.")
        print("rollback: endpoint temporário admin deve falhar na segunda inserção por índice único; conferir ausência de locação/ocupação e causa real no request history.")
        return 0
    try:
        if not args.customer_id or args.customer_id < 1 or not args.exemplar_id or args.exemplar_id < 1 or not args.due_at:
            raise ValueError("Indique cliente, exemplar e vencimento reais autorizados.")
        due = datetime.fromisoformat(args.due_at.replace("Z", "+00:00"))
        if due.tzinfo is None or due <= datetime.now(timezone.utc):
            raise ValueError("Informe vencimento futuro com offset explícito.")
        args.due_at = due.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        asyncio.run(execute(args))
    except ValueError as error:
        print(str(error))  # Somente mensagens controladas deste script.
        return 1
    except Exception:
        print("Validação não concluída. Preserve os registros e consulte o resultado no Xano antes de repetir.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
