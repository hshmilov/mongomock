from typing import List

from pymongo import MongoClient
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter


class MockManager:
    def __init__(self):
        # the initialization happens before uwsgi forks, but we need to connect afterwards, so we must use connect=False
        self.db = MongoClient('localhost', connect=False).mock_db

    def __get_entities(self, entity, plugin_name, client_id, offset, limit):
        query = {'plugin_name': plugin_name, 'client_id': client_id}
        response = dict()
        response['total_count'] = self.db[entity].count_documents(query)
        response['data'] = []
        for doc in self.db[entity].find(query).skip(int(offset)).limit(int(limit)):
            response['data'].append(doc['data'])

        return response

    def get_devices(self, plugin_name, client_id, offset, limit):
        return self.__get_entities('devices', plugin_name, client_id, offset, limit)

    def get_users(self, plugin_name, client_id, offset, limit):
        return self.__get_entities('users', plugin_name, client_id, offset, limit)

    def delete_db(self):
        self.db.devices.delete_many({})
        self.db.users.delete_many({})

    def put_devices(self, devices: List[DeviceAdapter], plugin_name, client_id='client_0'):
        devices = [{'plugin_name': plugin_name, 'client_id': client_id, 'data': data.to_dict()} for data in devices]
        self.db.devices.insert_many(devices)

    def put_users(self, users: List[UserAdapter], plugin_name, client_id='client_0'):
        users = [{'plugin_name': plugin_name, 'client_id': client_id, 'data': data.to_dict()} for data in users]
        self.db.devices.insert_many(users)
