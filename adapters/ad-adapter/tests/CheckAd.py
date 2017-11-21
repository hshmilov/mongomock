""" This file is not for CR"""

import requests
import json

url = 'http://127.0.0.1:5000'
#url = 'http://192.168.40.133:5000'

payload = dict()
payload['domain_name'] = 'DC=TestDomain,DC=test'
payload['admin_name'] = 'TestDomain\Administrator'
payload['admin_password'] = 'Password1'

print('0 Reseting the DC list')
r = requests.delete(url + '/dc')
print(r.text)
print('0.1 Change log level to debug')
r = requests.put(url + '/logger?level=debug')
print(r.text)
print('1 Getting version'
      )r = requests.get(url + '/version')
print(r.text)
print('2 getting list')
r = requests.get(url + '/dc')
print(r.text)
print('3 Adding DC with missing parameters (should fail)')
payload = dict()
payload['domain_name'] = 'DC=TestDomain,DC=test'
payload['admin_name'] = 'TestDomain\Administrator'
r = requests.post(url + '/dc/WIN-0HI4F5QHV2T', data=json.dumps(payload))
print(r.text)
print('3.1 Adding DC')
payload = dict()
payload['domain_name'] = 'DC=TestDomain,DC=test'
payload['admin_name'] = 'TestDomain\Administrator'
payload['admin_password'] = 'Password1'
r = requests.post(url + '/dc/WIN-0HI4F5QHV2T', data=json.dumps(payload))
print(r.text)
print('4 getting list again')
r = requests.get(url + '/dc')
print(r.text)
print('5 Adding same DC should fail')
r = requests.post(url + '/dc/WIN-0HI4F5QHV2T', data=json.dumps(payload))
print(r.text)
print('6 Getting devices from all DCs')
r = requests.get(url + '/device')
print(r.text)
print('6.1 Getting devices from this DC')
r = requests.get(url + '/dc/WIN-0HI4F5QHV2T/device')
print(r.text)
print('7 Reseting the DC list')
r = requests.delete(url + '/dc')
print(r.text)
print('8 DC list (should be empty)')
r = requests.get(url + '/dc')
print(r.text)
print('9 Adding DC with only read user')
payload = dict()
payload['domain_name'] = 'DC=TestDomain,DC=test'
payload['query_name'] = 'TestDomain\Administrator'
payload['query_password'] = 'Password1'
r = requests.post(url + '/dc/WIN-0HI4F5QHV2T', data=json.dumps(payload))
print(r.text)
print('10 getting list again')
r = requests.get(url + '/dc')
print(r.text)
print('11 getting only one dc')
r = requests.get(url + '/dc/WIN-0HI4F5QHV2T')
print(r.text)
print('12 Adding a bad DC')
r = requests.post(url + '/dc/bad-dc', data=json.dumps(payload))
print(r.text)
print('12.1 getting list again')
r = requests.get(url + '/dc')
print(r.text)
print('12.2 Getting devices from all dcs (one of them should fail)')
r = requests.get(url + '/device')
print(r.text)
