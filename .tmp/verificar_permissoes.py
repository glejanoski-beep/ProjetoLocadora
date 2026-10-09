import asyncio
import json
import secrets
import subprocess
from pathlib import Path
import httpx

class PacedClient(httpx.AsyncClient):
    async def request(self, *args, **kwargs):
        for attempt in range(5):
            await asyncio.sleep(1.5)
            response = await super().request(*args, **kwargs)
            if response.status_code != 429:
                return response
            await asyncio.sleep(20)
        return response

async def main():
    base = 'https://x8ki-letl-twmt.n7.xano.io/api:_jhd1WGf'
    events = 'https://x8ki-letl-twmt.n7.xano.io/api:rCeXfhqR'
    results = []
    credentials_reader = "const fs=require('fs'),os=require('os'),path=require('path');const yaml=require('C:/Users/Lejanoski/AppData/Roaming/npm/node_modules/@xano/cli/node_modules/js-yaml');const p=yaml.load(fs.readFileSync(path.join(os.homedir(),'.xano/credentials.yaml'),'utf8')).profiles['locadora-permissoes'];process.stdout.write(JSON.stringify(p));"
    profile = json.loads(subprocess.run(['node', '-e', credentials_reader], capture_output=True, text=True, check=True).stdout)
    meta = profile['instance_origin'] + '/api:meta/workspace/149184'
    meta_headers = {'Authorization': 'Bearer ' + profile['access_token']}
    def check(name, passed, **details):
        results.append(dict(caso=name, aprovado=bool(passed), **details))
        Path('.tmp/permissoes-resultados.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print(name + ': ' + ('OK' if passed else 'FALHOU'), flush=True)
    async with PacedClient(timeout=30) as client:
        r = await client.get(meta + '/table', headers=meta_headers)
        r.raise_for_status()
        tables = r.json()
        tables = tables.get('items',[]) if isinstance(tables,dict) else tables
        table_id = next(x['id'] for x in tables if x['name'] == 'user')
        content = meta + '/table/' + str(table_id) + '/content'
        r = await client.get(content, headers=meta_headers, params={'per_page':100})
        r.raise_for_status()
        existing = r.json()
        existing = existing.get('items',[]) if isinstance(existing,dict) else existing
        baseline = {x['id']:(x.get('role'),x.get('is_active')) for x in existing}
        async def patch(uid, **updates):
            r = await client.post(content + '/bulk/patch', headers=meta_headers, json={'items':[{'row_id':str(uid),'updates':updates}]})
            r.raise_for_status()
            assert r.json().get('success_total') == 1
        async def run_role(uid, role):
            r = await client.post(meta + '/function/run', headers=meta_headers, json={'branch':'v1', 'name':'Quick Start/enforce_role', 'input':{'user_id':uid,'required_role':role}})
            r.raise_for_status()
            body = r.json()
            nested = body.get('result')
            return body.get('status') == 'ok' and not (isinstance(nested,dict) and nested.get('status') == 'exception')
        for previous in existing:
            if previous.get('name') == 'Teste permissoes descartavel' and previous.get('email','').startswith('teste-permissoes-') and previous.get('email','').endswith('@example.invalid'):
                await patch(previous['id'], role='member',is_active=False)
                baseline[previous['id']] = ('member',False)
        for route, method in [('/auth/me', 'GET'), ('/reset/update_password', 'POST'), ('/message/send_welcome_email', 'POST')]:
            r = await client.request(method, base + route, json={'password': 'TestOnly123!', 'confirm_password': 'TestOnly123!', 'user_id': 0} if method == 'POST' else None)
            check('sem autenticacao ' + route, r.status_code in (401, 403), status=r.status_code)
        r = await client.get(events + '/logs/user/my_events')
        check('sem autenticacao eventos', r.status_code in (401, 403), status=r.status_code)
        email = 'teste-permissoes-' + secrets.token_hex(6) + '@example.invalid'
        password = secrets.token_urlsafe(24) + 'Aa1!'
        r = await client.post(base + '/auth/signup', json={'name':'Teste permissoes descartavel', 'email':email, 'password':password, 'role':'admin'})
        check('cadastro publico', r.status_code == 200, status=r.status_code)
        if r.status_code == 200:
            payload = r.json()
            uid = payload['user_id']
            headers = {'Authorization':'Bearer ' + payload['authToken']}
            r = await client.get(base + '/auth/me', headers=headers)
            check('member ativo e promocao manipulada recusada', r.status_code == 200 and r.json().get('role') == 'member', status=r.status_code, usuario_teste_id=uid)
            r = await client.get(events + '/logs/user/my_events', headers=headers)
            check('eventos filtrados por usuario', r.status_code == 200 and all(x.get('user_id') == uid for x in r.json()), status=r.status_code)
            r = await client.post(base + '/message/send_welcome_email', headers=headers, json={'user_id':uid})
            check('member recusado antes de envio', r.status_code in (401,403), status=r.status_code)
            r = await client.get(events + '/logs/user/my_events', headers=headers)
            logs = r.json() if r.status_code == 200 else []
            denied = [x for x in logs if x.get('action') == 'authorization_denied']
            check('auditoria identifica member sem segredos', any(x.get('user_id') == uid and x.get('metadata',{}).get('result') == 'denied_role:admin' for x in denied) and all(set(x.get('metadata',{})) <= {'result','resource_type','resource_id'} for x in denied))
            check('sem evento de envio', not any(x.get('action') == 'welcome_email_sent' for x in logs))
            new_password = secrets.token_urlsafe(24) + 'Aa1!'
            r = await client.post(base + '/reset/update_password', headers=headers, json={'password':new_password, 'confirm_password':new_password})
            check('member ativo altera senha descartavel', r.status_code == 200, status=r.status_code)
            r = await client.post(base + '/auth/login', json={'email':email, 'password':new_password})
            check('login com nova senha', r.status_code == 200, status=r.status_code)
            r = await client.post(base + '/auth/login', json={'email':email, 'password':password})
            check('senha anterior recusada', r.status_code in (401,403), status=r.status_code)
            check('runner member permite member', await run_role(uid, 'member'))
            check('runner member recusa admin', not await run_role(uid, 'admin'))
            check('runner recusa papel minimo invalido', not await run_role(uid, 'invalid'))
            check('runner recusa usuario inexistente', not await run_role(0, 'member'))
            await patch(uid, role='admin')
            for role in ['member','admin']:
                check('runner admin permite ' + role, await run_role(uid, role))
            r = await client.get(base + '/auth/me', headers=headers)
            check('admin ativo consulta identidade com token anterior', r.status_code == 200 and r.json().get('role') == 'admin', status=r.status_code)
            r = await client.get(events + '/logs/user/my_events', headers=headers)
            check('admin ativo consulta eventos', r.status_code == 200 and all(x.get('user_id') == uid for x in r.json()), status=r.status_code)
            await patch(uid, is_active=False)
            for route, method, route_base, data in [('/auth/me','GET',base,None),('/logs/user/my_events','GET',events,None),('/message/send_welcome_email','POST',base,{'user_id':uid}),('/reset/update_password','POST',base,{'password':'Unexpected123!','confirm_password':'Unexpected123!'})]:
                r = await client.request(method, route_base + route, headers=headers, json=data)
                check('admin desativado token anterior ' + route, r.status_code in (401,403), status=r.status_code)
            check('runner recusa desativado', not await run_role(uid, 'member'))
            await patch(uid, role='member')
            for route, route_base in [('/auth/me',base),('/logs/user/my_events',events)]:
                r = await client.get(route_base + route, headers=headers)
                check('member desativado token anterior ' + route, r.status_code in (401,403), status=r.status_code)
            await patch(uid, is_active=True)
            r = await client.post(base + '/auth/login', json={'email':email,'password':new_password})
            check('recusa de senha desativada preserva senha', r.status_code == 200, status=r.status_code)
            await patch(uid, role=None)
            check('runner recusa papel ausente', not await run_role(uid, 'member'))
            r = await client.get(base + '/auth/me', headers=headers)
            check('API recusa papel ausente', r.status_code in (401,403), status=r.status_code)
            await patch(uid, role='member')
            # A coluna bool nao aceita null em todos os planos; nao mudar schema.
            try:
                await patch(uid, is_active=None)
                r = await client.get(content + '/' + str(uid), headers=meta_headers)
                legacy = r.json().get('is_active') is None
                check('estado legado sem valor', legacy and await run_role(uid,'member'))
            finally:
                await patch(uid, is_active=True)
            r = await client.get(events + '/logs/user/my_events', headers=headers)
            logs = r.json() if r.status_code == 200 else []
            check('recusas sem evento operacional de envio', not any(x.get('action') == 'welcome_email_sent' for x in logs))
            denied = [x for x in logs if x.get('action') == 'authorization_denied']
            check('auditoria de inatividade e papel ausente', {'denied_inactive','denied_unknown_role'} <= {x.get('metadata',{}).get('result') for x in denied})
            check('auditoria minima em todas recusas', all(x.get('user_id') == uid and set(x.get('metadata',{})) <= {'result','resource_type','resource_id'} for x in denied))
            await patch(uid, role='member',is_active=False)
            r = await client.get(content, headers=meta_headers, params={'per_page':100})
            current = r.json()
            current = current.get('items',[]) if isinstance(current,dict) else current
            check('papeis e estados preexistentes preservados', all(baseline.get(x['id']) == (x.get('role'),x.get('is_active')) for x in current if x['id'] in baseline))
    Path('.tmp/permissoes-resultados.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))

asyncio.run(main())
