from typing import Iterable

from pymongo import MongoClient
from axonius.smart_json_class import SmartJsonClass
from axonius.utils import datetime
from mockingbird.commons.mock_network import MockNetwork, MockNetworkEntities
from mockingbird.mock_adapters import get_all_parsers


class MockManager:
    def __init__(self):
        # the initialization happens before uwsgi forks, but we need to connect afterwards, so we must use connect=False
        self.db = MongoClient('localhost', connect=False).mock_db

    def __update_times(self, data, delta: datetime.timedelta):
        if isinstance(data, datetime.datetime):
            return data + delta

        if isinstance(data, dict):
            return {key: self.__update_times(value, delta) for key, value in data.items()}

        if isinstance(data, list):
            return [self.__update_times(value, delta) for value in data]

        return data

    def __get_entities(self, entity, plugin_name, client_id, offset, limit, remove_raw):
        query = {'plugin_name': plugin_name, 'client_id': client_id}
        response = dict()
        response['total_count'] = self.db[entity].count_documents(query)
        response['data'] = []
        for doc in self.db[entity].find(query).skip(int(offset)).limit(int(limit)):
            delta_to_add = datetime.datetime.now() - doc['time']
            doc['data'] = self.__update_times(doc['data'], delta_to_add)
            if not remove_raw:
                doc['data']['raw'] = doc['data'].copy()
            response['data'].append(doc['data'])

        return response

    def get_devices(self, plugin_name, client_id, offset, limit, remove_raw=False):
        return self.__get_entities('devices', plugin_name, client_id, offset, limit, remove_raw)

    def get_users(self, plugin_name, client_id, offset, limit, remove_raw=False):
        return self.__get_entities('users', plugin_name, client_id, offset, limit, remove_raw)

    def delete_db(self):
        self.db.devices.delete_many({})
        self.db.users.delete_many({})

    def put_devices(self, devices: Iterable[SmartJsonClass], plugin_name, client_id='client_0'):
        devices = [{'plugin_name': plugin_name, 'client_id': client_id,
                    'data': data.to_dict(), 'time': datetime.datetime.now()} for data in devices]
        if devices:
            self.db.devices.insert_many(devices)

        return devices

    def put_users(self, users: Iterable[SmartJsonClass], plugin_name, client_id='client_0'):
        users = [{'plugin_name': plugin_name, 'client_id': client_id,
                  'data': data.to_dict(), 'time': datetime.datetime.now()} for data in users]
        if users:
            self.db.users.insert_many(users)

        return users

    def create_demo_from_network(self, network: MockNetwork):
        print('[+] Deleting current database')
        self.delete_db()

        for parser_con in get_all_parsers():
            parser = parser_con()
            print(f'[+] Parsing {parser.plugin_name}')
            self.put_devices(
                parser.parse_entities(MockNetworkEntities.MockNetworkDeviceEntity, network.get_devices()),
                parser.plugin_name
            )
            self.put_users(
                parser.parse_entities(MockNetworkEntities.MockNetworkUserEntity, network.get_users()),
                parser.plugin_name
            )

        print('[+] Done')
