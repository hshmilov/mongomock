"""
Script to automatically create a json file in the correct format for json_file adapter from a current adapter devices.

In order to run this:
1) Start empty axonius machine with only the adapter you want to mock
2) Add the credentials for the adapter
3) Run discovery and wait for it to finish (Successfully)
4) run the script inside venv and give it the adapter name (cisco_adapter) as first argument)
5) The output file is in the current directory with the name mock_mock.json

Good Luck
"""
import re
import json
import datetime
import sys
import requests
import pymongo


# pylint: disable=C0103, R1710
def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.strftime('%Y-%m-%d %H:%M:%S')


def get_fields_from_gui():
    resp = requests.post('https://127.0.0.1/api/login',
                         data='{"user_name":"admin","password":"cAll2SecureAll","remember_me":false}', verify=False)
    session = re.findall('session=(.*?);', resp.headers['Set-Cookie'])[0]
    resp.close()
    return requests.get('https://127.0.0.1/api/devices/fields', headers={'Cookie': 'session=' + session},
                        verify=False).text


def main(adapter_name):
    connection_line = 'mongodb://{user}:{password}@{addr}:{port}'.format(user='ax_user', password='ax_pass',
                                                                         addr='mongo.axonius.local', port=27017)
    client = pymongo.MongoClient(connection_line)
    raw_devices = list(client['aggregator']['devices_db'].find({}))
    raw_devices = [x['adapters'][0] for x in raw_devices]
    # pylint: disable=W0106
    [x.update(x['data']) for x in raw_devices]
    [x.pop('data') for x in raw_devices]
    for i, v in enumerate(raw_devices):
        v['id'] = f'device{i}'

    raw_data = json.loads(get_fields_from_gui())
    fields = [x['name'] for x in raw_data['generic']]
    fields = [x.replace('specific_data.data.', '') for x in fields]
    schema = []
    for i, x in enumerate(raw_data['specific'][adapter_name]):
        schema.append(x)
        schema[i]['name'] = schema[i]['name'].replace(f'adapters_data.{adapter_name}.', '')

    devices = {'devices': raw_devices, 'fields': fields, 'additional_schema': schema, 'raw_fields': []}

    with open('mock_mock.json', 'w') as fh:
        fh.write(json.dumps(devices, default=default))


if __name__ == '__main__':
    main(sys.argv[1])
