import re
import json
import requests

from axonius.consts.gui_consts import PREDEFINED_ROLE_RESTRICTED


def test_csrf_header_exists():
    resp = requests.post('https://gui.axonius.local/api/login',
                         data='{"user_name":"admin","password":"cAll2SecureAll","remember_me":false}', verify=False)
    session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
    resp.close()
    resp = requests.get('https://gui.axonius.local/api/settings/roles/assignable_roles',
                        headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 200
    role_id = [x['value'] for x in json.loads(resp.content) if x['text'] == PREDEFINED_ROLE_RESTRICTED][0]
    resp.close()
    resp = requests.put('https://gui.axonius.local/api/settings/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa",'
                             f'"last_name":"aaa","role_id":"{role_id}"}}',
                        headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 403
    resp.close()
    resp = requests.get('https://gui.axonius.local/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    csrf_token = resp.content
    resp.close()
    resp = requests.put('https://gui.axonius.local/api/settings/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa",'
                             f'"last_name":"aaa","role_id":"{role_id}"}}',
                        headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 200
    resp.close()
    resp = requests.get('https://gui.axonius.local/api/settings/users',
                        headers={'Cookie': 'session=' + session}, verify=False)
    assert resp.status_code == 200
    user_id = [x['uuid'] for x in json.loads(resp.content) if x['first_name'] == 'aaa'][0]
    resp.close()
    resp = requests.put('https://gui.axonius.local/api/settings/users',
                        data='{"user_name":"aaa","password":"aaa","first_name":"aaa",'
                             f'"last_name":"aaa","role_id":"{role_id}"}}',
                        headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 403
    resp = requests.delete('https://gui.axonius.local/api/settings/users/' + user_id,
                           headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 403
    resp = requests.get('https://gui.axonius.local/api/csrf', headers={'Cookie': 'session=' + session}, verify=False)
    csrf_token = resp.content
    resp.close()
    resp = requests.delete('https://gui.axonius.local/api/settings/users/' + user_id,
                           headers={'Cookie': 'session=' + session, 'X-CSRF-TOKEN': csrf_token}, verify=False)
    assert resp.status_code == 200
    resp.close()
    resp = requests.delete('https://gui.axonius.local/api/logout', headers={'Cookie': 'session=' + session},
                           verify=False)
    resp.close()
