import re
import json
import requests


def test_csrf_header_exists():
    resp = requests.post('https://127.0.0.1/api/login',
                         data='{"user_name":"admin","password":"cAll2SecureAll","remember_me":false}', verify=False)
    session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
    resp.close()
    resp = requests.put('https://127.0.0.1/api/system/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa","last_name":"aaa","role_name":""}',
                        headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 403
    resp.close()
    resp = requests.get('https://127.0.0.1/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    csrf_token = resp.content
    resp.close()
    resp = requests.put('https://127.0.0.1/api/system/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa","last_name":"aaa","role_name":""}',
                        headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 200
    resp.close()
    resp = requests.get('https://127.0.0.1/api/system/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa","last_name":"aaa","role_name":""}',
                        headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 200
    user_id = [x['uuid'] for x in json.loads(resp.content) if x['first_name'] == 'aaa'][0]
    resp.close()
    resp = requests.put('https://127.0.0.1/api/system/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa","last_name":"aaa","role_name":""}',
                        headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 403
    resp = requests.delete('https://127.0.0.1/api/system/users/' + user_id,
                           headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 403
    resp = requests.get('https://127.0.0.1/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    csrf_token = resp.content
    resp.close()
    resp = requests.delete('https://127.0.0.1/api/system/users/' + user_id,
                           headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 200
    resp.close()
    resp = requests.delete('https://127.0.0.1/api/logout', headers={'Cookie': 'session=' + session}, verify=False)
    resp.close()
