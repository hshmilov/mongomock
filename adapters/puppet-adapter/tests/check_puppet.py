""" This file is not for CR"""

import requests
import json

url = 'http://127.0.0.1:5000'

payload = dict()
payload['user_name'] = 'puppet'
payload['password'] = 'puppet'


print('1 Getting version')
r = requests.get(url + '/version')
print('2 getting list')
r = requests.get(url + '/puppet')
print(r.text)
print('3 Adding puppet')
r = requests.post(url + '/puppet/puppet', data=json.dumps(payload))
print(r.text)
print('4 getting list again')
r = requests.get(url + '/puppet')
print(r.text)
print('5 Adding same puppet should fail')
r = requests.post(url + '/puppet/puppet', data=json.dumps(payload))
print(r.text)
print('6 Getting devices from all Puppet Servers')
r = requests.get(url + '/device')
print(r.text)
print('6.1 Getting devices from this Puppet Servers')
r = requests.get(url + '/puppet/puppet/device')
print(r.text)
print('7 Reseting the Puppet Servers list')
r = requests.delete(url + '/puppet')
print(r.text)
print('8 Puppet Servers list (should be empty)')
r = requests.get(url + '/puppet')
print(r.text)
print('9 Adding Puppet Server')
r = requests.post(url + '/puppet/puppet', data=json.dumps(payload))
print(r.text)
print('10 getting list again')
r = requests.get(url + '/puppet')
print(r.text)
print('11 getting only one puppet')
r = requests.get(url + '/puppet/puppet')
print(r.text)
print('12 Adding a bad puppet')
r = requests.post(url + '/puppet/bad-puppet', data=json.dumps(payload))
print(r.text)
print('12 Getting devices from all Puppet Servers (one of them should fail)')
r = requests.get(url + '/device')
print(r.text)
